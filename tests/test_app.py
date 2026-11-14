"""Smoke test for the Streamlit UI. Skipped when the [ui] extra is not installed.

AppTest runs the script in-process (no server, no browser, no network) and lets
the test click widgets like a user would.
"""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture
def app(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("DEMO_MODE", raising=False)
    return AppTest.from_file(str(APP), default_timeout=120).run()


def test_app_starts_without_errors(app):
    assert not app.exception
    assert app.checkbox(key="llm").disabled       # no key -> LLM option is off
    assert [t.label for t in app.tabs] == ["Evaluation on synthetic data", "Validate a CSV"]


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
    assert [t.label for t in at.tabs][-1] == "Ask the benchmark"
    at.text_input(key="question").set_value("q1")
    at.button(key="ask").click().run()
    assert not at.exception
    answer = at.tabs[2].info[0].value
    assert answer.startswith("Number of records for contract_type = CLT:")
    assert "approved records" in answer


def test_demo_mode_hides_upload(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "1")
    monkeypatch.setenv("LLM_API_KEY", "fake-key")   # even with a key, no LLM option in the demo
    at = AppTest.from_file(str(APP), default_timeout=120).run()
    assert not at.exception
    assert [t.label for t in at.tabs] == ["Evaluation on synthetic data", "LLM results"]
    assert not at.get("file_uploader")               # the upload widget is never rendered
    assert not at.checkbox                           # no LLM checkbox at all
    assert at.slider(key="companies").max == 50
    assert at.info[0].value.startswith("Public demo: synthetic data only.")
    assert "precision **0.959**" in at.tabs[1].markdown[0].value


def test_app_runs_evaluation(app):
    app.slider(key="companies").set_value(8)
    app.button(key="run").click().run()
    assert not app.exception
    labels = [m.label for m in app.metric]
    assert {"Precision", "Recall", "F1"} <= set(labels)
    assert float(app.metric[labels.index("Precision")].value) > 0.85
