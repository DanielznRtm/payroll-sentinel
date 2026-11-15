"""How realistic are the synthetic salaries? Compare them with RAIS, Brazil's official job records.

RAIS (Relação Anual de Informações Sociais, Ministério do Trabalho e Emprego) lists
every formal job of the year, without names or IDs. The microdata are published as
.7z files per region at ftp.mtps.gov.br/pdet/microdados/RAIS/. They are not in the
repository: download one and pass its path. The file is read as a stream through
the system `tar` (Windows 10+ and most Linux/macOS systems open .7z with it), so the
uncompressed text never touches the disk.

    python scripts/rais_check.py RAIS_VINC_PUB_SP.7z [--reports reports]

Seven columns are read: CBO occupation, municipality, active on 31 December, contracted
hours, contract type, intermittent flag and December pay. Age, sex, race, nationality,
disability and schooling are never read. Kept: CLT jobs active on 31 December, 40 to
44 hours a week, not intermittent, with a positive December pay, in the CBO codes
approved for each family (cbo_titles.CBO_CODES) and in the synthetic cities of São
Paulo state. Only aggregates leave this script.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from payroll_sentinel.cbo_titles import CBO_CODES  # noqa: E402
from payroll_sentinel.generate import generate  # noqa: E402

COLS = {"cbo": "CBO 2002 Ocupação - Código", "city": "Município - Código",
        "active": "Ind Vínculo Ativo 31/12 - Código", "hours": "Qtd Hora Contr",
        "contract": "Tipo Vínculo - Código", "intermittent": "Ind Trabalho Intermitente - Código",
        "pay": "Vl Rem Dezembro Nom"}
CITIES = {"355030": "São Paulo", "350950": "Campinas", "355220": "Sorocaba"}  # IBGE codes, 6 digits
CLT = {"10", "15", "20", "25", "60", "65", "70", "75"}  # urban/rural CLT, open-ended or fixed-term
FAMILY_OF = {code: fam for fam, codes in CBO_CODES.items() for code in codes}
MIN_ROWS = 30


def stream(path: str):
    """Yield chunks of the RAIS text inside the .7z, decompressed on the fly by `tar`."""
    tar = shutil.which("tar") if sys.platform != "win32" else r"C:\Windows\System32\tar.exe"
    proc = subprocess.Popen([tar, "-xOf", path], stdout=subprocess.PIPE)
    try:
        yield from pd.read_csv(proc.stdout, sep=",", quotechar='"', encoding="latin-1", dtype=str,
                               usecols=list(COLS.values()), chunksize=1_000_000)
    finally:
        proc.kill()


def keep(chunk: pd.DataFrame, counts: dict) -> pd.DataFrame:
    """Rows comparable with a synthetic full-time CLT payroll row, plus counts of what was dropped."""
    c = chunk.rename(columns={v: k for k, v in COLS.items()})
    counts["rows read"] = counts.get("rows read", 0) + len(c)
    c = c[c["cbo"].isin(FAMILY_OF.keys()) & c["city"].isin(CITIES.keys())]
    hours = pd.to_numeric(c["hours"], errors="coerce")
    c = c[c["active"].eq("1") & c["contract"].isin(CLT) & c["intermittent"].ne("1") & hours.between(40, 44)]
    pay = pd.to_numeric(c["pay"].str.replace(",", ".", regex=False), errors="coerce")
    counts["matching jobs with no December pay"] = (counts.get("matching jobs with no December pay", 0)
                                                   + int((pay.fillna(0) <= 0).sum()))
    c = c.assign(pay=pay)[pay > 0]
    return pd.DataFrame({"family": c["cbo"].map(FAMILY_OF), "cbo": c["cbo"],
                         "city": c["city"].map(CITIES), "pay": c["pay"]})


def stats(values: pd.Series) -> dict:
    """Median, quartiles and the spread of log pay, the quantity the peer comparison works on."""
    v = values.to_numpy(dtype=float)
    return {"rows": len(v), "median": float(np.median(v)), "p25": float(np.percentile(v, 25)),
            "p75": float(np.percentile(v, 75)), "log-pay SD": float(np.std(np.log(v)))}


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scope, part in [("3 cities", df)] + [(c, df[df["city"].eq(c)]) for c in CITIES.values()]:
        for fam, g in part.groupby("family"):
            if len(g) >= MIN_ROWS:
                rows.append({"scope": scope, "family": fam, **stats(g["pay"])})
    return pd.DataFrame(rows)


def by_code(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["family", "cbo"])["pay"].agg(rows="size", median="median").reset_index()
    g = g[g["rows"] >= MIN_ROWS].sort_values(["family", "rows"], ascending=[True, False])
    g["share of family"] = (g["rows"] / g.groupby("family")["rows"].transform("sum")).round(3)
    g["median"] = g["median"].map(lambda v: f"{v:,.0f}")
    return g[["family", "cbo", "rows", "share of family", "median"]]


def synthetic(n_companies: int = 200, seed: int = 42) -> pd.DataFrame:
    sub, truth = generate(seed=seed, n_companies=n_companies)
    df = sub.merge(truth[["row_id", "true_family", "error_type"]], on="row_id")
    df = df[df["error_type"].eq("none") & df["contract_type"].eq("CLT") & df["weekly_hours"].ge(40)
            & df["city"].isin(CITIES.values())]
    return pd.DataFrame({"family": df["true_family"], "city": df["city"], "pay": df["monthly_salary"]})


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("archive")
    p.add_argument("--reports", default="reports")
    args = p.parse_args()

    counts: dict = {}
    real = pd.concat([keep(chunk, counts) for chunk in stream(args.archive)], ignore_index=True)
    table = summarize(real).merge(summarize(synthetic()), on=["scope", "family"], how="left",
                                  suffixes=("", " (synthetic)"))
    table["synthetic / real median"] = (table["median (synthetic)"] / table["median"]).round(2)
    shown = table[["scope", "family", "rows", "median", "median (synthetic)", "synthetic / real median",
                   "p25", "p75", "log-pay SD", "log-pay SD (synthetic)"]].copy()
    for c in ("median", "median (synthetic)", "p25", "p75"):
        shown[c] = shown[c].map(lambda v: "-" if pd.isna(v) else f"{v:,.0f}")
    for c in ("log-pay SD", "log-pay SD (synthetic)"):
        shown[c] = shown[c].round(2)

    lines = [
        "# How realistic are the synthetic salaries? (RAIS)", "",
        f"Source: RAIS microdata, file `{Path(args.archive).name}` (Ministério do Trabalho e Emprego). "
        f"Rows read: {counts['rows read']:,}. Kept: CLT jobs active on 31 December, 40-44 h/week, not "
        "intermittent, in the approved CBO codes, in São Paulo, Campinas and Sorocaba: "
        f"{len(real):,} jobs. Left out because December pay was empty or zero: "
        f"{counts['matching jobs with no December pay']:,}.", "",
        "RAIS December pay includes overtime and commissions paid that month (not the 13th "
        "salary); the synthetic `monthly_salary` is base pay. RAIS has no seniority level, so both "
        "sides pool every level and the medians also reflect the level mix. Synthetic: "
        f"generate(seed=42, n_companies=200), clean full-time CLT rows. Groups with fewer than "
        f"{MIN_ROWS} rows are not shown.", "",
        "`log-pay SD` is the spread of log pay inside a group: the peer comparison flags salaries "
        "far from their peers on this scale, so a wider real spread means real errors hide more "
        "easily.", "",
        shown.to_markdown(index=False), "",
        "## By CBO code (3 cities)", "",
        "A family pools several CBO occupations; their pay can differ a lot (for example retail "
        "sellers and sales managers in `sales_rep`).", "",
        by_code(real).to_markdown(index=False), "",
    ]
    out = Path(args.reports)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "realism_rais.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"Report written to {path}")


if __name__ == "__main__":
    main()
