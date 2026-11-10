"""The pipeline as plain functions, with no file or console I/O.

Shared by the command line (`cli.py`) and the web UI (`app.py`), so both always
compute exactly the same numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .evaluate import score, title_accuracy
from .generate import generate
from .normalize import llm_normalize, rule_normalize
from .validate import ValidationResult, validate

# Columns the validator reads. Any extra columns in a file are kept and ignored.
REQUIRED_COLUMNS = ["company_id", "employee_id", "job_title", "contract_type",
                    "weekly_hours", "monthly_salary", "annual_bonus", "hire_date"]


def normalize_titles(titles: pd.Series, use_llm: bool = False,
                     cache_path: str | Path | None = None) -> pd.DataFrame:
    if not use_llm:
        return rule_normalize(titles)
    from .llm import LLMClient
    return llm_normalize(titles, LLMClient.from_env(), cache_path=cache_path)


def missing_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in REQUIRED_COLUMNS if c not in df.columns]


def validate_submissions(df: pd.DataFrame, use_llm: bool = False,
                         cache_path: str | Path | None = None) -> ValidationResult:
    """Validate a company file. Adds a `row_id` column when the file has none."""
    if "row_id" not in df.columns:
        df = df.copy()
        df.insert(0, "row_id", range(len(df)))
    return validate(df, normalize_titles(df["job_title"], use_llm, cache_path))


@dataclass
class Evaluation:
    submitted: pd.DataFrame
    truth: pd.DataFrame
    result: ValidationResult
    score: dict            # validator with the chosen title normalizer
    oracle_score: dict     # same validator with perfect titles
    titles: pd.DataFrame   # title normalization accuracy
    method: str

    def report_lines(self) -> list[str]:
        s, so, md = self.score, self.oracle_score, (lambda df: df.to_markdown(index=False))
        return [
            "# Evaluation report", "",
            f"{len(self.submitted)} records from {self.submitted['company_id'].nunique()} companies; "
            f"{int((self.truth['error_type'] != 'none').sum())} planted errors. "
            f"Title normalizer: **{self.method}**.", "",
            "## 1. Title normalization", "", md(self.titles), "",
            "## 2. Error detection (any flag on an errored row)", "",
            f"Overall: precision **{s['overall']['precision']}**, recall **{s['overall']['recall']}**, "
            f"F1 **{s['overall']['f1']}**. False alarms on clean rows: {s['false_alarm_rate']:.2%}.", "",
            md(s["per_type"]), "",
            "## 3. Statistical detectors (annual-as-monthly + level mismatch)", "",
            f"Rows the peer comparison could see: {s['stat_coverage']} of the planted statistical errors "
            "(rows with unmapped titles are excluded).", "",
            s["detectors"].to_markdown(), "",
            "## 4. How much do titles matter?", "",
            "Same validator, but with perfect (oracle) titles:", "",
            f"- Overall recall: {s['overall']['recall']} with {self.method} vs "
            f"{so['overall']['recall']} with oracle titles",
            f"- Statistical errors visible: {s['stat_coverage']} vs {so['stat_coverage']}",
            f"- Ensemble F1: {s['detectors'].loc['flag_ensemble', 'f1']} vs "
            f"{so['detectors'].loc['flag_ensemble', 'f1']}", "",
            "## 5. Company decisions", "",
            md(self.result.companies.sort_values("blocked_share", ascending=False)),
        ]

    def report(self) -> str:
        return "\n".join(self.report_lines())


def run_evaluation(seed: int = 42, n_companies: int = 25, use_llm: bool = False,
                   cache_path: str | Path | None = None) -> Evaluation:
    """Generate synthetic data with planted errors, validate it and score it against the truth."""
    submitted, truth = generate(seed=seed, n_companies=n_companies)
    norm = normalize_titles(submitted["job_title"], use_llm, cache_path)
    oracle = truth[["true_family", "true_level"]].rename(
        columns={"true_family": "family", "true_level": "level"})
    oracle.loc[submitted["job_title"].fillna("").astype(str).str.strip().eq(""), ["family", "level"]] = None

    result = validate(submitted, norm, seed=seed)
    result_oracle = validate(submitted, oracle, seed=seed)
    return Evaluation(
        submitted=submitted, truth=truth, result=result,
        score=score(result, truth), oracle_score=score(result_oracle, truth),
        titles=title_accuracy(norm, truth, submitted["job_title"]),
        method="LLM" if use_llm else "keyword rules",
    )
