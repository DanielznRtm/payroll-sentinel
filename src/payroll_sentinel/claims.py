"""What a labor petition asks for, as a fixed JSON shape that the code checks.

An extractor (keyword rules or an LLM) reads a petition and returns:

    {"admission_date": "2021-03-15", "termination_date": "2025-08-10",
     "termination_type": "without_cause", "monthly_salary": "6000.00",
     "weekly_hours": "44", "filing_date": "2026-02-03",
     "claims": [{"type": "overtime", "quote": "...", "hours_per_month": "20"},
                {"type": "other", "quote": "...", "label": "danos morais"}]}

``parse_extraction`` keeps only what it can check against the petition text:
- every claim type is on a fixed list, and its quote is copied from the petition;
- every date and number appears in the petition (dates like 15/03/2021 or
  15 de março de 2021, numbers like 6.000,00), so an extractor cannot invent a
  salary or a date;
- the label of a claim the code does not compute may not contain digits.
Anything that fails is dropped and the reason kept in ``problems``. The
extractor never computes an amount: the code does (triage.py).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .llm import LLMOutputError

CLAIM_TYPES = {
    "overtime": "Horas extras",
    "unpaid_fgts": "FGTS não depositado",
    "fgts_fine": "Multa de 40% do FGTS",
    "notice_pay": "Aviso prévio indenizado",
    "thirteenth": "13º salário proporcional",
    "vacation": "Férias proporcionais + 1/3",
    "late_severance_fine": "Multa do art. 477 da CLT",
    "other": "Outro pedido (revisão humana)",
}
COMPUTED_CLAIMS = tuple(t for t in CLAIM_TYPES if t != "other")
TERMINATION_TYPES = ("without_cause", "resignation", "with_cause", "unknown")
TOP_KEYS = {"admission_date", "termination_date", "termination_type", "monthly_salary", "weekly_hours",
            "filing_date", "claims"}
MAX_QUOTE, MAX_LABEL = 400, 80

MONTHS_PT = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
             "outubro", "novembro", "dezembro")
_DATE_NUMERIC = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_DATE_WORDS = re.compile(r"\b(\d{1,2})º? de (" + "|".join(MONTHS_PT) + r") de (\d{4})\b", re.IGNORECASE)
_NUMBER = re.compile(r"(?<![\d.,])(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{1,2})?(?![\d])")


@dataclass(frozen=True)
class Claim:
    type: str
    quote: str
    hours_per_month: Decimal | None = None   # overtime
    months: int | None = None                # unpaid_fgts
    label: str | None = None                 # other


@dataclass(frozen=True)
class Extraction:
    admission_date: date | None = None
    termination_date: date | None = None
    termination_type: str = "unknown"
    monthly_salary: Decimal | None = None
    weekly_hours: Decimal | None = None
    filing_date: date | None = None
    claims: tuple[Claim, ...] = ()
    problems: tuple[str, ...] = ()          # what was dropped and why

    def as_truth(self) -> dict:
        """The ground-truth shape of petitions.py (no quotes), to compare with it."""
        def num(value):
            return None if value is None else format(Decimal(value).normalize(), "f")

        def day(value):
            return None if value is None else value.isoformat()

        claims = []
        for c in self.claims:
            item = {"type": c.type}
            if c.type == "overtime" and c.hours_per_month is not None:
                item["hours_per_month"] = num(c.hours_per_month)
            if c.type == "unpaid_fgts" and c.months is not None:
                item["months"] = str(c.months)
            if c.type == "other" and c.label:
                item["label"] = c.label
            claims.append(item)
        return {"admission_date": day(self.admission_date), "termination_date": day(self.termination_date),
                "termination_type": self.termination_type, "monthly_salary": num(self.monthly_salary),
                "weekly_hours": num(self.weekly_hours), "filing_date": day(self.filing_date), "claims": claims}


def _norm(text: str) -> str:
    return " ".join(text.split()).casefold()


def dates_in_text(text: str) -> set[date]:
    """Every valid date written as 15/03/2021 or 15 de março de 2021 (1º de março too)."""
    found = set()
    for d, m, y in _DATE_NUMERIC.findall(text):
        try:
            found.add(date(int(y), int(m), int(d)))
        except ValueError:
            pass
    for d, month, y in _DATE_WORDS.findall(text):
        try:
            found.add(date(int(y), MONTHS_PT.index(month.lower()) + 1, int(d)))
        except ValueError:
            pass
    return found


def numbers_in_text(text: str) -> set[Decimal]:
    """Every number in Brazilian format (6.000,00 / 6000,00 / 44), outside dates."""
    text = _DATE_WORDS.sub(" ", _DATE_NUMERIC.sub(" ", text))
    return {Decimal(n.replace(".", "").replace(",", ".")) for n in _NUMBER.findall(text)}


def _decimal(value) -> Decimal | None:
    if isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation:
        return None
    return number if number.is_finite() and number >= 0 else None


def parse_extraction(raw: str | dict, text: str) -> Extraction:
    """Keep only what can be checked against ``text``; every dropped field is explained in ``problems``."""
    problems: list[str] = []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw, parse_float=Decimal)
        except json.JSONDecodeError:
            return Extraction(problems=("answer is not valid JSON",))
    if not isinstance(raw, dict):
        return Extraction(problems=("answer is not a JSON object",))
    if set(raw) - TOP_KEYS:
        problems.append(f"ignored unknown keys {sorted(set(raw) - TOP_KEYS)}")
    dates, numbers, haystack = dates_in_text(text), numbers_in_text(text), _norm(text)

    def checked_date(key):
        value = raw.get(key)
        if value in (None, ""):
            return None
        try:
            day = date.fromisoformat(str(value))
        except ValueError:
            problems.append(f"{key}: '{value}' is not a YYYY-MM-DD date")
            return None
        if day not in dates:
            problems.append(f"{key}: {day} is not written in the petition")
            return None
        return day

    def checked_number(where, value):
        if value in (None, ""):
            return None
        number = _decimal(value)
        if number is None:
            problems.append(f"{where}: '{value}' is not a number")
            return None
        if number not in numbers:
            problems.append(f"{where}: {value} is not written in the petition")
            return None
        return number

    kind = raw.get("termination_type") or "unknown"
    if kind not in TERMINATION_TYPES:
        problems.append(f"termination_type: '{kind}' is not one of {list(TERMINATION_TYPES)}")
        kind = "unknown"

    claims: list[Claim] = []
    raw_claims = raw.get("claims") or []
    if not isinstance(raw_claims, list):
        problems.append("claims is not a list")
        raw_claims = []
    for i, item in enumerate(raw_claims):
        where = f"claims[{i}]"
        if not isinstance(item, dict) or item.get("type") not in CLAIM_TYPES:
            problems.append(f"{where}: unknown claim type {item.get('type') if isinstance(item, dict) else item!r}")
            continue
        kind_ = item["type"]
        quote = item.get("quote")
        if not isinstance(quote, str) or not quote.strip() or len(quote) > MAX_QUOTE \
                or _norm(quote) not in haystack:
            problems.append(f"{where} ({kind_}): the quote is not copied from the petition")
            continue
        if kind_ != "other" and any(c.type == kind_ for c in claims):
            problems.append(f"{where} ({kind_}): repeated claim")
            continue
        hours = months = label = None
        if kind_ == "overtime":
            hours = checked_number(f"{where} hours_per_month", item.get("hours_per_month"))
        if kind_ == "unpaid_fgts":
            found = checked_number(f"{where} months", item.get("months"))
            if found is not None and found == found.to_integral_value():
                months = int(found)
            elif found is not None:
                problems.append(f"{where} months: {found} is not a whole number")
        if kind_ == "other":
            text_label = item.get("label")
            if isinstance(text_label, str) and text_label.strip() and len(text_label) <= MAX_LABEL \
                    and not re.search(r"\d", text_label):
                label = text_label.strip()
            else:
                problems.append(f"{where}: the label must be short text without digits")
        claims.append(Claim(kind_, " ".join(quote.split()), hours, months, label))

    return Extraction(
        admission_date=checked_date("admission_date"), termination_date=checked_date("termination_date"),
        termination_type=kind, monthly_salary=checked_number("monthly_salary", raw.get("monthly_salary")),
        weekly_hours=checked_number("weekly_hours", raw.get("weekly_hours")),
        filing_date=checked_date("filing_date"), claims=tuple(claims), problems=tuple(problems))


# --- Keyword rules: the baseline the LLM must beat --------------------------------

_DATE = r"(\d{1,2}/\d{1,2}/\d{4}|\d{1,2}º? de (?:" + "|".join(MONTHS_PT) + r") de \d{4})"
RULES = {
    "overtime": r"horas extra",
    "fgts_fine": r"multa (?:de )?40|40% sobre|multa fundiária",
    "unpaid_fgts": r"fgts",
    "notice_pay": r"aviso prévio",
    "thirteenth": r"13º|décimo terceiro|gratificação natalina",
    "vacation": r"férias",
    "late_severance_fine": r"art\. ?477|verbas rescisórias",
}
OTHER_RULES = {"danos morais": r"danos? mora", "adicional de insalubridade": r"insalubridade",
               "adicional de periculosidade": r"periculosidade", "vínculo de emprego": r"vínculo",
               "vale-transporte": r"vale-transporte"}


def rule_extract(text: str) -> Extraction:
    """Keyword baseline: a claim type is found when a sentence mentions it, even to say it was paid."""
    flat = " ".join(text.split())                       # petitions break lines in the middle of sentences
    sentences = re.split(r"(?<=[.;:])\s+", flat)
    in_words = _DATE_WORDS.findall(flat)                # the closing line dates the petition
    filing = " de ".join(in_words[-1]) if in_words else None

    def first(pattern, flags=re.IGNORECASE):
        match = re.search(pattern, flat, flags)
        return match.group(1) if match else None

    def as_iso(found):
        days = dates_in_text(found or "")
        return next(iter(days)).isoformat() if days else None

    raw = {
        "admission_date": as_iso(first(r"admitid[oa] em " + _DATE)),
        "termination_date": as_iso(first(r"(?:dispensad[oa]|demitid[oa])[^.]*? em " + _DATE)
                                   or first(r"pediu demissão em " + _DATE)),
        "termination_type": ("without_cause" if re.search(r"sem justa causa", flat, re.I)
                             else "resignation" if re.search(r"pediu demissão", flat, re.I)
                             else "with_cause" if re.search(r"justa causa", flat, re.I) else "unknown"),
        "monthly_salary": (first(r"salário[^.]*?R\$ ?(\d[\d.]*,\d{2})") or "").replace(".", "").replace(",", "."),
        "weekly_hours": first(r"(\d+) horas semanais"),
        "filing_date": as_iso(filing),
        "claims": [],
    }
    for kind, pattern in RULES.items():
        hits = [s for s in sentences if re.search(pattern, s, re.IGNORECASE)]
        if kind == "unpaid_fgts":
            hits = [s for s in hits if not re.search(RULES["fgts_fine"], s, re.IGNORECASE)]
        if hits:
            claim = {"type": kind, "quote": hits[0]}
            if kind == "overtime":
                claim["hours_per_month"] = first(r"(\d+) horas extras (?:por mês|mensais)")
            if kind == "unpaid_fgts":
                claim["months"] = first(r"últimos (\d+) meses") or first(r"(\d+) depósitos mensais do FGTS")
            raw["claims"].append(claim)
    for label, pattern in OTHER_RULES.items():
        hits = [s for s in sentences if re.search(pattern, s, re.IGNORECASE)]
        if hits:
            raw["claims"].append({"type": "other", "quote": hits[0], "label": label})
    return parse_extraction(raw, text)


# --- LLM extraction ---------------------------------------------------------------

MAX_PETITION_CHARS = 20_000

SYSTEM_PROMPT = """You read a Brazilian labor complaint (petição inicial trabalhista) and copy its facts and requests into a fixed JSON object. You never compute anything.

Return only a JSON object with these keys:
- "admission_date", "termination_date": the dates the job started and ended, as "YYYY-MM-DD", or null.
- "filing_date": the date written at the end of the petition, as "YYYY-MM-DD", or null.
- "termination_type": "without_cause" (dispensa sem justa causa), "resignation" (pedido de demissão), "with_cause" (justa causa) or "unknown".
- "monthly_salary": the monthly salary as written, with a dot for decimals (R$ 6.000,00 -> "6000.00"), or null.
- "weekly_hours": the contracted weekly hours ("44"), or null.
- "claims": one object for each request the petition makes (usually in "DOS PEDIDOS"). A right that is only mentioned as a fact, or said to have been paid or received, is not a claim. Each object has:
  - "type": "overtime" (horas extras), "unpaid_fgts" (FGTS não depositado), "fgts_fine" (multa de 40% do FGTS), "notice_pay" (aviso prévio indenizado), "thirteenth" (13º salário proporcional), "vacation" (férias proporcionais com 1/3), "late_severance_fine" (multa do art. 477 da CLT) or "other" (any other request);
  - "quote": the words of the petition that make the request, copied exactly;
  - "hours_per_month": for overtime only, the overtime hours per month stated in the petition;
  - "months": for unpaid_fgts only, the number of months without deposits stated in the petition;
  - "label": for other only, a short name of the request in Portuguese, without numbers.

Use only dates and numbers written in the petition, and null when it does not say. Never add amounts of money to claims."""


def llm_extract(text: str, client, cache_path: str | Path | None = None) -> Extraction:
    """Ask the LLM for the JSON above, then keep only what parse_extraction can check.

    The raw answer is cached by the petition's hash (one cache file per model), so the
    checks can change without paying for the calls again.
    """
    if len(text) > MAX_PETITION_CHARS:
        return Extraction(problems=(f"petition longer than {MAX_PETITION_CHARS} characters: not sent",))
    key = hashlib.sha256(text.encode("utf-8")).hexdigest()
    cache_file = Path(cache_path) if cache_path else None
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file and cache_file.exists() else {}
    if key not in cache:
        try:
            cache[key] = client.chat(SYSTEM_PROMPT, text, json_mode=True)
        except LLMOutputError as exc:
            return Extraction(problems=(f"model output rejected: {exc}",))
        if cache_file:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")
    return parse_extraction(cache[key], text)
