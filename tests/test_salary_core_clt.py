"""CLT net pay: INSS and IRRF checked against official examples and hand calculations.

No expected value here comes from running the code. Each one is either a Receita
Federal worked example, copied as published, or computed by hand from the 2026
tables in salary_core/params/2026.json, with the arithmetic in the comment.
"""

from decimal import Decimal as D

import pytest

from salary_core import clt_net, inss_employee, irrf_monthly, irrf_table_tax, load_params

P = load_params(2026)


# Receita Federal, "Exemplos de Aplicação da Lei 15.270/2025" (gov.br, updated 2026-03-04):
# https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/tabelas/exemplos-de-aplicacao-da-lei-15-270-2025
# The page took its INSS amounts from the 2025 table, so INSS is an input here and only IRRF is checked.
# columns: income, INSS, deduction mode, base, table tax, reduction, tax withheld
RECEITA_EXAMPLES = [
    # Example 1. The page prints the base as 2.428,00, a typo for 3,036.00 - 607.20 = 2,428.80.
    ("3036.00", "257.73", "simplified", "2428.80", "0.00", "0.00", "0.00"),
    ("4000.00", "373.41", "simplified", "3392.80", "114.76", "114.76", "0.00"),     # example 2
    ("5000.00", "509.60", "simplified", "4392.80", "312.89", "312.89", "0.00"),     # example 3
    ("6000.00", "649.60", "legal", "5350.40", "562.63", "179.75", "382.88"),        # example 4
    ("7607.20", "0.00", "simplified", "7000.00", "1016.27", "0.00", "1016.27"),     # example 5, no reduction
]


@pytest.mark.parametrize("income,inss,mode,base,table_tax,reduction,tax", RECEITA_EXAMPLES)
def test_receita_worked_examples(income, inss, mode, base, table_tax, reduction, tax):
    r = irrf_monthly(income, P, social_security=D(inss))
    assert (r.deduction_mode, r.base, r.table_tax, r.reduction, r.tax) == (mode, D(base), D(table_tax),
                                                                          D(reduction), D(tax))


def test_reference_case_6000_without_dependents():
    # INSS: 1,621.00 x 7.5 % = 121.575; 1,281.84 x 9 % = 115.3656; 1,451.43 x 12 % = 174.1716;
    #       1,645.73 x 14 % = 230.4022; exact sum 641.5144 -> 641.51 (rounded once, as the Receita does).
    # IRRF: legal base 6,000 - 641.51 = 5,358.49 (simplified would be 5,392.80, more tax);
    #       5,358.49 x 27.5 % - 908.73 = 564.85475 -> 564.85;
    #       reduction 978.62 - 0.133145 x 6,000 = 978.62 - 798.87 = 179.75; tax 564.85 - 179.75 = 385.10.
    r = clt_net("6000.00", P)
    assert r.deductions == {"inss": D("641.51"), "irrf": D("385.10")}
    assert r.net == D("4973.39")        # 6,000 - 641.51 - 385.10


@pytest.mark.parametrize("gross,expected", [
    ("0.00", "0.00"),
    ("1000.00", "75.00"),     # part-time below the minimum wage: 1,000 x 7.5 %
    ("1621.00", "121.58"),    # 1,621.00 x 7.5 % = 121.575
    ("2902.84", "236.94"),    # 121.575 + 1,281.84 x 9 % (115.3656) = 236.9406
    ("4354.27", "411.11"),    # 236.9406 + 1,451.43 x 12 % (174.1716) = 411.1122
    ("8475.55", "988.09"),    # 411.1122 + 4,121.28 x 14 % (576.9792) = 988.0914: the most anyone pays
    ("10000.00", "988.09"),   # above the ceiling, the same as at the ceiling
])
def test_inss_at_each_band_limit(gross, expected):
    assert inss_employee(gross, P) == D(expected)


@pytest.mark.parametrize("base,expected", [
    ("2428.80", "0.00"),      # top of the exempt bracket
    ("2826.65", "29.84"),     # 2,826.65 x 7.5 % - 182.16 = 29.83875
    ("3751.05", "168.50"),    # 3,751.05 x 15 % - 394.16 = 168.4975
    ("4664.68", "374.06"),    # 4,664.68 x 22.5 % - 675.49 = 374.063
    ("4664.69", "374.06"),    # 4,664.69 x 27.5 % - 908.73 = 374.05975: the table has no jump between brackets
])
def test_irrf_table_at_each_bracket_limit(base, expected):
    assert irrf_table_tax(D(base), P) == D(expected)


# No social security (like Receita example 5), so the simplified discount of 607.20 always wins.
@pytest.mark.parametrize("income,base,table_tax,reduction,tax", [
    ("5000.00", "4392.80", "312.89", "312.89", "0.00"),   # 4,392.80 x 22.5 % - 675.49 = 312.89, all reduced
    # 4,392.81 x 22.5 % - 675.49 = 312.89225; reduction 978.62 - 0.133145 x 5,000.01 = 312.8937 -> 312.89
    ("5000.01", "4392.81", "312.89", "312.89", "0.00"),
    # 6,742.80 x 27.5 % - 908.73 = 945.54; reduction 978.62 - 978.61575 = 0.00425 -> 0.00
    ("7350.00", "6742.80", "945.54", "0.00", "945.54"),
    ("7350.01", "6742.81", "945.54", "0.00", "945.54"),   # above 7,350 there is no reduction
])
def test_lei_15270_reduction_limits(income, base, table_tax, reduction, tax):
    r = irrf_monthly(income, P)
    assert (r.deduction_mode, r.base, r.table_tax, r.reduction, r.tax) == ("simplified", D(base), D(table_tax),
                                                                          D(reduction), D(tax))


def test_dependents_lower_the_legal_base():
    # INSS 641.51 (reference case). Legal base 6,000 - 641.51 - 2 x 189.59 = 4,979.31;
    # 4,979.31 x 27.5 % - 908.73 = 460.58025 -> 460.58 (simplified: 574.29); 460.58 - 179.75 = 280.83.
    r = clt_net("6000.00", P, dependents=2)
    assert r.income_tax.deduction_mode == "legal" and r.income_tax.base == D("4979.31")
    assert r.deductions["irrf"] == D("280.83")
    assert r.net == D("5077.66")        # 6,000 - 641.51 - 280.83


def test_salary_above_both_limits():
    # INSS at the ceiling: 988.09. Legal base 10,000 - 988.09 = 9,011.91;
    # 9,011.91 x 27.5 % - 908.73 = 1,569.54525 -> 1,569.55. Above 7,350: no reduction.
    r = clt_net("10000.00", P)
    assert r.deductions == {"inss": D("988.09"), "irrf": D("1569.55")}
    assert r.net == D("7442.36")


def test_minimum_wage_and_the_5000_exemption():
    assert clt_net("1621.00", P).net == D("1499.42")              # 1,621 - 121.58, no IRRF
    r = clt_net("5000.00", P)                                     # INSS: 411.1122 + 645.73 x 14 % = 501.5144
    assert r.deductions == {"inss": D("501.51"), "irrf": D("0.00")}
    assert r.net == D("4498.49")


def test_net_pay_never_falls_when_gross_rises():
    """The reduction fades out between 5,000 and 7,350; a raise must still never lower net pay."""
    nets = [clt_net(g, P).net for g in range(1000, 20001, 10)]
    assert all(b >= a for a, b in zip(nets, nets[1:]))


def test_invalid_inputs_are_refused():
    with pytest.raises(ValueError):
        clt_net("-1", P)
    with pytest.raises(ValueError):
        clt_net("6000", P, dependents=-1)
    assert clt_net(6000.0, P) == clt_net("6000.00", P)    # a float is read from its text, exactly
