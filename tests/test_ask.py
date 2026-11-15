"""Questions over the benchmark. No network: the LLM is a scripted fake.

The questions here are neutral tokens (q1, q2...): the real evaluation questions
are written by hand in eval/questions.csv.
"""

import json
import re

import pandas as pd
import pytest

from payroll_sentinel import cli
from payroll_sentinel.ask import (MIN_RECORDS, NOT_UNDERSTOOD, REFUSAL, QueryError, QuestionsError,
                                  ask, benchmark_table, build_benchmark, evaluate_questions,
                                  load_questions, parse_query, run_query)
from payroll_sentinel.llm import LLMClient, LLMStats


def q(filters=(), group_by=None, metric="median", column="monthly_salary"):
    return {"in_scope": True, "filters": [dict(zip(("column", "op", "value"), f)) for f in filters],
            "group_by": group_by, "metric": metric, "column": column}


@pytest.fixture
def table():
    rows = ([("data_analyst", "senior", "Campinas", "CLT", s, 0.0) for s in (8000, 9000, 10000, 11000, 12000, 13000)]
            + [("data_analyst", "junior", "São Paulo", "CLT", s, 0.0) for s in (4000, 4500, 5000)]
            + [("software_engineer", "mid", "São Paulo", "CLT", s, 1000.0) for s in (10000, 10500, 11000, 11500, 12000)])
    return pd.DataFrame(rows, columns=["family", "level", "city", "contract_type",
                                       "monthly_salary", "annual_bonus"])


class ScriptedClient:
    """Stands in for an LLM: answers each question with a fixed raw reply."""
    model, tag = "fake-model", "fake_fake-model"

    def __init__(self, replies):
        self.replies = replies
        self.stats = LLMStats()

    def chat(self, system, user, json_mode=False):
        self.stats.calls += 1
        reply = self.replies[user]
        return reply if isinstance(reply, str) else json.dumps(reply)


# --- parse_query: the only door between LLM text and the data -----------------
def test_parse_query_accepts_the_fixed_shape():
    query = parse_query(json.dumps(q([("level", "eq", "senior"), ("family", "in", ["data_analyst"])])))
    assert query.filters == (("family", "in", ("data_analyst",)), ("level", "eq", ("senior",)))
    assert (query.metric, query.column, query.group_by) == ("median", "monthly_salary", None)
    assert parse_query('```json\n{"in_scope": false}\n```') is None      # out of scope


@pytest.mark.parametrize("bad, reason", [
    ("not json", "not JSON"),
    ("[1, 2]", "JSON object"),
    ({**q(), "sql": "DROP TABLE"}, "unknown keys"),
    ({**q(), "in_scope": "yes"}, "in_scope"),
    (q([("company_id", "eq", "EMP001")]), "cannot filter on column"),
    (q([("family", "contains", "data")]), "operator"),
    (q([("family", "eq", "__import__('os').system('x')")]), "not allowed for 'family'"),
    (q([("city", "eq", "campinas")]), "not allowed for 'city'"),          # exact values only
    (q([("level", "in", [])]), "non-empty list"),
    (q([("level", "eq", "senior"), ("level", "eq", "junior")]), "filtered twice"),
    (q(group_by="employee_id"), "cannot group by"),
    (q(metric="max"), "metric"),
    (q(column="employee_name"), "column"),
    ({"in_scope": True, "filters": [{"column": "level", "op": "eq"}], "metric": "median"}, "exactly"),
])
def test_parse_query_rejects_anything_else(bad, reason):
    with pytest.raises(QueryError, match=reason):
        parse_query(bad if isinstance(bad, str) else json.dumps(bad))


# --- run_query: computed by pandas, never by the LLM -------------------------
def test_run_query_median_with_record_count(table):
    answer = run_query(table, parse_query(q([("family", "eq", "data_analyst"), ("level", "eq", "senior"),
                                             ("city", "eq", "Campinas")])))
    assert answer.n == 6 and answer.value == 10500.0
    assert answer.text == ("Median monthly salary (full-time equivalent) for city = Campinas; "
                           "family = data_analyst; level = senior: R$ 10,500 (based on 6 approved records).")


def test_run_query_refuses_small_groups(table):
    answer = run_query(table, parse_query(q([("level", "eq", "junior")])))
    assert answer.n == 3 < MIN_RECORDS and answer.value is None
    assert answer.text.startswith("Not enough data: only 3 approved records match")


def test_run_query_operators_metrics_and_grouping(table):
    count = run_query(table, parse_query(q([("family", "ne", "software_engineer")], metric="count")))
    assert (count.n, count.value) == (9, 9.0)
    p75 = run_query(table, parse_query(q([("level", "in", ["mid"])], metric="p75", column="annual_bonus")))
    assert p75.value == 1000.0
    grouped = run_query(table, parse_query(q(group_by="level", metric="mean")))
    assert grouped.groups.set_index("level")["records"].to_dict() == {"junior": 3, "mid": 5, "senior": 6}
    assert grouped.groups.set_index("level")["value"].to_dict()["junior"] is None   # < 5 records hidden
    assert "1 groups with fewer than 5 records are not shown" in grouped.text


def test_benchmark_uses_only_approved_rows_as_full_time_equivalent():
    table = build_benchmark(seed=1, n_companies=6)
    assert set(table.columns) == {"family", "level", "city", "contract_type", "monthly_salary", "annual_bonus"}
    assert table["family"].notna().all()                  # unmapped titles are 'warn', never 'ok'
    submitted = pd.DataFrame({"row_id": [0, 1], "city": ["Recife"] * 2, "contract_type": ["CLT"] * 2,
                              "weekly_hours": [22, 44], "monthly_salary": [3000.0, 3000.0],
                              "annual_bonus": [0, 0]})

    class Result:
        records = pd.DataFrame({"row_id": [0, 1], "family": ["hr_analyst"] * 2, "level": ["mid"] * 2,
                                "status": ["ok", "block"]})
    small = benchmark_table(submitted, Result())
    assert small["monthly_salary"].tolist() == [6000.0]   # 22 h scaled to 44 h; blocked row dropped


# --- ask: the LLM only fills the form ---------------------------------------------
def test_ask_runs_a_valid_query_and_refuses_the_rest(table):
    client = ScriptedClient({
        "q1": q([("family", "eq", "software_engineer")]),
        "q2": {"in_scope": False},
        "q3": "SELECT * FROM salaries",
        "q4": q([("family", "eq", "pandas.read_csv('/etc/passwd')")]),
    })
    first = ask("q1", table, client)
    assert first.answer.value == 11000.0 and "based on 5 approved records" in first.text
    assert ask("q2", table, client).text == REFUSAL
    for question in ("q3", "q4"):
        rejected = ask(question, table, client)
        assert (rejected.text, rejected.answer, rejected.query) == (NOT_UNDERSTOOD, None, None)
        assert rejected.error
    assert ask("   ", table, client).error == "empty question"
    assert client.stats.calls == 4                        # the empty question never reaches the LLM


# --- Evaluation ----------------------------------------------------------------
def write_questions(path, rows):
    pd.DataFrame(rows, columns=["question", "expected_query"]).to_csv(path, index=False)
    return path


def test_load_questions_checks_the_file(tmp_path):
    with pytest.raises(QuestionsError, match="no questions yet"):
        load_questions(write_questions(tmp_path / "empty.csv", []))
    with pytest.raises(QuestionsError) as err:
        load_questions(write_questions(tmp_path / "bad.csv", [["q1", ""], ["q2", json.dumps(q(metric="max"))],
                                                              ["", '{"in_scope": false}']]))
    msg = str(err.value)
    assert "line 2: expected_query is empty" in msg
    assert "line 3: invalid expected_query (metric 'max' is not allowed)" in msg
    assert "line 4: empty question" in msg


def test_evaluate_questions_scores_queries_and_answers(table, tmp_path):
    expected = q([("family", "eq", "software_engineer")])
    questions = load_questions(write_questions(tmp_path / "qs.csv", [
        ["q1", json.dumps(expected)],                                   # right query
        ["q2", json.dumps(expected)],                                   # extra filter, same answer
        ["q3", json.dumps(expected)],                                   # wrong family
        ["q4", '{"in_scope": false}'],                                  # refused: right
        ["q5", '{"in_scope": false}'],                                  # answered: wrong
    ]))
    client = ScriptedClient({
        "q1": expected,
        "q2": q([("family", "eq", "software_engineer"), ("city", "eq", "São Paulo")]),
        "q3": q([("family", "eq", "data_analyst")]),
        "q4": {"in_scope": False},
        "q5": expected,
    })
    rows = evaluate_questions(questions, table, client)
    assert rows["query_ok"].tolist() == [True, False, False, True, False]
    assert rows["answer_ok"].tolist() == [True, True, False, True, False]


def test_cli_ask_and_eval_ask_with_a_fake_llm(tmp_path, monkeypatch, capsys):
    client = ScriptedClient({"q1": q([("contract_type", "eq", "CLT")], metric="count"),
                             "q2": {"in_scope": False}})
    monkeypatch.setattr(LLMClient, "from_env", classmethod(lambda cls: client))
    monkeypatch.setattr("sys.argv", ["payroll_sentinel", "ask", "q1", "--companies", "6"])
    cli.main()
    out = capsys.readouterr().out
    assert out.startswith("Number of records for contract_type = CLT:")
    assert '"metric": "count"' in out

    monkeypatch.setattr("payroll_sentinel.ask.build_benchmark", lambda: build_benchmark(1, 6))
    path = write_questions(tmp_path / "qs.csv", [["q1", json.dumps(q([("contract_type", "eq", "CLT")],
                                                                     metric="count"))],
                                                 ["q2", '{"in_scope": false}']])
    monkeypatch.setattr("sys.argv", ["payroll_sentinel", "eval-ask", str(path), "--reports",
                                     str(tmp_path / "out")])
    cli.main()
    report = (tmp_path / "out" / "ask_eval_fake_fake-model.md").read_text(encoding="utf-8")
    assert re.search(r"\| query accuracy \(all questions\)\s*\| 2\s*\| 2\s*\| 1\.000", report)
    assert "No errors." in report


def test_committed_questions_file_is_valid():
    from pathlib import Path
    questions = load_questions(Path(__file__).resolve().parents[1] / "eval" / "questions.csv")
    assert questions["expected"].notna().any() and questions["expected"].isna().any()  # in and out of scope


def test_cli_eval_ask_refuses_the_empty_template(monkeypatch, tmp_path):
    template = tmp_path / "questions.csv"
    template.write_text("question,expected_query\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["payroll_sentinel", "eval-ask", str(template)])
    with pytest.raises(SystemExit, match="no questions yet"):
        cli.main()
