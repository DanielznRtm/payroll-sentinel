"""LLM claim extraction (with a fake client: no test touches the network), evaluation and CLI."""

import json
import sys

import pytest

from payroll_sentinel import cli
from payroll_sentinel.claims import MAX_PETITION_CHARS, llm_extract, parse_extraction, rule_extract
from payroll_sentinel.claims_eval import HeldoutError, evaluate_claims, extraction_from_truth, load_heldout_petitions
from payroll_sentinel.llm import LLMOutputError, LLMStats
from payroll_sentinel.petitions import generate_petitions
from salary_core import load_params

from test_claims import GOOD, MINI

P = load_params(2026)


class FakeClient:
    """Stands in for an LLM: always gives the same answer, or raises it."""
    model, tag, label = "fake-model", "fake_fake-model", "fake-model"

    def __init__(self, answer):
        self.answer, self.calls, self.stats = answer, 0, LLMStats()

    def chat(self, system, user, json_mode=False):
        self.calls += 1
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def test_llm_answer_is_checked_and_cached(tmp_path):
    cache = tmp_path / "cache.json"
    client = FakeClient(json.dumps(GOOD))
    first = llm_extract(MINI, client, cache)
    assert first == parse_extraction(GOOD, MINI) and first.problems == ()
    again = llm_extract(MINI, FakeClient("never asked"), cache)    # answered from the cache
    assert again == first and client.calls == 1


def test_a_hallucinated_salary_never_reaches_the_triage(tmp_path):
    r = llm_extract(MINI, FakeClient(json.dumps({**GOOD, "monthly_salary": "9000.00"})), tmp_path / "c.json")
    assert r.monthly_salary is None and "monthly_salary: 9000.00 is not written in the petition" in r.problems


def test_bad_model_output_is_reported_not_cached(tmp_path):
    cache = tmp_path / "cache.json"
    r = llm_extract(MINI, FakeClient(LLMOutputError("not JSON")), cache)
    assert r.claims == () and r.problems[0].startswith("model output rejected")
    assert not cache.exists()                                   # the next run asks again
    assert llm_extract("x" * (MAX_PETITION_CHARS + 1), FakeClient("{}")).problems[0].startswith("petition longer")


def test_a_perfect_extractor_scores_everything_right():
    petitions = generate_petitions(20, seed=3)
    truth_of = {p.text: p.truth for p in petitions}
    ev = evaluate_claims(petitions, lambda text: extraction_from_truth(truth_of[text]), P, "oracle", "test")
    assert ev.totals_match == 20 and ev.errors == []
    assert all(fp == fn == 0 for _, fp, fn in ev.claims.values())
    assert "Priced total equal to the truth's: 20/20 (100.0 %)" in ev.report()


def test_rules_are_scored_with_their_trap_errors():
    petitions = generate_petitions(20, seed=3)
    ev = evaluate_claims(petitions, rule_extract, P, "keyword rules", "test")
    invented = sum(fp for _, fp, _ in ev.claims.values())
    assert invented > 0 and sum(fn for _, _, fn in ev.claims.values()) == 0
    assert any("invented claim" in what for _, what in ev.errors)


def test_triage_command_prints_the_priced_claims(tmp_path, monkeypatch, capsys):
    petition = tmp_path / "petition.txt"
    petition.write_text(MINI, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["payroll_sentinel", "triage", str(petition)])
    cli.main()
    out = capsys.readouterr().out
    assert "overtime: R$ 43,363.64" in out             # 20 h x 53 months, divisor 220 (test_salary_core_labor)
    assert "other (danos morais): not priced" in out
    assert "Priced total: R$ " in out


# --- Hand-written petitions: the loader refuses an unfair truth.json --------------

MINI_TRUTH = {"admission_date": "2021-03-15", "termination_date": "2025-08-10", "termination_type": "without_cause",
              "monthly_salary": "6000.00", "weekly_hours": "44", "filing_date": "2026-02-03",
              "claims": [{"type": "overtime", "hours_per_month": "20"}, {"type": "other", "label": "danos morais"}]}


def _folder(tmp_path, truth):
    (tmp_path / "H01.txt").write_text(MINI, encoding="utf-8")
    (tmp_path / "truth.json").write_text(json.dumps(truth, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_heldout_petitions_load_with_their_truth(tmp_path):
    petitions = load_heldout_petitions(_folder(tmp_path, {"H01.txt": MINI_TRUTH}))
    assert [(p.id, p.truth) for p in petitions] == [("H01", MINI_TRUTH)]


@pytest.mark.parametrize("truth,message", [
    ({}, "H01.txt: no entry in truth.json"),
    ({"H01.txt": MINI_TRUTH, "H02.txt": MINI_TRUTH}, "H02.txt has no petition file"),
    ({"H01.txt": {**MINI_TRUTH, "monthly_salary": "6500.00"}}, "monthly_salary 6500.00 is not written in digits"),
    ({"H01.txt": {**MINI_TRUTH, "filing_date": "2026-02-04"}}, "filing_date 2026-02-04 is not written as a date"),
    ({"H01.txt": {**MINI_TRUTH, "claims": [{"type": "hazard_pay"}]}}, "unknown claim"),
])
def test_an_unfair_truth_is_refused_before_any_run(tmp_path, truth, message):
    with pytest.raises(HeldoutError, match=message):
        load_heldout_petitions(_folder(tmp_path, truth))


def test_an_empty_folder_is_not_ready(tmp_path):
    with pytest.raises(HeldoutError, match="no petitions"):
        load_heldout_petitions(tmp_path)


def test_eval_claims_on_a_heldout_folder_writes_its_report(tmp_path, monkeypatch, capsys):
    (tmp_path / "heldout").mkdir()
    folder = _folder(tmp_path / "heldout", {"H01.txt": MINI_TRUTH})
    monkeypatch.setattr(sys, "argv", ["payroll_sentinel", "eval-claims", "--heldout", str(folder),
                                      "--reports", str(tmp_path / "reports")])
    cli.main()
    report = (tmp_path / "reports" / "claims_heldout_rules.md").read_text(encoding="utf-8")
    assert "written by hand" in report
    assert "H01: invented claim: thirteenth" in report    # the rules take "O 13º ... foi pago" for a claim
