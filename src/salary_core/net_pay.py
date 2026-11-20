"""Monthly net pay by kind of contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from salary_core.taxes import (IncomeTax, cents, inss_employee, inss_pro_labore, irrf_monthly, money,
                               simples_effective_rate)


@dataclass(frozen=True)
class NetPay:
    contract: str                    # "clt", "internship" or "pj_simples"
    gross: Decimal                   # monthly salary, stipend or invoiced revenue
    deductions: dict[str, Decimal]   # every amount taken from gross, by name
    income_tax: IncomeTax            # IRRF step by step
    net: Decimal                     # what reaches the person
    details: dict = field(default_factory=dict)   # contract-specific facts (e.g. the Simples annex)


def clt_net(gross, params: dict, *, dependents: int = 0) -> NetPay:
    """CLT employee: gross - INSS - IRRF (13th salary, vacation and FGTS are not part of a month's pay)."""
    gross = money(gross)
    inss = inss_employee(gross, params)
    tax = irrf_monthly(gross, params, social_security=inss, dependents=dependents)
    return NetPay("clt", gross, {"inss": inss, "irrf": tax.tax}, tax, gross - inss - tax.tax)


def intern_net(stipend, params: dict, *, dependents: int = 0) -> NetPay:
    """Internship (Lei 11.788/2008): no mandatory INSS and no FGTS, so stipend - IRRF."""
    stipend = money(stipend)
    tax = irrf_monthly(stipend, params, dependents=dependents)
    return NetPay("internship", stipend, {"irrf": tax.tax}, tax, stipend - tax.tax)


def pj_net(monthly_revenue, pro_labore, params: dict, *, dependents: int = 0) -> NetPay:
    """One-partner company in the Simples Nacional providing a service taxed in Annex III or V.

    Assumes a steady state: the last 12 months had the same revenue and pro-labore, the
    pro-labore is the whole payroll (no employees), and the rest of the revenue is paid out
    as profit, which is exempt. The partner keeps revenue - DAS - INSS - IRRF on the pro-labore.
    Raises ValueError for cases this model does not cover, instead of returning a number.
    """
    revenue, pro_labore = money(monthly_revenue), money(pro_labore)
    simples = params["simples_nacional"]
    revenue_12m = 12 * revenue
    if revenue_12m > simples["revenue_limit_12m"]:
        raise ValueError("12-month revenue above the Simples Nacional limit")
    if pro_labore < params["minimum_wage"]["monthly"]:
        raise ValueError("pro-labore below the minimum wage")
    if pro_labore > revenue:
        raise ValueError("pro-labore above the revenue")

    fator_r = pro_labore / revenue    # payroll / revenue; the same over 12 months in a steady state
    annex = "III" if fator_r >= simples["fator_r_threshold"] else "V"
    rate = simples_effective_rate(revenue_12m, simples[f"annex_{annex.lower()}"])
    das = cents(revenue * rate)
    inss = inss_pro_labore(pro_labore, params)
    tax = irrf_monthly(pro_labore, params, social_security=inss, dependents=dependents)

    profit = revenue - das - pro_labore
    if profit < 0:
        raise ValueError("revenue does not cover the DAS and the pro-labore")
    if profit > params["dividend_withholding"]["monthly_threshold"]:
        raise ValueError("monthly profit above the Lei 15.270/2025 withholding threshold: not modeled")
    return NetPay("pj_simples", revenue, {"das": das, "inss_pro_labore": inss, "irrf_pro_labore": tax.tax}, tax,
                  revenue - das - inss - tax.tax,
                  details={"annex": annex, "fator_r": fator_r, "effective_rate": rate, "profit": profit})
