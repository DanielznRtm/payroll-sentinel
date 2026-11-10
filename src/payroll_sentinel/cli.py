"""Command line entry point.

    python -m payroll_sentinel.cli run            # generate + validate + evaluate (rules only, free)
    python -m payroll_sentinel.cli run --llm      # same, titles normalized by an LLM (see llm.py)
    python -m payroll_sentinel.cli validate FILE  # validate your own CSV
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .pipeline import run_evaluation, validate_submissions


def cmd_run(args) -> None:
    data, reports = Path(args.data), Path(args.reports)
    data.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    ev = run_evaluation(seed=args.seed, n_companies=args.companies, use_llm=args.llm,
                        cache_path=data / "llm_title_cache.json")
    ev.submitted.to_csv(data / "submissions.csv", index=False)
    ev.truth.to_csv(data / "ground_truth.csv", index=False)
    ev.result.issues.to_csv(reports / "issues.csv", index=False)
    ev.result.companies.to_csv(reports / "companies.csv", index=False)

    lines = ev.report_lines()
    (reports / "evaluation.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:30]))
    print(f"\nReports written to {reports}/")


def cmd_validate(args) -> None:
    out = Path(args.reports)
    result = validate_submissions(pd.read_csv(args.file), use_llm=args.llm,
                                  cache_path=out / "llm_title_cache.json")
    out.mkdir(parents=True, exist_ok=True)
    result.issues.to_csv(out / "issues.csv", index=False)
    result.companies.to_csv(out / "companies.csv", index=False)
    print(result.companies.to_string(index=False))
    print(f"\n{len(result.issues)} issues written to {out / 'issues.csv'}")


def main() -> None:
    p = argparse.ArgumentParser(prog="payroll_sentinel")
    sub = p.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="generate synthetic data, validate and evaluate")
    run.add_argument("--seed", type=int, default=42)
    run.add_argument("--companies", type=int, default=25)
    run.add_argument("--llm", action="store_true", help="normalize titles with an LLM")
    run.add_argument("--data", default="data")
    run.add_argument("--reports", default="reports")
    run.set_defaults(func=cmd_run)
    val = sub.add_parser("validate", help="validate a CSV file")
    val.add_argument("file")
    val.add_argument("--llm", action="store_true")
    val.add_argument("--reports", default="reports")
    val.set_defaults(func=cmd_validate)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
