"""Tax parameters: official sources, exact decimals, and salary_core's independence."""

import ast
import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from salary_core import load_params

CORE_DIR = Path(__file__).resolve().parents[1] / "src" / "salary_core"


def test_2026_params_load_as_exact_decimals():
    p = load_params(2026)
    assert p["year"] == 2026
    assert p["irrf_reduction_monthly"]["slope"] == Decimal("0.133145")   # exact, not 0.13314499...
    assert p["minimum_wage"]["monthly"] == Decimal("1621.00")
    assert p["inss_employee"]["bands"][-1]["up_to"] == Decimal("8475.55")  # INSS ceiling


def test_every_block_cites_an_official_https_source():
    p = load_params(2026)
    blocks = {k: v for k, v in p.items() if k != "year"}
    assert len(blocks) == 8
    for name, block in blocks.items():
        assert block["source"], name
        for url in block["source"]:
            host = url.split("/")[2]
            assert url.startswith("https://") and host.endswith(".gov.br"), (name, url)


def test_unknown_year_is_refused():
    with pytest.raises(ValueError, match="no tax parameters for 1999"):
        load_params(1999)


def test_a_block_without_source_is_refused(tmp_path):
    data = json.loads((CORE_DIR / "params" / "2026.json").read_text(encoding="utf-8"))
    del data["irrf_monthly"]["source"]
    (tmp_path / "2026.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="'irrf_monthly' needs a list of https sources"):
        load_params(2026, directory=tmp_path)


def test_salary_core_uses_only_the_standard_library():
    """Module C will reuse salary_core, so it must not depend on payroll_sentinel, pandas or numpy."""
    stdlib = set(sys.stdlib_module_names)
    for path in CORE_DIR.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names = [node.module]
            else:
                continue
            for name in names:
                top = name.split(".")[0]
                assert top in stdlib or top == "salary_core", f"{path.name} imports {name}"
