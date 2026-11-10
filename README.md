# Payroll Sentinel

[![tests](https://github.com/DanielznRtm/payroll-sentinel/actions/workflows/tests.yml/badge.svg)](https://github.com/DanielznRtm/payroll-sentinel/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Validating salary data before it enters a compensation benchmark.**

Salary benchmarks are built from payroll files that dozens of companies send in.
One annual salary typed into the monthly field, one `8.500,00` read as `8,5`, or one
senior paid like an intern is enough to bend the market median for everyone.
Some of these errors are visible in a single row; others only show up when you
compare a salary with every peer in the dataset.

Payroll Sentinel checks each submission before it is accepted. It flags each row as
`block` (can't enter until it's fixed) or `warn` (needs human review), explains
the probable cause in plain language, and decides per company whether to accept
the file or ask for a resubmission.

Everything runs on **synthetic data with planted, labeled errors**, so every claim
below is measured, not assumed.

## Roadmap: clean data first, AI on top

Payroll Sentinel is the first of three modules that build on each other:

| Module | What it does | Status |
|---|---|---|
| **A. Payroll Sentinel** | Validates payroll data before it enters a salary benchmark | v0.1, this repo |
| **B. Labor-claim triage** | Reads a labor-claim petition, extracts each claim with an LLM and checks it against the validated payroll. Taxes and labor-law amounts come from a deterministic calculation engine, never from the LLM | Planned |
| **C. Pay-fairness tool** | A public tool that tells a person whether their pay is fair: market percentile, net income after work-related costs, and CLT vs. contractor (PJ) | Specified |

The order is deliberate. B's calculations are only as good as the payroll they
read, and C's comparisons are only as good as the data behind them.

## How it works

```
 company CSV ──► title normalization ──► deterministic rules ──► peer comparison ──► report
                 (keyword rules or an     (required fields,        (same family+level,
                  LLM, cached)             duplicates, dates,       all companies)
                                           proportional minimum     robust z | IQR | Isolation Forest
                                           wage, bonus ratio)       └── majority vote (2 of 3)
                                                                    └── cause from peer ratio
```

* **Rules** catch structural errors one row at a time. They are cheap and easy to
  explain, and they get Brazilian labor details right. The minimum wage
  (R$ 1.621 in 2026) is prorated by weekly hours, and internship stipends are
  exempt. A naive `salary < 1621` check would flag legitimate part-time and
  intern rows; the synthetic data plants both on purpose.
* **Peer comparison** puts every salary on a full-time-equivalent basis and
  compares it with all other companies' salaries for the same job family and
  level. Three detectors vote, and a majority vote keeps the recall while cutting
  the false alarms of any single detector.
* **Cause diagnosis** turns a peer ratio into an action. A ratio of about 12× means
  an annual value was typed as monthly. A ratio below 0.5× or above 2× means the
  title or level is probably wrong.
* **Title normalization** maps messy titles (`Dev Backend Sr.`, `HRBP`,
  `ANALISTA DE BI II | Squad Pagamentos`) to a canonical taxonomy. Without it,
  a row has no peer group and is invisible to the statistical checks.

## Results

Default run: 4,502 records, 25 companies, 242 planted errors (seed 42). Titles
were normalized with keyword rules only, with no LLM. Results are stable across
seeds 7, 42 and 123: F1 between 0.920 and 0.925.

| Metric | Value |
|---|---|
| Precision (flagged rows that really had an error) | **0.96** |
| Recall (errored rows that got flagged) | **0.88** |
| False alarms on clean rows | **0.21 %** |
| Cause correctly identified, when detected | 96–100 % per error type |

Peer-comparison detectors on the statistical error types:

| Detector | Precision | Recall | F1 |
|---|---|---|---|
| Robust z-score | 0.85 | 0.84 | 0.85 |
| IQR fence | 0.70 | 0.95 | 0.81 |
| Isolation Forest | 0.51 | 0.55 | 0.53 |
| **Majority vote** | **0.86** | **0.86** | **0.86** |

The full report, including per-error-type numbers and company decisions, is in
[`reports/evaluation.md`](reports/evaluation.md).

## What I learned

1. **The bottleneck is titles, not anomaly detection.** Keyword rules map 100 %
   of common titles but only 4 % of long-tail ones (`SWE`, `HRBP`,
   `Account Executive`). That leaves 24 % of rows with no peer group, hiding 19 of
   the 81 statistical errors. With perfect titles, the same validator's recall
   rises from **0.88 to 0.97**. That gap is the job for the LLM normalizer.
2. **Rules should go first.** Seven of the nine error types reach 100 % recall
   with plain rules, at zero cost and with an explanation anyone can read.
3. **The ensemble mostly fixes IQR's false alarms.** Isolation Forest adds little
   on a one-dimensional problem like this one. The majority vote ends up about as
   good as the robust z-score alone, but noticeably more precise than the IQR fence.
   I kept all three in the report because a weak detector is a finding too.
4. **There is a detection floor.** Level mismatches smaller than about 2.5× the
   peer median sit inside normal pay dispersion (log-salary SD around 0.3 within a
   group) and are often missed. Catching them would need richer context, such as
   the company's own pay bands, not a better outlier detector.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m payroll_sentinel.cli run                     # generate + validate + evaluate (free, offline)
pytest                                                 # 20 tests (2 skip without the [ui] extra)
python -m payroll_sentinel.cli validate my_payroll.csv # your own file (same columns as data/submissions.csv)
```

### Web UI (no terminal needed after setup)

```bash
pip install -e ".[ui]"
streamlit run app.py      # then open http://localhost:8501
```

On Windows, double-click `run_ui.bat` instead: it starts the app from `.venv`
and opens the browser. The UI has two tabs:

* **Evaluation on synthetic data**: pick a seed and a number of companies, run,
  and see the same metrics as `reports/evaluation.md`, with filterable issues and
  CSV/Markdown downloads.
* **Validate a CSV**: upload your own file. Uploads always use the keyword rules,
  so payroll data is never sent to an LLM.

The server only listens on `localhost` and Streamlit's usage statistics are off
(`.streamlit/config.toml`).

### Optional: LLM title normalization (free tiers)

The LLM client talks to any OpenAI-compatible endpoint, so switching provider is
an environment variable:

```bash
export LLM_PROVIDER=gemini LLM_API_KEY=...   # Google AI Studio key, free tier
# export LLM_PROVIDER=groq LLM_API_KEY=...   # GroqCloud, free tier
# export LLM_PROVIDER=ollama                 # local model, no key
# export LLM_MODEL=...                       # override the default model name
python -m payroll_sentinel.cli run --llm
```

Several choices keep it cheap and robust:

* Only **unique** cleaned titles are sent (about 4,500 rows become a few hundred titles).
* Titles go out in batches of 40.
* Calls are throttled to stay under free-tier rate limits.
* Results are cached to disk, so a re-run costs nothing.
* Every answer is validated against the taxonomy. Invalid or missing answers fall
  back to the rule result.

Free tiers may use your prompts for training, which is fine for synthetic data but
not for real payroll.

## Project structure

```
src/payroll_sentinel/
  taxonomy.py   job families, levels, cities, minimum-wage rule
  generate.py   synthetic submissions + planted errors + ground truth
  normalize.py  keyword baseline and LLM normalizer (batching, cache, validation)
  llm.py        ~40-line OpenAI-compatible client (Gemini / Groq / Ollama)
  validate.py   rules, peer-comparison ensemble, cause diagnosis, company decision
  evaluate.py   precision/recall per error type and per detector, title accuracy
  pipeline.py   the pipeline as plain functions, shared by the CLI and the web UI
  cli.py        `run` and `validate` commands
app.py          Streamlit web UI (`streamlit run app.py`, or run_ui.bat on Windows)
tests/          rules, normalizers, LLM parsing/caching (with a fake client), end-to-end quality, UI smoke test
```

## Limitations and next steps

* The data is synthetic. Level markers follow regular patterns, so level accuracy
  is 100 % here; real titles are messier.
* The LLM normalizer is implemented and tested against a fake OpenAI-compatible
  server, but its accuracy hasn't been measured on a real model yet. **Next step:**
  run Gemini, Groq and a local model, and add an accuracy × latency × cost table.
* Planned feature for this module: natural-language questions over the validated
  benchmark ("median for a senior data analyst in Campinas?"), with the LLM
  writing a pandas query and the code executing it.

## License

[MIT](LICENSE)
