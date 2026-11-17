"""Payroll Sentinel web UI (texts in Portuguese, for Brazilian companies).

    pip install -e ".[ui]"
    streamlit run app.py          # or double-click run_ui.bat on Windows

Main flow: a company uploads its payroll (CSV or Excel), checks the column mapping
and gets back what to accept, review and block, with reasons and an Excel report.
Uploaded files are compared with synthetic reference peers, processed in memory for
the session only, and never sent to an LLM. Other tabs measure the validator on
synthetic data with planted errors. Every number comes from `payroll_sentinel`,
the same code the CLI uses.

Public demo: set DEMO_MODE=1 (environment variable or a root-level key in
Streamlit secrets). The LLM option and the question tab disappear, the number of
companies is capped, and a saved LLM report is shown instead of a live call.
"""

from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from payroll_sentinel.ask import MIN_RECORDS, ask, build_benchmark
from payroll_sentinel.generate import generate
from payroll_sentinel.normalize import rule_normalize
from payroll_sentinel.pipeline import (REQUIRED_COLUMNS, reference_peers, run_evaluation,
                                       validate_against_reference)
from payroll_sentinel.taxonomy import FAMILIES, REFERENCE_DATE, legal_min_wage
from payroll_sentinel.upload import MAX_ROWS, OPTIONAL, FileProblem, apply_mapping, guess_mapping, read_table

LLM_CACHE = Path("data") / "llm_title_cache.json"
LLM_REPORT = Path(__file__).parent / "reports" / "evaluation_llm_gemini-3.5-flash-lite.md"
REPO = "https://github.com/DanielznRtm/payroll-sentinel"
MAX_COMPANIES, DEMO_MAX_COMPANIES = 60, 50
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

PRIVACY = ("O arquivo é processado só em memória, durante a sua sessão, e não é gravado. "
           "Nenhum dado vai para um LLM: os cargos são lidos por regras. As verificações não "
           "precisam de nome nem CPF; tire essas colunas antes de enviar.")
# Validator causes -> (problem, what to do), in the words a payroll analyst uses.
CAUSES = {
    "missing_salary": ("Salário vazio", "Preencha o salário mensal."),
    "missing_title": ("Cargo vazio", "Preencha o cargo."),
    "duplicate_id": ("Matrícula repetida", "Cada pessoa precisa de uma matrícula única."),
    "duplicate_record": ("Linha repetida com outra matrícula",
                         "Confira se a mesma pessoa foi enviada duas vezes."),
    "future_hire_date": ("Data de admissão impossível",
                         f"Use dd/mm/aaaa, até {REFERENCE_DATE:%d/%m/%Y} (data de corte)."),
    "decimal_shift": ("Vírgula no lugar errado", "Ex.: 8.500,00 virou 8,50. Corrija o valor."),
    "below_min_wage": ("Abaixo do salário mínimo",
                       "Confira o valor e a carga horária: o mínimo é proporcional às horas."),
    "bonus_outlier": ("Bônus muito alto", "O bônus anual passa de 1,5 salário anual: confirme."),
    "extreme_value": ("Valor fora de qualquer escala",
                      "Mais de 30 vezes longe do mercado: erro de digitação ou de unidade."),
    "annual_as_monthly": ("Salário anual no campo mensal", "Envie o valor mensal (anual ÷ 12)."),
    "divided_by_12": ("Salário mensal dividido por 12", "Envie o valor mensal cheio."),
    "level_salary_mismatch": ("Salário de outro nível", "Confira se o cargo e o nível estão certos."),
    "statistical_outlier": ("Fora do padrão do mercado", "Confirme o valor."),
    "unmapped_title": ("Cargo não reconhecido",
                       "Fica fora da comparação com o mercado; confira o nome do cargo."),
}
STATUS = {"block": "Bloquear", "warn": "Revisar", "ok": "Aceitar"}
DECISIONS = {"ACCEPT": "Aceitar o arquivo",
             "ACCEPT without blocked rows": "Aceitar sem as linhas bloqueadas",
             "REJECT - ask company to resubmit": "Rejeitar: pedir um arquivo corrigido"}
FIELDS = {"company_id": "Empresa (opcional)", "employee_id": "Matrícula", "job_title": "Cargo",
          "contract_type": "Tipo de contrato", "weekly_hours": "Horas por semana",
          "monthly_salary": "Salário mensal", "annual_bonus": "Bônus anual (opcional)",
          "hire_date": "Data de admissão"}
METHODS = {"keyword rules + CBO": "regras (palavras-chave + títulos da CBO)",
           "keyword rules only": "regras (só palavras-chave)"}
DETECTORS = {"vote_z": "z-score robusto", "vote_iqr": "Cerca IQR", "vote_iforest": "Isolation Forest",
             "flag_ensemble": "Votação (2 de 3)"}
NO_COLUMN = "(não tenho)"
FAMILY_LABELS = {key: f["label"] for key, f in FAMILIES.items()}


def demo_mode() -> bool:
    """True when the deployment sets DEMO_MODE, in Streamlit secrets or the environment."""
    try:
        value = st.secrets.get("DEMO_MODE")
    except FileNotFoundError:  # no secrets.toml: normal when running locally
        value = None
    if value is None:
        value = os.getenv("DEMO_MODE", "")
    return str(value).strip().lower() in {"1", "true", "yes"}


def llm_available() -> bool:
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    return provider == "ollama" or bool(os.getenv("LLM_API_KEY"))


def num(value) -> str:
    """4.502 (Brazilian thousands separator)."""
    return format(int(value), ",").replace(",", ".")


def dec(value: float, digits: int = 3, sign: bool = False) -> str:
    """0,892 (Brazilian decimal comma); sign=True gives +0,037 for a delta."""
    return format(value, f"{'+' if sign else ''}.{digits}f").replace(".", ",")


def pct(value: float, digits: int = 1) -> str:
    """7,1%"""
    return f"{value:.{digits}%}".replace(".", ",")


def brl(value: float) -> str:
    """R$ 7.200,00"""
    if pd.isna(value):
        return "-"
    return "R$ " + f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# st.cache_data reruns a function only when its arguments change. Only synthetic data
# is cached; an uploaded file lives in st.session_state, which ends with the session.
@st.cache_data(show_spinner=False)
def cached_evaluation(seed: int, n_companies: int, use_llm: bool):
    return run_evaluation(seed, n_companies, use_llm, LLM_CACHE if use_llm else None)


@st.cache_data(show_spinner=False)
def cached_reference() -> pd.DataFrame:
    return reference_peers()


@st.cache_data(show_spinner=False)
def sample_payroll() -> bytes:
    """One synthetic company with planted errors, written the way a Brazilian payroll export is."""
    sub = generate(seed=11, n_companies=1)[0]

    def date(iso):
        return "" if pd.isna(iso) else "/".join(reversed(str(iso).split("-")))

    def money(v):
        return "" if pd.isna(v) else f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    out = pd.DataFrame({
        "Matrícula": sub["employee_id"].str.split("-").str[1], "Cargo": sub["job_title"],
        "Tipo de contrato": sub["contract_type"].replace({"ESTAGIO": "Estágio"}),
        "Carga horária": sub["weekly_hours"], "Salário": sub["monthly_salary"].map(money),
        "Bônus anual": sub["annual_bonus"].map(money), "Data de admissão": sub["hire_date"].map(date),
        "Cidade": sub["city"]})
    return out.to_csv(sep=";", index=False).encode("utf-8-sig")


@st.cache_data(show_spinner=False)
def template_csv() -> bytes:
    return ";".join(FIELDS[c].replace(" (opcional)", "") for c in REQUIRED_COLUMNS).encode("utf-8-sig")


def sidebar() -> None:
    with st.sidebar:
        st.markdown("### Payroll Sentinel")
        st.write("Confere a folha de pagamento antes de ela entrar num benchmark salarial.")
        st.markdown("**Como funciona**\n\n"
                    "1. Envie a folha em CSV ou Excel.\n"
                    "2. Confira as colunas reconhecidas.\n"
                    "3. Veja o que aceitar, revisar e bloquear, e baixe o relatório.")
        st.markdown("**O que é verificado**\n\n"
                    "- Campos vazios, matrículas e linhas repetidas, datas impossíveis.\n"
                    "- Salário mínimo proporcional às horas (estágio é isento).\n"
                    "- Salário comparado com o mercado do mesmo cargo e nível.")
        st.markdown("**Privacidade**")
        st.caption("Nada é gravado, e nenhum dado vai para um LLM.")
        st.markdown(f"[Código no GitHub]({REPO}) · [Relatório técnico]({REPO}/blob/main/docs/technical-report.md)")


# --- Validate a payroll ------------------------------------------------------
def problems_table(result, data: pd.DataFrame) -> pd.DataFrame:
    """One row per problem found, in Portuguese, with the numbers that explain it."""
    issues = result.issues.merge(result.records[["row_id", "peer_ratio"]], on="row_id", how="left")
    issues = issues.merge(data[["row_id", "job_title", "monthly_salary", "weekly_hours"]], on="row_id")

    def detail(r) -> str:
        if r["check"] == "peer_comparison" and pd.notna(r["peer_ratio"]):
            return f"{r['peer_ratio']:.1f}× a mediana do mercado para o cargo e nível"
        if r["cause"] == "below_min_wage":
            return f"mínimo para {r['weekly_hours']:g} h/semana: {brl(legal_min_wage(r['weekly_hours']))}"
        return ""

    return pd.DataFrame({
        "Linha": issues["row_id"] + 2,  # +1 for the header, +1 because spreadsheets count from 1
        "Matrícula": issues["employee_id"], "Cargo": issues["job_title"].fillna("—"),
        "Salário": issues["monthly_salary"].map(brl),
        "Situação": issues["severity"].map(STATUS),
        "Problema": issues["cause"].map(lambda c: CAUSES.get(c, (c, ""))[0]),
        "O que fazer": issues["cause"].map(lambda c: CAUSES.get(c, ("", ""))[1]),
        "Detalhe": issues.apply(detail, axis=1),
    }).sort_values(["Situação", "Linha"], key=lambda s: s.map({"Bloquear": 0, "Revisar": 1})
                   if s.name == "Situação" else s)


def annotated(raw: pd.DataFrame, result) -> pd.DataFrame:
    """The company's own columns plus the outcome of each row."""
    status = result.records.set_index("row_id")["status"]
    reasons = (result.issues.assign(p=result.issues["cause"].map(lambda c: CAUSES.get(c, (c,))[0]))
               .groupby("row_id")["p"].agg(lambda s: "; ".join(dict.fromkeys(s))))
    out = raw.copy()
    out["Situação"] = [STATUS[status.get(i, "ok")] for i in range(len(raw))]
    out["Problemas"] = [reasons.get(i, "") for i in range(len(raw))]
    return out


def excel_report(summary: pd.DataFrame, problems: pd.DataFrame, rows: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        summary.to_excel(xl, sheet_name="Resumo", index=False)
        problems.to_excel(xl, sheet_name="Problemas", index=False)
        rows[rows["Situação"].ne("Bloquear")].to_excel(xl, sheet_name="Linhas aceitas", index=False)
        rows[rows["Situação"].eq("Bloquear")].to_excel(xl, sheet_name="Linhas para corrigir", index=False)
    return buf.getvalue()


def column_mapping(df: pd.DataFrame, file_key: str) -> dict[str, str | None]:
    guess = guess_mapping(df.columns)
    unknown = [c for c in REQUIRED_COLUMNS if guess[c] is None and c not in OPTIONAL]
    options = [NO_COLUMN] + [str(c) for c in df.columns]
    with st.expander("2. Confira as colunas", expanded=bool(unknown)):
        if unknown:
            st.warning("Escolha a coluna do arquivo para: " + ", ".join(FIELDS[c] for c in unknown) + ".")
        st.caption("Reconhecemos as colunas pelo nome. Colunas extras (como cidade) só ajudam a "
                   "diferenciar linhas parecidas.")
        cols = st.columns(4)
        mapping = {}
        for i, target in enumerate(REQUIRED_COLUMNS):
            default = str(guess[target]) if guess[target] is not None else NO_COLUMN
            choice = cols[i % 4].selectbox(FIELDS[target], options, index=options.index(default),
                                           key=f"map_{target}_{file_key}")
            mapping[target] = None if choice == NO_COLUMN else df.columns[options.index(choice) - 1]
        st.dataframe(df.head(5), hide_index=True)
    return mapping


def title_families(data: pd.DataFrame, file_key: str) -> dict[str, str]:
    """Titles the rules do not know, with the family the company picks for each one."""
    titles = data["job_title"].dropna().astype(str)
    titles = titles[titles.str.strip().ne("")]
    unknown = titles[rule_normalize(titles)["family"].isna()]
    if unknown.empty:
        return {}
    counts = unknown.value_counts()
    with st.expander(f"Cargos que não reconhecemos: {len(counts)} cargos em {int(counts.sum())} linhas "
                     "(opcional)"):
        st.caption("Sem família, a linha fica fora da comparação com o mercado e vai para revisão. "
                   "Escolha a família de cada cargo para compará-lo; deixe em branco se não for de "
                   "nenhuma. O nível continua vindo do nome do cargo (Jr, Pleno, Sr...).")
        table = pd.DataFrame({"Cargo": counts.index, "Linhas": counts.to_numpy(), "Família": None})
        edited = st.data_editor(table, key=f"titles_{file_key}", hide_index=True, width="stretch",
                                disabled=["Cargo", "Linhas"],
                                column_config={"Família": st.column_config.SelectboxColumn(
                                    "Família", options=list(FAMILY_LABELS.values()))})
    by_label = {label: key for key, label in FAMILY_LABELS.items()}
    return {title: by_label[fam] for title, fam in zip(edited["Cargo"], edited["Família"])
            if isinstance(fam, str) and fam in by_label}


def show_result(result, data: pd.DataFrame, raw: pd.DataFrame) -> None:
    st.subheader("3. Resultado")
    companies = result.companies
    for _, c in companies.iterrows():
        text = (f"**{DECISIONS[c['decision']]}**: {num(c['rows'])} linhas, {c['blocked']} bloqueadas "
                f"({pct(c['blocked_share'])}), {c['warnings']} para revisar.")
        if len(companies) > 1:
            text = f"Empresa `{c['company_id']}`: " + text
        {"ACCEPT": st.success, "ACCEPT without blocked rows": st.warning}.get(c["decision"], st.error)(text)
    if (companies["decision"] == "REJECT - ask company to resubmit").any():
        st.caption("Um arquivo com mais de 5 % de linhas bloqueadas volta inteiro para correção.")

    status = result.records["status"]
    m = st.columns(4)
    m[0].metric("Linhas", f"{num(len(status))}")
    m[1].metric("Aceitas", f"{num(int((status == 'ok').sum()))}")
    m[2].metric("Para revisar", f"{num(int((status == 'warn').sum()))}")
    m[3].metric("Bloqueadas", f"{num(int((status == 'block').sum()))}")

    problems = problems_table(result, data)
    rows = annotated(raw, result)
    summary = pd.DataFrame({"Empresa": companies["company_id"], "Linhas": companies["rows"],
                            "Bloqueadas": companies["blocked"], "Para revisar": companies["warnings"],
                            "Decisão": companies["decision"].map(DECISIONS)})
    if problems.empty:
        st.info("Nenhum problema encontrado.")
    else:
        st.markdown("**Problemas por tipo**")
        counts = (problems.groupby(["Problema", "Situação", "O que fazer"]).size().reset_index(name="Linhas")
                  .sort_values(["Situação", "Linhas"], ascending=[True, False]))
        st.dataframe(counts[["Problema", "Situação", "Linhas", "O que fazer"]], hide_index=True,
                     width="stretch", column_config={"Linhas": st.column_config.ProgressColumn(
                         "Linhas", format="%d", min_value=0, max_value=int(counts["Linhas"].max()))})
        st.markdown("**Linhas com problema**")
        show = st.segmented_control("Mostrar", ["Bloquear", "Revisar"], default=["Bloquear", "Revisar"],
                                    selection_mode="multi", key="filter_status")
        st.dataframe(problems[problems["Situação"].isin(show or [])], hide_index=True, width="stretch")
        st.caption("**Bloquear**: não entra no benchmark até ser corrigida. **Revisar**: entra depois "
                   "de uma pessoa conferir. A comparação com o mercado usa salários de referência "
                   "sintéticos, calibrados com a RAIS 2025 (registros oficiais de emprego), do mesmo "
                   "cargo e nível.")

    st.markdown("**Baixe o resultado**")
    d = st.columns(3)
    d[0].download_button("Relatório completo (Excel)", excel_report(summary, problems, rows),
                         "relatorio_payroll_sentinel.xlsx", XLSX, type="primary", key="dl_xlsx")
    d[1].download_button(f"Linhas aceitas ({num(int(rows['Situação'].ne('Bloquear').sum()))}, CSV)",
                         rows[rows["Situação"].ne("Bloquear")].to_csv(index=False, sep=";").encode("utf-8-sig"),
                         "linhas_aceitas.csv", "text/csv", key="dl_accepted")
    d[2].download_button(f"Linhas para corrigir ({num(int(rows['Situação'].eq('Bloquear').sum()))}, CSV)",
                         rows[rows["Situação"].eq("Bloquear")].to_csv(index=False, sep=";").encode("utf-8-sig"),
                         "linhas_para_corrigir.csv", "text/csv", key="dl_to_fix")


def payroll_tab() -> None:
    st.subheader("1. Envie a folha de pagamento")
    left, right = st.columns([3, 2])
    with left:
        file = st.file_uploader("Arquivo CSV ou Excel (.xlsx)", type=["csv", "xlsx"], key="upload",
                                help=f"Até {num(MAX_ROWS)} linhas. Uma linha por pessoa.")
        st.caption(PRIVACY)
    with right:
        st.markdown("**Sem um arquivo agora?**")
        # ?exemplo in the URL opens the app with the sample loaded: a one-click demo link.
        if st.button("Usar uma folha de exemplo", key="use_sample") or "exemplo" in st.query_params:
            st.session_state["sample_chosen"] = True
        st.caption("Uma empresa sintética com erros plantados.")
        b = st.columns(2)
        b[0].download_button("Baixar o exemplo", sample_payroll(), "folha_exemplo.csv", "text/csv",
                             key="dl_sample")
        b[1].download_button("Baixar modelo vazio", template_csv(), "modelo_folha.csv", "text/csv",
                             key="dl_template")

    if file is not None:
        name, content = file.name, file.getvalue()
    elif st.session_state.get("sample_chosen"):
        name, content = "folha_exemplo.csv", sample_payroll()
    else:
        with st.expander("Quais colunas a folha precisa ter?"):
            st.markdown("\n".join(f"- **{FIELDS[c]}**" for c in REQUIRED_COLUMNS))
            st.caption("Nomes comuns como *Matrícula*, *Cargo*, *Salário* e *Data de admissão* são "
                       "reconhecidos sozinhos. Valores como `R$ 8.500,00` e datas como `25/03/2020` "
                       "funcionam; estágio pode vir como *Estágio* ou *Estagiário*.")
        return

    file_key = hashlib.sha256(content).hexdigest()[:12]
    try:
        raw = read_table(content, name)
    except FileProblem as exc:
        st.error(str(exc))
        return
    mapping = column_mapping(raw, file_key)
    try:
        data, notes = apply_mapping(raw, mapping)
    except FileProblem as exc:
        st.error(str(exc))
        return
    for note in notes:
        st.caption(note)
    data.insert(0, "row_id", range(len(data)))
    families = title_families(data, file_key)

    run_key = (file_key, tuple(sorted((k, str(v)) for k, v in mapping.items())),
               tuple(sorted(families.items())))
    if st.session_state.get("run_key") != run_key:
        try:
            with st.spinner("Comparando com o mercado de referência..."):
                st.session_state["result"] = validate_against_reference(data, cached_reference(), families)
        except Exception as exc:  # e.g. text where a number was expected
            st.error(f"Não foi possível validar o arquivo: {exc}")
            return
        st.session_state["run_key"] = run_key
    show_result(st.session_state["result"], data, raw)


# --- How the validator is measured -----------------------------------------
def evaluation_tab(demo: bool) -> None:
    st.write("Para saber se o validador funciona, geramos folhas sintéticas com **erros plantados** "
             "(o gabarito), validamos e contamos quantos erros foram encontrados. Os salários seguem "
             "a dispersão real da RAIS 2025. Mesmos números de `python -m payroll_sentinel.cli run`.")
    c1, c2, c3 = st.columns(3)
    seed = c1.number_input("Semente aleatória", min_value=0, value=42, step=1, key="seed",
                           help="Mesma semente, mesmos dados. Os números do README usam 42.")
    companies = c2.slider("Empresas", min_value=5, key="companies", value=25,
                          max_value=DEMO_MAX_COMPANIES if demo else MAX_COMPANIES)
    if demo:  # no API key on the public server: show the saved LLM run instead
        use_llm = False
        c3.caption("Cargos lidos por regras (palavras-chave + títulos da CBO). Veja a aba "
                   "**Resultados com LLM** para uma execução salva com LLM.")
    else:
        use_llm = c3.checkbox("Ler cargos com um LLM", key="llm", disabled=not llm_available(),
                              help="Precisa de LLM_API_KEY (ou LLM_PROVIDER=ollama) antes de abrir "
                                   "o app. Desligado: regras offline e gratuitas.")

    if st.button("Rodar avaliação", type="primary", key="run"):
        st.session_state["eval_params"] = (int(seed), int(companies), bool(use_llm))
    if "eval_params" not in st.session_state:
        return
    try:
        with st.spinner("Gerando, validando e contando..."):
            ev = cached_evaluation(*st.session_state["eval_params"])
    except Exception as exc:  # LLM key, network or rate-limit problems
        st.error(f"A execução falhou: {exc}")
        return

    s, so = ev.score, ev.oracle_score
    st.success(f"{num(len(ev.submitted))} linhas de {ev.submitted['company_id'].nunique()} empresas, "
               f"{int((ev.truth['error_type'] != 'none').sum())} erros plantados. Cargos: **{METHODS.get(ev.method, ev.method)}**.")
    if ev.llm_coverage is not None:
        st.caption(f"Cargos respondidos pelo LLM: {pct(ev.llm_coverage)} (o resto ficou com as regras).")
    m = st.columns(4)
    m[0].metric("Precisão", dec(s["overall"]["precision"]), help="Das linhas apontadas, quantas tinham erro.")
    m[1].metric("Recall", dec(s["overall"]["recall"]), help="Dos erros plantados, quantos foram achados.")
    m[2].metric("F1", dec(s["overall"]["f1"]), help="Média harmônica de precisão e recall.")
    m[3].metric("Falsos alarmes", f"{pct(s['false_alarm_rate'], 2)}", help="Linhas limpas apontadas.")

    st.markdown("**Erros encontrados por tipo**")
    per_type = s["per_type"].assign(error_type=lambda d: d["error_type"].map(lambda c: CAUSES.get(c, (c,))[0]))
    st.dataframe(per_type.rename(columns={"error_type": "Erro plantado", "planted": "Plantados",
                                          "detected": "Encontrados", "recall": "Recall",
                                          "correct_cause": "Causa certa", "cause_accuracy": "% causa certa"}),
                 hide_index=True)
    left, right = st.columns(2)
    with left:
        st.markdown("**Detectores da comparação com pares**")
        st.caption(f"Erros estatísticos visíveis: {s['stat_coverage']} (cargo não reconhecido fica sem pares).")
        st.dataframe(s["detectors"].rename(index=DETECTORS, columns={
            "precision": "Precisão", "recall": "Recall", "f1": "F1", "tp": "Acertos",
            "fp": "Alarmes falsos", "fn": "Perdidos", "flagged": "Apontados"}))
    with right:
        st.markdown("**Leitura dos cargos**")
        titles = ev.titles.assign(subset=ev.titles["subset"].replace(
            {"all": "todos", "common titles": "cargos comuns", "long-tail titles": "cargos raros"}))
        st.dataframe(titles.rename(columns={
            "subset": "Cargos", "rows": "Linhas", "family_acc": "Família certa",
            "level_acc": "Nível certo", "both_acc": "Os dois", "unmapped": "Sem família"}), hide_index=True)
        st.metric("Recall com cargos perfeitos", dec(so["overall"]["recall"]),
                  delta=dec(so["overall"]["recall"] - s["overall"]["recall"], sign=True),
                  help="O mesmo validador com os cargos certos: o ganho que falta na leitura dos cargos.")
    st.download_button("Baixar evaluation.md", ev.report(), "evaluation.md", "text/markdown", key="dl_report")


def llm_results_tab() -> None:
    st.caption("Relatório salvo de uma execução real (semente 42, 25 empresas) com os cargos lidos por "
               "`gemini-3.5-flash-lite`. É um arquivo do repositório, não uma chamada ao LLM agora. "
               "O relatório técnico está em inglês.")
    st.markdown(LLM_REPORT.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def cached_benchmark() -> pd.DataFrame:
    return build_benchmark()


def ask_tab() -> None:
    st.write("Pergunte em português ou inglês sobre o benchmark sintético validado (semente 42, "
             "25 empresas), por exemplo *qual a mediana de analista de dados sênior em Campinas?*")
    st.caption("O LLM só transforma a pergunta numa consulta de formato fixo (filtros, agrupamento, "
               "métrica). O código confere cada campo e calcula cada número; nunca executa texto do "
               f"LLM. Só entram linhas aprovadas, com salário equivalente a tempo integral, e são "
               f"precisos pelo menos {MIN_RECORDS} registros.")
    question = st.text_input("Pergunta", key="question", max_chars=500)
    if st.button("Perguntar", type="primary", key="ask") and question.strip():
        from payroll_sentinel.llm import LLMClient
        try:
            with st.spinner("Traduzindo a pergunta e calculando a resposta..."):
                st.session_state["ask_result"] = ask(question, cached_benchmark(), LLMClient.from_env())
        except Exception as exc:  # LLM key, network or rate-limit problems
            st.error(f"A chamada ao LLM falhou: {exc}")
            return
    result = st.session_state.get("ask_result")
    if result is None:
        return
    st.info(result.text)
    if result.answer is not None and result.answer.groups is not None:
        st.dataframe(result.answer.groups, hide_index=True)
    if result.query is not None:
        with st.expander("Consulta conferida e executada pelo código"):
            st.json(result.query.to_dict())
    if result.error:
        st.caption(f"Resposta do LLM rejeitada: {result.error}")


DEMO = demo_mode()
st.set_page_config(page_title="Payroll Sentinel", page_icon="🛡️", layout="wide")
sidebar()
st.title("🛡️ Payroll Sentinel")
st.caption("Valide a folha de pagamento antes de ela entrar no benchmark salarial: erros de "
           "digitação, de unidade e de cadastro, apontados linha a linha.")
names = ["Validar minha folha", "Como medimos", "Resultados com LLM"]
show_ask = not DEMO and llm_available()  # the question tab needs a key; the demo has none
tabs = st.tabs(names + (["Perguntar ao benchmark"] if show_ask else []))
with tabs[0]:
    payroll_tab()
with tabs[1]:
    evaluation_tab(demo=DEMO)
with tabs[2]:
    llm_results_tab()
if show_ask:
    with tabs[3]:
        ask_tab()
