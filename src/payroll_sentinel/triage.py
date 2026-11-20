"""Triage of a labor petition: which claims the code can price, and what each is worth.

The extraction (claims.py) says what the petition asks for. This module decides
which claims are owed for the way the contract ended, applies the limitation
periods and prices each claim with salary_core. Nothing here comes from an LLM:
every amount, date and flag is computed from the year's parameters, which cite
their official sources. Amounts are estimates, without interest or monetary
correction, and a claim the code cannot price is left to a person.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from salary_core import labor
from salary_core.taxes import cents

from .claims import COMPUTED_CLAIMS, Extraction

# Claims owed whatever the way the contract ended.
ALWAYS_OWED = {"overtime", "unpaid_fgts", "late_severance_fine"}
# Claims that depend on it: a resignation gives no paid notice and no 40 % fine (the worker gave notice);
# just cause removes the 13th, vacation, notice and fine unless a judge overturns it.
OWED = {"without_cause": set(COMPUTED_CLAIMS),
        "resignation": ALWAYS_OWED | {"thirteenth", "vacation"}}
NOT_OWED_ON_RESIGNATION = {"notice_pay", "fgts_fine"}


@dataclass(frozen=True)
class Estimate:
    type: str
    amount: Decimal | None   # None: the code did not price it
    note: str                # how it was computed, or why it was not


@dataclass(frozen=True)
class Triage:
    estimates: tuple[Estimate, ...]
    total: Decimal           # sum of the priced claims
    flags: tuple[str, ...]
    procedure: str | None    # likely procedure from the estimated total


def _years_before(day: date, years: int) -> date:
    return labor.add_months(day, -12 * years)


def triage(extraction: Extraction, params: dict) -> Triage:
    e, flags = extraction, []
    proc = params["labor_procedure"]
    claims = list(e.claims)

    def unpriced(note: str) -> Triage:
        return Triage(tuple(Estimate(c.type, None, note) for c in claims), Decimal("0.00"), tuple(flags), None)

    if e.admission_date is None or e.termination_date is None or e.monthly_salary is None:
        flags.append("admission, termination or salary missing: nothing can be priced")
        return unpriced("contract facts missing")
    start, end, salary = e.admission_date, e.termination_date, e.monthly_salary
    if end < start:
        flags.append("termination before admission: check the dates")
        return unpriced("inconsistent dates")
    period_start = start
    if e.filing_date is None:
        flags.append("filing date missing: limitation periods not checked")
    else:
        if e.filing_date.year != params["year"]:
            flags.append(f"filed in {e.filing_date.year}, priced with {params['year']} parameters")
        if e.filing_date > labor.add_months(end, 12 * int(proc["limitation_years_after_end"])):
            flags.append(f"time-barred: filed more than {proc['limitation_years_after_end']} years after the "
                         "contract ended (CF art. 7, XXIX)")
            return unpriced("time-barred")
        period_start = max(start, _years_before(e.filing_date, int(proc["limitation_years_back"])))
        if period_start > start:
            flags.append(f"credits before {period_start.isoformat()} are time-barred "
                         f"({proc['limitation_years_back']}-year limit)")

    kind = e.termination_type
    types = {c.type for c in claims}
    paid_notice = kind == "without_cause" and "notice_pay" in types
    estimates = []
    for c in claims:
        if c.type == "other":
            estimates.append(Estimate(c.type, None, "not priced by the code: human review"))
            continue
        if kind == "resignation" and c.type in NOT_OWED_ON_RESIGNATION:
            estimates.append(Estimate(c.type, None, "not owed on a resignation"))
            continue
        if c.type not in OWED.get(kind, ALWAYS_OWED):
            estimates.append(Estimate(c.type, None, "depends on how the contract ended: human review"))
            continue
        estimates.append(_price(c, start, end, period_start, salary, e.weekly_hours, paid_notice, params))

    total = cents(sum((x.amount for x in estimates if x.amount is not None), Decimal("0")))
    limit = params["minimum_wage"]["monthly"] * proc["summary_procedure_max_minimum_wages"]
    wages = proc["summary_procedure_max_minimum_wages"]
    procedure = (f"summary (sumaríssimo, up to {wages} minimum wages)" if total <= limit
                 else f"ordinary (above {wages} minimum wages)")
    if any(x.amount is None for x in estimates):
        flags.append("some claims need human review")
    return Triage(tuple(estimates), total, tuple(flags), procedure)


def _pct(rate: Decimal) -> str:
    return format((rate * 100).normalize(), "f") + " %"


def _price(c, start, end, period_start, salary, weekly_hours, paid_notice, params) -> Estimate:
    t, r = c.type, params["labor_rights"]
    if t == "notice_pay":
        days = labor.notice_days(start, end, params)
        return Estimate(t, labor.notice_pay(salary, start, end, params), f"{days} days of salary")
    if t == "thirteenth":
        note = "1/12 per month since January of the termination year" + (", notice projected" if paid_notice else "")
        return Estimate(t, labor.thirteenth_proportional(salary, start, end, params, paid_notice=paid_notice), note)
    if t == "vacation":
        last = labor.projected_end(start, end, params) if paid_notice else end
        months = labor.vacation_months(start, last, params)
        return Estimate(t, labor.vacation_proportional(salary, start, end, params, paid_notice=paid_notice),
                        f"{months}/12 of the salary plus one third")
    if t == "fgts_fine":
        return Estimate(t, labor.fgts_fine(salary, start, end, params, paid_notice=paid_notice),
                        f"{_pct(r['fgts_fine_rate'])} of {_pct(r['fgts_rate'])} of the salary per month "
                        "of contract (lower bound)")
    if t == "late_severance_fine":
        return Estimate(t, labor.late_severance_fine(salary, params), "one monthly salary")
    if t == "unpaid_fgts":
        if c.months is None:
            return Estimate(t, None, "months without deposits not stated: human review")
        months = min(c.months, labor.months_worked(period_start, end, params))
        note = f"{_pct(r['fgts_rate'])} of the salary for {months} months" + (" (capped by the 5-year limit)" if months < c.months else "")
        return Estimate(t, labor.unpaid_fgts(salary, months, params), note)
    if t == "overtime":
        if c.hours_per_month is None or weekly_hours is None:
            return Estimate(t, None, "overtime hours or weekly hours not stated: human review")
        try:
            amount = labor.overtime_pay(salary, weekly_hours, c.hours_per_month, period_start, end, params)
        except ValueError as exc:
            return Estimate(t, None, str(exc))
        months = labor.months_worked(period_start, end, params)
        return Estimate(t, amount, f"{c.hours_per_month} h a month for {months} months at "
                                   f"{_pct(1 + r['overtime_premium'])} of the hourly wage")
    raise ValueError(f"unknown claim type {t}")
