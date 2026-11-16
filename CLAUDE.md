# CLAUDE.md

Context for Claude Code. Read this before every task.

## About this project

Payroll Sentinel validates payroll submissions before they enter a salary benchmark.
It is a portfolio project by a control and automation engineering student preparing
for AI and data internships. The point is to show end-to-end AI delivery with
**measured** results, not demos.

## How to work with me

- Talk to me in **Brazilian Portuguese**. Code, comments, commit messages, README
  and docs stay in **English**.
- I am learning. Before a change, tell me in 1 to 3 sentences what you will do and
  why. After it, explain any concept I may not know (e.g. why median/MAD instead of
  mean/std). I must be able to defend every line in an interview.
- Make small, focused commits with conventional prefixes (`feat`, `fix`, `test`,
  `docs`, `ci`, `refactor`). Ask before pushing.
- Prefer the smallest change that works. Ask before adding a dependency.

## Ground rules (decided; ask before changing)

- **Zero cost.** No paid APIs. Every LLM call goes through
  `src/payroll_sentinel/llm.py` (OpenAI-compatible: Gemini free tier by default,
  Groq or local Ollama). Keys come only from environment variables
  (`LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`); never hardcode or commit them.
- **The LLM never produces numbers shown to users.** It interprets text (job titles,
  later legal petitions) and explains results. All calculations are deterministic
  Python with tests.
- **Synthetic data only.** `generate.py` plants labeled errors so every claim is
  measured against ground truth. Never commit real personal or payroll data
  (`data/` is gitignored). Free-tier LLMs may train on prompts, so never send real
  personal data to them.
- **Measure every change.** For any change to normalization, detection or LLM
  prompts, run the pipeline and compare `reports/evaluation.md` before and after.
  README numbers are updated only from a real run.
- **No test may hit the network.** LLM code is tested with the `FakeClient` pattern
  in `tests/test_pipeline.py`.

## Commands

```bash
pip install -e ".[dev]"
pytest -q
python -m payroll_sentinel.cli run            # rules only, offline, free
python -m payroll_sentinel.cli run --llm      # needs LLM_API_KEY
python -m payroll_sentinel.cli validate FILE  # validate a CSV with the same columns
pip install -e ".[ui]" && streamlit run app.py  # web UI (Windows: double-click run_ui.bat)
```

CI (`.github/workflows/tests.yml`) runs the tests and the full pipeline on Python
3.10 and 3.12. Keep it green, and keep the actions on Node 24 versions
(`actions/checkout@v6`, `actions/setup-python@v6`).

## Architecture (Module A)

Data flows `generate` → `normalize` (rules or LLM) → `validate` → `evaluate`;
`pipeline.py` wires them as plain functions, used by both `cli.py` and the
Streamlit UI in `app.py`. Uploads in the UI always use rules, never the LLM. `taxonomy.py` holds the job families, levels, cities, the
pay parameters fitted to RAIS (`pay_sigma`, city index by kind of job) and the
2026 minimum wage (R$ 1,621, prorated by weekly hours; internship stipends are
exempt). `validate.py` has two layers: deterministic rules, then a peer comparison
in which robust z-score, IQR and Isolation Forest vote (flag at 2 of 3).

Baseline (v1.1 data, seed 42, default rules = keywords + CBO): precision 0.892,
recall 0.785, F1 0.835; with perfect titles, recall is 0.822. LLM titles
(`gemini-3.5-flash-lite`, cached answers of one run): precision 0.913, recall 0.822,
F1 0.865; report in `reports/evaluation_llm_gemini-3.5-flash-lite.md`. On the v1.0
generator (narrow spread) these were F1 0.92 and 0.963: the detection floor (level
mismatches inside RAIS-like spread, 4 of 45 caught) is now the main limit.
The LLM title cache has one file per provider and model
(`data/llm_title_cache_<provider>_<model>.json`), so models never share answers;
`run --llm --no-cache` times a model, and every LLM report states calls, 429s and time.
Model comparison (README "Comparing models", reports in `reports/models/`): flash-lite
is the default; `gemini-3.5-flash` is better on real titles but hits free-tier 429s;
Groq `openai/gpt-oss-20b` needs `LLM_REASONING_EFFORT=low` (optional env var, sent
only when set) and abstains too often. Ollama is not measured (no NVIDIA GPU).
`scripts/public_data_check.py` runs titles and the full validator on two public
Kaggle salary files and the Italian survey `datapizza-ai-lab/salaries` (Hugging Face,
CC BY-NC 4.0, `--italy` parquet); paths are passed in, the files are never committed,
Age/Gender are never read, and only titles reach the LLM. It led to the symmetric unit-error diagnosis
(`divided_by_12`, `extreme_value`, 6-9x to review) and the `duplicate_record` rule.

## Roadmap

1. **Module A, v1.0.0 released; v1.1.0 committed locally (see CHANGELOG.md). Next:**
   - CBO 2002 titles and synonyms are part of the default rules since v1.1 (the user
     decided; `--no-cbo` gives the v1.0 keyword rules; `cbo_titles.py` generated by
     `scripts/build_cbo_titles.py` from the 64 codes the user approved; the CBO zip
     sits in gitignored `data/cbo/`). Measured: held-out family 61.4 % -> 63.2 %, no
     new wrong family or false mapping; synthetic F1 unchanged. The public-data
     report used the v1.0 keyword rules (with the CBO, 1 US row of 6,702 changes).
   - State of Data Brazil 2025-2026 (Kaggle CSV in gitignored `data/state_of_data/`)
     checks synthetic salaries: `scripts/state_of_data_check.py` reads only six
     non-personal columns; data analyst and data scientist medians are within 10 %
     nationwide in v1.0 and within 11 % in v1.1 (report `reports/realism_state_of_data.md`).
     It is not used for fitting, so it stays an independent check.
   - RAIS 2025 São Paulo microdata (`data/rais/RAIS_VINC_PUB_SP.7z`, gitignored)
     checked by `scripts/rais_check.py`, streamed through the system `tar` (Windows
     11 tar opens .7z, about 2.5 minutes). v1.1 (the user decided): sales is compared
     only on B2B codes (retail seller 521110 and sales manager 142320 stay in the
     title lookup, out of the comparison); support keeps all codes.
     `scripts/calibrate_generator.py` fits, in São Paulo only, each family's
     `pay_sigma` to the RAIS log-pay SD and the sales/support `mid_salary` to the RAIS
     median, plus the Campinas/Sorocaba city index by kind of job (same-occupation
     ratios); targets in `reports/realism_rais.json`. Interns keep sigma 0.15 (no
     internships in RAIS). Pay parameters do not change titles or planted errors (a
     test checks it), so the LLM cache stays valid. Report `reports/realism_rais.md`.
     Left open: other cities' index (only the SP file was used), family-specific
     office gaps outside SP, the same level steps for every family;
   - the README model table (accuracy × latency × cost) has two Gemini models and
     Groq; a local Ollama model needs an NVIDIA GPU;
   - natural-language questions over the benchmark are built (`ask.py`): the LLM
     only fills a fixed JSON query that the code validates and runs. Measured on
     the user's 30 questions in `eval/questions.csv`: 27/30 right, 5/5 out-of-scope
     refused (`gemini-3.5-flash-lite`, one run); the prompt was not tuned on them.
2. **Module B, labor-claim triage:**
   - A shared deterministic engine `salary_core` computes net pay for CLT,
     contractor (PJ, Simples Nacional) and internship.
   - Tax parameters live per year in versioned files with source links
     (`params/2026.yaml`); none are hardcoded.
   - At least 20 verified test cases. Reference case: R$ 6,000 CLT, no dependents →
     INSS R$ 641.52, IRRF R$ 385.10 after the Lei 15.270/2025 reduction.
   - The LLM extracts claims from petitions; the code computes amounts.
3. **Module C** is specified privately. Do not add it to this repo until I decide.
