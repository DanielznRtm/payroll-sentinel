"""Labor rights for claim estimates, checked against hand calculations.

Every expected value is computed by hand from the labor_rights block of
salary_core/params/2026.json (laws on planalto.gov.br), never by running the code.
Reference contract: admitted 2021-03-15, dismissed without cause 2025-08-10, R$ 6,000.
"""

from datetime import date
from decimal import Decimal as D

import pytest

from salary_core import load_params
from salary_core.labor import (add_months, fgts_fine, late_severance_fine, months_worked, notice_days, notice_pay,
                               overtime_pay, projected_end, thirteenth_proportional, unpaid_fgts, vacation_months,
                               vacation_proportional)

P = load_params(2026)
START, END = date(2021, 3, 15), date(2025, 8, 10)
PROJECTED = date(2025, 9, 21)   # END + 42 days of notice: Aug 10 + 21 = Aug 31, + 21 = Sep 21


def test_reference_notice_and_its_projection():
    # 4 completed years (2025-03-15 passed): 30 + 3 x 4 = 42 days; pay 6,000 / 30 x 42 = 8,400.00.
    assert notice_days(START, END, P) == 42
    assert notice_pay("6000.00", START, END, P) == D("8400.00")
    assert projected_end(START, END, P) == PROJECTED


@pytest.mark.parametrize("start,end,days", [
    (date(2024, 3, 15), date(2025, 3, 14), 30),   # one day short of a year
    (date(2024, 3, 15), date(2025, 3, 15), 33),   # one completed year
    (date(2005, 6, 30), date(2025, 6, 30), 90),   # 20 years: 30 + 60, the maximum
    (date(2000, 1, 1), date(2025, 6, 30), 90),    # 25 years would be 105: capped at 90
])
def test_notice_days_by_years_of_service(start, end, days):
    assert notice_days(start, end, P) == days


def test_thirteenth_counts_the_projected_notice():
    # With the projection: Jan-Aug 2025 (8) + Sep 1-21 (21 days >= 15) = 9/12 -> 6,000 x 9 / 12 = 4,500.00.
    assert thirteenth_proportional("6000.00", START, END, P, paid_notice=True) == D("4500.00")
    # Without it: Jan-Jul (7) + Aug 1-10 (10 days < 15) = 7/12 -> 3,500.00.
    assert thirteenth_proportional("6000.00", START, END, P) == D("3500.00")


def test_thirteenth_when_the_notice_crosses_into_the_next_year():
    # Admitted 2019-09-20, dismissed 2025-12-15: 6 years -> 30 + 18 = 48 days -> projected 2026-02-01.
    # From 2025-01-01: 12 months of 2025 + Jan 2026 + Feb 1 (1 day, no) = 13/12 -> 7,150 x 13 / 12 = 7,745.8333.
    start, end = date(2019, 9, 20), date(2025, 12, 15)
    assert projected_end(start, end, P) == date(2026, 2, 1)
    assert thirteenth_proportional("7150.00", start, end, P, paid_notice=True) == D("7745.83")


def test_vacation_of_the_current_period_plus_one_third():
    # Period starts 2025-03-15; 6 whole months to 2025-09-14, then Sep 15-21 = 7 days < 15: 6/12.
    # 6,000 x 6 / 12 = 3,000, plus one third (1,000) = 4,000.00.
    assert vacation_months(START, PROJECTED, P) == 6
    assert vacation_proportional("6000.00", START, END, P, paid_notice=True) == D("4000.00")


def test_fgts_fine_estimate_over_the_whole_contract():
    # Months with >= 15 days: Mar 2021 (15-31 = 17 days) 1, Apr-Dec 2021 9, 2022-2024 36,
    # Jan-Aug 2025 8, Sep 1-21 2025 1 = 55. Deposits 6,000 x 8 % x 55 = 26,400; fine 40 % = 10,560.00.
    assert months_worked(START, PROJECTED, P) == 55
    assert fgts_fine("6000.00", START, END, P, paid_notice=True) == D("10560.00")


def test_overtime_over_the_worked_period():
    # Overtime is only worked until END: 1 + 9 + 36 + 7 (Jan-Jul 2025; Aug 1-10 < 15 days) = 53 months.
    # 6,000 / 220 x 1.5 x 20 h x 53 = 9,540,000 / 220 = 43,363.6363... -> 43,363.64.
    assert overtime_pay("6000.00", 44, 20, START, END, P) == D("43363.64")


def test_overtime_divisor_follows_weekly_hours():
    # 40 h a week: divisor 200. 6,000 / 200 = 30 x 1.5 = 45 per hour x 20 h x 12 months = 10,800.00.
    assert overtime_pay("6000.00", 40, 20, date(2025, 1, 1), date(2025, 12, 31), P) == D("10800.00")


def test_overtime_after_ec_141_is_left_to_a_person():
    assert overtime_pay("6000.00", 44, 10, date(2026, 1, 1), date(2026, 10, 15), P) > 0
    with pytest.raises(ValueError, match="EC 141"):
        overtime_pay("6000.00", 44, 10, date(2026, 1, 1), date(2026, 10, 16), P)


def test_fgts_and_late_severance_fines():
    assert unpaid_fgts("6000.00", 8, P) == D("3840.00")        # 6,000 x 8 % x 8 months
    assert late_severance_fine("6000.00", P) == D("6000.00")   # one monthly salary


def test_contract_shorter_than_a_year():
    # Admitted 2025-05-20, dismissed 2025-08-21: 0 years -> 30 days of notice -> projected 2025-09-20.
    start, end = date(2025, 5, 20), date(2025, 8, 21)
    projected = projected_end(start, end, P)
    assert projected == date(2025, 9, 20)
    # 13th: May 20-31 (12 days) no, Jun, Jul, Aug, Sep 1-20 (20 days) = 4/12 -> 2,000.00.
    assert thirteenth_proportional("6000.00", start, end, P, paid_notice=True) == D("2000.00")
    # Vacation: 4 whole months from May 20 to Sep 19, then Sep 20 = 1 day: 4/12 -> 2,000 + 666.67 = 2,666.67.
    assert vacation_proportional("6000.00", start, end, P, paid_notice=True) == D("2666.67")


@pytest.mark.parametrize("start,end,months", [
    (date(2025, 4, 16), date(2025, 4, 30), 1),    # exactly 15 days count as a month
    (date(2025, 4, 17), date(2025, 4, 30), 0),    # 14 days do not
    (date(2025, 1, 10), date(2025, 3, 20), 3),    # Jan 22 days, Feb whole, Mar 20 days
    (date(2025, 1, 20), date(2025, 3, 10), 1),    # Jan 12 and Mar 10 days drop; Feb counts
])
def test_months_worked_uses_the_15_day_rule(start, end, months):
    assert months_worked(start, end, P) == months


def test_dates_and_invalid_periods():
    assert add_months(date(2021, 1, 31), 1) == date(2021, 2, 28)      # the 31st becomes the month's last day
    assert add_months(date(2024, 2, 29), 12) == date(2025, 2, 28)
    with pytest.raises(ValueError, match="before it starts"):
        months_worked(date(2025, 5, 1), date(2025, 4, 1), P)
