"""Synthetic petitions, the extraction checks and the keyword baseline."""

import json
from datetime import date
from decimal import Decimal as D

import pytest

from payroll_sentinel.claims import (COMPUTED_CLAIMS, dates_in_text, numbers_in_text, parse_extraction,
                                     rule_extract)
from payroll_sentinel.petitions import generate_petitions

PETITIONS = generate_petitions(60, seed=7)

MINI = """EXCELENTÍSSIMO(A) SENHOR(A) JUIZ(A) DA VARA DO TRABALHO DE SANTOS

O Reclamante foi admitido em 15/03/2021, com salário mensal de R$ 6.000,00. A jornada contratual era de
44 horas semanais. Foi dispensado sem justa causa em 10/08/2025. Trabalhava em média 20 horas extras por
mês. O 13º salário de 2024 foi pago corretamente.

DOS PEDIDOS
a) pagamento das horas extras, com adicional de 50%;
b) indenização por danos morais, no valor de R$ 20.000,00;

Santos, 3 de fevereiro de 2026."""

GOOD = {"admission_date": "2021-03-15", "termination_date": "2025-08-10", "termination_type": "without_cause",
        "monthly_salary": "6000.00", "weekly_hours": "44", "filing_date": "2026-02-03",
        "claims": [{"type": "overtime", "quote": "pagamento das horas extras, com adicional de 50%",
                    "hours_per_month": "20"},
                   {"type": "other", "quote": "indenização por danos morais", "label": "danos morais"}]}


def test_generator_is_reproducible_and_consistent():
    assert [p.text for p in generate_petitions(60, seed=7)] == [p.text for p in PETITIONS]
    for p in PETITIONS:
        t = p.truth
        assert date.fromisoformat(t["admission_date"]) < date.fromisoformat(t["termination_date"]) \
            < date.fromisoformat(t["filing_date"])
        types = [c["type"] for c in t["claims"]]
        assert len([c for c in types if c != "other"]) >= 2
        if t["termination_type"] == "resignation":
            assert "notice_pay" not in types and "fgts_fine" not in types   # no notice or fine on resignation


def test_every_truth_value_is_written_in_its_petition():
    """The validator drops values that are not in the text, so the ground truth must always be there."""
    for p in PETITIONS:
        t = p.truth
        days, numbers = dates_in_text(p.text), numbers_in_text(p.text)
        assert {date.fromisoformat(t[k]) for k in ("admission_date", "termination_date", "filing_date")} <= days
        values = [t["monthly_salary"], t["weekly_hours"]] + [c.get("hours_per_month") or c.get("months")
                                                             for c in t["claims"]]
        assert {D(v) for v in values if v is not None} <= numbers, p.id


def test_dates_and_numbers_in_brazilian_formats():
    assert dates_in_text("em 15/03/2021 e em 1º de março de 2021; 31/02/2021 não existe") == {
        date(2021, 3, 15), date(2021, 3, 1)}
    found = numbers_in_text("R$ 6.000,00, R$6000,50, 44 horas, 40%, em 15/03/2021")
    assert {D("6000"), D("6000.50"), D("44"), D("40")} <= found
    assert D("15") not in found and D("2021") not in found       # numbers inside dates are not numbers


def test_a_correct_extraction_is_kept_whole():
    r = parse_extraction(json.dumps(GOOD), MINI)
    assert r.problems == ()
    assert r.as_truth() == {"admission_date": "2021-03-15", "termination_date": "2025-08-10",
                            "termination_type": "without_cause", "monthly_salary": "6000", "weekly_hours": "44",
                            "filing_date": "2026-02-03",
                            "claims": [{"type": "overtime", "hours_per_month": "20"},
                                       {"type": "other", "label": "danos morais"}]}


@pytest.mark.parametrize("change,dropped,reason", [
    ({"monthly_salary": "7000.00"}, "monthly_salary", "not written in the petition"),     # invented salary
    ({"admission_date": "2021-03-16"}, "admission_date", "not written in the petition"),   # invented date
    ({"filing_date": "03/02/2026"}, "filing_date", "not a YYYY-MM-DD date"),
    ({"termination_type": "fired"}, "termination_type", "is not one of"),
])
def test_fields_that_cannot_be_checked_are_dropped(change, dropped, reason):
    r = parse_extraction({**GOOD, **change}, MINI)
    assert getattr(r, dropped) in (None, "unknown")
    assert any(reason in p for p in r.problems)


@pytest.mark.parametrize("claim,reason", [
    ({"type": "overtime", "quote": "o reclamante fazia horas extras todos os dias"}, "not copied"),   # invented quote
    ({"type": "hazard_pay", "quote": "pagamento das horas extras"}, "unknown claim type"),
])
def test_claims_that_cannot_be_checked_are_dropped(claim, reason):
    r = parse_extraction({**GOOD, "claims": [claim]}, MINI)
    assert r.claims == () and reason in r.problems[0]


def test_claim_details_are_checked_too():
    claims = [{"type": "overtime", "quote": "horas extras", "hours_per_month": "25"},           # 25 is not in the text
              {"type": "other", "quote": "danos morais", "label": "danos morais de R$ 20.000"}]  # digits in a label
    r = parse_extraction({**GOOD, "claims": claims}, MINI)
    assert [(c.type, c.hours_per_month, c.label) for c in r.claims] == [("overtime", None, None), ("other", None, None)]
    assert len(r.problems) == 2


def test_an_answer_that_is_not_json_gives_an_empty_extraction():
    r = parse_extraction("Here is the JSON: {", MINI)
    assert r.claims == () and r.problems == ("answer is not valid JSON",)


def test_keyword_rules_read_the_facts_but_take_a_mention_for_a_claim():
    r = rule_extract(MINI).as_truth()
    assert (r["admission_date"], r["termination_date"], r["monthly_salary"], r["weekly_hours"], r["filing_date"]) == (
        "2021-03-15", "2025-08-10", "6000", "44", "2026-02-03")
    types = {c["type"] for c in r["claims"]}
    assert {"overtime", "other"} <= types
    assert "thirteenth" in types          # "O 13º salário de 2024 foi pago corretamente": a false claim


def test_keyword_rules_on_the_synthetic_petitions():
    """Template text is easy: rules miss no claim but count every trap sentence as one."""
    missed = invented = 0
    for p in PETITIONS:
        truth = {c["type"] for c in p.truth["claims"]} & set(COMPUTED_CLAIMS)
        found = {c.type for c in rule_extract(p.text).claims} & set(COMPUTED_CLAIMS)
        missed += len(truth - found)
        invented += len(found - truth)
    assert missed == 0 and invented > 0
