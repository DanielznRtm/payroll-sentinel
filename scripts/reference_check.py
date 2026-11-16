"""Does comparing one company's file with reference peers help? Validate each company on its own.

    python scripts/reference_check.py [--seed 7] [--reports reports]

The web UI validates an uploaded file together with the clean synthetic benchmark
(pipeline.reference_peers, seed 42), because one company rarely has 15 peers of the
same family and level. This script takes another seed's companies, validates each
one alone and against the reference, and counts the planted errors found. Titles go
through the offline rules, as in the UI. Unrecognized-title warnings do not count
as detections.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from payroll_sentinel.generate import generate  # noqa: E402
from payroll_sentinel.pipeline import (reference_peers, validate_against_reference,  # noqa: E402
                                       validate_submissions)


def outcomes(seed: int) -> pd.DataFrame:
    sub, truth = generate(seed=seed, n_companies=25)
    ref = reference_peers()
    rows = []
    for mode in ("alone", "with reference peers"):
        for _, part in sub.groupby("company_id"):
            res = validate_submissions(part) if mode == "alone" else validate_against_reference(part, ref)
            flagged = set(res.issues.loc[res.issues["cause"].ne("unmapped_title"), "row_id"])
            rows += [{"mode": mode, "error_type": err, "flagged": rid in flagged}
                     for rid, err in zip(part["row_id"], truth.loc[part.index, "error_type"])]
    return pd.DataFrame(rows)


def report(df: pd.DataFrame, seed: int) -> str:
    errors = df[df["error_type"].ne("none")]
    by_type = errors.groupby(["error_type", "mode"])["flagged"].sum().unstack()
    by_type.insert(0, "planted", errors[errors["mode"].eq("alone")].groupby("error_type").size())
    overall = errors.groupby("mode")["flagged"].agg(caught="sum", planted="size")
    overall["recall"] = (overall["caught"] / overall["planted"]).round(3)
    overall["false alarms on clean rows"] = (df[df["error_type"].eq("none")].groupby("mode")["flagged"]
                                             .mean().map(lambda v: f"{v:.2%}"))
    return "\n".join([
        "# One company's file: alone vs. with reference peers", "",
        f"Seed {seed}, 25 companies, each validated on its own with the offline rules. Reference "
        "peers: the clean rows of generate(seed=42, n_companies=25), as in the web UI. "
        "Unrecognized-title warnings are not counted as detections.", "",
        "## Overall", "", overall.reset_index().to_markdown(index=False), "",
        "## Planted errors caught, by type", "", by_type.reset_index().to_markdown(index=False), "",
    ])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--reports", default="reports")
    args = p.parse_args()
    text = report(outcomes(args.seed), args.seed)
    out = Path(args.reports)
    out.mkdir(parents=True, exist_ok=True)
    (out / "reference_peers.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
