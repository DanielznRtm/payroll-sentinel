"""Deterministic net-pay engine for Brazilian contracts (CLT, Simples Nacional contractor, internship).

Shared by the modules of this repository. It uses only the standard library and
never imports ``payroll_sentinel``. Every rate and limit comes from
``salary_core/params/<year>.json``.
"""

from salary_core.net_pay import NetPay, clt_net, intern_net, pj_net
from salary_core.parameters import load_params
from salary_core.taxes import (IncomeTax, inss_employee, inss_pro_labore, irrf_monthly, irrf_table_tax,
                               simples_effective_rate)

__all__ = ["IncomeTax", "NetPay", "clt_net", "inss_employee", "inss_pro_labore", "intern_net", "irrf_monthly",
           "irrf_table_tax", "load_params", "pj_net", "simples_effective_rate"]
