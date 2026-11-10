"""Command line entry point.

    python -m payroll_sentinel.cli run            # generate + validate + evaluate (rules only, free)
    python -m payroll_sentinel.cli run --llm      # same, titles normalized by an LLM (see llm.py)
    python -m payroll_sentinel.cli validate FILE  # validate your own CSV
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .evaluate import score, title_accuracy
from .generate import generate
from .normalize import llm_normalize, rule_normalize
from .validate import validate


def _normalize(titles: pd.Series, use_llm: bool, cache: Path) -> pd.DataFrame:
    if not use_llm:
        return rule_normalize(titles)
    from .llm import LLMClient
    return llm_normalize(titles, LLMClient.from_env(), cache_path=cache)


def _md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


def cmd_run(args) -> None:
    data, reports = Path(args.data), Path(args.reports)
    data.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    submitted, truth = generate(seed=args.seed, n_companies=args.companies)
    submitted.to_csv(data / "submissions.csv", index=False)
    truth.to_csv(data / "ground_truth.csv", index=False)

    norm = _normalize(submitted["job_title"], args.llm, data / "llm_title_cache.json")
    oracle = truth[["true_family", "true_level"]].rename(
        columns={"true_family": "family", "true_level": "level"})
    oracle.loc[submitted["job_title"].fillna("").astype(str).str.strip().eq(""), ["family", "level"]] = None

    result = validate(submitted, norm, seed=args.seed)
    result_oracle = validate(submitted, oracle, seed=args.seed)
    result.issues.to_csv(reports / "issues.csv", index=False)
    result.companies.to_csv(reports / "companies.csv", index=False)

    s, so = score(result, truth), score(result_oracle, truth)
    titles = title_accuracy(norm, truth, submitted["job_title"])
    method = "LLM" if args.llm else "keyword rules"

    lines = [
        "# Evaluation report", "",
        f"{len(submitted)} records from {submitted['company_id'].nunique()} companies; "
        f"{int((truth['error_type'] != 'none').sum())} planted errors. Title normalizer: **{method}**.", "",
        "## 1. Title normalization", "", _md(titles), "",
        "## 2. Error detection (any flag on an errored row)", "",
        f"Overall: precision **{s['overall']['precision']}**, recall **{s['overall']['recall']}**, "
        f"F1 **{s['overall']['f1']}**. False alarms on clean rows: {s['false_alarm_rate']:.2%}.", "",
        _md(s["per_type"]), "",
        "## 3. Statistical detectors (annual-as-monthly + level mismatch)", "",
        f"Rows the peer comparison could see: {s['stat_coverage']} of the planted statistical errors "
        "(rows with unmapped titles are excluded).", "",
        s["detectors"].to_markdown(), "",
        "## 4. How much do titles matter?", "",
        "Same validator, but with perfect (oracle) titles:", "",
        f"- Overall recall: {s['overall']['recall']} with {method} vs {so['overall']['recall']} with oracle titles",
        f"- Statistical errors visible: {s['stat_coverage']} vs {so['stat_coverage']}",
        f"- Ensemble F1: {s['detectors'].loc['flag_ensemble', 'f1']} vs "
        f"{so['detectors'].loc['flag_ensemble', 'f1']}", "",
        "## 5. Company decisions", "", _md(result.companies.sort_values("blocked_share", ascending=False)),
    ]
    (reports / "evaluation.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:30]))
    print(f"\nReports written to {reports}/")


def cmd_validate(args) -> None:
    df = pd.read_csv(args.file)
    if "row_id" not in df.columns:
        df.insert(0, "row_id", range(len(df)))
    norm = _normalize(df["job_title"], args.llm, Path(args.reports) / "llm_title_cache.json")
    result = validate(df, norm)
    out = Path(args.reports)
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
