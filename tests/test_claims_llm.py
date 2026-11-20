"""LLM claim extraction (with a fake client: no test touches the network), evaluation and CLI."""

import json
import sys

from payroll_sentinel import cli
from payroll_sentinel.claims import MAX_PETITION_CHARS, llm_extract, parse_extraction, rule_extract
from payroll_sentinel.claims_eval import evaluate_claims, extraction_from_truth
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
