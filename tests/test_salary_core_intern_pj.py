"""Internship and Simples Nacional contractor (PJ) net pay, checked against hand calculations.

Expected values are computed by hand from salary_core/params/2026.json, never by running
the code; the arithmetic is in the comments. Simples rates are from LC 123/2006, Annexes III
and V (LC 155/2016); INSS on pro-labore is 11 % up to the ceiling (R$ 8,475.55).
"""

from decimal import Decimal as D

import pytest

from salary_core import intern_net, load_params, pj_net

P = load_params(2026)


def test_internship_stipend_has_no_inss():
    # Legal base 1,500 and simplified base 892.80 are both in the exempt bracket: no IRRF.
    r = intern_net("1500.00", P)
    assert r.deductions == {"irrf": D("0.00")} and r.net == D("1500.00")


def test_high_internship_stipend_pays_irrf_with_the_reduction():
    # No INSS, so the simplified discount wins: base 6,000 - 607.20 = 5,392.80;
    # 5,392.80 x 27.5 % - 908.73 = 574.29; reduction 978.62 - 0.133145 x 6,000 = 179.75; tax 394.54.
    r = intern_net("6000.00", P)
    assert r.income_tax.deduction_mode == "simplified"
    assert r.deductions == {"irrf": D("394.54")} and r.net == D("5605.46")


def test_pj_annex_iii_first_band():
    # fator R 2,800 / 10,000 = 0.28 >= 0.28 -> Annex III; 12-month revenue 120,000 -> 6 %, DAS 600.00.
    # INSS 11 % x 2,800 = 308.00. IRRF: simplified base 2,192.80 is exempt (legal base 2,492 would pay 4.74).
    r = pj_net("10000.00", "2800.00", P)
    assert r.details["annex"] == "III" and r.details["effective_rate"] == D("0.06")
    assert r.deductions == {"das": D("600.00"), "inss_pro_labore": D("308.00"), "irrf_pro_labore": D("0.00")}
    assert r.net == D("9092.00")                 # 10,000 - 600 - 308
    assert r.details["profit"] == D("6600.00")   # 10,000 - 600 - 2,800, paid out exempt


def test_pj_one_cent_below_fator_r_moves_to_annex_v():
    # fator R 2,799.99 / 10,000 = 0.279999 < 0.28 -> Annex V, 15.5 %: DAS 1,550.00.
    # INSS 11 % x 2,799.99 = 307.9989 -> 308.00; IRRF exempt as above.
    r = pj_net("10000.00", "2799.99", P)
    assert r.details["annex"] == "V"
    assert r.deductions == {"das": D("1550.00"), "inss_pro_labore": D("308.00"), "irrf_pro_labore": D("0.00")}
    assert r.net == D("8142.00")                 # 950 a month less than at fator R 0.28


def test_pj_annex_iii_second_band_with_irrf_reduction():
    # 12-month revenue 240,000 -> (240,000 x 11.2 % - 9,360) / 240,000 = 0.073; DAS 20,000 x 0.073 = 1,460.00.
    # INSS 11 % x 5,600 = 616.00. IRRF: legal base 5,600 - 616 = 4,984; 4,984 x 27.5 % - 908.73 = 461.87
    # (simplified 4,992.80 -> 464.29); reduction 978.62 - 0.133145 x 5,600 = 233.008 -> 233.01; tax 228.86.
    r = pj_net("20000.00", "5600.00", P)
    assert r.details["effective_rate"] == D("0.073")
    assert r.deductions == {"das": D("1460.00"), "inss_pro_labore": D("616.00"), "irrf_pro_labore": D("228.86")}
    assert r.net == D("17695.14")                # 20,000 - 1,460 - 616 - 228.86


def test_pj_pro_labore_above_the_inss_ceiling():
    # 12-month revenue 480,000 -> (480,000 x 13.5 % - 17,640) / 480,000 = 0.09825; DAS 3,930.00.
    # INSS 11 % x 8,475.55 (ceiling) = 932.3105 -> 932.31. IRRF: legal base 11,200 - 932.31 = 10,267.69;
    # 10,267.69 x 27.5 % - 908.73 = 1,914.88475 -> 1,914.88; above 7,350: no reduction.
    r = pj_net("40000.00", "11200.00", P)
    assert r.deductions == {"das": D("3930.00"), "inss_pro_labore": D("932.31"), "irrf_pro_labore": D("1914.88")}
    assert r.net == D("33222.81")                # 40,000 - 3,930 - 932.31 - 1,914.88


@pytest.mark.parametrize("revenue,pro_labore,reason", [
    ("400000.01", "112000.00", "Simples Nacional limit"),    # 12 x revenue = 4,800,000.12 > 4,800,000
    # DAS 100,000 x (1,200,000 x 16 % - 35,640) / 1,200,000 = 13,030; profit 100,000 - 13,030 - 28,000 = 58,970
    ("100000.00", "28000.00", "withholding threshold"),
    ("3000.00", "840.00", "below the minimum wage"),
    ("2000.00", "2500.00", "above the revenue"),
    ("2000.00", "1900.00", "does not cover"),               # DAS 6 % = 120; 2,000 - 120 - 1,900 < 0
])
def test_pj_cases_outside_the_model_are_refused(revenue, pro_labore, reason):
    with pytest.raises(ValueError, match=reason):
        pj_net(revenue, pro_labore, P)
