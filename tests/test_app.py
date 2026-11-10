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
    return AppTest.from_file(str(APP), default_timeout=120).run()


def test_app_starts_without_errors(app):
    assert not app.exception
    assert app.checkbox(key="llm").disabled       # no key -> LLM option is off


def test_app_runs_evaluation(app):
    app.slider(key="companies").set_value(8)
    app.button(key="run").click().run()
    assert not app.exception
    labels = [m.label for m in app.metric]
    assert {"Precision", "Recall", "F1"} <= set(labels)
    assert float(app.metric[labels.index("Precision")].value) > 0.85
