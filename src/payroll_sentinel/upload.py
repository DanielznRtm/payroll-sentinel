"""Read a company's payroll file as it comes and map it to the columns the validator reads.

Companies send CSV or Excel files with their own column names and Brazilian formats
("R$ 8.500,00", "25/03/2020", "Estágio", semicolon-separated CSV). These pure
functions turn such a file into the standard columns (pipeline.REQUIRED_COLUMNS).
No Streamlit here: the web UI calls them and the tests cover them.
"""

from __future__ import annotations

import datetime as dt
import io
import re
import unicodedata

import numpy as np
import pandas as pd

from .pipeline import REQUIRED_COLUMNS

# Column names companies often use, compared after _key() (lowercase, no accents, "_").
ALIASES: dict[str, list[str]] = {
    "company_id": ["company_id", "empresa", "cnpj", "id_empresa", "cod_empresa", "codigo_empresa"],
    "employee_id": ["employee_id", "matricula", "id_funcionario", "id_colaborador", "cod_funcionario",
                    "codigo_funcionario", "id_empregado", "id"],
    "job_title": ["job_title", "cargo", "funcao", "nome_cargo", "cargo_nome", "titulo_cargo"],
    "contract_type": ["contract_type", "tipo_contrato", "tipo_de_contrato", "contrato", "vinculo",
                      "tipo_vinculo", "regime"],
    "weekly_hours": ["weekly_hours", "horas_semanais", "carga_horaria", "carga_horaria_semanal",
                     "jornada", "jornada_semanal", "horas"],
    "monthly_salary": ["monthly_salary", "salario", "salario_mensal", "salario_base", "salario_bruto",
                       "remuneracao", "remuneracao_mensal"],
    "annual_bonus": ["annual_bonus", "bonus", "bonus_anual", "plr", "premio", "premiacao"],
    "hire_date": ["hire_date", "admissao", "data_admissao", "data_de_admissao", "dt_admissao"],
}
# Columns a file may leave out, and the value used instead.
OPTIONAL = {"company_id": "minha_empresa", "annual_bonus": 0.0}
MAX_ROWS = 20_000


class FileProblem(ValueError):
    """The file cannot be validated as it is; the message says why, for the person who sent it."""


def _key(name: object) -> str:
    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def read_table(raw: bytes, filename: str) -> pd.DataFrame:
    """CSV (comma or semicolon, UTF-8 or Latin-1) or Excel (first sheet), every cell as read."""
    try:
        if filename.lower().endswith((".xlsx", ".xlsm")):
            df = pd.read_excel(io.BytesIO(raw), dtype=object)
        else:
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = raw.decode("latin-1")  # Excel on Windows saves CSV in this encoding
            first = text.split("\n", 1)[0]
            sep = ";" if first.count(";") > first.count(",") else ","
            df = pd.read_csv(io.StringIO(text), sep=sep, dtype=str, skipinitialspace=True)
    except Exception as exc:
        raise FileProblem(f"Não foi possível ler o arquivo: {exc}") from exc
    df = df.dropna(how="all")
    if df.empty:
        raise FileProblem("O arquivo não tem linhas.")
    if len(df) > MAX_ROWS:
        raise FileProblem(f"O arquivo tem {len(df):,} linhas; o limite é {MAX_ROWS:,}.")
    return df.reset_index(drop=True)


def guess_mapping(columns) -> dict[str, str | None]:
    """For each standard column, the file's column with a known name, or None."""
    keys = {_key(c): c for c in columns}
    return {target: next((keys[n] for n in names if n in keys), None) for target, names in ALIASES.items()}


def parse_number(values: pd.Series) -> pd.Series:
    """Numbers as Brazilian files write them: 'R$ 8.500,00', '8500,5', '8.500', or plain."""
    if pd.api.types.is_numeric_dtype(values):
        return values.astype(float)

    def one(v) -> float:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return np.nan
        if isinstance(v, (int, float, np.number)):
            return float(v)
        t = re.sub(r"\s|R\$", "", str(v))
        if not t:
            return np.nan
        if "," in t and "." in t:  # the separator that comes last is the decimal one
            t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
        elif "," in t:
            t = t.replace(",", ".")
        elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", t):  # 8.500 is eight thousand five hundred
            t = t.replace(".", "")
        try:
            return float(t)
        except ValueError:
            return np.nan

    return values.map(one).astype(float)


def parse_hours(values: pd.Series) -> pd.Series:
    """'44', '44h', '44 horas', '30,0' -> hours per week."""
    if pd.api.types.is_numeric_dtype(values):
        return values.astype(float)
    found = values.astype(str).str.extract(r"(\d+(?:[.,]\d+)?)")[0]
    return pd.to_numeric(found.str.replace(",", ".", regex=False), errors="coerce")


def parse_date(values: pd.Series) -> pd.Series:
    """Dates as ISO text ('2020-03-25'). Day comes first in '25/03/2020', as in Brazil.

    A date that cannot be read is kept as it was, so the validator reports it.
    """
    def one(v):
        if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NaT:
            return None
        if isinstance(v, (pd.Timestamp, dt.datetime, dt.date)):
            return pd.Timestamp(v).date().isoformat()
        t = str(v).strip()
        if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", t):
            day, month, year = (int(x) for x in t.split("/"))
            try:
                return dt.date(year, month, day).isoformat()
            except ValueError:
                return t
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}([ T].*)?", t):
            return t[:10]
        return t

    return values.map(one)


def _contract(value) -> object:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return value
    k = _key(value).upper()
    if k.startswith("CLT"):
        return "CLT"
    if k.startswith("ESTAG"):  # estágio, estagiário(a)
        return "ESTAGIO"
    return str(value).strip()


def _id(value) -> object:
    """Excel turns 1001 into 1001.0; IDs are text."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return value if value is None or (isinstance(value, float) and np.isnan(value)) else str(value).strip()


def apply_mapping(df: pd.DataFrame, mapping: dict[str, str | None]) -> tuple[pd.DataFrame, list[str]]:
    """The file with standard column names and values, plus notes on what was assumed.

    Columns the company sent but the validator does not need are kept, as in the CLI.
    """
    missing = [c for c in REQUIRED_COLUMNS if not mapping.get(c) and c not in OPTIONAL]
    if missing:
        raise FileProblem("Faltam colunas obrigatórias: " + ", ".join(missing))
    chosen = [v for v in mapping.values() if v]
    if len(chosen) != len(set(chosen)):
        raise FileProblem("A mesma coluna do arquivo foi escolhida para dois campos.")

    out = df.drop(columns=[c for c in REQUIRED_COLUMNS if c in df.columns and c not in chosen])
    out = out.rename(columns={src: target for target, src in mapping.items() if src})
    notes = []
    for col, default in OPTIONAL.items():
        if not mapping.get(col):
            out[col] = default
            notes.append(f"Sem coluna para `{col}`: usamos {default!r} em todas as linhas.")
    out["company_id"] = out["company_id"].map(_id)
    out["employee_id"] = out["employee_id"].map(_id)
    out["job_title"] = out["job_title"].map(lambda v: v if pd.isna(v) else str(v).strip())
    out["contract_type"] = out["contract_type"].map(_contract)
    out["weekly_hours"] = parse_hours(out["weekly_hours"])
    out["monthly_salary"] = parse_number(out["monthly_salary"])
    out["annual_bonus"] = parse_number(out["annual_bonus"]).fillna(0.0)
    out["hire_date"] = parse_date(out["hire_date"])
    return out, notes
