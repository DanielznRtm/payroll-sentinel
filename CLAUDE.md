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
Streamlit UI in `app.py`. Uploads in the UI always use rules, never the LLM. `taxonomy.py` holds the job families, levels, cities and the
2026 minimum wage (R$ 1,621, prorated by weekly hours; internship stipends are
exempt). `validate.py` has two layers: deterministic rules, then a peer comparison
in which robust z-score, IQR and Isolation Forest vote (flag at 2 of 3).

Baseline (seed 42, keyword rules): precision 0.96, recall 0.884, F1 0.92. With
perfect titles, recall is 0.967, so title normalization is the main lever.
LLM titles (`gemini-3.5-flash-lite`, one run, seed 42): precision 0.959, recall
0.967, F1 0.963; report in `reports/evaluation_llm_gemini-3.5-flash-lite.md`.
The LLM title cache is keyed by title only, so use a separate `--data` folder per
model when comparing models.

## Roadmap

1. **Module A, next:**
   - add a README table comparing models (accuracy × latency × cost): Gemini is
     measured, Groq and a local Ollama model are next;
   - add natural-language questions over the benchmark (the LLM writes a pandas
     query, the code executes it).
2. **Module B, labor-claim triage:**
   - A shared deterministic engine `salary_core` computes net pay for CLT,
     contractor (PJ, Simples Nacional) and internship.
   - Tax parameters live per year in versioned files with source links
     (`params/2026.yaml`); none are hardcoded.
   - At least 20 verified test cases. Reference case: R$ 6,000 CLT, no dependents →
     INSS R$ 641.52, IRRF R$ 385.10 after the Lei 15.270/2025 reduction.
   - The LLM extracts claims from petitions; the code computes amounts.
3. **Module C** is specified privately. Do not add it to this repo until I decide.
