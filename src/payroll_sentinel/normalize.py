"""Map messy job titles to the canonical (family, level) taxonomy.

Two normalizers share one interface:

* `rule_normalize` - deterministic keyword/regex baseline. Free, instant,
  explainable, but only knows the spellings it was written for.
* `llm_normalize` - sends the *unique* titles in batches to any
  OpenAI-compatible chat endpoint (Gemini free tier, Groq, local Ollama),
  validates every answer against the taxonomy and caches results on disk.
  Anything the LLM gets wrong or leaves out falls back to the rule result.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

from .llm import LLMClient
from .taxonomy import FAMILIES, LEVELS


def clean_title(title: object) -> str:
    if title is None or (isinstance(title, float) and pd.isna(title)):
        return ""
    text = unicodedata.normalize("NFKD", str(title))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = re.sub(r"[^a-z0-9&]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# --- Rule-based baseline ---------------------------------------------------
_LEVEL_RULES = [  # order matters: first match wins
    ("intern", {"estagio", "estagiario", "estagiaria", "intern"}),
    ("lead", {"especialista", "lead", "lider", "staff", "iv"}),
    ("senior", {"sr", "senior", "iii"}),
    ("junior", {"jr", "junior", "i"}),
    ("mid", {"pl", "pleno", "ii"}),
]

# Keywords written from the common spellings only (the "first version" an
# engineer would ship). The long tail is what the LLM is for.
_FAMILY_RULES = [
    (r"cientista de dados|data scientist", "data_scientist"),
    (r"analista de dados|data analyst", "data_analyst"),
    (r"desenvolvedor|engenheir[oa] de software|software engineer|programador", "software_engineer"),
    (r"gerente de produto|product manager", "product_manager"),
    (r"\brh\b|recursos humanos", "hr_analyst"),
    (r"financeir|financial", "financial_analyst"),
    (r"vendas|vendedor", "sales_rep"),
    (r"suporte|atendimento|atendente", "customer_support"),
    (r"operador", "production_operator"),
    (r"tecnic[oa] de manutencao|eletromecanico", "maintenance_technician"),
]


def rule_level(clean: str) -> str:
    tokens = set(clean.split())
    for level, keys in _LEVEL_RULES:
        if tokens & keys:
            return level
    return "mid"  # no level marker: most companies mean mid-level


def rule_family(clean: str) -> str | None:
    for pattern, family in _FAMILY_RULES:
        if re.search(pattern, clean):
            return family
    return None


def rule_normalize(titles: pd.Series) -> pd.DataFrame:
    clean = titles.map(clean_title)
    out = pd.DataFrame({
        "family": clean.map(lambda c: rule_family(c) if c else None),
        "level": clean.map(lambda c: rule_level(c) if c else None),
    }, index=titles.index)
    out["source"] = "rules"
    return out


# --- LLM normalizer --------------------------------------------------------
SYSTEM_PROMPT = """You normalize Brazilian job titles into a fixed taxonomy for a salary benchmark.

Families (use the key on the left):
{families}

Levels: intern (estágio), junior, mid (pleno; also used when the title has no level),
senior, lead (especialista, líder, staff, tech lead, level IV).

Rules:
- Ignore team, location, shift or unit suffixes ("- SP", "| Squad X", "(Remoto)").
- Roman numerals: I=junior, II=mid, III=senior, IV=lead.
- If a title clearly fits no family, use null for family. Never invent new keys.

Answer ONLY with JSON: {{"results": [{{"id": <int>, "family": <key or null>, "level": <level>}}]}}
with one entry per input id."""


def _build_system_prompt() -> str:
    lines = [f"- {key}: {f['label']} (e.g. {', '.join(f['easy'][:2])})" for key, f in FAMILIES.items()]
    return SYSTEM_PROMPT.format(families="\n".join(lines))


def parse_llm_batch(raw: str, ids: list[int]) -> dict[int, tuple[str | None, str | None]]:
    """Parse and validate one LLM answer. Invalid entries are dropped."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return {}
    results = data.get("results", []) if isinstance(data, dict) else []
    wanted, parsed = set(ids), {}
    for item in results:
        if not isinstance(item, dict):
            continue
        try:
            i = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        family, level = item.get("family"), item.get("level")
        if i not in wanted or level not in LEVELS:
            continue
        if family is not None and family not in FAMILIES:
            continue
        parsed[i] = (family, level)
    return parsed


def llm_normalize(titles: pd.Series, client: LLMClient, cache_path: str | Path | None = None,
                  batch_size: int = 40) -> pd.DataFrame:
    """Normalize titles with an LLM. Only unique cleaned titles are sent."""
    base = rule_normalize(titles)
    clean = titles.map(clean_title)
    cache: dict[str, list] = {}
    cache_file = Path(cache_path) if cache_path else None
    if cache_file and cache_file.exists():
        cache = json.loads(cache_file.read_text(encoding="utf-8"))

    todo = sorted({c for c in clean if c and c not in cache})
    system = _build_system_prompt()
    for start in range(0, len(todo), batch_size):
        chunk = todo[start:start + batch_size]
        ids = list(range(len(chunk)))
        user = "\n".join(f"{i}: {t}" for i, t in zip(ids, chunk))
        try:
            raw = client.chat(system, user, json_mode=True)
        except Exception as exc:  # network, quota, auth... keep going with rules
            print(f"[llm] batch {start // batch_size} failed: {exc}")
            continue
        for i, (family, level) in parse_llm_batch(raw, ids).items():
            cache[chunk[i]] = [family, level]
        if cache_file:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")

    out = base.copy()
    hit = clean.map(lambda c: c in cache)
    out.loc[hit, "family"] = clean[hit].map(lambda c: cache[c][0])
    out.loc[hit, "level"] = clean[hit].map(lambda c: cache[c][1])
    out.loc[hit, "source"] = "llm"
    return out
