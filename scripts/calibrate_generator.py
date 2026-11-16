"""Fit the generator's pay parameters to RAIS (reports/realism_rais.json, written by rais_check.py).

    python scripts/calibrate_generator.py [--targets reports/realism_rais.json]

It prints the values to write into taxonomy.py and the fit they reach; it edits no file.

- City index by kind of job, for the cities the RAIS file covers (Campinas and
  Sorocaba): copied from the targets (same-occupation pay relative to São Paulo).
- pay_sigma of each family with RAIS codes: the individual spread that makes the
  synthetic log-pay SD in São Paulo equal the RAIS one. RAIS has no level, so the
  generator's level multipliers stay and the rest of the spread goes here. Data
  analyst and product manager have no CBO code: they get the median of the other
  office families.
- mid_salary of sales_rep and customer_support only (their definitions were settled
  in v1.1): scaled so the synthetic median in São Paulo equals RAIS.

Medians and spreads are fitted in São Paulo, where the generator sets its base
salaries; Campinas and Sorocaba enter only through the city index, so the report's
rows for them remain a check. The synthetic side is the one rais_check.py reports:
generate(seed=42, n_companies=200), clean full-time CLT rows.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from payroll_sentinel.taxonomy import CITIES, FAMILIES  # noqa: E402
from rais_check import synthetic  # noqa: E402

FIT_MEDIAN = ("sales_rep", "customer_support")
MIN_SIGMA = 0.05


def next_sigma(sigma: float, target_sd: float, synthetic_sd: float) -> float:
    """Add the missing variance to the individual noise (independent parts add up in variance)."""
    return float(max(MIN_SIGMA, np.sqrt(max(sigma ** 2 + target_sd ** 2 - synthetic_sd ** 2, 0.0))))


def synthetic_stats() -> pd.DataFrame:
    df = synthetic()
    sp = df[df["city"].eq("São Paulo")]
    return sp.groupby("family")["pay"].agg(median="median", sd=lambda p: float(np.std(np.log(p))))


def fit(targets: dict, rounds: int = 8) -> None:
    """Change CITIES and FAMILIES in memory, then round them as they will be written."""
    fams = targets["families (São Paulo)"]
    for city, kinds in targets["city index"].items():
        CITIES[city].update({kind: round(v, 2) for kind, v in kinds.items()})
    for _ in range(rounds):
        now = synthetic_stats()
        for fam, t in fams.items():
            f = FAMILIES[fam]
            f["pay_sigma"] = next_sigma(f["pay_sigma"], t["log-pay SD"], now.loc[fam, "sd"])
            if fam in FIT_MEDIAN:
                f["mid_salary"] *= t["median"] / now.loc[fam, "median"]
        office = np.median([FAMILIES[f]["pay_sigma"] for f in fams if FAMILIES[f]["kind"] == "office"])
        for fam, f in FAMILIES.items():
            if fam not in fams:
                f["pay_sigma"] = float(office)
    for f in FAMILIES.values():
        f["pay_sigma"] = round(f["pay_sigma"], 2)
        f["mid_salary"] = int(round(f["mid_salary"] / 50) * 50)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--targets", default="reports/realism_rais.json")
    args = p.parse_args()
    targets = json.loads(Path(args.targets).read_text(encoding="utf-8"))
    fit(targets)

    print("Values for taxonomy.py:")
    for fam, f in FAMILIES.items():
        print(f"  {fam:24s} mid_salary {f['mid_salary']:>6}   pay_sigma {f['pay_sigma']:.2f}")
    for city, kinds in targets["city index"].items():
        print(f"  {city}: " + ", ".join(f"{k} {CITIES[city][k]:.2f}" for k in kinds))

    now = synthetic_stats()
    fams = targets["families (São Paulo)"]
    check = pd.DataFrame([{"family": fam, "median (RAIS)": t["median"],
                           "median (synthetic)": now.loc[fam, "median"],
                           "log-pay SD (RAIS)": t["log-pay SD"], "log-pay SD (synthetic)": now.loc[fam, "sd"]}
                          for fam, t in fams.items()]).round(2)
    print("\nFit with the rounded values (São Paulo, all levels):")
    print(check.to_string(index=False))


if __name__ == "__main__":
    main()
