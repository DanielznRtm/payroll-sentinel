import json

import pandas as pd
import pytest

from payroll_sentinel.evaluate import score
from payroll_sentinel.generate import generate
from payroll_sentinel.normalize import clean_title, llm_normalize, parse_llm_batch, rule_normalize
from payroll_sentinel.pipeline import missing_columns, run_evaluation, validate_submissions
from payroll_sentinel.taxonomy import legal_min_wage
from payroll_sentinel.validate import rule_checks, validate


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
    rows = [_row(row_id=i, employee_id=f"C1-{i}") for i in range(5)]
    rows.append(_row(row_id=5, employee_id="C1-5", monthly_salary=8.5))
    df = pd.DataFrame(rows)
    result = validate(df, rule_normalize(df["job_title"]))
    assert set(result.issues["cause"]) == {"decimal_shift"}
    assert result.records["flag_ensemble"].isna().all()


def test_duplicate_ids_flag_both_rows():
    issues = rule_checks(pd.DataFrame([_row(row_id=0), _row(row_id=1)]))
    assert sorted(i["row_id"] for i in issues if i["cause"] == "duplicate_id") == [0, 1]


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
    def __init__(self):
        self.calls = 0

    def chat(self, system, user, json_mode=False):
        self.calls += 1
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


def test_validate_submissions_without_row_id(data):
    submitted = data[0].drop(columns=["row_id"])
    assert missing_columns(submitted) == []
    result = validate_submissions(submitted)
    assert "row_id" not in submitted.columns           # caller's frame is not modified
    assert len(result.records) == len(submitted)
    assert missing_columns(submitted.drop(columns=["hire_date"])) == ["hire_date"]
