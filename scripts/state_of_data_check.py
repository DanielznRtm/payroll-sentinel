"""How realistic are the synthetic salaries? Compare them with the State of Data Brazil survey.

State of Data Brazil (Data Hackers and Bain, published on Kaggle) asks Brazilian data
professionals for their job, level and monthly salary band. The file is not in the
repository: download it and pass its path.

    python scripts/state_of_data_check.py STATE_OF_DATA_CSV [--reports reports]

Only six columns are read: work status, manager flag, job, level, salary band and
state. Age, gender, race and every other personal answer are never read. The
comparison uses CLT employees who are not managers, the closest match to a payroll
file. Salaries come in bands, so medians are grouped-data medians (interpolated
inside the band that holds the middle answer).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from payroll_sentinel.generate import generate  # noqa: E402

COLUMNS = {"status": "2.a_", "manager": "2.d_", "job": "2.f_", "level": "2.g_",
           "band": "2.h_", "uf": "1.i.1_"}
JOBS = {  # survey answer -> project family
    "Analista de Dados/Data Analyst": "data_analyst",
    "Analista de BI/BI Analyst": "data_analyst",
    "Cientista de Dados/Data Scientist": "data_scientist",
    "Desenvolvedor/ Engenheiro de Software/ Analista de Sistemas": "software_engineer",
    "Data Product Manager/ Product Manager (PM/APM/DPM/GPM/PO)": "product_manager",
}
LEVELS = {"Júnior": "junior", "Pleno": "mid", "Sênior": "senior", "Especialista/Staff+": "lead"}
ORDER = ["junior", "mid", "senior", "lead"]
MIN_ANSWERS = 15  # fewer answers than this: no median is shown


def band_bounds(text: str) -> tuple[float, float] | None:
    """'de R$ 8.001/mês a R$ 12.000/mês' -> (8000, 12000); open or malformed bands -> None."""
    nums = [float(n.replace(".", "")) for n in re.findall(r"\d[\d.]*", str(text))]
    if str(text).startswith("Menos de") and nums:
        return 0.0, nums[0]
    if len(nums) == 2 and nums[1] > nums[0]:
        return nums[0] - 1, nums[1]
    return None  # 'Acima de R$ 40.001' is open-ended; one answer reads 'R$ 25.001 a R$ 3000'


def grouped_median(bounds: pd.Series) -> float | None:
    """Median of answers given as (low, high) bands: find the band holding the middle answer
    and interpolate linearly inside it."""
    counts = bounds.value_counts().sort_index()
    half, seen = counts.sum() / 2, 0
    for (low, high), n in counts.items():
        if seen + n >= half:
            return low + (half - seen) / n * (high - low)
        seen += n
    return None


def survey_medians(path: str) -> tuple[pd.DataFrame, dict]:
    header = pd.read_csv(path, nrows=0).columns
    cols = {k: next(c for c in header if c.startswith(p)) for k, p in COLUMNS.items()}
    raw = pd.read_csv(path, usecols=list(cols.values())).rename(columns={v: k for k, v in cols.items()})
    notes = {"answers": len(raw), "malformed band": int(raw["band"].astype(str).str.contains("a R\\$ 3000").sum())}
    df = raw[raw["status"].eq("Empregado (CLT)") & raw["manager"].eq(0)].copy()
    df["family"], df["lvl"] = df["job"].map(JOBS), df["level"].map(LEVELS)
    df["bounds"] = df["band"].map(band_bounds)
    notes["open band (over R$ 40,000)"] = int(df["band"].astype(str).str.startswith("Acima").sum())
    df = df.dropna(subset=["family", "lvl", "bounds"])
    notes["CLT individual contributors used"] = len(df)
    rows = []
    for scope, part in (("São Paulo", df[df["uf"].eq("SP")]), ("Brazil", df)):
        for (fam, lvl), g in part.groupby(["family", "lvl"]):
            rows.append({"scope": scope, "family": fam, "level": lvl, "survey answers": len(g),
                         "survey median": grouped_median(g["bounds"]) if len(g) >= MIN_ANSWERS else None})
    return pd.DataFrame(rows), notes


def synthetic_medians(n_companies: int = 200, seed: int = 42) -> pd.DataFrame:
    sub, truth = generate(seed=seed, n_companies=n_companies)
    df = sub.merge(truth[["row_id", "true_family", "true_level", "error_type"]], on="row_id")
    df = df[df["error_type"].eq("none") & df["contract_type"].eq("CLT") & df["weekly_hours"].ge(40)]
    rows = []
    for scope, part in (("São Paulo", df[df["city"].eq("São Paulo")]), ("Brazil", df)):
        for (fam, lvl), g in part.groupby(["true_family", "true_level"]):
            rows.append({"scope": scope, "family": fam, "level": lvl,
                         "synthetic median": float(g["monthly_salary"].median())})
    return pd.DataFrame(rows)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("csv")
    p.add_argument("--reports", default="reports")
    args = p.parse_args()

    survey, notes = survey_medians(args.csv)
    table = survey.merge(synthetic_medians(), on=["scope", "family", "level"], how="left")
    table["synthetic / survey"] = (table["synthetic median"] / table["survey median"]).round(2)
    table["level"] = pd.Categorical(table["level"], ORDER, ordered=True)
    table = table.sort_values(["scope", "family", "level"])

    ratios = []
    for (scope, fam), g in table.groupby(["scope", "family"], observed=True):
        g = g.set_index("level")
        if pd.isna(g["survey median"].get("mid")):
            continue
        for lvl in ("junior", "senior", "lead"):
            if lvl in g.index and pd.notna(g.at[lvl, "survey median"]):
                ratios.append({"scope": scope, "family": fam, "level / mid": lvl,
                               "survey": round(g.at[lvl, "survey median"] / g.at["mid", "survey median"], 2),
                               "synthetic": round(g.at[lvl, "synthetic median"] / g.at["mid", "synthetic median"], 2)})

    shown = table.copy()
    for c in ("survey median", "synthetic median"):
        shown[c] = shown[c].map(lambda v: "-" if pd.isna(v) else f"{v:,.0f}")
    lines = [
        "# How realistic are the synthetic salaries? (State of Data Brazil)", "",
        "Survey: State of Data Brazil 2025-2026 (Data Hackers and Bain, Kaggle), "
        f"{notes['answers']} answers. Used: CLT employees who are not managers, in the four "
        f"mapped jobs: {notes['CLT individual contributors used']} answers. Open band "
        f"(over R$ 40,000, left out): {notes['open band (over R$ 40,000)']}. Malformed band "
        f"('R$ 25.001 a R$ 3000'): {notes['malformed band']}.", "",
        "Monthly salary medians in R$. Survey medians are grouped-data medians over salary "
        f"bands, shown only with at least {MIN_ANSWERS} answers. Synthetic medians come from "
        "generate(seed=42, n_companies=200), clean full-time CLT rows only.", "",
        "## Median salary by family and level", "",
        shown.to_markdown(index=False), "",
        "## Pay by level relative to mid level", "",
        "The synthetic generator uses fixed multipliers (junior 0.65, senior 1.45, lead 1.95).", "",
        pd.DataFrame(ratios).to_markdown(index=False), "",
    ]
    out = Path(args.reports)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "realism_state_of_data.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"Report written to {path}")


if __name__ == "__main__":
    main()
