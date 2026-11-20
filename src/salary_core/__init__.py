"""Deterministic net-pay engine for Brazilian contracts (CLT, Simples Nacional contractor, internship).

Shared by the modules of this repository. It uses only the standard library and
never imports ``payroll_sentinel``. Every rate and limit comes from
``salary_core/params/<year>.json``.
"""

from salary_core.parameters import load_params

__all__ = ["load_params"]
