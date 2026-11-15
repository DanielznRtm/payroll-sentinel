"""Held-out title evaluation. No network: the LLM is a scripted fake client.

Titles here are neutral tokens (t1, t2...) on purpose: real held-out titles are
written by hand in eval/heldout_titles.csv, never generated.
"""

import json
import re
from pathlib import Path

import pandas as pd
import pytest

from payroll_sentinel import cli
from payroll_sentinel.llm import LLMClient, LLMStats
from payroll_sentinel.taxonomy import FAMILIES
from payroll_sentinel.titles_eval import HeldoutError, compare, load_heldout, summarize

HELDOUT = Path(__file__).resolve().parents[1] / "eval" / "heldout_titles.csv"


class ScriptedClient:
    """Stands in for an LLM: answers each cleaned title from a fixed table."""
    model = label = "llama3.1:8b"  # has a ':' like real Ollama names, not allowed in Windows file names

    def __init__(self, answers):
        self.answers = answers
        self.stats = LLMStats()

    def chat(self, system, user, json_mode=False):
        results = []
        for line in user.splitlines():
            i, title = line.split(": ", 1)
            family, level = self.answers[title]
            results.append({"id": int(i), "family": family, "level": level})
        return json.dumps({"results": results})


def write_csv(path, rows):
    pd.DataFrame(rows, columns=["title", "family", "level"]).to_csv(path, index=False)
    return path


def run_cli(monkeypatch, *args):
    monkeypatch.setattr("sys.argv", ["payroll_sentinel", "eval-titles", *map(str, args)])
    cli.main()


def test_load_heldout_reports_every_problem(tmp_path):
    listed = FAMILIES["data_scientist"]["easy"][0]
    path = write_csv(tmp_path / "h.csv", [
        ["TODO 1", "data_scientist", "senior"],
        ["t1", "astronaut", "senior"],
        ["t2", "data_scientist", ""],
        [listed, "data_scientist", "mid"],
        ["t3", "", ""],
        ["T3!", "", ""],
        ["", "hr_analyst", "mid"],
    ])
    with pytest.raises(HeldoutError) as err:
        load_heldout(path)
    msg = str(err.value)
    assert "line 2: placeholder title 'TODO 1'" in msg
    assert "line 3: unknown family 'astronaut'" in msg
    assert "line 4: level must be one of" in msg
    assert "line 5:" in msg and "already in taxonomy.py" in msg
    assert "line 7: 'T3!' duplicates line 6" in msg
    assert "line 8: empty title" in msg


def test_load_heldout_out_of_taxonomy_has_no_level(tmp_path):
    gold = load_heldout(write_csv(tmp_path / "h.csv", [["t1", "data_scientist", "senior"],
                                                       ["t2", "", "mid"]]))
    assert gold["family"].tolist() == ["data_scientist", None]
    assert gold["level"].tolist() == ["senior", None]   # a level without a family is never scored


def test_compare_separates_abstention_from_wrong_family():
    gold = pd.DataFrame({"title": ["t1", "t2", "t3", "t4", "t5", "t6"],
                         "family": ["data_scientist"] * 3 + ["software_engineer", None, None],
                         "level": ["senior"] * 3 + ["junior", None, None]})
    pred = pd.DataFrame({"family": ["data_scientist", "data_analyst", None, "software_engineer",
                                    None, "hr_analyst"],
                         "level": ["senior", "senior", "senior", "mid", "mid", "mid"]})
    rows = compare(gold, pred)
    assert rows["family_outcome"].tolist() == ["correct", "wrong family", "abstained", "correct",
                                               "correct abstention", "false mapping"]
    assert rows["error"].tolist() == ["", "wrong family", "abstained", "wrong level", "",
                                      "false mapping"]

    s = summarize(rows)
    acc = s["accuracy"].set_index("metric")["share"]
    assert acc["family accuracy"] == 0.5                         # 2 of 4 inside the taxonomy
    assert acc["level accuracy"] == 0.75                         # only t4 has the wrong level
    assert acc["family and level"] == 0.25
    assert acc["family accuracy when it answers"] == 0.667       # 2 of the 3 it did not abstain on
    assert s["inside"].set_index("outcome")["titles"].to_dict() == {
        "correct": 2, "wrong family": 1, "abstained": 1}
    assert s["outside"].set_index("outcome")["titles"].to_dict() == {
        "correct abstention": 1, "false mapping": 1}
    assert s["errors"]["title"].tolist() == ["t2", "t3", "t4", "t6"]


def test_eval_titles_with_rules_writes_report(tmp_path, monkeypatch, capsys):
    path = write_csv(tmp_path / "h.csv", [["t1", "data_scientist", "senior"], ["t2", "", ""]])
    run_cli(monkeypatch, path, "--reports", tmp_path / "out")
    report = (tmp_path / "out" / "titles_heldout_rules.md").read_text(encoding="utf-8")
    assert "Normalizer: **keyword rules**" in report
    assert "| abstained" in report                  # rules do not know the token t1
    assert re.search(r"\| correct abstention\s*\| 1\s*\| 1\.000", report)
    assert re.search(r"\| family accuracy when it answers \| 0\s*\| 0\s*\| n/a", report)
    assert "## 4. Every error (1)" in report
    assert "Report written to" in capsys.readouterr().out


def test_eval_titles_with_llm_uses_the_client_and_no_cache(tmp_path, monkeypatch):
    client = ScriptedClient({"t1": ("data_scientist", "senior"), "t2": (None, "mid")})
    monkeypatch.setattr(LLMClient, "from_env", classmethod(lambda cls: client))
    monkeypatch.chdir(tmp_path)
    path = write_csv(tmp_path / "h.csv", [["t1", "data_scientist", "senior"], ["t2", "", ""]])
    run_cli(monkeypatch, path, "--llm", "--reports", "out")
    report = (tmp_path / "out" / "titles_heldout_llm_llama3.1-8b.md").read_text(encoding="utf-8")
    assert "Normalizer: **LLM (llama3.1:8b)**" in report
    assert "Titles answered by the LLM: 100.0%" in report
    assert "No errors." in report
    assert "LLM run: 0 LLM calls" in report         # the scripted client does not count calls
    assert not (tmp_path / "data").exists()         # nothing cached on disk


def test_eval_titles_refuses_the_unfilled_template(monkeypatch, tmp_path):
    path = write_csv(tmp_path / "h.csv", [["TODO 1", "data_scientist", "senior"], ["TODO 2", "", ""]])
    with pytest.raises(SystemExit, match="placeholder title 'TODO 1'"):
        run_cli(monkeypatch, path, "--reports", tmp_path / "out")
    assert not (tmp_path / "out").exists()          # no report from placeholder rows


def test_committed_heldout_file_is_valid():
    gold = load_heldout(HELDOUT)                    # raises on any format problem
    assert gold["family"].notna().any() and gold["family"].isna().any()
