"""Triage: which claims are owed, limitation periods, and the priced total.

Amounts are the hand-checked values of tests/test_salary_core_labor.py (reference
contract: admitted 2021-03-15, dismissed without cause 2025-08-10, R$ 6,000, 44 h).
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal as D

from salary_core import load_params

from payroll_sentinel.claims import Claim, Extraction
from payroll_sentinel.triage import triage

P = load_params(2026)
ALL = (Claim("overtime", "q", hours_per_month=D("20")), Claim("unpaid_fgts", "q", months=8),
       Claim("fgts_fine", "q"), Claim("notice_pay", "q"), Claim("thirteenth", "q"), Claim("vacation", "q"),
       Claim("late_severance_fine", "q"), Claim("other", "q", label="danos morais"))
REF = Extraction(admission_date=date(2021, 3, 15), termination_date=date(2025, 8, 10),
                 termination_type="without_cause", monthly_salary=D("6000.00"), weekly_hours=D("44"),
                 filing_date=date(2026, 2, 3), claims=ALL)


def amounts(result):
    return {e.type: e.amount for e in result.estimates}


def test_reference_contract_prices_every_computed_claim():
    r = triage(REF, P)
    assert amounts(r) == {"overtime": D("43363.64"),        # 20 h x 53 months, divisor 220
                          "unpaid_fgts": D("3840.00"),      # 8 % x 6,000 x 8
                          "fgts_fine": D("10560.00"),       # 40 % of 8 % x 6,000 x 55 months (notice projected)
                          "notice_pay": D("8400.00"),       # 42 days
                          "thirteenth": D("4500.00"),       # 9/12 with the notice projected
                          "vacation": D("4000.00"),         # 6/12 + 1/3
                          "late_severance_fine": D("6000.00"),
                          "other": None}                    # danos morais: a person decides
    # 43,363.64 + 3,840 + 10,560 + 8,400 + 4,500 + 4,000 + 6,000 = 80,663.64 > 40 x 1,621 = 64,840
    assert r.total == D("80663.64")
    assert r.procedure.startswith("ordinary")
    assert "some claims need human review" in r.flags


def test_resignation_owes_no_notice_or_fine_and_no_projection():
    r = triage(replace(REF, termination_type="resignation"), P)
    a = amounts(r)
    assert a["notice_pay"] is None and a["fgts_fine"] is None
    # No projection: 13th Jan-Jul = 7/12 -> 3,500.00. Vacation: 4 whole months from 2025-03-15 to 07-14,
    # then Jul 15 - Aug 10 = 27 days >= 15: 5/12 -> 2,500 + 833.33 = 3,333.33.
    assert (a["thirteenth"], a["vacation"]) == (D("3500.00"), D("3333.33"))


def test_just_cause_leaves_termination_claims_to_a_person():
    a = amounts(triage(replace(REF, termination_type="with_cause"), P))
    assert [t for t, v in a.items() if v is None] == ["fgts_fine", "notice_pay", "thirteenth", "vacation", "other"]
    assert a["overtime"] == D("43363.64")            # overtime is owed however the contract ended


def test_filed_more_than_two_years_after_the_end_is_time_barred():
    # Contract ended 2024-01-10; two years later is 2026-01-10, before the filing on 2026-02-03.
    r = triage(replace(REF, admission_date=date(2020, 3, 1), termination_date=date(2024, 1, 10)), P)
    assert r.total == D("0.00") and all(e.amount is None for e in r.estimates)
    assert any(f.startswith("time-barred") for f in r.flags)


def test_credits_older_than_five_years_are_cut():
    # Admitted 2018-01-01; filed 2026-02-03, so credits start on 2021-02-03. Overtime months:
    # Feb 2021 (3-28 = 26 days) 1, Mar-Dec 2021 10, 2022-2024 36, Jan-Jul 2025 7 = 54.
    # 6,000 / 220 x 1.5 x 20 x 54 = 9,720,000 / 220 = 44,181.8181... -> 44,181.82.
    r = triage(replace(REF, admission_date=date(2018, 1, 1)), P)
    assert amounts(r)["overtime"] == D("44181.82")
    assert "credits before 2021-02-03 are time-barred (5-year limit)" in r.flags


def test_missing_facts_are_never_guessed():
    r = triage(replace(REF, monthly_salary=None), P)
    assert r.total == D("0.00") and all(e.amount is None for e in r.estimates)
    a = amounts(triage(replace(REF, weekly_hours=None), P))
    assert a["overtime"] is None and a["notice_pay"] == D("8400.00")


def test_overtime_after_ec_141_goes_to_a_person():
    late = replace(REF, termination_date=date(2026, 10, 20), filing_date=date(2026, 11, 10))
    estimate = next(e for e in triage(late, P).estimates if e.type == "overtime")
    assert estimate.amount is None and "EC 141" in estimate.note


def test_small_claims_follow_the_summary_procedure():
    # One monthly salary of 2,000 is far below 40 x 1,621 = 64,840.
    small = replace(REF, monthly_salary=D("2000.00"), claims=(Claim("late_severance_fine", "q"),))
    r = triage(small, P)
    assert r.total == D("2000.00") and r.procedure.startswith("summary")
