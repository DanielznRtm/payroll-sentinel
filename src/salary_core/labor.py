"""Labor rights owed on a CLT contract, to estimate what a labor claim is worth.

Every rate and limit comes from the ``labor_rights`` block of the year's
parameters. Dates are ``datetime.date``; a period includes both its first and
last day. Each amount is computed exactly and rounded to cents once.

Month counting follows the 13th-salary rule: a month counts when at least 15
of its days were worked (Lei 4.090/1962, art. 1, par. 2).
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal

from salary_core.taxes import cents, money


def _rights(params: dict) -> dict:
    return params["labor_rights"]


def _check_period(start: date, end: date) -> None:
    if end < start:
        raise ValueError(f"period ends ({end}) before it starts ({start})")


def add_months(day: date, months: int) -> date:
    """Same day of the month, ``months`` later; the 31st becomes the last day of a shorter month."""
    index = day.year * 12 + day.month - 1 + months
    year, month = divmod(index, 12)
    return date(year, month + 1, min(day.day, calendar.monthrange(year, month + 1)[1]))


def completed_years(start: date, end: date) -> int:
    """Whole years of service from ``start`` to ``end``."""
    _check_period(start, end)
    return end.year - start.year - ((end.month, end.day) < (start.month, start.day))


def months_worked(start: date, end: date, params: dict) -> int:
    """Calendar months in the period with at least the minimum number of days worked."""
    _check_period(start, end)
    min_days = int(_rights(params)["month_fraction_min_days"])
    count, first = 0, date(start.year, start.month, 1)
    while first <= end:
        last = date(first.year, first.month, calendar.monthrange(first.year, first.month)[1])
        days = (min(end, last) - max(start, first)).days + 1
        if days >= min_days:
            count += 1
        first = last + timedelta(days=1)
    return count


def notice_days(start: date, end: date, params: dict) -> int:
    """Lei 12.506/2011: 30 days, plus 3 per completed year of service, up to 90."""
    r = _rights(params)
    days = r["notice_base_days"] + r["notice_days_per_year"] * completed_years(start, end)
    return int(min(days, r["notice_max_days"]))


def projected_end(start: date, end: date, params: dict) -> date:
    """Last day of the contract counting paid notice as service time (CLT art. 487, par. 1)."""
    return end + timedelta(days=notice_days(start, end, params))


def notice_pay(salary, start: date, end: date, params: dict) -> Decimal:
    """Paid notice: one day's salary (salary / 30) per day of notice."""
    return cents(money(salary) / _rights(params)["days_per_month"] * notice_days(start, end, params))


def _last_day(start: date, termination: date, params: dict, paid_notice: bool) -> date:
    _check_period(start, termination)
    return projected_end(start, termination, params) if paid_notice else termination


def thirteenth_proportional(salary, start: date, termination: date, params: dict, *, paid_notice: bool = False) -> Decimal:
    """1/12 of the salary per month from January of the termination year (earlier years assumed paid).

    With paid notice the count runs to the projected end, which may cross into the next
    year: a dismissal on 15 December with 48 days of notice owes 13/12.
    """
    end = _last_day(start, termination, params, paid_notice)
    months = months_worked(max(start, date(termination.year, 1, 1)), end, params)
    return cents(money(salary) * months / 12)


def vacation_months(start: date, end: date, params: dict) -> int:
    """Twelfths of the current vacation period, which starts on the last anniversary of ``start``."""
    period_start = add_months(start, 12 * completed_years(start, end))
    months = 0
    while add_months(period_start, months + 1) <= end + timedelta(days=1):
        months += 1
    rest = (end - add_months(period_start, months)).days + 1
    if rest >= _rights(params)["month_fraction_min_days"]:
        months += 1
    return min(12, months)


def vacation_proportional(salary, start: date, termination: date, params: dict, *, paid_notice: bool = False) -> Decimal:
    """Proportional vacation of the incomplete period plus one third (CF art. 7, XVII)."""
    end = _last_day(start, termination, params, paid_notice)
    base = money(salary) * vacation_months(start, end, params) / 12
    return cents(base + base / _rights(params)["vacation_bonus_divisor"])


def overtime_pay(salary, weekly_hours, hours_per_month, start: date, end: date, params: dict) -> Decimal:
    """Unpaid overtime: hourly wage x (1 + premium) x hours per month x months worked in the period.

    The hourly wage is salary / (5 x weekly hours). Raises ValueError for periods after
    ``overtime_computed_until`` (EC 141/2026 changed weekly hours and rest days).
    """
    r = _rights(params)
    if end > date.fromisoformat(r["overtime_computed_until"]):
        raise ValueError(f"overtime after {r['overtime_computed_until']} needs human review (EC 141/2026)")
    weekly, hours = money(weekly_hours), money(hours_per_month)
    if weekly == 0:
        raise ValueError("weekly hours must be positive")
    hourly = money(salary) / (r["hour_divisor_per_weekly_hour"] * weekly)
    return cents(hourly * (1 + r["overtime_premium"]) * hours * months_worked(start, end, params))


def unpaid_fgts(salary, months: int, params: dict) -> Decimal:
    """FGTS deposits missing for ``months`` months: 8 % of the salary each month."""
    if months < 0:
        raise ValueError("months must be zero or positive")
    return cents(money(salary) * _rights(params)["fgts_rate"] * months)


def fgts_fine(salary, start: date, termination: date, params: dict, *, paid_notice: bool = False) -> Decimal:
    """40 % of the FGTS deposits of the whole contract, estimated as 8 % of the current salary per month.

    A lower bound: deposits on the 13th salary and vacation, interest and monetary
    correction are left out. Paid notice counts as months of deposits.
    """
    r = _rights(params)
    end = _last_day(start, termination, params, paid_notice)
    deposits = money(salary) * r["fgts_rate"] * months_worked(start, end, params)
    return cents(deposits * r["fgts_fine_rate"])


def late_severance_fine(salary, params: dict) -> Decimal:
    """CLT art. 477, par. 8: severance paid late costs one monthly salary."""
    return cents(money(salary) * _rights(params)["late_severance_fine_salaries"])
