"""Reading company files as they come (CSV/Excel, Brazilian formats) and the reference peers."""

import io

import numpy as np
import pandas as pd
import pytest

from payroll_sentinel.generate import generate
from payroll_sentinel.pipeline import (REQUIRED_COLUMNS, reference_peers, validate_against_reference,
                                       validate_submissions)
from payroll_sentinel.upload import (FileProblem, apply_mapping, guess_mapping, parse_date,
                                     parse_number, read_table)

BR_CSV = (
    "Matrícula;Cargo;Tipo de contrato;Carga horária;Salário;PLR;Data de admissão;Nome\n"
    "1001;Analista de Dados Pleno;CLT;44h;R$ 7.200,00;3.000,00;15/03/2021;Ana\n"
    "1002;Estagiário de RH;Estágio;30;1.400,50;;01/02/2026;Bruno\n"
).encode("latin-1")


def test_brazilian_csv_is_read_and_mapped():
    df = read_table(BR_CSV, "folha.csv")
    mapping = guess_mapping(df.columns)
    assert mapping["employee_id"] == "Matrícula" and mapping["monthly_salary"] == "Salário"
    assert mapping["company_id"] is None                       # optional: one company per file
    out, notes = apply_mapping(df, mapping)
    assert out[REQUIRED_COLUMNS].to_dict("records") == [
        {"company_id": "minha_empresa", "employee_id": "1001", "job_title": "Analista de Dados Pleno",
         "contract_type": "CLT", "weekly_hours": 44.0, "monthly_salary": 7200.0, "annual_bonus": 3000.0,
         "hire_date": "2021-03-15"},
        {"company_id": "minha_empresa", "employee_id": "1002", "job_title": "Estagiário de RH",
         "contract_type": "ESTAGIO", "weekly_hours": 30.0, "monthly_salary": 1400.5, "annual_bonus": 0.0,
         "hire_date": "2026-02-01"}]
    assert "Nome" in out.columns                              # extra columns are kept, as in the CLI
    assert len(notes) == 1 and "company_id" in notes[0]


def test_excel_file_is_read_with_its_types(tmp_path):
    pytest.importorskip("openpyxl")
    src = pd.DataFrame({"matricula": [1001.0], "cargo": ["Operador de Produção"], "vinculo": ["clt"],
                        "jornada": [44], "salario": [2600.0], "admissao": [pd.Timestamp("2019-07-01")]})
    buf = io.BytesIO()
    src.to_excel(buf, index=False)
    df = read_table(buf.getvalue(), "folha.xlsx")
    out, _ = apply_mapping(df, guess_mapping(df.columns))
    row = out.iloc[0]
    assert (row["employee_id"], row["contract_type"], row["hire_date"]) == ("1001", "CLT", "2019-07-01")
    assert row["monthly_salary"] == 2600.0 and row["annual_bonus"] == 0.0


@pytest.mark.parametrize("text, value", [
    ("R$ 8.500,00", 8500.0), ("8500,5", 8500.5), ("8.500", 8500.0), ("8,5", 8.5),   # 8,5: a typo the
    ("8,500.00", 8500.0), ("7200", 7200.0), ("", np.nan), ("abc", np.nan)])         # validator must see
def test_numbers_in_brazilian_and_plain_formats(text, value):
    got = parse_number(pd.Series([text], dtype=object)).iloc[0]
    assert got == value or (np.isnan(value) and np.isnan(got))


def test_dates_put_the_day_first_and_keep_what_they_cannot_read():
    got = parse_date(pd.Series(["25/03/2020", "2020-03-25 00:00:00", "31/02/2020", "ontem"])).tolist()
    assert got == ["2020-03-25", "2020-03-25", "31/02/2020", "ontem"]


def test_missing_required_columns_and_double_use_are_explained():
    df = pd.DataFrame({"cargo": ["x"], "salario": ["1"]})
    with pytest.raises(FileProblem, match="employee_id"):
        apply_mapping(df, guess_mapping(df.columns))
    mapping = {c: None for c in REQUIRED_COLUMNS} | {
        "employee_id": "cargo", "job_title": "cargo", "contract_type": "cargo", "weekly_hours": "cargo",
        "monthly_salary": "salario", "hire_date": "cargo"}
    with pytest.raises(FileProblem, match="dois campos"):
        apply_mapping(df, mapping)


def test_empty_file_is_refused():
    with pytest.raises(FileProblem, match="não tem linhas"):
        read_table(b"cargo;salario\n", "x.csv")


def test_reference_peers_make_a_single_company_comparable():
    sub, truth = generate(seed=7, n_companies=25)
    errors = truth["error_type"].eq("annual_as_monthly")
    company = sub.loc[errors, "company_id"].value_counts().index[0]   # a company with such errors
    part = sub[sub["company_id"].eq(company)]
    planted = set(part.loc[errors[part.index], "row_id"])

    def caught(res):
        return planted & set(res.issues.loc[res.issues["check"].eq("peer_comparison"), "row_id"])

    result = validate_against_reference(part, reference_peers())
    alone = validate_submissions(part)                             # too few peers on its own
    assert len(caught(result)) > len(caught(alone))
    assert set(result.records["row_id"]) == set(part["row_id"])  # only the file's rows come back
    assert result.companies["company_id"].tolist() == [company]


def test_company_can_name_the_family_of_a_title_the_rules_do_not_know():
    ref = reference_peers()
    row = {"company_id": "c", "employee_id": "1", "job_title": "Dev Backend Sr.", "contract_type": "CLT",
           "weekly_hours": 44, "monthly_salary": 15000.0 * 12, "annual_bonus": 0.0, "hire_date": "2020-01-01"}
    df = pd.DataFrame([row])
    unknown = validate_against_reference(df, ref)
    assert set(unknown.issues["cause"]) == {"unmapped_title"}      # no family: no peers, x12 unseen
    named = validate_against_reference(df, ref, {"Dev Backend Sr.": "software_engineer"})
    assert set(named.issues["cause"]) == {"annual_as_monthly"}
    assert named.records.loc[0, "level"] == "senior"                 # the level still comes from "Sr."
