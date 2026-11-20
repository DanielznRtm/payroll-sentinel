"""Score claim extraction against ground truth, for keyword rules or an LLM.

For every petition the extraction is compared with the truth on three levels:
- claims: which claim types were found (precision and recall per type);
- facts: dates, salary, hours and termination type, counting a missing value
  apart from a wrong one (a missing value is sent to a person; a wrong one is not);
- money: the total triage.py prices from the extraction against the total it
  prices from the truth. This is the number a user would see.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Callable

from .claims import CLAIM_TYPES, TERMINATION_TYPES, TOP_KEYS, Claim, Extraction, dates_in_text, numbers_in_text
from .petitions import Petition
from .triage import triage

FACT_FIELDS = ("admission_date", "termination_date", "termination_type", "monthly_salary", "weekly_hours",
               "filing_date")


def extraction_from_truth(truth: dict) -> Extraction:
    """The ground truth as an Extraction, to price it with the same triage."""
    def day(key):
        return date.fromisoformat(truth[key]) if truth.get(key) else None

    def num(key):
        return Decimal(truth[key]) if truth.get(key) is not None else None

    claims = tuple(Claim(c["type"], "", hours_per_month=Decimal(c["hours_per_month"]) if "hours_per_month" in c else None,
                         months=int(c["months"]) if "months" in c else None, label=c.get("label"))
                   for c in truth["claims"])
    return Extraction(day("admission_date"), day("termination_date"), truth["termination_type"],
                      num("monthly_salary"), num("weekly_hours"), day("filing_date"), claims)


def _same(a, b) -> bool:
    if a is None or b is None:
        return a is b
    try:
        return Decimal(a) == Decimal(b)
    except ArithmeticError:
        return a == b


@dataclass
class ClaimsEval:
    method: str
    source: str
    n: int = 0
    claims: dict = field(default_factory=dict)       # type -> [true positives, false positives, false negatives]
    facts: dict = field(default_factory=dict)        # field -> [correct, missing, wrong]
    details: list = field(default_factory=lambda: [0, 0])  # claim details right / compared
    totals_match: int = 0
    total_gap: Decimal = Decimal("0")                # sum of |extracted total - true total|
    with_problems: int = 0
    problems: int = 0
    errors: list = field(default_factory=list)       # (petition id, what went wrong)
    seconds: float = 0.0
    llm_stats: str | None = None

    def add(self, pid: str, truth: dict, got: Extraction, params: dict) -> None:
        self.n += 1
        found = got.as_truth()
        true_types = {c["type"] for c in truth["claims"]}
        got_types = {c["type"] for c in found["claims"]}
        for t in CLAIM_TYPES:
            tp_fp_fn = self.claims.setdefault(t, [0, 0, 0])
            tp_fp_fn[0] += int(t in true_types and t in got_types)
            tp_fp_fn[1] += int(t in got_types and t not in true_types)
            tp_fp_fn[2] += int(t in true_types and t not in got_types)
        for t in sorted(got_types - true_types):
            self.errors.append((pid, f"invented claim: {t}"))
        for t in sorted(true_types - got_types):
            self.errors.append((pid, f"missed claim: {t}"))

        for f in FACT_FIELDS:
            right_missing_wrong = self.facts.setdefault(f, [0, 0, 0])
            want, have = truth.get(f), found[f]
            if f == "termination_type" and have == "unknown":
                have = None
            if _same(want, have):
                right_missing_wrong[0] += 1
            elif have is None:
                right_missing_wrong[1] += 1
                self.errors.append((pid, f"{f} missing (truth {want})"))
            else:
                right_missing_wrong[2] += 1
                self.errors.append((pid, f"{f} wrong: {have} (truth {want})"))

        for key in ("hours_per_month", "months"):
            want = next((c[key] for c in truth["claims"] if key in c), None)
            match = [c for c in found["claims"] if c["type"] == ("overtime" if key == "hours_per_month" else "unpaid_fgts")]
            if want is not None and match:
                self.details[1] += 1
                if _same(want, match[0].get(key)):
                    self.details[0] += 1
                else:
                    self.errors.append((pid, f"{key} {match[0].get(key)} (truth {want})"))

        true_total = triage(extraction_from_truth(truth), params).total
        got_total = triage(got, params).total
        self.totals_match += int(got_total == true_total)
        self.total_gap += abs(got_total - true_total)
        if got_total != true_total:
            self.errors.append((pid, f"priced total R$ {got_total} (truth R$ {true_total})"))
        if got.problems:
            self.with_problems += 1
            self.problems += len(got.problems)
            for p in got.problems:
                self.errors.append((pid, f"dropped by the checks: {p}"))

    def report(self) -> str:
        def pct(a, b):
            return f"{100 * a / b:.1f} %" if b else "n/a"

        tp = sum(v[0] for v in self.claims.values())
        fp = sum(v[1] for v in self.claims.values())
        fn = sum(v[2] for v in self.claims.values())
        lines = [f"# Claim extraction: {self.method}", "",
                 f"Petitions: {self.n} ({self.source}). Time: {self.seconds:.1f} s.", ""]
        if self.llm_stats:
            lines += [f"LLM calls made in this run (answers already in the cache are reused, not counted): "
                      f"{self.llm_stats}.", ""]
        lines += ["## Money", "",
                  f"- Priced total equal to the truth's: {self.totals_match}/{self.n} ({pct(self.totals_match, self.n)})",
                  f"- Sum of the differences: R$ {self.total_gap:,.2f}", "",
                  "## Claims found", "",
                  f"Overall: precision {pct(tp, tp + fp)}, recall {pct(tp, tp + fn)} "
                  f"({tp} right, {fp} invented, {fn} missed).", "",
                  "| Claim | Right | Invented | Missed | Precision | Recall |", "|---|---|---|---|---|---|"]
        for t, (a, b, c) in self.claims.items():
            lines.append(f"| {t} | {a} | {b} | {c} | {pct(a, a + b)} | {pct(a, a + c)} |")
        lines += ["", "## Facts", "", "A missing value goes to a person; a wrong one would be priced.", "",
                  "| Fact | Right | Missing | Wrong |", "|---|---|---|---|"]
        for f, (a, b, c) in self.facts.items():
            lines.append(f"| {f} | {a} | {b} | {c} |")
        lines += ["", f"Claim details (overtime hours, months without FGTS): {self.details[0]}/{self.details[1]} right.",
                  "", "## Checks", "",
                  f"{self.with_problems} petitions had something dropped by the checks ({self.problems} items): "
                  "a date or number not written in the petition, a quote not copied from it, or an unknown claim.",
                  "", "## Every error", ""]
        lines += [f"- {pid}: {what}" for pid, what in self.errors] or ["None."]
        return "\n".join(lines) + "\n"


def evaluate_claims(petitions: list[Petition], extract: Callable[[str], Extraction], params: dict,
                    method: str, source: str) -> ClaimsEval:
    ev = ClaimsEval(method, source)
    start = time.monotonic()
    for p in petitions:
        ev.add(p.id, p.truth, extract(p.text), params)
    ev.seconds = time.monotonic() - start
    return ev


# --- Hand-written petitions -------------------------------------------------------

class HeldoutError(ValueError):
    """The hand-written petitions or their truth.json are not ready to be scored."""


def check_truth(name: str, truth: dict, text: str) -> list[str]:
    """Problems that would make the truth unfair: values the checks could never accept, unknown types."""
    problems = []
    if not isinstance(truth, dict) or set(truth) != TOP_KEYS:
        return [f"{name}: truth must have exactly the keys {sorted(TOP_KEYS)}"]
    if truth["termination_type"] not in TERMINATION_TYPES:
        problems.append(f"{name}: termination_type must be one of {list(TERMINATION_TYPES)}")
    days, numbers = dates_in_text(text), numbers_in_text(text)
    for key in ("admission_date", "termination_date", "filing_date"):
        value = truth[key]
        if value is None:
            continue
        try:
            day = date.fromisoformat(value)
        except (TypeError, ValueError):
            problems.append(f"{name}: {key} must be YYYY-MM-DD or null")
            continue
        if day not in days:
            problems.append(f"{name}: {key} {value} is not written as a date in the petition (like 15/03/2021 or "
                            "15 de março de 2021); the checks would drop it, so the right answer is null")
    values = [("monthly_salary", truth["monthly_salary"]), ("weekly_hours", truth["weekly_hours"])]
    for c in truth["claims"] if isinstance(truth["claims"], list) else []:
        if not isinstance(c, dict) or c.get("type") not in CLAIM_TYPES:
            problems.append(f"{name}: unknown claim {c!r}")
            continue
        if set(c) - {"type", "hours_per_month", "months", "label"}:
            problems.append(f"{name}: claim {c['type']} has unknown keys")
        values += [(f"{c['type']} {k}", c[k]) for k in ("hours_per_month", "months") if k in c]
    for where, value in values:
        if value is None:
            continue
        try:
            written = Decimal(str(value)) in numbers
        except ArithmeticError:
            written = False
        if not written:
            problems.append(f"{name}: {where} {value} is not written in digits in the petition; the checks would "
                            "drop it, so the right answer is null")
    return problems


def load_heldout_petitions(folder: str | Path) -> list[Petition]:
    """Petitions written by hand (*.txt) and their expected extraction (truth.json, keyed by file name)."""
    folder = Path(folder)
    texts = sorted(folder.glob("*.txt"))
    if not texts:
        raise HeldoutError(f"no petitions (*.txt) in {folder} yet")
    truth_file = folder / "truth.json"
    if not truth_file.exists():
        raise HeldoutError(f"{truth_file} is missing")
    truth = json.loads(truth_file.read_text(encoding="utf-8"))
    names = {p.name for p in texts}
    problems = [f"{n}: no entry in truth.json" for n in sorted(names - set(truth))]
    problems += [f"truth.json: {n} has no petition file" for n in sorted(set(truth) - names)]
    petitions = []
    for path in texts:
        text = path.read_text(encoding="utf-8")
        if path.name in truth:
            problems += check_truth(path.name, truth[path.name], text)
            petitions.append(Petition(path.stem, text, truth[path.name]))
    if problems:
        raise HeldoutError("\n".join(problems))
    return petitions
