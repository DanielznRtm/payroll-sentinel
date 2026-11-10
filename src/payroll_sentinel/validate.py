"""Validate payroll submissions before they enter the salary benchmark.

Two layers:

1. Deterministic rules (one row at a time): required fields, duplicated IDs,
   impossible dates, minimum wage proportional to weekly hours, bonus ratio.
2. Statistical checks (the whole benchmark at once): each salary is compared
   with every other company's salaries for the same (family, level). Three
   detectors vote - robust z-score, IQR fence and Isolation Forest - and a
   row is flagged when at least two agree (majority vote ensemble).

Every issue carries a probable cause and a severity:
    block -> row cannot enter the benchmark until fixed
    warn  -> row enters only after human review
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from .taxonomy import FULL_TIME_HOURS, LEVEL_ORDINAL, REFERENCE_DATE, legal_min_wage

DECIMAL_SHIFT_CEILING = 300.0   # a monthly salary below this is a typo, not a wage
BONUS_RATIO_LIMIT = 1.5         # annual bonus > 1.5x annual base salary
MIN_GROUP_SIZE = 15             # minimum peers to compare against
Z_LIMIT = 3.5
IQR_K = 1.5


@dataclass
class ValidationResult:
    issues: pd.DataFrame        # one row per issue
    records: pd.DataFrame       # one row per record, with status and detector votes
    companies: pd.DataFrame     # one row per submitting company


def _issue(row_id, company_id, employee_id, check, cause, severity, message):
    return {"row_id": row_id, "company_id": company_id, "employee_id": employee_id,
            "check": check, "cause": cause, "severity": severity, "message": message}


def rule_checks(df: pd.DataFrame) -> list[dict]:
    issues: list[dict] = []
    title = df["job_title"].fillna("").astype(str).str.strip()
    salary = pd.to_numeric(df["monthly_salary"], errors="coerce")
    bonus = pd.to_numeric(df["annual_bonus"], errors="coerce").fillna(0)
    hire = pd.to_datetime(df["hire_date"], errors="coerce")
    dup = df.duplicated(["company_id", "employee_id"], keep=False)
    ref = pd.Timestamp(REFERENCE_DATE)

    for i, r in df.iterrows():
        base = (r["row_id"], r["company_id"], r["employee_id"])
        if pd.isna(salary[i]):
            issues.append(_issue(*base, "required_fields", "missing_salary", "block",
                                 "Monthly salary is empty."))
        if title[i] == "":
            issues.append(_issue(*base, "required_fields", "missing_title", "block",
                                 "Job title is empty."))
        if dup[i]:
            issues.append(_issue(*base, "unique_id", "duplicate_id", "block",
                                 f"Employee ID {r['employee_id']} appears more than once."))
        if pd.isna(hire[i]) or hire[i] > ref or hire[i].year < 1950:
            issues.append(_issue(*base, "dates", "future_hire_date", "block",
                                 f"Hire date {r['hire_date']} is impossible for a {REFERENCE_DATE} cut-off."))
        s = salary[i]
        if pd.notna(s):
            if s < DECIMAL_SHIFT_CEILING:
                issues.append(_issue(*base, "salary_range", "decimal_shift", "block",
                                     f"Salary R$ {s:,.2f} looks like a decimal separator error "
                                     f"(e.g. 8.500,00 read as 8,5)."))
            elif r["contract_type"] == "CLT" and s < legal_min_wage(r["weekly_hours"]):
                floor = legal_min_wage(r["weekly_hours"])
                issues.append(_issue(*base, "min_wage", "below_min_wage", "block",
                                     f"R$ {s:,.2f} is below the legal minimum of R$ {floor:,.2f} "
                                     f"for {r['weekly_hours']}h/week."))
            if s >= DECIMAL_SHIFT_CEILING and bonus[i] > BONUS_RATIO_LIMIT * 12 * s:
                issues.append(_issue(*base, "bonus_ratio", "bonus_outlier", "warn",
                                     f"Annual bonus is {bonus[i] / (12 * s):.1f}x the annual base salary."))
    return issues


def _diagnose(ratio: float) -> tuple[str, str]:
    """Probable cause from salary / peer-median ratio."""
    if 6.0 <= ratio <= 20.0:
        return "annual_as_monthly", "block"
    if ratio >= 2.0 or ratio <= 0.5:
        return "level_salary_mismatch", "warn"
    return "statistical_outlier", "warn"


def statistical_checks(df: pd.DataFrame, families: pd.Series, levels: pd.Series,
                       seed: int = 0) -> tuple[pd.DataFrame, list[dict]]:
    salary = pd.to_numeric(df["monthly_salary"], errors="coerce")
    eligible = salary.ge(DECIMAL_SHIFT_CEILING) & families.notna() & levels.notna()
    # Compare part-time contracts on a full-time-equivalent basis (40h and 44h are both full time).
    hours = pd.to_numeric(df["weekly_hours"], errors="coerce").fillna(FULL_TIME_HOURS)
    fte = salary * np.where(hours < 36, FULL_TIME_HOURS / hours.clip(lower=1), 1.0)
    work = pd.DataFrame({"row_id": df["row_id"], "log_s": np.log(fte.where(eligible)),
                         "family": families, "level": levels})[eligible].copy()
    work["group"] = work["family"].astype(str) + "/" + work["level"].astype(str)
    sizes = work.groupby("group")["log_s"].transform("size")
    work = work[sizes >= MIN_GROUP_SIZE].copy()

    g = work.groupby("group")["log_s"]
    work["median"] = g.transform("median")
    work["resid"] = work["log_s"] - work["median"]
    mad = work.groupby("group")["resid"].transform(lambda x: np.median(np.abs(x)))
    work["z"] = 0.6745 * work["resid"] / mad.replace(0, np.nan)
    q1, q3 = g.transform(lambda x: x.quantile(0.25)), g.transform(lambda x: x.quantile(0.75))
    iqr = q3 - q1

    work["vote_z"] = work["z"].abs() > Z_LIMIT
    work["vote_iqr"] = (work["log_s"] < q1 - IQR_K * iqr) | (work["log_s"] > q3 + IQR_K * iqr)

    hire = pd.to_datetime(df.loc[work.index, "hire_date"], errors="coerce")
    tenure = ((pd.Timestamp(REFERENCE_DATE) - hire).dt.days / 365).clip(0, 50).fillna(0)
    bonus = pd.to_numeric(df.loc[work.index, "annual_bonus"], errors="coerce").fillna(0)
    features = np.column_stack([
        work["resid"], work["level"].map(LEVEL_ORDINAL),
        np.log1p(bonus / (12 * np.exp(work["log_s"]))), tenure,
    ])
    if len(work):
        forest = IsolationForest(n_estimators=300, contamination=0.03, random_state=seed)
        work["vote_iforest"] = forest.fit_predict(features) == -1
    else:  # no peer group is large enough (e.g. a small file): nothing to compare against
        work["vote_iforest"] = False
    work["votes"] = work[["vote_z", "vote_iqr", "vote_iforest"]].sum(axis=1)
    work["flag_ensemble"] = work["votes"] >= 2
    work["peer_ratio"] = np.exp(work["resid"])

    issues = []
    for i, r in work[work["flag_ensemble"]].iterrows():
        cause, severity = _diagnose(r["peer_ratio"])
        peers = int(sizes[i])
        msg = (f"Salary is {r['peer_ratio']:.2f}x the median of {peers} peers "
               f"({r['group']}, median R$ {np.exp(r['median']):,.0f}). Votes: {int(r['votes'])}/3.")
        if cause == "annual_as_monthly":
            msg += " Looks like an annual value typed in the monthly field."
        elif cause == "level_salary_mismatch":
            msg += " Check whether the title/level is right."
        issues.append(_issue(r["row_id"], df.at[i, "company_id"], df.at[i, "employee_id"],
                             "peer_comparison", cause, severity, msg))
    return work, issues


def validate(df: pd.DataFrame, norm: pd.DataFrame, block_share_to_reject: float = 0.05,
             seed: int = 0) -> ValidationResult:
    """Run all checks. `norm` has columns family, level, source (index aligned with df)."""
    issues = rule_checks(df)
    work, stat_issues = statistical_checks(df, norm["family"], norm["level"], seed=seed)
    issues += stat_issues
    for i in df.index[norm["family"].isna() & df["job_title"].fillna("").astype(str).str.strip().ne("")]:
        issues.append(_issue(df.at[i, "row_id"], df.at[i, "company_id"], df.at[i, "employee_id"],
                             "title_mapping", "unmapped_title", "warn",
                             f"Title '{df.at[i, 'job_title']}' did not map to any job family; "
                             "excluded from peer comparison."))
    issues_df = pd.DataFrame(issues, columns=["row_id", "company_id", "employee_id", "check",
                                              "cause", "severity", "message"])

    records = df[["row_id", "company_id", "employee_id", "job_title"]].copy()
    records["family"], records["level"] = norm["family"], norm["level"]
    votes = work[["vote_z", "vote_iqr", "vote_iforest", "flag_ensemble", "peer_ratio"]]
    records = records.join(votes)
    sev = issues_df.groupby("row_id")["severity"].agg(set)
    records["status"] = records["row_id"].map(
        lambda r: "block" if "block" in sev.get(r, set()) else ("warn" if r in sev.index else "ok"))

    companies = records.groupby("company_id").agg(
        rows=("row_id", "size"),
        blocked=("status", lambda s: int((s == "block").sum())),
        warnings=("status", lambda s: int((s == "warn").sum())),
    )
    companies["blocked_share"] = companies["blocked"] / companies["rows"]
    companies["decision"] = np.where(
        companies["blocked_share"] > block_share_to_reject, "REJECT - ask company to resubmit",
        np.where(companies["blocked"] > 0, "ACCEPT without blocked rows", "ACCEPT"))
    return ValidationResult(issues_df, records, companies.reset_index())
