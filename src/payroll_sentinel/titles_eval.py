"""Measure title normalization on hand-written titles that are NOT in taxonomy.py.

The synthetic benchmark draws its titles from the `easy`/`hard` lists in
`taxonomy.py`, and both the keyword rules and the LLM prompt were written
knowing those lists. A held-out file (`title,family,level`, written by hand)
shows how normalization generalizes to spellings nobody planned for.

An empty `family` means "outside the taxonomy": the right answer there is to
abstain (family None), which the validator turns into an `unmapped_title`
warning for human review.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .normalize import clean_title, llm_normalize, rule_normalize
from .taxonomy import FAMILIES, LEVELS

COLUMNS = ["title", "family", "level"]
PLACEHOLDER = "TODO"  # template rows the author has not replaced yet


class HeldoutError(ValueError):
    """The held-out file cannot be used as ground truth."""


def _taxonomy_titles() -> set[str]:
    return {clean_title(t) for f in FAMILIES.values() for t in f["easy"] + f["hard"]}


def load_heldout(path: str | Path) -> pd.DataFrame:
    """Read and check a held-out file. Empty family/level become None.

    Raises HeldoutError listing every problem at once, with file line numbers,
    so a hand-written file can be fixed in one pass.
    """
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    if missing := [c for c in COLUMNS if c not in df.columns]:
        raise HeldoutError(f"Missing columns: {', '.join(missing)}")
    df = df[COLUMNS].apply(lambda col: col.str.strip())
    if df.empty:
        raise HeldoutError("The file has no rows.")

    problems, seen, listed = [], {}, _taxonomy_titles()
    for i, row in df.iterrows():
        line = i + 2  # header is line 1
        title, family, level = row["title"], row["family"], row["level"]
        clean = clean_title(title)
        if not clean:
            problems.append(f"line {line}: empty title")
            continue
        if title.upper().startswith(PLACEHOLDER):
            problems.append(f"line {line}: placeholder title '{title}' not replaced yet")
        if family and family not in FAMILIES:
            problems.append(f"line {line}: unknown family '{family}'")
        if family and level not in LEVELS:
            problems.append(f"line {line}: level must be one of {', '.join(LEVELS)} (got '{level}')")
        if clean in listed:
            problems.append(f"line {line}: '{title}' is already in taxonomy.py, so it is not held out")
        if clean in seen:
            problems.append(f"line {line}: '{title}' duplicates line {seen[clean]}")
        seen.setdefault(clean, line)
    if problems:
        raise HeldoutError("\n".join(problems))

    # object dtype keeps None as None (a string column would turn it into NaN).
    # A level without a family is never scored, so it is dropped.
    return pd.DataFrame({
        "title": df["title"].astype(object),
        "family": pd.Series([f or None for f in df["family"]], index=df.index, dtype=object),
        "level": pd.Series([(lvl or None) if f else None for f, lvl in zip(df["family"], df["level"])],
                           index=df.index, dtype=object),
    })


def _none(value):
    return None if pd.isna(value) else value


def compare(gold: pd.DataFrame, pred: pd.DataFrame) -> pd.DataFrame:
    """One row per title: expected vs predicted, the family outcome and the error kind."""
    rows = []
    for (_, g), (_, p) in zip(gold.iterrows(), pred.iterrows()):
        exp_f, exp_l = _none(g["family"]), _none(g["level"])
        got_f, got_l = _none(p["family"]), _none(p["level"])
        if exp_f is None:  # outside the taxonomy: abstaining is the right answer
            outcome = "correct abstention" if got_f is None else "false mapping"
            level_ok = None
            errors = [] if got_f is None else ["false mapping"]
        else:
            outcome = "abstained" if got_f is None else ("correct" if got_f == exp_f else "wrong family")
            level_ok = got_l == exp_l
            errors = ([] if outcome == "correct" else [outcome]) + ([] if level_ok else ["wrong level"])
        rows.append({"title": g["title"], "expected_family": exp_f, "expected_level": exp_l,
                     "predicted_family": got_f, "predicted_level": got_l,
                     "in_taxonomy": exp_f is not None, "family_outcome": outcome,
                     "level_ok": level_ok, "error": " + ".join(errors)})
    return pd.DataFrame(rows)


def _share(k: int, n: int) -> float | None:
    return round(k / n, 3) if n else None  # None: nothing to measure, shown as n/a


def _markdown(df: pd.DataFrame) -> str:
    """Markdown table with shares as fixed 3-decimal text and n/a for 'nothing to measure'."""
    df = df.copy()
    if "share" in df.columns:
        df["share"] = [("n/a" if pd.isna(v) else f"{v:.3f}") for v in df["share"]]
    # Without disable_numparse, tabulate would turn "0.500" back into 0.5 and "0.000" into 0.
    return df.to_markdown(index=False, disable_numparse=True)


def summarize(rows: pd.DataFrame) -> dict:
    """Accuracy inside the taxonomy, family outcomes, and abstention outside it."""
    inside, outside = rows[rows["in_taxonomy"]], rows[~rows["in_taxonomy"]]
    n_in, n_out = len(inside), len(outside)
    fam_ok = inside["family_outcome"].eq("correct")
    lvl_ok = inside["level_ok"].astype(bool)
    answered = int(inside["family_outcome"].ne("abstained").sum())
    accuracy = pd.DataFrame([
        {"metric": "family accuracy", "correct": int(fam_ok.sum()), "titles": n_in,
         "share": _share(int(fam_ok.sum()), n_in)},
        {"metric": "level accuracy", "correct": int(lvl_ok.sum()), "titles": n_in,
         "share": _share(int(lvl_ok.sum()), n_in)},
        {"metric": "family and level", "correct": int((fam_ok & lvl_ok).sum()), "titles": n_in,
         "share": _share(int((fam_ok & lvl_ok).sum()), n_in)},
        {"metric": "family accuracy when it answers", "correct": int(fam_ok.sum()),
         "titles": answered, "share": _share(int(fam_ok.sum()), answered)},
    ])

    def outcomes(part: pd.DataFrame, names: list[str]) -> pd.DataFrame:
        counts = part["family_outcome"].value_counts()
        return pd.DataFrame([{"outcome": o, "titles": int(counts.get(o, 0)),
                              "share": _share(int(counts.get(o, 0)), len(part))} for o in names])

    return {"n_in": n_in, "n_out": n_out, "accuracy": accuracy,
            "inside": outcomes(inside, ["correct", "wrong family", "abstained"]),
            "outside": outcomes(outside, ["correct abstention", "false mapping"]),
            "errors": rows[rows["error"].ne("")]}


@dataclass
class TitleEval:
    rows: pd.DataFrame
    method: str                    # shown in the report
    slug: str                      # used in the report file name
    llm_coverage: float | None = None
    llm_run: str | None = None

    def report(self, source: str) -> str:
        s, md = summarize(self.rows), _markdown
        coverage = [] if self.llm_coverage is None else [
            f"Titles answered by the LLM: {self.llm_coverage:.1%} (the rest fell back to keyword rules).", ""]
        if self.llm_run:
            coverage += [f"LLM run: {self.llm_run}.", ""]
        errors = s["errors"][["title", "expected_family", "expected_level", "predicted_family",
                              "predicted_level", "error"]].fillna("-")
        return "\n".join([
            "# Held-out title normalization", "",
            f"File `{source}`: {s['n_in'] + s['n_out']} hand-written titles not listed in "
            f"`taxonomy.py`; {s['n_in']} inside the taxonomy, {s['n_out']} outside it "
            "(empty family: the right answer is to abstain). "
            f"Normalizer: **{self.method}**.", "", *coverage,
            "## 1. Titles inside the taxonomy", "", md(s["accuracy"]), "",
            "\"When it answers\" leaves out the titles where the normalizer abstained.", "",
            "## 2. Family outcome inside the taxonomy", "",
            "`wrong family` puts a salary in the wrong peer group without any warning. "
            "`abstained` leaves the family empty, so the validator raises `unmapped_title` "
            "for human review.", "", md(s["inside"]), "",
            "## 3. Titles outside the taxonomy", "",
            "Here abstaining is correct; `false mapping` forces the title into a family.", "",
            md(s["outside"]), "",
            f"## 4. Every error ({len(errors)})", "",
            md(errors) if len(errors) else "No errors.", "",
        ])


def _slug(text: str) -> str:
    """Safe file-name part: model names such as 'llama3.1:8b' contain ':'."""
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-")


def evaluate_titles(gold: pd.DataFrame, use_llm: bool = False) -> TitleEval:
    """Normalize the held-out titles with rules or the LLM and compare with the answers.

    The LLM run uses no cache on purpose: the cache is keyed by title only, so a
    cached answer could come from a different model than the one being measured.
    """
    if not use_llm:
        return TitleEval(compare(gold, rule_normalize(gold["title"])), "keyword rules", "rules")
    from .llm import LLMClient
    client = LLMClient.from_env()
    start = time.perf_counter()
    pred = llm_normalize(gold["title"], client)
    seconds = time.perf_counter() - start
    return TitleEval(compare(gold, pred), f"LLM ({client.label})", f"llm_{_slug(client.model)}",
                     llm_coverage=float(pred["source"].eq("llm").mean()),
                     llm_run=f"{client.stats.summary()}; {seconds:.1f} s in total")
