"""Run title normalization and the full validator on public salary files.

There is no ground truth here: the point is to see what real data does to the
pipeline. The files are not in the repository (download them and pass the paths):

    python scripts/public_data_check.py INDIA_CSV US_CSV [--italy PARQUET] [--no-cache]

- India file (`Salary_Dataset_DataScienceLovers.csv`: Company Name, Job Title,
  Salary, Location, Employment Status, Job Roles): every "Job Roles" value is a
  software role, a weak label for the family; "Intern" status is one for the level.
- US-style file (`Salary_Data.csv`): Job Title, Salary, Education Level and
  Years of Experience are read; Age and Gender never are. No labels.
- Italian survey (Hugging Face `datapizza-ai-lab/salaries`, CC BY-NC 4.0, the
  parquet file of its train split; reading it needs pyarrow, which the [ui] extra
  installs). Its `valid` column is the publisher's own flag; age, gender, the
  submission time and `valid` itself are never given to the validator.

Only job titles reach the LLM (configured as in llm.py). Salaries stay in their
own currency (annual / 12): the minimum-wage and decimal-shift rules are set in
reais, so here they only catch absurdly low values. Company names never appear
in the report.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from payroll_sentinel.llm import LLMClient
from payroll_sentinel.normalize import llm_normalize, rule_normalize
from payroll_sentinel.taxonomy import REFERENCE_DATE
from payroll_sentinel.validate import validate

SE = "software_engineer"
DEBATABLE = ["Testing", "Database"]
HIRE = "2020-01-01"  # the files have no hire date, and an empty one blocks every row
CONTRACT = {"Full Time": "CLT", "Trainee": "CLT", "Intern": "ESTAGIO", "Contractor": "PJ"}
CAUSES = ["missing_salary", "missing_title", "duplicate_record", "decimal_shift", "below_min_wage",
          "extreme_value", "annual_as_monthly", "divided_by_12", "level_salary_mismatch",
          "statistical_outlier", "future_hire_date"]
# Italian survey answers handed to the validator as extra columns (so a copied answer
# is a copied row). Age, gender, submission time and the publisher's flag are left out.
IT_ANSWERS = ["monthsOfExperience", "educationType", "companyIndustry", "companySize", "province",
              "workMode", "aiUsageFrequency", "editor", "rating"]
IT_LISTS = ["technologies", "aiTechnologies", "aiTaskTypes", "aiUpdateSources", "admiredTechnologies"]


def adapt_india(raw: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "company_id": raw["Company Name"].fillna("(no name)"),
        "employee_id": [f"r{i}" for i in range(len(raw))],
        "job_title": raw["Job Title"], "contract_type": raw["Employment Status"].map(CONTRACT),
        "weekly_hours": 44, "monthly_salary": (raw["Salary"] / 12).round(2),
        "annual_bonus": 0.0, "hire_date": HIRE, "city": raw["Location"],
    })


def adapt_us(raw: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "company_id": "public_us", "employee_id": [f"r{i}" for i in range(len(raw))],
        "job_title": raw["Job Title"], "contract_type": "CLT", "weekly_hours": 44,
        "monthly_salary": (raw["Salary"] / 12).round(2), "annual_bonus": 0.0, "hire_date": HIRE,
        "education": raw["Education Level"], "years_experience": raw["Years of Experience"],
    })


def adapt_italy(raw: pd.DataFrame) -> pd.DataFrame:
    """Hire date = reference date minus months of experience (total experience, not tenure:
    an approximation, but 24,126 months becomes an impossible date). Contract FOREIGN: the
    Brazilian minimum wage does not apply, and in euros it would block real part-time pay."""
    start = REFERENCE_DATE.year * 12 + REFERENCE_DATE.month - 1 - raw["monthsOfExperience"]
    joined = {c: raw[c].map(lambda v: ", ".join(v) if v is not None and len(v) else "")
              for c in IT_LISTS}
    return pd.DataFrame({
        "company_id": "survey", "employee_id": [f"r{i}" for i in range(len(raw))],
        "job_title": raw["jobTitle"].str.replace("_", " "), "contract_type": "FOREIGN",
        "weekly_hours": 44, "monthly_salary": (raw["salary"] / 12).round(2), "annual_bonus": 0.0,
        "hire_date": [f"{m // 12:04d}-{m % 12 + 1:02d}-01" for m in start],
        **{c: raw[c] for c in IT_ANSWERS}, **joined,
    })


def md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


def outcome(family) -> str:
    return "abstained" if pd.isna(family) else (SE if family == SE else "other family")


def title_section(india: pd.DataFrame, us: pd.DataFrame, rules, llm) -> list[str]:
    pairs = india.dropna(subset=["Job Title"]).groupby(["Job Roles", "Job Title"]).size()
    pairs = pairs.rename("rows").reset_index()
    rows = []
    for method, pred in (("rules", rules), ("LLM", llm)):
        p = pairs.assign(method=method, family=pairs["Job Title"].map(pred["family"]))
        rows.append(p.assign(outcome=p["family"].map(outcome)))
    both = pd.concat(rows)
    both["group"] = both["Job Roles"].where(both["Job Roles"].isin(DEBATABLE), "9 developer roles")
    order = [SE, "other family", "abstained"]

    def shares(weight: str | None) -> pd.DataFrame:
        out = []
        for (group, method), part in both.groupby(["group", "method"]):
            w = part["rows"] if weight else pd.Series(1, index=part.index)
            s = w.groupby(part["outcome"]).sum() / w.sum()
            out.append({"group": group, "titles": method, "n": int(w.sum()),
                        **{k: round(float(s.get(k, 0.0)), 3) for k in order}})
        return pd.DataFrame(out)

    llm_only = both[both["method"].eq("LLM")]
    other = llm_only[llm_only["outcome"].eq("other family")].sort_values("rows", ascending=False)
    abst = llm_only[llm_only["outcome"].eq("abstained")].sort_values("rows", ascending=False)
    interns = india[india["Employment Status"].eq("Intern")]
    us_titles = pd.Series(us["Job Title"].dropna().unique())
    coverage = pd.DataFrame([{
        "titles": method,
        "rows with a family": round(float(us["Job Title"].map(pred["family"]).notna().mean()), 3),
        "distinct titles with a family": f"{int(us_titles.map(pred['family']).notna().sum())} / {len(us_titles)}",
    } for method, pred in (("rules", rules), ("LLM", llm))])
    top = us["Job Title"].value_counts().head(25).rename_axis("title").reset_index(name="rows")
    for method, pred in (("rules", rules), ("LLM", llm)):
        top[method] = [f"{'-' if pd.isna(pred.at[t, 'family']) else pred.at[t, 'family']} / "
                       f"{pred.at[t, 'level']}" for t in top["title"]]
    return [
        "## 1. Job titles", "",
        "### India file: family against the weak label (expected: software_engineer)", "",
        "Share of distinct titles (`n` = titles):", "", md(shares(None)), "",
        "Share of rows (`n` = rows; frequent titles weigh more):", "", md(shares("rows")), "",
        f"LLM titles mapped to another family ({len(other)}); many show the weak label is wrong:", "",
        md(other[["Job Roles", "Job Title", "family", "rows"]].head(25)) if len(other) else "None.", "",
        f"LLM abstentions ({len(abst)}), most frequent first:", "",
        md(abst[["Job Roles", "Job Title", "rows"]].head(20)) if len(abst) else "None.", "",
        f"Rows with Employment Status `Intern`: {len(interns)}; given level `intern` by rules "
        f"{interns['Job Title'].map(rules['level']).eq('intern').mean():.1%}, by the LLM "
        f"{interns['Job Title'].map(llm['level']).eq('intern').mean():.1%}.", "",
        "### US-style file: coverage (no labels)", "",
        "Many titles (marketing, operations, directors) are outside the 10 families, so "
        "abstaining is often right.", "", md(coverage), "",
        "Most frequent titles (family / level):", "", md(top), "",
    ]


def mapping_lines(name: str, titles: pd.Series, rules, llm, note: str) -> list[str]:
    """Coverage and most frequent titles for a file without labels."""
    distinct = pd.Series(titles.dropna().unique())
    coverage = pd.DataFrame([{
        "titles": method,
        "rows with a family": round(float(titles.map(pred["family"]).notna().mean()), 3),
        "distinct titles with a family": f"{int(distinct.map(pred['family']).notna().sum())} / {len(distinct)}",
    } for method, pred in (("rules", rules), ("LLM", llm))])
    top = titles.value_counts().head(30).rename_axis("title").reset_index(name="rows")
    for method, pred in (("rules", rules), ("LLM", llm)):
        top[method] = [f"{'-' if pd.isna(pred.at[t, 'family']) else pred.at[t, 'family']} / "
                       f"{pred.at[t, 'level']}" for t in top["title"]]
    return [f"### {name}: coverage (no labels)", "", note, "", md(coverage), "",
            "Most frequent titles (family / level):", "", md(top), ""]


def publisher_lines(df: pd.DataFrame, issues: pd.DataFrame, valid: pd.Series) -> list[str]:
    """Cross the validator's outcome with the publisher's own `valid` flag. Title-only
    warnings (unmapped_title) are left out: they are about the taxonomy, not the values."""
    real = issues[issues["cause"] != "unmapped_title"]
    sev = real.groupby("row_id")["severity"].agg(set)
    ours = df["row_id"].map(lambda r: "blocked" if "block" in sev.get(r, set())
                            else ("review" if r in sev.index else "no issue"))
    theirs = valid.map({True: "publisher: valid", False: "publisher: invalid"}).to_numpy()
    tab = pd.crosstab(theirs, ours.to_numpy()).rename_axis(index="publisher", columns=None).reset_index()
    invalid_rows = df.loc[~valid.to_numpy(), "row_id"]
    causes = (real[real["row_id"].isin(invalid_rows)].groupby("cause")["row_id"].nunique()
              .rename("rows").reset_index())
    annual = (df["monthly_salary"] * 12).round(0).to_numpy()  # 10,000 / 12 * 12 is 9,999.96
    band = np.select([annual < 10_000, annual > 200_000], ["under 10,000", "over 200,000"],
                     "10,000 to 200,000")
    extremes = pd.crosstab([theirs, band], ours.to_numpy()).rename_axis(
        index=["publisher", "annual salary"], columns=None).reset_index()
    return ["Validator outcome (LLM titles) against the publisher's `valid` flag:", "", md(tab), "",
            f"Causes among the {len(invalid_rows)} rows the publisher marks invalid:", "",
            md(causes) if len(causes) else "None.", "",
            "The same outcome by annual salary band:", "", md(extremes), ""]


def validation_section(name: str, df: pd.DataFrame, currency: str, rules, llm,
                       publisher_valid: pd.Series | None = None) -> list[str]:
    df = df.reset_index(drop=True)
    df.insert(0, "row_id", range(len(df)))
    summary, kept = [], None
    for method, pred in (("rules", rules), ("LLM", llm)):
        norm = pd.DataFrame({"family": df["job_title"].map(pred["family"]),
                             "level": df["job_title"].map(pred["level"])})
        res = validate(df, norm)
        iss = res.issues
        by_cause = iss.groupby("cause")["row_id"].nunique()
        summary.append({
            "titles": method,
            "rows in peer comparison": f"{res.records['flag_ensemble'].notna().mean():.1%}",
            "blocked rows": int(res.records["status"].eq("block").sum()),
            "peer-comparison flags": int(res.records["flag_ensemble"].fillna(False).astype(bool).sum()),
            **{c: int(by_cause.get(c, 0)) for c in CAUSES},
        })
        if method == "LLM":
            kept = res
    peer = kept.issues[kept.issues["check"].eq("peer_comparison")]
    flagged = peer.merge(df[["row_id", "job_title", "monthly_salary"]], on="row_id").merge(
        kept.records[["row_id", "family", "level", "peer_ratio"]], on="row_id")
    flagged["annual salary"] = (flagged["monthly_salary"] * 12).round(0)
    flagged["peer median (annual)"] = (flagged["annual salary"] / flagged["peer_ratio"]).round(0)
    flagged["peer_ratio"] = flagged["peer_ratio"].round(3)
    cols = ["job_title", "family", "level", "annual salary", "peer median (annual)", "peer_ratio",
            "cause", "severity"]
    far = np.abs(np.log(flagged["peer_ratio"]))
    lines = [f"### {name} ({len(df)} rows, {df['company_id'].nunique()} companies, {currency})", "",
             "Rows per cause (a row can have several):", "", md(pd.DataFrame(summary)), "",
             "Peer-comparison causes with LLM titles:", "",
             md(flagged.groupby(["cause", "severity"]).size().rename("rows").reset_index()), "",
             "Most extreme flags (LLM titles; salaries are annual):", "",
             md(flagged.assign(far=far).sort_values("far", ascending=False)[cols].head(12)), "",
             "Mildest flags (LLM titles):", "",
             md(flagged.assign(far=far).sort_values("far")[cols].head(6)), ""]
    if name == "India":
        decisions = kept.companies["decision"].value_counts().rename("companies").reset_index()
        lines += ["Company decisions (LLM titles). Most companies here have one to three rows, so a "
                  "single blocked row is more than the 5 % that rejects a file:", "", md(decisions), ""]
    if publisher_valid is not None:
        lines += publisher_lines(df, kept.issues, publisher_valid.reset_index(drop=True))
    return lines


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("india_csv")
    p.add_argument("us_csv")
    p.add_argument("--italy", help="parquet file of datapizza-ai-lab/salaries (train split)")
    p.add_argument("--reports", default="reports")
    p.add_argument("--cache-dir", default="data")
    p.add_argument("--no-cache", action="store_true", help="ask the LLM for every title")
    args = p.parse_args()

    india = pd.read_csv(args.india_csv)
    us = pd.read_csv(args.us_csv, usecols=["Education Level", "Job Title", "Years of Experience",
                                           "Salary"])  # Age and Gender are never read
    italy_raw = pd.read_parquet(args.italy) if args.italy else None
    italy = adapt_italy(italy_raw) if italy_raw is not None else None
    sources = [india["Job Title"], us["Job Title"]] + ([italy["job_title"]] if italy is not None else [])
    titles = pd.Series(pd.concat(sources).dropna().unique())
    rules = rule_normalize(titles).set_index(titles)
    client = LLMClient.from_env()
    cache = None if args.no_cache else Path(args.cache_dir) / f"llm_title_cache_public_{client.tag}.json"
    start = time.perf_counter()
    llm = llm_normalize(titles, client, cache_path=cache).set_index(titles)
    run = f"{client.stats.summary()}; {time.perf_counter() - start:.1f} s in total"
    if client.stats.calls == 0:
        run += " (every title came from the cache, so this is not a timing measurement)"

    lines = ["# Public salary files: titles and full validation", "",
             f"Titles: keyword rules and LLM ({client.label}), {len(titles)} distinct titles. "
             f"LLM run: {run}.", "",
             "No ground truth: section 1 uses weak labels that ship with the data, and section 2 "
             "lists what the validator flags, for a human to judge. Adapter: annual salary / 12 in "
             f"the original currency, 44 h/week, bonus 0; hire date {HIRE} for the India and "
             "US-style files, and the reference date minus months of experience for the Italian "
             "survey.", ""]
    lines += title_section(india, us, rules, llm)
    if italy is not None:
        lines += mapping_lines(
            "Italian survey", italy["job_title"], rules, llm,
            "117 job categories chosen from a list (no seniority in them, so every row is `mid` "
            "unless the title implies a level). Many IT roles (project manager, IT consultant, "
            "solutions architect) are outside the 10 families.")
    lines += ["## 2. Full validation", ""]
    lines += validation_section("India", adapt_india(india), "INR", rules, llm)
    lines += validation_section("US-style", adapt_us(us), "USD", rules, llm)
    if italy is not None:
        lines += validation_section("Italian survey", italy, "EUR", rules, llm,
                                    publisher_valid=italy_raw["valid"])

    out = Path(args.reports)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"public_data_{client.tag}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nReport written to {path}")


if __name__ == "__main__":
    main()
