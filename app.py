"""Payroll Sentinel web UI.

    pip install -e ".[ui]"
    streamlit run app.py          # or double-click run_ui.bat on Windows

Two tabs: run the evaluation on synthetic data, or validate your own CSV.
All numbers come from `payroll_sentinel.pipeline`, the same code the CLI uses.
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from payroll_sentinel.generate import generate
from payroll_sentinel.pipeline import (REQUIRED_COLUMNS, missing_columns, run_evaluation,
                                       validate_submissions)

LLM_CACHE = Path("data") / "llm_title_cache.json"
DETECTOR_NAMES = {"vote_z": "Robust z-score", "vote_iqr": "IQR fence",
                  "vote_iforest": "Isolation Forest", "flag_ensemble": "Majority vote (2 of 3)"}


def llm_available() -> bool:
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    return provider == "ollama" or bool(os.getenv("LLM_API_KEY"))


# st.cache_data reruns a function only when its arguments change. Streamlit
# re-executes this whole script on every click, so without the cache each
# filter change would regenerate and revalidate thousands of rows.
@st.cache_data(show_spinner=False)
def cached_evaluation(seed: int, n_companies: int, use_llm: bool):
    return run_evaluation(seed, n_companies, use_llm, LLM_CACHE if use_llm else None)


@st.cache_data(show_spinner=False)
def cached_validation(raw: bytes):
    return validate_submissions(pd.read_csv(io.BytesIO(raw)))


@st.cache_data(show_spinner=False)
def sample_csv() -> bytes:
    return generate(seed=42, n_companies=25)[0].to_csv(index=False).encode("utf-8")


def show_validation(result, key: str) -> None:
    """Company decisions, filterable issues and downloads (used by both tabs)."""
    st.subheader("Company decisions")
    st.dataframe(result.companies.sort_values("blocked_share", ascending=False), hide_index=True,
                 column_config={"blocked_share": st.column_config.NumberColumn(format="percent")})

    st.subheader("Issues")
    issues = result.issues
    c1, c2 = st.columns(2)
    severity = c1.multiselect("Severity", ["block", "warn"], default=["block", "warn"], key=f"{key}_sev")
    company = c2.multiselect("Company", sorted(issues["company_id"].unique()), key=f"{key}_co",
                             placeholder="All companies")
    shown = issues[issues["severity"].isin(severity)]
    if company:
        shown = shown[shown["company_id"].isin(company)]
    st.caption(f"{len(shown)} of {len(issues)} issues. `block`: cannot enter the benchmark until "
               "fixed. `warn`: enters only after human review.")
    st.dataframe(shown, hide_index=True)

    d1, d2 = st.columns(2)
    d1.download_button("Download issues.csv", issues.to_csv(index=False), "issues.csv",
                       "text/csv", key=f"{key}_dl_issues")
    d2.download_button("Download companies.csv", result.companies.to_csv(index=False),
                       "companies.csv", "text/csv", key=f"{key}_dl_companies")


def evaluation_tab() -> None:
    st.write("Generates synthetic payroll files with **planted, labeled errors**, validates them "
             "and measures how many errors were caught. Same numbers as "
             "`python -m payroll_sentinel.cli run`.")
    c1, c2, c3 = st.columns(3)
    seed = c1.number_input("Random seed", min_value=0, value=42, step=1, key="seed",
                           help="Same seed, same data. The README numbers use 42.")
    companies = c2.slider("Companies", min_value=5, max_value=60, value=25, key="companies")
    use_llm = c3.checkbox("Normalize titles with an LLM", key="llm", disabled=not llm_available(),
                          help="Needs LLM_API_KEY (or LLM_PROVIDER=ollama) set before starting "
                               "the app. Off: free, offline keyword rules.")

    if st.button("Run evaluation", type="primary", key="run"):
        st.session_state["eval_params"] = (int(seed), int(companies), bool(use_llm))
    if "eval_params" not in st.session_state:
        return

    try:
        with st.spinner("Generating, validating and scoring..."):
            ev = cached_evaluation(*st.session_state["eval_params"])
    except Exception as exc:  # LLM key, network or rate-limit problems
        st.error(f"The run failed: {exc}")
        return

    s, so = ev.score, ev.oracle_score
    st.success(f"{len(ev.submitted):,} records from {ev.submitted['company_id'].nunique()} companies, "
               f"{int((ev.truth['error_type'] != 'none').sum())} planted errors. "
               f"Title normalizer: **{ev.method}**.")

    m = st.columns(4)
    m[0].metric("Precision", s["overall"]["precision"], help="Flagged rows that really had an error.")
    m[1].metric("Recall", s["overall"]["recall"], help="Errored rows that got flagged.")
    m[2].metric("F1", s["overall"]["f1"])
    m[3].metric("False alarms on clean rows", f"{s['false_alarm_rate']:.2%}")

    st.subheader("Detection by error type")
    st.dataframe(s["per_type"], hide_index=True)

    st.subheader("Peer-comparison detectors")
    st.caption(f"Statistical errors the peer comparison could see: {s['stat_coverage']} "
               "(rows with unmapped titles have no peer group).")
    st.dataframe(s["detectors"].rename(index=DETECTOR_NAMES))

    st.subheader("Title normalization")
    st.dataframe(ev.titles, hide_index=True)
    o = st.columns(2)
    o[0].metric("Recall with perfect titles", so["overall"]["recall"],
                delta=round(so["overall"]["recall"] - s["overall"]["recall"], 3),
                help="Same validator fed the true titles: the gain left for better title normalization.")
    o[1].metric("Statistical errors visible with perfect titles", so["stat_coverage"])

    show_validation(ev.result, key="eval")
    st.download_button("Download evaluation.md", ev.report(), "evaluation.md", "text/markdown",
                       key="dl_report")


def upload_tab() -> None:
    st.write("Upload a payroll CSV to validate it. Required columns: "
             + ", ".join(f"`{c}`" for c in REQUIRED_COLUMNS) + ".")
    st.info("Uploaded files are processed only on this computer and always use the keyword "
            "rules: payroll data is never sent to an LLM.")
    st.download_button("Download a sample file (synthetic, with planted errors)", sample_csv(),
                       "sample_submissions.csv", "text/csv", key="dl_sample")

    file = st.file_uploader("Payroll CSV", type="csv", key="upload")
    if file is None:
        return
    raw = file.getvalue()
    try:
        header = pd.read_csv(io.BytesIO(raw), nrows=0)
    except Exception as exc:
        st.error(f"Could not read the file as CSV: {exc}")
        return
    if missing := missing_columns(header):
        st.error("Missing columns: " + ", ".join(f"`{c}`" for c in missing))
        return

    try:
        with st.spinner("Validating..."):
            result = cached_validation(raw)
    except Exception as exc:  # e.g. text in a numeric column
        st.error(f"Validation failed: {exc}")
        return
    status = result.records["status"]
    m = st.columns(4)
    m[0].metric("Rows", f"{len(status):,}")
    m[1].metric("Blocked rows", int((status == "block").sum()))
    m[2].metric("Rows to review", int((status == "warn").sum()))
    m[3].metric("Companies to reject",
                int(result.companies["decision"].str.startswith("REJECT").sum()))
    show_validation(result, key="upload")


st.set_page_config(page_title="Payroll Sentinel", layout="wide")
st.title("Payroll Sentinel")
st.caption("Validating salary data before it enters a compensation benchmark.")
tab_eval, tab_upload = st.tabs(["Evaluation on synthetic data", "Validate a CSV"])
with tab_eval:
    evaluation_tab()
with tab_upload:
    upload_tab()
