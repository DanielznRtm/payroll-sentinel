"""Answer questions about the validated benchmark without letting the LLM run code.

The LLM only translates a question into a small JSON query with a fixed shape:

    {"in_scope": true,
     "filters": [{"column": "family", "op": "eq", "value": "data_analyst"}],
     "group_by": null, "metric": "median", "column": "monthly_salary"}

The code checks every field against allow-lists (columns, operators, metrics
and the exact values each column may take) and runs the query with pandas
boolean masks. Nothing the LLM writes is executed: no eval/exec and no
`DataFrame.query` strings. Every number in the answer is computed here and the
answer text is a template filled by the code.

Safety rules:
- only rows the validator approved (status ok) are in the benchmark, with
  salaries as full-time equivalents;
- every answer states how many records it used, and fewer than MIN_RECORDS
  records gives "not enough data" (it also stops a filter from singling out
  one person's salary);
- anything outside these columns is refused with one sentence.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .generate import generate
from .normalize import rule_normalize
from .taxonomy import CITIES, FAMILIES, LEVELS
from .validate import ValidationResult, full_time_equivalent, validate

MIN_RECORDS = 5
MAX_QUESTION_CHARS = 500

FILTER_VALUES: dict[str, list[str]] = {
    "family": list(FAMILIES),
    "level": list(LEVELS),
    "city": list(CITIES),
    "contract_type": ["CLT", "ESTAGIO"],
}
OPERATORS = {"eq", "ne", "in"}
VALUE_COLUMNS = {"monthly_salary": "monthly salary (full-time equivalent)",
                 "annual_bonus": "annual bonus"}
METRICS = {"median": "Median", "mean": "Average", "p25": "25th percentile",
           "p75": "75th percentile", "count": "Number of records"}
QUERY_KEYS = {"in_scope", "filters", "group_by", "metric", "column"}

REFUSAL = ("This question is outside what the benchmark can answer: it only covers salaries "
           "and bonuses by job family, level, city and contract type.")
NOT_UNDERSTOOD = "Sorry, the question could not be turned into a valid benchmark query."


class QueryError(ValueError):
    """The query is not valid: it is never executed."""


@dataclass(frozen=True)
class Query:
    filters: tuple[tuple[str, str, tuple[str, ...]], ...]  # (column, op, values), sorted
    group_by: str | None
    metric: str
    column: str

    def to_dict(self) -> dict:
        return {"in_scope": True,
                "filters": [{"column": c, "op": op, "value": list(v) if op == "in" else v[0]}
                            for c, op, v in self.filters],
                "group_by": self.group_by, "metric": self.metric, "column": self.column}


def parse_query(raw: str | dict) -> Query | None:
    """Validate an LLM answer. Returns None for an out-of-scope question.

    Raises QueryError for anything that is not exactly the allowed shape.
    """
    if isinstance(raw, str):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise QueryError(f"not JSON ({exc.msg})") from None
    if not isinstance(raw, dict):
        raise QueryError("the query must be a JSON object")
    if extra := set(raw) - QUERY_KEYS:
        raise QueryError(f"unknown keys: {sorted(extra)}")
    if raw.get("in_scope") is False:
        return None
    if raw.get("in_scope") is not True:
        raise QueryError("in_scope must be true or false")

    filters, seen = [], set()
    raw_filters = raw.get("filters") or []
    if not isinstance(raw_filters, list):
        raise QueryError("filters must be a list")
    for f in raw_filters:
        if not isinstance(f, dict) or set(f) != {"column", "op", "value"}:
            raise QueryError("each filter needs exactly column, op and value")
        col, op, value = f["column"], f["op"], f["value"]
        if col not in FILTER_VALUES:
            raise QueryError(f"cannot filter on column {col!r}")
        if col in seen:
            raise QueryError(f"column {col!r} is filtered twice")
        seen.add(col)
        if op not in OPERATORS:
            raise QueryError(f"operator {op!r} is not allowed")
        values = value if op == "in" else [value]
        if not isinstance(values, list) or not values:
            raise QueryError(f"operator 'in' needs a non-empty list for {col!r}")
        for v in values:
            if not isinstance(v, str) or v not in FILTER_VALUES[col]:
                raise QueryError(f"value {v!r} is not allowed for {col!r}")
        filters.append((col, op, tuple(sorted(set(values)))))

    group_by = raw.get("group_by")
    if group_by is not None and group_by not in FILTER_VALUES:
        raise QueryError(f"cannot group by {group_by!r}")
    metric = raw.get("metric")
    if metric not in METRICS:
        raise QueryError(f"metric {metric!r} is not allowed")
    column = raw.get("column") or "monthly_salary"
    if column not in VALUE_COLUMNS:
        raise QueryError(f"column {column!r} is not allowed")
    if metric == "count":
        column = "monthly_salary"  # a count does not depend on the value column
    return Query(tuple(sorted(filters)), group_by, metric, column)


# --- Running a query --------------------------------------------------------
def benchmark_table(submitted: pd.DataFrame, result: ValidationResult) -> pd.DataFrame:
    """Approved rows only (status ok), with full-time-equivalent monthly salaries."""
    rec = result.records[["row_id", "family", "level", "status"]]
    df = submitted.merge(rec, on="row_id", how="inner")
    df = df[df["status"].eq("ok")]
    salary = pd.to_numeric(df["monthly_salary"], errors="coerce")
    return pd.DataFrame({
        "family": df["family"], "level": df["level"], "city": df["city"],
        "contract_type": df["contract_type"],
        "monthly_salary": full_time_equivalent(salary, df["weekly_hours"]).round(2),
        "annual_bonus": pd.to_numeric(df["annual_bonus"], errors="coerce"),
    }).reset_index(drop=True)


def build_benchmark(seed: int = 42, n_companies: int = 25) -> pd.DataFrame:
    """The synthetic benchmark the README numbers use, validated with the keyword rules."""
    submitted, _ = generate(seed=seed, n_companies=n_companies)
    result = validate(submitted, rule_normalize(submitted["job_title"]), seed=seed)
    return benchmark_table(submitted, result)


def _metric(values: pd.Series, metric: str) -> float:
    if metric == "count":
        return float(len(values))
    if metric == "median":
        return float(values.median())
    if metric == "mean":
        return float(values.mean())
    return float(values.quantile(0.25 if metric == "p25" else 0.75))


def _describe(query: Query) -> str:
    if not query.filters:
        return "all approved records"
    parts = []
    for col, op, values in query.filters:
        shown = ", ".join(values)
        parts.append(f"{col} {'not ' if op == 'ne' else ''}{'in' if op == 'in' else '='} {shown}")
    return "; ".join(parts)


def _money(value: float) -> str:
    return f"R$ {value:,.0f}"


@dataclass
class Answer:
    query: Query
    n: int                          # records used
    value: float | None             # None: not enough data, or a grouped answer
    groups: pd.DataFrame | None     # one row per group: group, records, value (None if < MIN_RECORDS)
    text: str

    def result_key(self) -> tuple:
        """What the answer says, for comparing two answers."""
        groups = None if self.groups is None else tuple(
            (str(r[0]), int(r[1]), None if pd.isna(r[2]) else round(float(r[2]), 2))
            for r in self.groups.itertuples(index=False))
        return self.n, None if self.value is None else round(self.value, 2), groups


def run_query(table: pd.DataFrame, query: Query) -> Answer:
    """Execute a validated query with boolean masks. Never evaluates text."""
    mask = pd.Series(True, index=table.index)
    for col, op, values in query.filters:
        hit = table[col].isin(values)
        mask &= ~hit if op == "ne" else hit
    rows = table[mask]
    values = pd.to_numeric(rows[query.column], errors="coerce").dropna()
    n = int(len(values))
    label = METRICS[query.metric]
    what = "" if query.metric == "count" else f" {VALUE_COLUMNS[query.column]}"
    scope = _describe(query)

    if n < MIN_RECORDS:
        text = (f"Not enough data: only {n} approved records match ({scope}). "
                f"At least {MIN_RECORDS} are needed for an answer.")
        return Answer(query, n, None, None, text)

    if query.group_by is None:
        value = _metric(values, query.metric)
        shown = f"{int(value)}" if query.metric == "count" else _money(value)
        text = f"{label}{what} for {scope}: {shown} (based on {n} approved records)."
        return Answer(query, n, value, None, text)

    groups = []
    for key, part in rows.groupby(query.group_by, sort=True):
        part_values = pd.to_numeric(part[query.column], errors="coerce").dropna()
        k = int(len(part_values))
        groups.append({query.group_by: key, "records": k,
                       "value": _metric(part_values, query.metric) if k >= MIN_RECORDS else None})
    groups_df = pd.DataFrame(groups)
    # object dtype keeps None (not enough data) apart from a real number; float would turn it into NaN
    groups_df["value"] = pd.Series([g["value"] for g in groups], index=groups_df.index, dtype=object)
    hidden = int(groups_df["value"].isna().sum())
    text = (f"{label}{what} for {scope}, by {query.group_by} "
            f"(based on {n} approved records).")
    if hidden:
        text += f" {hidden} groups with fewer than {MIN_RECORDS} records are not shown."
    return Answer(query, n, None, groups_df, text)


# --- Asking the LLM ---------------------------------------------------------
SYSTEM_PROMPT = """You translate questions about a Brazilian salary benchmark into a JSON query.
You never answer the question yourself and never write code.

The benchmark has one row per employee with these columns:
- family: {families}
- level: intern (estágio), junior, mid (pleno), senior, lead (especialista, líder, staff)
- city: {cities}
- contract_type: CLT, ESTAGIO (internship)
- monthly_salary: monthly base salary in BRL, full-time equivalent
- annual_bonus: annual bonus in BRL (bônus, PLR)

Answer ONLY with JSON in one of these two shapes:
{{"in_scope": true, "filters": [{{"column": <family|level|city|contract_type>, "op": <"eq"|"ne"|"in">, "value": <a value, or a list of values for "in">}}],
  "group_by": <null or family|level|city|contract_type>, "metric": <"median"|"mean"|"p25"|"p75"|"count">,
  "column": <"monthly_salary"|"annual_bonus">}}
{{"in_scope": false}}

Rules:
- Use only the exact values listed above. "salário" means monthly_salary; the default metric is median.
- "média" is mean; "quantos" is count; "quartil inferior"/"p25" is p25; "quartil superior"/"p75" is p75.
- "por cidade", "por nível"... means group_by.
- Use {{"in_scope": false}} for anything else: companies, opinions, advice, single people,
  or data the columns above do not have."""


def _system_prompt() -> str:
    families = ", ".join(f"{key} ({f['label']})" for key, f in FAMILIES.items())
    return SYSTEM_PROMPT.format(families=families, cities=", ".join(CITIES))


@dataclass
class AskResult:
    question: str
    query: Query | None      # None: refused or not understood
    answer: Answer | None
    text: str
    error: str | None = None  # why the LLM output was rejected, if it was


def ask(question: str, table: pd.DataFrame, client) -> AskResult:
    question = question.strip()
    if not question:
        return AskResult(question, None, None, NOT_UNDERSTOOD, "empty question")
    if len(question) > MAX_QUESTION_CHARS:
        return AskResult(question, None, None, NOT_UNDERSTOOD,
                         f"question longer than {MAX_QUESTION_CHARS} characters")
    raw = client.chat(_system_prompt(), question, json_mode=True)
    try:
        query = parse_query(raw)
    except QueryError as exc:
        return AskResult(question, None, None, NOT_UNDERSTOOD, str(exc))
    if query is None:
        return AskResult(question, None, None, REFUSAL)
    answer = run_query(table, query)
    return AskResult(question, query, answer, answer.text)


# --- Evaluation on eval/questions.csv -----------------------------------------
class QuestionsError(ValueError):
    """The questions file cannot be used as ground truth."""


def load_questions(path: str | Path) -> pd.DataFrame:
    """Columns question, expected_query (JSON, or {"in_scope": false})."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    if missing := [c for c in ("question", "expected_query") if c not in df.columns]:
        raise QuestionsError(f"Missing columns: {', '.join(missing)}")
    if df.empty:
        raise QuestionsError("The file has no questions yet.")
    problems, expected = [], []
    for i, row in df.iterrows():
        line = i + 2
        if not row["question"].strip():
            problems.append(f"line {line}: empty question")
        if not row["expected_query"].strip():
            problems.append(f"line {line}: expected_query is empty")
            expected.append(None)
            continue
        try:
            expected.append(parse_query(row["expected_query"]))
        except QueryError as exc:
            problems.append(f"line {line}: invalid expected_query ({exc})")
            expected.append(None)
    if problems:
        raise QuestionsError("\n".join(problems))
    out = df[["question"]].copy()
    out["expected"] = expected
    return out


def _query_text(query: Query | None) -> str:
    return '{"in_scope": false}' if query is None else json.dumps(query.to_dict(), ensure_ascii=False)


def evaluate_questions(questions: pd.DataFrame, table: pd.DataFrame, client) -> pd.DataFrame:
    """One row per question: is the query right, and is the answer right?

    The right answer is computed by the code from the expected query, so a
    different query that happens to give the same numbers still counts as a
    right answer (but not as a right query).
    """
    rows = []
    for question, expected in zip(questions["question"], questions["expected"]):
        got = ask(question, table, client)
        if expected is None:
            query_ok = answer_ok = got.query is None and got.error is None
        elif got.query is None:
            query_ok = answer_ok = False
        else:
            query_ok = got.query == expected
            answer_ok = run_query(table, expected).result_key() == got.answer.result_key()
        llm_query = f"rejected: {got.error}" if got.error else _query_text(got.query)
        rows.append({"question": question, "in_scope": expected is not None,
                     "expected_query": _query_text(expected), "llm_query": llm_query,
                     "query_ok": query_ok, "answer_ok": answer_ok})
    return pd.DataFrame(rows)


def ask_report(rows: pd.DataFrame, source: str, model: str, llm_run: str) -> str:
    inside, outside = rows[rows["in_scope"]], rows[~rows["in_scope"]]

    def share(k: int, n: int) -> str:
        return f"{k / n:.3f}" if n else "n/a"

    summary = pd.DataFrame([
        {"metric": "query accuracy (all questions)", "correct": int(rows["query_ok"].sum()),
         "questions": len(rows), "share": share(int(rows["query_ok"].sum()), len(rows))},
        {"metric": "answer accuracy (all questions)", "correct": int(rows["answer_ok"].sum()),
         "questions": len(rows), "share": share(int(rows["answer_ok"].sum()), len(rows))},
        {"metric": "in-scope answers right", "correct": int(inside["answer_ok"].sum()),
         "questions": len(inside), "share": share(int(inside["answer_ok"].sum()), len(inside))},
        {"metric": "out-of-scope questions refused", "correct": int(outside["answer_ok"].sum()),
         "questions": len(outside), "share": share(int(outside["answer_ok"].sum()), len(outside))},
    ])
    errors = rows[~(rows["query_ok"] & rows["answer_ok"])]
    md = (lambda df: df.to_markdown(index=False, disable_numparse=True))
    return "\n".join([
        "# Ask the benchmark: evaluation", "",
        f"File `{source}`: {len(rows)} questions, {len(inside)} in scope and {len(outside)} out of "
        f"scope. Model: **{model}**. Right answers are computed by the code from the expected query.",
        "", f"LLM run: {llm_run}.", "",
        "## 1. Accuracy", "", md(summary), "",
        "A wrong query can still give the right answer (for example, an extra filter that "
        "changes nothing); that counts for the answer, not for the query.", "",
        f"## 2. Every error ({len(errors)})", "",
        md(errors[["question", "expected_query", "llm_query", "query_ok", "answer_ok"]])
        if len(errors) else "No errors.", "",
    ])


def run_ask_eval(path: str | Path, table: pd.DataFrame | None = None) -> tuple[str, str]:
    """Run the whole evaluation with the LLM from the environment. Returns (file tag, report)."""
    from .llm import LLMClient
    questions = load_questions(path)
    client = LLMClient.from_env()
    table = build_benchmark() if table is None else table
    start = time.perf_counter()
    rows = evaluate_questions(questions, table, client)
    run = f"{client.stats.summary()}; {time.perf_counter() - start:.1f} s in total"
    return client.tag, ask_report(rows, Path(path).as_posix(), client.model, run)
