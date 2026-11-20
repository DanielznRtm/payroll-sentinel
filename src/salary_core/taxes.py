"""INSS and monthly income tax (IRRF), computed from one year's parameters.

Money is ``Decimal``. Each tax is computed exactly and rounded to cents once,
half up, at the end, as in the Receita Federal worked examples.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
ZERO = Decimal("0")


def cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def money(value) -> Decimal:
    """An amount in reais: int, str, Decimal, or float (read from its shortest text, so 6000.1 stays exact)."""
    if isinstance(value, bool):
        raise TypeError("an amount cannot be a bool")
    amount = Decimal(repr(value)) if isinstance(value, float) else Decimal(value)
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"an amount must be zero or positive, got {value!r}")
    return amount


def inss_employee(gross, params: dict) -> Decimal:
    """CLT employee contribution: each rate applies only to the part of the salary inside its band.

    Above the last limit (the ceiling) nothing more is charged.
    """
    gross = money(gross)
    total, lower = ZERO, ZERO
    for band in params["inss_employee"]["bands"]:
        if gross <= lower:
            break
        total += (min(gross, band["up_to"]) - lower) * band["rate"]
        lower = band["up_to"]
    return cents(total)


def inss_pro_labore(pro_labore, params: dict) -> Decimal:
    """A partner's pro-labore: a flat rate withheld by the company, up to the INSS ceiling."""
    ceiling = params["inss_employee"]["bands"][-1]["up_to"]
    return cents(min(money(pro_labore), ceiling) * params["inss_contribuinte_individual"]["rate"])


def simples_effective_rate(revenue_12m: Decimal, annex: list[dict]) -> Decimal:
    """Simples Nacional: (12-month revenue x nominal rate - deduction) / 12-month revenue."""
    for band in annex:
        if revenue_12m <= band["up_to"]:
            return (revenue_12m * band["rate"] - band["deduction"]) / revenue_12m
    raise ValueError("12-month revenue above the Simples Nacional limit")


@dataclass(frozen=True)
class IncomeTax:
    """One month of IRRF, step by step, so a result can be explained and checked."""

    taxable_income: Decimal  # rendimentos tributáveis, before any deduction
    deduction_mode: str      # "legal" (social security + dependents) or "simplified"
    base: Decimal            # taxable income minus the chosen deduction
    table_tax: Decimal       # tax from the progressive table
    reduction: Decimal       # Lei 15.270/2025 reduction, never above table_tax
    tax: Decimal             # what is withheld


def irrf_table_tax(base, params: dict) -> Decimal:
    """Progressive table: base x rate of its bracket - the bracket's deduction."""
    base = Decimal(base)
    if base <= 0:
        return ZERO
    for bracket in params["irrf_monthly"]["brackets"]:
        if bracket["up_to"] is None or base <= bracket["up_to"]:
            return max(ZERO, cents(base * bracket["rate"] - bracket["deduction"]))
    raise ValueError("the last IRRF bracket must have no upper limit")


def irrf_reduction(taxable_income: Decimal, table_tax: Decimal, params: dict) -> Decimal:
    """Lei 15.270/2025: computed on the income before deductions, capped at the table tax."""
    r = params["irrf_reduction_monthly"]
    if taxable_income <= r["full_until"]:
        reduction = r["full_reduction_max"]
    elif taxable_income <= r["phase_out_until"]:
        reduction = cents(r["constant"] - r["slope"] * taxable_income)
    else:
        reduction = ZERO
    return min(reduction, table_tax)


def irrf_monthly(taxable_income, params: dict, *, social_security=0, dependents: int = 0) -> IncomeTax:
    """Monthly IRRF. The payer applies the legal deductions or the simplified discount, whichever taxes less."""
    if isinstance(dependents, bool) or not isinstance(dependents, int) or dependents < 0:
        raise ValueError(f"dependents must be a whole number >= 0, got {dependents!r}")
    income = money(taxable_income)
    table = params["irrf_monthly"]
    legal = income - money(social_security) - dependents * table["dependent_deduction"]
    simplified = income - table["simplified_discount"]
    # Less tax wins; on a tie (often both zero), the larger deduction is reported.
    table_tax, base, mode = min((irrf_table_tax(legal, params), legal, "legal"),
                                (irrf_table_tax(simplified, params), simplified, "simplified"))
    reduction = irrf_reduction(income, table_tax, params)
    return IncomeTax(income, mode, max(base, ZERO), table_tax, reduction, table_tax - reduction)
