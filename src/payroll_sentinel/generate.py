"""Synthetic payroll submissions with planted, labeled errors.

Each company submits a payroll file to the salary benchmark. Most rows are
clean; a known fraction carries one planted error. The generator returns the
submitted data (what the validator sees) and a ground-truth table (what the
evaluator uses).

The data also contains *legitimate* rows that look suspicious on purpose:
interns paid below the minimum wage (allowed: internship stipends are not
bound by it) and part-time CLT contracts paid below the full-time minimum but
above the proportional one. A good validator must not flag them.
"""

from __future__ import annotations

import datetime as dt
import unicodedata

import numpy as np
import pandas as pd

from .taxonomy import (CITIES, FAMILIES, LEVEL_MULTIPLIER, LEVELS, NO_INTERN_FAMILIES,
                       REFERENCE_DATE, SECTORS, legal_min_wage)

LEVEL_WEIGHTS = [0.08, 0.25, 0.32, 0.25, 0.10]

LEVEL_TEMPLATES = {
    "intern": ["Estágio - {b}", "Estagiário(a) | {b}", "{b} (Estágio)", "Intern - {b}"],
    "junior": ["{b} Jr", "{b} Jr.", "{b} Júnior", "{b} Junior", "{b} I", "Junior {b}"],
    "mid": ["{b} Pleno", "{b} Pl", "{b} II", "{b}", "{b}"],
    "senior": ["{b} Sr", "{b} Sr.", "{b} Sênior", "{b} Senior", "{b} III", "Senior {b}"],
    "lead": ["{b} Especialista", "Líder {b}", "{b} Lead", "{b} IV", "Staff {b}"],
}
NOISE_SUFFIXES = [" - SP", " | Squad Pagamentos", " (Remoto)", " - Turno B", " / Unidade 2"]

# Planted error types -> share of records. At most one error per record.
ERROR_RATES = {
    "missing_salary": 0.004,
    "missing_title": 0.004,
    "below_min_wage": 0.006,
    "decimal_shift": 0.006,
    "annual_as_monthly": 0.008,
    "bonus_outlier": 0.006,
    "duplicate_id": 0.006,   # rows involved (planted in pairs)
    "future_hire_date": 0.004,
    "level_salary_mismatch": 0.010,
}
SEVERITY = {
    "missing_salary": "block", "missing_title": "block", "below_min_wage": "block",
    "decimal_shift": "block", "annual_as_monthly": "block", "duplicate_id": "block",
    "future_hire_date": "block", "bonus_outlier": "warn", "level_salary_mismatch": "warn",
}


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def render_title(family: str, level: str, rng: np.random.Generator) -> tuple[str, bool]:
    """Build a messy raw job title. Returns (title, is_hard_variant)."""
    fam = FAMILIES[family]
    hard = rng.random() < 0.25
    base = str(rng.choice(fam["hard"] if hard else fam["easy"]))
    title = str(rng.choice(LEVEL_TEMPLATES[level])).format(b=base)
    if rng.random() < 0.10:
        title += str(rng.choice(NOISE_SUFFIXES))
    r = rng.random()
    if r < 0.08:
        title = title.lower()
    elif r < 0.13:
        title = title.upper()
    if rng.random() < 0.15:
        title = _strip_accents(title)
    if rng.random() < 0.05:
        title = "  " + title.replace(" ", "  ", 1) + " "
    return title, hard


def _clean_records(rng: np.random.Generator, n_companies: int) -> pd.DataFrame:
    rows = []
    city_names = list(CITIES)
    for c in range(n_companies):
        company_id = f"EMP{c + 1:03d}"
        sector = str(rng.choice(list(SECTORS)))
        families = list(SECTORS[sector])
        fam_w = np.array(list(SECTORS[sector].values()))
        fam_w = fam_w / fam_w.sum()
        size = int(rng.integers(60, 260))
        pay_factor = float(rng.lognormal(0, 0.12))
        home_city = str(rng.choice(city_names[:-1]))
        for e in range(size):
            family = str(rng.choice(families, p=fam_w))
            level = str(rng.choice(LEVELS, p=LEVEL_WEIGHTS))
            if level == "intern" and family in NO_INTERN_FAMILIES:
                level = "junior"
            city = home_city if rng.random() < 0.7 else str(rng.choice(city_names))

            if level == "intern":
                contract, hours = "ESTAGIO", 30
            else:
                contract = "CLT"
                part_time = family == "customer_support" and rng.random() < 0.20
                hours = 30 if part_time else int(rng.choice([44, 40], p=[0.6, 0.4]))

            salary = (FAMILIES[family]["mid_salary"] * LEVEL_MULTIPLIER[level] * pay_factor
                      * CITIES[city] * rng.lognormal(0, 0.15))
            if hours == 30 and contract == "CLT":
                salary *= 30 / 44
            if contract == "CLT":  # employers in this world respect the law
                salary = max(salary, legal_min_wage(hours) * rng.uniform(1.03, 1.15))
            salary = round(salary / 10) * 10

            if level == "intern":
                bonus = 0.0
            elif family == "sales_rep":
                bonus = salary * rng.uniform(2, 8)
            else:
                bonus = 0.0 if rng.random() < 0.3 else salary * rng.uniform(0, 2.5)

            max_years = 2 if level == "intern" else 12
            hire = REFERENCE_DATE - dt.timedelta(days=int(rng.integers(15, 365 * max_years)))

            title, hard = render_title(family, level, rng)
            rows.append({
                "company_id": company_id, "sector": sector,
                "employee_id": f"{company_id}-{e + 1:05d}",
                "job_title": title, "city": city, "contract_type": contract,
                "weekly_hours": hours, "monthly_salary": float(salary),
                "annual_bonus": round(float(bonus), 2), "hire_date": hire.isoformat(),
                "true_family": family, "true_level": level, "hard_title": hard,
            })
    return pd.DataFrame(rows)


def _plant_errors(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    df = df.copy()
    df["error_type"] = "none"
    n = len(df)

    def pick(k: int, mask: pd.Series | None = None) -> np.ndarray:
        free = df["error_type"].eq("none")
        if mask is not None:
            free &= mask
        idx = df.index[free].to_numpy()
        return rng.choice(idx, size=min(k, len(idx)), replace=False)

    clt = df["contract_type"].eq("CLT")
    for err, rate in ERROR_RATES.items():
        k = max(1, int(round(rate * n)))
        if err == "missing_salary":
            idx = pick(k)
            df.loc[idx, "monthly_salary"] = np.nan
        elif err == "missing_title":
            idx = pick(k)
            df.loc[idx, "job_title"] = rng.choice(["", " ", None], size=len(idx))
        elif err == "below_min_wage":
            idx = pick(k, clt & df["weekly_hours"].ge(40))
            df.loc[idx, "monthly_salary"] = [round(legal_min_wage(44) * rng.uniform(0.55, 0.93), 2)
                                             for _ in idx]
        elif err == "decimal_shift":  # "8.500,00" parsed as 8.5 or 85.0
            idx = pick(k, clt)
            df.loc[idx, "monthly_salary"] = (df.loc[idx, "monthly_salary"]
                                             / rng.choice([100, 1000], size=len(idx))).round(2)
        elif err == "annual_as_monthly":  # annual value typed in the monthly field
            idx = pick(k, clt)
            df.loc[idx, "monthly_salary"] = (df.loc[idx, "monthly_salary"]
                                             * rng.choice([12, 13.33], size=len(idx))).round(2)
        elif err == "bonus_outlier":
            idx = pick(k, clt)
            df.loc[idx, "annual_bonus"] = (df.loc[idx, "monthly_salary"]
                                           * rng.uniform(24, 60, size=len(idx))).round(2)
        elif err == "duplicate_id":
            idx = pick(k // 2 * 2)
            for a, b in zip(idx[::2], idx[1::2]):
                if df.at[a, "company_id"] != df.at[b, "company_id"]:
                    # move b's id inside a's company: re-pick within company
                    same = df.index[df["company_id"].eq(df.at[a, "company_id"])
                                    & df["error_type"].eq("none") & (df.index != a)]
                    b = int(rng.choice(same))
                df.at[b, "employee_id"] = df.at[a, "employee_id"]
                df.loc[[a, b], "error_type"] = "duplicate_id"
            continue
        elif err == "future_hire_date":
            idx = pick(k)
            df.loc[idx, "hire_date"] = [
                (REFERENCE_DATE + dt.timedelta(days=int(rng.integers(30, 900)))).isoformat()
                if rng.random() < 0.6 else "2062-03-15" for _ in idx]
        elif err == "level_salary_mismatch":  # salary of another level entirely
            idx = pick(k, clt)
            salary = df.loc[idx, "monthly_salary"].to_numpy()
            floor = df.loc[idx, "weekly_hours"].map(legal_min_wage).to_numpy() * 1.10
            up = rng.uniform(2.4, 3.2, len(idx))
            down = rng.uniform(0.30, 0.42, len(idx))
            # go down only when the result stays legal; otherwise go up
            go_down = (rng.random(len(idx)) < 0.4) & (salary * down > floor)
            df.loc[idx, "monthly_salary"] = np.round(np.where(go_down, salary * down, salary * up), -1)
        df.loc[idx, "error_type"] = err
    df["severity"] = df["error_type"].map(SEVERITY).fillna("none")
    return df


TRUTH_COLUMNS = ["company_id", "employee_id", "true_family", "true_level", "hard_title",
                 "error_type", "severity"]


def generate(seed: int = 42, n_companies: int = 25) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (submissions, truth). Both share a `row_id` key."""
    rng = np.random.default_rng(seed)
    df = _plant_errors(_clean_records(rng, n_companies), rng)
    df.insert(0, "row_id", np.arange(len(df)))
    submitted = df.drop(columns=["true_family", "true_level", "hard_title", "error_type",
                                 "severity", "sector"])
    truth = df[["row_id", *TRUTH_COLUMNS]]
    return submitted, truth
