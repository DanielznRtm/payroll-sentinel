"""Smoke test for the Streamlit UI. Skipped when the [ui] extra is not installed.

AppTest runs the script in-process (no server, no browser, no network) and lets
the test click widgets like a user would. AppTest cannot attach a file to the
uploader, so the payroll flow is driven through the sample-file button, which
goes through the same reading, mapping and validation code.
"""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = Path(__file__).resolve().parents[1] / "app.py"
TABS = ["Validar minha folha", "Como medimos", "Resultados com LLM"]


@pytest.fixture
def app(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("DEMO_MODE", raising=False)
    return AppTest.from_file(str(APP), default_timeout=120).run()


def test_app_starts_without_errors(app):
    assert not app.exception
    assert app.checkbox(key="llm").disabled       # no key -> LLM option is off
    assert [t.label for t in app.tabs] == TABS
    assert app.get("file_uploader")


def test_sample_payroll_goes_through_mapping_validation_and_downloads(app):
    app.button(key="use_sample").click().run()
    assert not app.exception
    labels = [m.label for m in app.metric]
    assert labels[:4] == ["Linhas", "Aceitas", "Para revisar", "Bloqueadas"]
    blocked = int(app.metric[3].value.replace(".", "").replace(",", ""))
    assert blocked > 0                            # the sample has planted errors
    banner = (app.success or app.warning or app.error)[0].value
    assert banner.startswith("**Aceitar") or banner.startswith("**Rejeitar")
    mapped = {s.label: s.value for s in app.selectbox}
    assert mapped["Matrícula"] == "Matrícula" and mapped["Salário mensal"] == "Salário"


def test_exemplo_link_opens_the_app_with_the_sample_validated(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("DEMO_MODE", raising=False)
    at = AppTest.from_file(str(APP), default_timeout=120)
    at.query_params["exemplo"] = ""
    at.run()
    assert not at.exception
    assert [m.label for m in at.metric][:4] == ["Linhas", "Aceitas", "Para revisar", "Bloqueadas"]


def test_ask_tab_needs_a_key_and_answers_with_the_code(monkeypatch):
    import json

    from payroll_sentinel.llm import LLMClient

    class ScriptedClient:
        def chat(self, system, user, json_mode=False):
            return json.dumps({"in_scope": True, "metric": "count", "column": "monthly_salary",
                               "filters": [{"column": "contract_type", "op": "eq", "value": "CLT"}]})

    monkeypatch.delenv("DEMO_MODE", raising=False)
    monkeypatch.setenv("LLM_API_KEY", "fake-key")
    monkeypatch.setattr(LLMClient, "from_env", classmethod(lambda cls: ScriptedClient()))
    at = AppTest.from_file(str(APP), default_timeout=120).run()
    assert [t.label for t in at.tabs][-1] == "Perguntar ao benchmark"
    at.text_input(key="question").set_value("q1")
    at.button(key="ask").click().run()
    assert not at.exception
    answer = at.tabs[3].info[0].value
    assert answer.startswith("Number of records for contract_type = CLT:")
    assert "approved records" in answer


def test_demo_mode_accepts_uploads_but_never_offers_an_llm(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "1")
    monkeypatch.setenv("LLM_API_KEY", "fake-key")   # even with a key, no LLM in the demo
    at = AppTest.from_file(str(APP), default_timeout=120).run()
    assert not at.exception
    assert [t.label for t in at.tabs] == TABS        # no question tab
    assert at.get("file_uploader")
    assert not at.checkbox                           # no LLM checkbox at all
    assert at.slider(key="companies").max == 50
    assert any("não é gravado" in c.value for c in at.caption)
    assert "precision **0.913**" in at.tabs[2].markdown[0].value


def test_app_runs_evaluation(app):
    app.slider(key="companies").set_value(8)
    app.button(key="run").click().run()
    assert not app.exception
    labels = [m.label for m in app.metric]
    assert {"Precisão", "Recall", "F1"} <= set(labels)
    assert float(app.metric[labels.index("Precisão")].value.replace(",", ".")) > 0.80
