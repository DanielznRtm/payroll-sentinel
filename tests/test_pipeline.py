import json
import re

import pandas as pd
import pytest

from payroll_sentinel.evaluate import score
from payroll_sentinel.generate import generate
from payroll_sentinel.llm import LLMClient, LLMOutputError, LLMRequestError, LLMStats
from payroll_sentinel.normalize import clean_title, llm_normalize, parse_llm_batch, rule_normalize
from payroll_sentinel.pipeline import missing_columns, run_evaluation, validate_submissions
from payroll_sentinel.taxonomy import legal_min_wage
from payroll_sentinel.validate import _diagnose, rule_checks, validate


@pytest.fixture(scope="module")
def data():
    return generate(seed=1, n_companies=8)


def _row(**kw):
    base = {"row_id": 0, "company_id": "C1", "employee_id": "C1-1", "job_title": "Analista de Dados",
            "city": "Sorocaba", "contract_type": "CLT", "weekly_hours": 44, "monthly_salary": 5000.0,
            "annual_bonus": 0.0, "hire_date": "2022-01-10"}
    base.update(kw)
    return base


def causes(rows):
    return {i["cause"] for i in rule_checks(pd.DataFrame(rows))}


def test_generator_is_deterministic(data):
    again = generate(seed=1, n_companies=8)
    pd.testing.assert_frame_equal(data[0], again[0])
    assert (data[1]["error_type"] != "none").sum() > 0


def test_clean_row_has_no_issues():
    assert causes([_row()]) == set()


def test_min_wage_is_proportional_to_hours():
    assert legal_min_wage(44) == pytest.approx(1621.0)
    # 30h part-time paid R$ 1.300 is legal (proportional minimum ~ R$ 1.105)
    assert causes([_row(weekly_hours=30, monthly_salary=1300.0)]) == set()
    assert causes([_row(monthly_salary=1300.0)]) == {"below_min_wage"}


def test_intern_stipend_is_not_bound_by_min_wage():
    assert causes([_row(contract_type="ESTAGIO", weekly_hours=30, monthly_salary=1100.0)]) == set()


def test_decimal_shift_and_bonus_and_dates():
    assert "decimal_shift" in causes([_row(monthly_salary=8.5)])
    assert "bonus_outlier" in causes([_row(annual_bonus=5000.0 * 40)])
    assert "future_hire_date" in causes([_row(hire_date="2062-03-15")])
    assert "future_hire_date" in causes([_row(hire_date="not a date")])


def test_small_file_without_peer_groups_still_runs_rules():
    # Fewer than MIN_GROUP_SIZE rows per (family, level): no peer comparison is possible.
    rows = [_row(row_id=i, employee_id=f"C1-{i}", monthly_salary=5000.0 + i) for i in range(5)]
    rows.append(_row(row_id=5, employee_id="C1-5", monthly_salary=8.5))
    df = pd.DataFrame(rows)
    result = validate(df, rule_normalize(df["job_title"]))
    assert set(result.issues["cause"]) == {"decimal_shift"}
    assert result.records["flag_ensemble"].isna().all()


@pytest.mark.parametrize("ratio,cause,severity", [
    (12.0, "annual_as_monthly", "block"),
    (25.0, "annual_as_monthly", "block"),     # 13.33 salaries of someone paid ~2x the median
    (7.0, "annual_as_monthly", "warn"),       # could also be a real top salary
    (1 / 12, "divided_by_12", "block"),       # the mirror image
    (1 / 7, "divided_by_12", "warn"),
    (180.0, "extreme_value", "block"),
    (1 / 40, "extreme_value", "block"),
    (3.0, "level_salary_mismatch", "warn"),
    (0.4, "level_salary_mismatch", "warn"),
    (1.3, "statistical_outlier", "warn"),
])
def test_cause_diagnosis_works_both_ways(ratio, cause, severity):
    assert _diagnose(ratio) == (cause, severity)


def test_duplicate_ids_flag_both_rows():
    issues = rule_checks(pd.DataFrame([_row(row_id=0), _row(row_id=1)]))
    assert sorted(i["row_id"] for i in issues if i["cause"] == "duplicate_id") == [0, 1]
    assert "duplicate_record" not in {i["cause"] for i in issues}   # one finding, not two


def test_rows_copied_under_a_new_id_go_to_review():
    rows = [_row(row_id=0, employee_id="C1-1"), _row(row_id=1, employee_id="C1-2"),
            _row(row_id=2, employee_id="C1-3", monthly_salary=5100.0),
            _row(row_id=3, employee_id="C2-1", company_id="C2")]   # same record, other company
    copies = [i for i in rule_checks(pd.DataFrame(rows)) if i["cause"] == "duplicate_record"]
    assert [i["row_id"] for i in copies] == [0, 1]
    assert {i["severity"] for i in copies} == {"warn"}


@pytest.mark.parametrize("title,family,level", [
    ("Analista de Dados Sr.", "data_analyst", "senior"),
    ("ENGENHEIRA DE SOFTWARE III", "software_engineer", "senior"),
    ("Estágio - Analista Financeiro", "financial_analyst", "intern"),
    ("Operador de Producao | Turno B", "production_operator", "mid"),
    ("Cientista de Dados I", "data_scientist", "junior"),
])
def test_rule_normalizer(title, family, level):
    out = rule_normalize(pd.Series([title])).iloc[0]
    assert (out["family"], out["level"]) == (family, level)


def test_clean_title_strips_accents_and_noise():
    assert clean_title("  Técnico de Manutenção  (Sênior) ") == "tecnico de manutencao senior"
    assert clean_title(None) == ""


def test_parse_llm_batch_validates_output():
    raw = '```json\n{"results": [{"id": 0, "family": "product_manager", "level": "senior"},' \
          '{"id": 1, "family": "astronaut", "level": "mid"}, {"id": 2, "family": null, "level": "mid"},' \
          '{"id": 9, "family": "sales_rep", "level": "mid"}]}\n```'
    assert parse_llm_batch(raw, [0, 1, 2]) == {0: ("product_manager", "senior"), 2: (None, "mid")}
    assert parse_llm_batch("sorry, I can't", [0]) == {}


class FakeClient:
    """Stands in for an LLM: answers every title as a senior product manager."""
    model, tag, label = "fake-model", "fake_fake-model", "fake-model"

    def __init__(self):
        self.calls = 0
        self.stats = LLMStats()

    def chat(self, system, user, json_mode=False):
        self.calls += 1
        self.stats.calls += 1
        ids = [int(line.split(":")[0]) for line in user.splitlines()]
        return json.dumps({"results": [{"id": i, "family": "product_manager", "level": "senior"}
                                       for i in ids]})


def test_llm_normalize_dedupes_batches_and_caches(tmp_path):
    titles = pd.Series(["PO Sr", "po sr", "PO  SR", "Product Owner III", ""])
    client = FakeClient()
    cache = tmp_path / "cache.json"
    out = llm_normalize(titles, client, cache_path=cache, batch_size=1)
    assert client.calls == 2                      # only 2 unique non-empty titles
    assert (out["source"].iloc[:4] == "llm").all()
    assert out["source"].iloc[4] == "rules"      # empty title never sent
    second = FakeClient()
    llm_normalize(titles, second, cache_path=cache)
    assert second.calls == 0                      # everything served from cache


class RejectingClient:
    """Stands in for an API that rejects every request (unknown model, bad key)."""
    def __init__(self):
        self.calls = 0

    def chat(self, system, user, json_mode=False):
        self.calls += 1
        raise LLMRequestError("HTTP 404 for model 'x': model not found")


class FlakyClient:
    """Stands in for a network that always times out."""
    def chat(self, system, user, json_mode=False):
        raise TimeoutError("read timed out")


def test_llm_normalize_stops_at_first_rejected_request(tmp_path):
    client = RejectingClient()
    with pytest.raises(LLMRequestError, match="model not found"):
        llm_normalize(pd.Series(["PO Sr", "Tech Lead"]), client, batch_size=1)
    assert client.calls == 1                      # no point trying the other batches


def test_llm_normalize_refuses_to_pass_rules_off_as_llm():
    with pytest.raises(RuntimeError, match="All 2 LLM batches failed"):
        llm_normalize(pd.Series(["PO Sr", "Tech Lead"]), FlakyClient(), batch_size=1)


def test_llm_client_error_keeps_provider_message(monkeypatch):
    class Resp:
        ok, status_code, text = False, 404, '{"error": {"message": "model is no longer available"}}'

    monkeypatch.setattr("payroll_sentinel.llm.requests.post", lambda *a, **k: Resp())
    client = LLMClient(base_url="http://fake", model="m", min_interval=0)
    with pytest.raises(LLMRequestError, match="no longer available"):
        client.chat("system", "user")


def test_end_to_end_quality(data):
    submitted, truth = data
    result = validate(submitted, rule_normalize(submitted["job_title"]))
    s = score(result, truth)
    assert s["overall"]["precision"] > 0.85
    assert s["overall"]["recall"] > 0.75
    assert s["false_alarm_rate"] < 0.01


def test_run_evaluation_matches_direct_scoring(data):
    submitted, truth = data
    ev = run_evaluation(seed=1, n_companies=8)
    direct = score(validate(submitted, rule_normalize(submitted["job_title"]), seed=1), truth)
    assert ev.score["overall"] == direct["overall"]
    assert ev.report().startswith("# Evaluation report")
    assert ev.oracle_score["overall"]["recall"] >= ev.score["overall"]["recall"]


def test_llm_report_states_coverage(monkeypatch, tmp_path):
    monkeypatch.setattr(LLMClient, "from_env", classmethod(lambda cls: FakeClient()))
    ev = run_evaluation(seed=1, n_companies=8, use_llm=True, cache_path=tmp_path / "c.json")
    assert ev.llm_coverage == 1.0
    assert "Titles answered by the LLM: 100.0%" in ev.report()
    assert re.search(r"LLM run: [1-9][0-9]* LLM calls", ev.report())
    assert ev.method == "LLM (fake-model)"
    # one cache file per provider and model, never a shared one
    assert (tmp_path / "c_fake_fake-model.json").exists()
    assert not (tmp_path / "c.json").exists()
    again = run_evaluation(seed=1, n_companies=8, use_llm=True, cache_path=tmp_path / "c.json")
    assert "not a timing measurement" in again.report()   # all from cache: 0 calls
    assert run_evaluation(seed=1, n_companies=8).llm_coverage is None


def test_validate_submissions_without_row_id(data):
    submitted = data[0].drop(columns=["row_id"])
    assert missing_columns(submitted) == []
    result = validate_submissions(submitted)
    assert "row_id" not in submitted.columns           # caller's frame is not modified
    assert len(result.records) == len(submitted)
    assert missing_columns(submitted.drop(columns=["hire_date"])) == ["hire_date"]


class FakeResponse:
    def __init__(self, status, body=None):
        self.status_code, self.ok, self._body, self.text = status, status < 400, body, ""

    def json(self):
        return self._body


def test_llm_client_counts_calls_retries_and_rate_limits(monkeypatch):
    replies = iter([FakeResponse(429), FakeResponse(200, {"choices": [{"message": {"content": "hi"}}]})])
    monkeypatch.setattr("payroll_sentinel.llm.requests.post", lambda *a, **k: next(replies))
    monkeypatch.setattr("payroll_sentinel.llm.time.sleep", lambda s: None)
    client = LLMClient(base_url="http://x", model="m", min_interval=0)
    assert client.chat("s", "u") == "hi"
    assert (client.stats.calls, client.stats.requests, client.stats.rate_limited) == (1, 2, 1)
    assert "1 rate-limit (429) responses" in client.stats.summary()


def test_llm_stats_separate_api_time_from_pacing(monkeypatch):
    clock = {"t": 100.0}                                  # fake clock: no real waiting

    def post(*args, **kwargs):
        clock["t"] += 2.0                                 # each API response takes 2 s
        return FakeResponse(200, {"choices": [{"message": {"content": "hi"}}]})

    monkeypatch.setattr("payroll_sentinel.llm.requests.post", post)
    monkeypatch.setattr("payroll_sentinel.llm.time.sleep", lambda s: clock.update(t=clock["t"] + s))
    monkeypatch.setattr("payroll_sentinel.llm.time.monotonic", lambda: clock["t"])
    client = LLMClient(base_url="http://x", model="m", min_interval=4.5)
    client.chat("s", "u")
    client.chat("s", "u")                                 # waits 2.5 s to keep 4.5 s between calls
    assert client.stats.api_seconds == pytest.approx(4.0)
    assert client.stats.seconds == pytest.approx(6.5)
    assert "4.0 s waiting for the API (2.0 s per request)" in client.stats.summary()


def test_llm_client_sends_reasoning_effort_only_when_set(monkeypatch):
    sent = []

    def post(*args, **kwargs):
        sent.append(kwargs["json"])
        return FakeResponse(200, {"choices": [{"message": {"content": "hi"}}]})

    monkeypatch.setattr("payroll_sentinel.llm.requests.post", post)
    plain = LLMClient(base_url="http://x", model="m", min_interval=0)
    plain.chat("s", "u")
    assert "reasoning_effort" not in sent[0]          # Gemini runs keep the exact payload
    assert plain.label == "m"
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_REASONING_EFFORT", "low")
    thinking = LLMClient.from_env()
    thinking.min_interval = 0
    thinking.chat("s", "u")
    assert sent[1]["reasoning_effort"] == "low"
    assert thinking.label == "openai/gpt-oss-20b, reasoning_effort=low"   # reports say how it ran


def test_invalid_json_from_the_model_fails_only_that_batch(monkeypatch):
    class Resp:
        ok, status_code = False, 400
        text = '{"error": {"code": "json_validate_failed", "failed_generation": ""}}'

    monkeypatch.setattr("payroll_sentinel.llm.requests.post", lambda *a, **k: Resp())
    client = LLMClient(base_url="http://fake", model="m", min_interval=0)
    with pytest.raises(LLMOutputError, match="did not return valid JSON"):
        client.chat("s", "u", json_mode=True)

    class HalfBrokenClient(FakeClient):
        def chat(self, system, user, json_mode=False):
            if "tech lead" in user:                   # titles reach the model cleaned
                raise LLMOutputError("model 'm' did not return valid JSON")
            return super().chat(system, user, json_mode)

    out = llm_normalize(pd.Series(["PO Sr", "Tech Lead"]), HalfBrokenClient(), batch_size=1)
    assert out["source"].tolist() == ["llm", "rules"]  # the bad batch falls back to rules


def test_llm_client_tag_and_model_list(monkeypatch):
    client = LLMClient(base_url="http://x", model="llama3.1:8b", provider="ollama")
    assert client.tag == "ollama_llama3.1-8b"          # ':' is not allowed in Windows file names
    body = {"data": [{"id": "b-model"}, {"id": "a-model"}]}
    monkeypatch.setattr("payroll_sentinel.llm.requests.get", lambda *a, **k: FakeResponse(200, body))
    assert client.list_models() == ["a-model", "b-model"]


def test_annotate_submission_splits_accepted_rows_and_rows_to_fix(data, tmp_path, monkeypatch, capsys):
    from payroll_sentinel import cli
    from payroll_sentinel.pipeline import annotate_submission

    submitted = data[0].drop(columns=["row_id"]).head(300)
    result = validate_submissions(submitted)
    annotated = annotate_submission(submitted, result)
    assert list(annotated.columns) == ["row_id", *submitted.columns, "status", "issues"]
    assert annotated["status"].tolist() == result.records["status"].tolist()
    blocked = annotated[annotated["status"].eq("block")]
    assert len(blocked) and blocked["issues"].ne("").all()       # every blocked row says why
    assert annotated.loc[annotated["status"].eq("ok"), "issues"].eq("").all()

    path = tmp_path / "file.csv"
    submitted.to_csv(path, index=False)
    monkeypatch.setattr("sys.argv", ["payroll_sentinel", "validate", str(path), "--reports", str(tmp_path)])
    cli.main()
    accepted = pd.read_csv(tmp_path / "accepted_rows.csv")
    to_fix = pd.read_csv(tmp_path / "rows_to_fix.csv")
    assert len(accepted) + len(to_fix) == len(submitted)
    assert set(to_fix["status"]) == {"block"} and "block" not in set(accepted["status"])
    assert "rows to fix in" in capsys.readouterr().out
