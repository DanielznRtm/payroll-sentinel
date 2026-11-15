"""Calculations inside scripts/ that feed README numbers. No network, no downloaded data."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from state_of_data_check import band_bounds, grouped_median  # noqa: E402


def test_band_bounds_reads_survey_salary_bands():
    assert band_bounds("de R$ 8.001/mês a R$ 12.000/mês") == (8000.0, 12000.0)
    assert band_bounds("Menos de R$ 1.000/mês") == (0.0, 1000.0)
    assert band_bounds("Acima de R$ 40.001/mês") is None          # open-ended: no upper bound
    assert band_bounds("de R$ 25.001/mês a R$ 3000/mês") is None  # malformed answer in the survey


def test_grouped_median_interpolates_inside_the_middle_band():
    two_bands = pd.Series([(0.0, 1000.0)] * 2 + [(1000.0, 2000.0)] * 2)
    assert grouped_median(two_bands) == 1000.0                    # the middle falls on the edge
    skewed = pd.Series([(0.0, 1000.0)] + [(1000.0, 2000.0)] * 3)
    assert grouped_median(skewed) == pytest.approx(1000 + (2 - 1) / 3 * 1000)
