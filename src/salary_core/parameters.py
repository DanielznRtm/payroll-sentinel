"""Tax parameters per year, read from versioned JSON files with official sources.

No rate or limit is written in Python: every number comes from
``salary_core/params/<year>.json``. Numbers are read as ``Decimal`` so that
0.133145 or 1621.00 are exact (a float cannot store most decimal fractions).
"""

from __future__ import annotations

import json
from decimal import Decimal
from importlib import resources
from pathlib import Path


def load_params(year: int, directory: str | Path | None = None) -> dict:
    """Load the parameters of ``year``. ``directory`` overrides the packaged files (for tests)."""
    if directory is None:
        path = resources.files("salary_core") / "params" / f"{year}.json"
    else:
        path = Path(directory) / f"{year}.json"
    if not path.is_file():
        raise ValueError(f"no tax parameters for {year}")
    params = json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal, parse_int=Decimal)
    if params.get("year") != year:
        raise ValueError(f"{year}.json says year {params.get('year')}")
    _check_sources(params, year)
    return params


def _check_sources(params: dict, year: int) -> None:
    """Every block of parameters must cite at least one official https source."""
    for name, block in params.items():
        if name == "year":
            continue
        sources = block.get("source") if isinstance(block, dict) else None
        if not sources or not all(isinstance(s, str) and s.startswith("https://") for s in sources):
            raise ValueError(f"{year}.json: '{name}' needs a list of https sources")
