"""Monthly net pay by kind of contract."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from salary_core.taxes import IncomeTax, inss_employee, irrf_monthly, money


@dataclass(frozen=True)
class NetPay:
    contract: str                    # "clt", "internship" or "pj_simples"
    gross: Decimal                   # monthly salary, stipend or invoiced revenue
    deductions: dict[str, Decimal]   # every amount taken from gross, by name
    income_tax: IncomeTax            # IRRF step by step
    net: Decimal                     # what reaches the person


def clt_net(gross, params: dict, *, dependents: int = 0) -> NetPay:
    """CLT employee: gross - INSS - IRRF (13th salary, vacation and FGTS are not part of a month's pay)."""
    gross = money(gross)
    inss = inss_employee(gross, params)
    tax = irrf_monthly(gross, params, social_security=inss, dependents=dependents)
    return NetPay("clt", gross, {"inss": inss, "irrf": tax.tax}, tax, gross - inss - tax.tax)
