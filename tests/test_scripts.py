"""Calculations inside scripts/ that feed README numbers. No network, no downloaded data."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from calibrate_generator import next_sigma  # noqa: E402
from rais_check import COLS, city_index, keep, stats  # noqa: E402
from state_of_data_check import band_bounds, grouped_median  # noqa: E402


def test_rais_filter_keeps_only_full_time_active_clt_jobs_in_mapped_occupations():
    rows = [  # cbo, city, active, hours, contract, intermittent, pay
        ("212405", "355030", "1", "44", "10", "0", "9500.00"),   # kept: developer in São Paulo
        ("212405", "355030", "0", "44", "10", "0", "9500.00"),   # not active on 31 December
        ("212405", "355030", "1", "20", "10", "0", "4000.00"),   # part-time
        ("212405", "355030", "1", "44", "30", "0", "9500.00"),   # civil servant, not CLT
        ("212405", "355030", "1", "44", "10", "1", "9500.00"),   # intermittent
        ("212405", "330455", "1", "44", "10", "0", "9500.00"),   # Rio de Janeiro: not a city here
        ("999999", "355030", "1", "44", "10", "0", "9500.00"),   # occupation outside the families
        ("212405", "350950", "1", "40", "10", "0", ".00"),       # kept by the filters, but no pay
    ]
    chunk = pd.DataFrame(rows, columns=list(COLS.values()))
    counts = {}
    kept = keep(chunk, counts)
    assert kept[["family", "cbo", "city", "pay"]].values.tolist() == [
        ["software_engineer", "212405", "São Paulo", 9500.0]]
    assert counts == {"rows read": 8, "matching jobs with no December pay": 1}


def test_rais_stats_reports_median_quartiles_and_log_spread():
    s = stats(pd.Series([1000.0, 2000.0, 4000.0]))
    assert (s["rows"], s["median"]) == (3, 2000.0)
    assert s["log-pay SD"] == pytest.approx(np.std(np.log([1000, 2000, 4000])))


def test_rais_city_index_compares_the_same_occupation_by_kind_of_job():
    def jobs(cbo, family, city, pay, n):
        return pd.DataFrame({"cbo": [cbo] * n, "family": [family] * n, "city": [city] * n, "pay": [pay] * n})
    df = pd.concat([
        jobs("212405", "software_engineer", "São Paulo", 10000.0, 40),
        jobs("212405", "software_engineer", "Campinas", 9000.0, 30),       # office: 0.9
        jobs("784205", "production_operator", "São Paulo", 2500.0, 30),
        jobs("784205", "production_operator", "Campinas", 3000.0, 30),     # industrial: 1.2
        jobs("721215", "production_operator", "Campinas", 9999.0, 10),     # too few jobs: ignored
    ])
    got = city_index(df).set_index("kind")["index"]
    assert got.to_dict() == pytest.approx({"industrial": 1.2, "office": 0.9})


def test_calibration_adds_only_the_missing_variance():
    assert next_sigma(0.15, 0.50, 0.40) == pytest.approx(np.sqrt(0.15 ** 2 + 0.50 ** 2 - 0.40 ** 2))
    assert next_sigma(0.15, 0.30, 0.40) == 0.05                    # never below the floor


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
