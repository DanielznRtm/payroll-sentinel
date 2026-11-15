# Payroll Sentinel

[![tests](https://github.com/DanielznRtm/payroll-sentinel/actions/workflows/tests.yml/badge.svg)](https://github.com/DanielznRtm/payroll-sentinel/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://payroll-sentinel.streamlit.app)

**Validating salary data before it enters a compensation benchmark.**

**[Try the live demo](https://payroll-sentinel.streamlit.app)**: no install needed. It runs on
synthetic data only, and the saved LLM results replace live LLM calls.

Salary benchmarks are built from payroll files that dozens of companies send in.
One annual salary typed into the monthly field, one `8.500,00` read as `8,5`, or one
senior paid like an intern is enough to bend the market median for everyone.
Some of these errors are visible in a single row; others only show up when you
compare a salary with every peer in the dataset.

Payroll Sentinel checks each submission before it is accepted. It flags each row as
`block` (can't enter until it's fixed) or `warn` (needs human review), explains
the probable cause in plain language, and decides per company whether to accept
the file or ask for a resubmission.

Every claim below is measured, not assumed: on **synthetic data with planted,
labeled errors**, on real job titles and questions written by hand, and on three
public salary datasets.

<!-- demo GIF goes here (docs/demo.gif) once it is recorded -->

## In one example

A company sends this file (illustrative numbers):

| Employee | Job title | Monthly salary |
|---|---|---|
| Ana | Analista de Dados Pleno | R$ 7,200 |
| Bruno | Analista de Dados Pleno | R$ 86,400 |
| Carla | Operadora de Produção | R$ 1,200 |
| Diego | HRBP Sr | R$ 9,800 |

Payroll Sentinel answers:

| Employee | Status | Why |
|---|---|---|
| Ana | ok | In line with other mid-level data analysts |
| Bruno | block | About 12× the peer median: an annual salary typed in the monthly field (7,200 × 12) |
| Carla | block | Below the 2026 minimum wage of R$ 1,621 for 44 h/week |
| Diego | ok | The LLM maps `HRBP Sr` to *HR analyst, senior*, so he is compared with the right peers. Keyword rules alone would leave him out |

Decision for the company: accept the file without the blocked rows, or ask for a corrected one.

## Results at a glance

| What | Result |
|---|---|
| Errors caught (recall), with LLM titles | 97 % (precision 96 %) |
| Real job titles mapped to the right family | 97.4 % (keyword rules: 61.4 %) |
| Questions answered right / out-of-scope questions refused | 27 of 30 / 5 of 5 |
| Public data: Indian salary rows reaching the peer comparison | 99.2 % (keyword rules: 2.7 %) |
| Cost | R$ 0 (free LLM tier) |

Details, methods and limits are in [Results](#results).

## Roadmap: clean data first, AI on top

Payroll Sentinel is the first of three modules that build on each other:

| Module | What it does | Status |
|---|---|---|
| **A. Payroll Sentinel** | Validates payroll data before it enters a salary benchmark | v1.0, this repo |
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
* **Cause diagnosis** turns a peer ratio into an action, the same way up and down.
  About 12× the peer median means an annual value was typed as monthly; about
  1/12 means a monthly value was divided by 12. Between 6× and 9× (or 1/6 and
  1/9) a real top salary is also plausible, so the row goes to review instead of
  being blocked. Beyond 30× either way it cannot be a real salary. A ratio below
  0.5× or above 2× means the title or level is probably wrong.
* **Title normalization** maps messy titles (`Dev Backend Sr.`, `HRBP`,
  `ANALISTA DE BI II | Squad Pagamentos`) to a canonical taxonomy. Without it,
  a row has no peer group and is invisible to the statistical checks.

## Results

Default run: 4,502 records, 25 companies, 242 planted errors (seed 42). The same
validator was run twice, changing only how job titles are normalized: free,
offline keyword rules, and an LLM (`gemini-3.5-flash-lite`, Gemini free tier).
With rules, results are stable across seeds 7, 42 and 123 (F1 between 0.920 and
0.925); the LLM run is a single run on seed 42.

| Metric | Keyword rules | LLM titles |
|---|---|---|
| Precision (flagged rows that really had an error) | 0.96 | 0.96 |
| Recall (errored rows that got flagged) | 0.88 | **0.97** |
| F1 | 0.92 | **0.96** |
| False alarms on clean rows | 0.21 % | 0.23 % |
| Long-tail titles mapped to the right job family | 4 % | **96.5 %** |
| Real held-out titles mapped to the right job family ([below](#held-out-titles-from-real-job-postings)) | 61.4 % | **97.4 %** |
| Statistical errors visible to the peer comparison | 62 / 81 | **81 / 81** |
| Cause correctly identified, when detected | 96–100 % per error type | 97–100 % per error type |

With LLM titles, recall equals the recall with perfect (oracle) titles: 0.967.
What it still misses is the detection floor described below, not titles.

Peer-comparison detectors on the statistical error types (keyword rules run):

| Detector | Precision | Recall | F1 |
|---|---|---|---|
| Robust z-score | 0.85 | 0.84 | 0.85 |
| IQR fence | 0.70 | 0.95 | 0.81 |
| Isolation Forest | 0.51 | 0.55 | 0.53 |
| **Majority vote** | **0.85** | **0.85** | **0.85** |

The full reports, including per-error-type numbers and company decisions, are in
[`reports/evaluation.md`](reports/evaluation.md) (keyword rules) and
[`reports/evaluation_llm_gemini-3.5-flash-lite.md`](reports/evaluation_llm_gemini-3.5-flash-lite.md) (LLM).
The LLM report and the pipeline runs in `reports/models/` predate the two-way cause
diagnosis: that change leaves flags, precision and recall as they are, so only
their cause and company tables would read differently today.

### Held-out titles from real job postings

The synthetic titles come from a fixed list, so I also wrote 130 titles by hand,
copied from real job postings (mostly Gupy, plus LinkedIn, Vagas.com and other
boards), with the source of each in [`eval/heldout_sources.csv`](eval/heldout_sources.csv).
None of them is in `taxonomy.py`, and 16 are outside the taxonomy, where the right
answer is to abstain. The labels were committed before the first run, and the
prompt was not changed afterwards.

| Metric (114 titles inside the taxonomy, 16 outside) | Keyword rules | LLM titles |
|---|---|---|
| Right family | 61.4 % | **97.4 %** |
| Right family, when it answers | 98.6 % | 99.1 % |
| Right family and level | 50.9 % | **86.8 %** |
| Abstained (sent to human review) | 37.7 % | 1.8 % |
| Wrong family (silent error) | 0.9 % | 0.9 % |
| Outside titles correctly left unmapped | 13 / 16 | 14 / 16 |

Rules almost never pick a wrong family, but they leave more than a third of real
titles unmapped; the LLM maps nearly all of them. Its family errors are a data
scientist post focused on web development (mapped to software engineer), a product
marketing manager mapped to product manager, and a forklift operator mapped to
production operator. 12 of its 17 errors are levels: 5 are ranges such as
`Pleno/Sênior`, where my labels take the first level cited and the model took the
higher one, and 4 involve Roman numerals. One run of `gemini-3.5-flash-lite`:
4 calls, no 429s, 15 s. Reports: [rules](reports/titles_heldout_rules.md),
[LLM](reports/titles_heldout_llm_gemini-3.5-flash-lite.md).

### Official Brazilian occupation titles (CBO)

Keyword rules only know the spellings they were written with. The official
Brazilian classification of occupations (CBO 2002, Ministério do Trabalho e
Emprego) lists 2,725 occupations and 7,870 synonyms. I picked the CBO codes that
belong to each family: 64 codes, reviewed by hand. Data analyst and product
manager have none: the CBO's "gerente de produtos" is a marketing manager.
[`scripts/build_cbo_titles.py`](scripts/build_cbo_titles.py) turns their titles and
synonyms into 276 phrases ([`cbo_titles.py`](src/payroll_sentinel/cbo_titles.py)).
With `--cbo`, a title the keywords miss is looked up there, longest phrase first;
the level still comes from the title.

| Metric | Keyword rules | Rules + CBO |
|---|---|---|
| Held-out titles: right family (114 inside the taxonomy) | 61.4 % | 63.2 % |
| Held-out titles: wrong family | 0.9 % | 0.9 % |
| Held-out titles outside the taxonomy left unmapped | 13 / 16 | 13 / 16 |
| Synthetic long-tail titles: right family (seed 42) | 4 % | 7.7 % |
| Synthetic F1 (seed 42) | 0.92 | 0.92 |

The CBO helps where companies write official Portuguese titles: it recovered
`Supervisor de Manutenção Industrial` and `Estagiário de Customer Success
Manager`, and it never mapped a title outside the taxonomy. It does not help with
English and tech jargon (`SWE`, `Account Executive`, `Analista de BI`), which is
where the long tail is. On seeds 7 and 123, F1 moved from 0.925 to 0.932 and
stayed at 0.924. On the three public files the share of titled rows did not change,
since their titles are in English or Italian. So the CBO stays an option for now,
and the LLM remains the main lever. Reports:
[held-out](reports/titles_heldout_rules_cbo.md),
[synthetic](reports/evaluation_rules_cbo.md).

### Comparing models

Each model ran once, on free tiers, through the same two tests: the full pipeline
(seed 42, `run --llm --no-cache`, 36 batches of 40 titles) and the 130 held-out
titles (`eval-titles --llm`, 4 batches).

| Model (provider) | Long-tail family (synthetic, 1,109 rows) | Held-out family (114 real titles) | Wrong family on held-out (false mappings, of 16 outside) | Detection F1 | Titles answered by the LLM | 429 responses | Total time (pipeline titles) | Cost |
|---|---|---|---|---|---|---|---|---|
| **`gemini-3.5-flash-lite`** (Gemini) | **99.5 %** | 97.4 % | 0.9 % (2) | **0.963** | 100 % | 0 | **160 s** | R$ 0 |
| `gemini-3.5-flash` (Gemini) | 83.5 % | **99.1 %** | 0.9 % (0) | 0.954 | 75.5 % | 43 | 1,069 s | R$ 0 |
| `openai/gpt-oss-20b` (Groq, `reasoning_effort=low`) | 52.1 % | 87.7 % | 2.6 % (2) | 0.921 | 100 % | 39 | 497 s | R$ 0 |
| Keyword rules (no LLM) | 4 % | 61.4 % | 0.9 % (3) | 0.92 | – | – | no API calls | R$ 0 |

**Default: `gemini-3.5-flash-lite`.** It is the only model that answered every
title at pipeline volume without a single 429, and it has the best long-tail
accuracy, the best F1 and the shortest time. `gemini-3.5-flash` is better on real
titles, but the free tier cannot sustain it for a 36-call run, and Groq's
`gpt-oss-20b` abstains too often to beat the keyword rules on F1.

* **`gemini-3.5-flash` is limited by the free tier, not by the model.** On the
  held-out titles (4 calls, no 429s) it was the most accurate model and never
  forced an outside title into a family. In the pipeline, 43 rate-limit responses
  made 9 of the 36 batches fall back to rules, which is why its long-tail score
  drops; it also waited 18.6 s per request on the held-out run.
* **`gpt-oss-20b` answers fast but abstains.** It waited only 1.7 s per request;
  the 497 s are back-off for Groq's 8,000 tokens-per-minute free limit. It left
  47.9 % of long-tail titles and 3.5 % of common ones unmapped. Because an LLM
  answer replaces the rule answer, it does worse than rules on common titles
  (96.5 % vs 100 %), and only 71 of the 81 statistical errors stay visible.
  False alarms nearly double: 18 clean rows flagged instead of 10 (0.42 % vs 0.23 %).
* **Single runs vary.** The Results table above shows 96.5 % long-tail accuracy
  for `gemini-3.5-flash-lite`: that is an earlier run of the same model and seed,
  and its report feeds the demo. Treat differences of a few points between single
  runs as noise.
* A local Ollama model was not measured: it needs an NVIDIA GPU, and the
  development machine has none.

Reports: pipeline runs in [`reports/models/`](reports/models/); held-out runs in
[flash-lite](reports/titles_heldout_llm_gemini-3.5-flash-lite.md),
[flash](reports/titles_heldout_llm_gemini-3.5-flash.md) and
[gpt-oss-20b](reports/titles_heldout_llm_openai-gpt-oss-20b.md).

### Questions over the benchmark

I wrote 30 questions in Portuguese, the way an HR client would ask them
([`eval/questions.csv`](eval/questions.csv)). 25 are in scope, and 3 of those
should get "not enough data". 5 are out of scope: a company ranking, raises over
time, a gender gap, meal vouchers and hiring advice. The expected queries were
filled in, reviewed and committed before the first run, and the code computes the
right answers from them. One run of `gemini-3.5-flash-lite`:

| Metric | Result |
|---|---|
| Right query (exact match) | 27 / 30 (90 %) |
| Right answer | 27 / 30 (90 %) |
| In-scope questions answered right | 22 / 25 (88 %) |
| Out-of-scope questions refused | **5 / 5** |

None of the three errors produced a wrong number. Two in-scope questions were
refused: `coordenador de manutenção` and `HRBP sênior em Curitiba`. The prompt
names neither "coordenador" as a lead level nor HRBP as an HR analyst, and the
model refused instead of guessing (for HRBP the right answer was "not enough
data": 4 records). The third, "devs e cientistas de dados em São Paulo", got one
median per family instead of one for both together, a reading flagged as
ambiguous during the review. As with the titles, the prompt was not changed after
these results. Run: 30 calls, 2 rate-limit (429) responses, 143 s. Report:
[`reports/ask_eval_gemini_gemini-3.5-flash-lite.md`](reports/ask_eval_gemini_gemini-3.5-flash-lite.md).

### Public salary data (no ground truth)

Synthetic data only tests the errors I planted, so I also ran the pipeline on
three public salary files. They are not in the repository, and
[`scripts/public_data_check.py`](scripts/public_data_check.py) takes their paths:

* `Salary_Dataset_DataScienceLovers.csv` (Kaggle): 22,770 rows of Indian tech
  salaries by company, title and city (INR, annual);
* `Salary_Data.csv` (Kaggle): 6,704 rows with title, education, experience and
  salary (USD, annual). Its age and gender columns are never read;
* [`datapizza-ai-lab/salaries`](https://huggingface.co/datasets/datapizza-ai-lab/salaries)
  (Hugging Face, CC BY-NC 4.0): 26,551 answers to an Italian tech salary survey
  (EUR, annual), with a `valid` flag set by the publisher. Its age, gender and
  submission-time columns are never given to the validator.

Only job titles were sent to the LLM. No file has labeled salary errors, so this is
a case study, not a benchmark. One run of `gemini-3.5-flash-lite` on 1,387 distinct
titles: 32 calls, no rate-limit (429) response, 147 s. Report:
[`reports/public_data_gemini_gemini-3.5-flash-lite.md`](reports/public_data_gemini_gemini-3.5-flash-lite.md).

**Titles.** The Indian file tags every row with a software job role, a weak label:

| Metric | Keyword rules | LLM titles |
|---|---|---|
| Developer rows mapped to software engineer (20,165 rows, 9 roles) | 3.1 % | **99.4 %** |
| Distinct developer titles mapped to software engineer (885) | 10.1 % | **96.0 %** |
| Intern rows given level intern (2,106) | 100 % | 100 % |
| US-style rows with any family (no labels; many titles, such as marketing, are outside the taxonomy) | 39.0 % | 73.4 % |
| Italian rows with any family (no labels; 117 job categories) | 15.6 % | 66.3 % |

Most LLM "errors" against the weak label are errors of the label. The roles seem
to be assigned by keyword, so `Mobile Repair Technician` sits under *Mobile* and
`Front End Cashier` under *Frontend*. The LLM mapped the first to maintenance
technician and left the cashier unmapped. A keyword label shares the blind spots
of keyword rules, so 96.0 % is a floor. Single runs vary here too: the previous
run (report in the git history) mapped 92.8 % of the distinct Testing titles to
software engineer, and this one 76.8 %, leaving `QA Tester` unmapped.

**Validation.** With LLM titles, 99.2 % of the Indian rows reach the peer
comparison, against 2.7 % with keyword rules. The validator found:

* in the US-style file, 5 missing salaries, 2 missing titles and 4 annual
  salaries of US$ 350 to 579, all blocked. 6,005 of its 6,704 rows sit in groups
  that repeat title, education, experience and salary;
* in the Indian file, 16 salaries more than 30× away from their peers, from
  90 million INR (180×) to developers paid 12,000 INR a year (1/40 to 1/77 of
  their peers). Another 111 are 6 to 30 times below their peers, the mirror image
  of an annual value typed as monthly: most likely monthly salaries in the annual
  field;
* in the Italian survey, 344 answers repeated word for word, and one with 24,126
  months (2,010 years) of experience, whose hire date became impossible.

**Against the publisher's own flag.** The Italian `valid` flag marks 84 answers
invalid, but their salaries look normal: the validator flags only 3 of them. Several
look like the same person answering twice within minutes, with different values,
which a row-by-row check cannot see. In the other direction, the publisher kept
answers that the validator does question:

| Answers the publisher marks valid | Blocked | Sent to review | No issue |
|---|---|---|---|
| Annual salary under €10,000 (139) | 8 | 83 | 48 |
| Annual salary over €200,000 (29), up to €1,000,000 | 16 | 6 | 7 |
| Everything else (26,299) | 0 | 560 | 25,739 |

The two checks complement each other: "valid" depends on what is being checked.
Here every job title lacks seniority, so all rows count as `mid`, and most of the
293 level warnings in this file only reflect juniors and seniors in one peer
group.

The real files also showed three weaknesses that the synthetic data could not.
All three are now fixed, and precision and recall stayed the same on seeds 7, 42
and 123:

1. Values about 1/12 of their peers were diagnosed as wrong levels. The diagnosis
   now works both ways (`divided_by_12`).
2. Senior salaries at large companies, 6 to 7 times the market median, were
   blocked as typos. The 6–9× band now goes to review (8 Indian rows).
3. Rows copied under a new employee ID passed unnoticed. They now get a
   `duplicate_record` warning (6,005 US-style rows, 344 Italian, 64 Indian).

Two limits remain. Rejecting a company above 5 % blocked rows does not fit a file
with one to three rows per company: 121 of 11,261 Indian companies were rejected.
The taxonomy also has no level above lead, so the LLM puts managers and directors
at senior or lead inconsistently.

### How realistic are the synthetic salaries?

The generator's salaries are made up, so I checked them against State of Data
Brazil 2025-2026, a survey of Brazilian data professionals by Data Hackers and Bain
(Kaggle; not in the repository). [`scripts/state_of_data_check.py`](scripts/state_of_data_check.py)
reads only six columns: work status, manager flag, job, level, salary band and
state. It never reads age, gender or race. It keeps CLT employees who are not
managers, the closest match to a payroll file (1,037 answers). Salaries come in
bands, so the survey medians are grouped-data medians, interpolated inside the
band that holds the middle answer.

| Brazil, monthly median | Junior | Mid | Senior | Lead (specialist/staff) |
|---|---|---|---|---|
| Data analyst, survey | R$ 4,200 | R$ 6,457 | R$ 9,563 | R$ 13,100 |
| Data analyst, synthetic | R$ 4,210 | R$ 6,550 | R$ 9,410 | R$ 12,915 |
| Data scientist, survey | R$ 6,875 | R$ 9,241 | R$ 14,714 | R$ 17,059 |
| Data scientist, synthetic | R$ 6,280 | R$ 9,520 | R$ 13,770 | R$ 18,565 |

For the two data families, synthetic medians are within 10 % of the survey
nationwide, and the level steps match: a senior data analyst earns 1.48× the
mid-level median in the survey and 1.44× in the synthetic data. São Paulo, where
the generator sets its base salaries, is less close: synthetic medians run up to
18 % high, for lead data scientists. A data survey is a poor sample of other
roles. It has fewer than 15 product managers per level, and only 18 mid-level and
24 senior software engineers: their medians match the synthetic data at senior level,
while the synthetic mid level is 44 % higher. The survey also had one malformed
answer of its own: a salary band "from R$ 25,001 to R$ 3,000". Report:
[`reports/realism_state_of_data.md`](reports/realism_state_of_data.md).

**Real pay from RAIS.** RAIS is Brazil's official record of every formal job,
published without names or IDs. [`scripts/rais_check.py`](scripts/rais_check.py)
reads the 2025 São Paulo file (25.5 million rows) as a stream from the
`.7z` archive in about 3 minutes. It uses seven columns (occupation, municipality,
active on 31 December, hours, contract type, intermittent flag, December pay) and
never age, sex, race, nationality, disability or schooling. It keeps full-time CLT
jobs in the CBO codes approved for each family, in São Paulo, Campinas and
Sorocaba: 509,542 jobs (36,904 more had no December pay). RAIS has no seniority
level, so both sides pool every level, and RAIS pay includes overtime and
commissions while the synthetic salary is base pay.

| 3 cities | Real median | Synthetic median | Synthetic / real | Real log-pay SD | Synthetic log-pay SD |
|---|---|---|---|---|---|
| Software engineer | R$ 10,093 | R$ 10,100 | 1.00 | 0.66 | 0.42 |
| Financial analyst | R$ 6,573 | R$ 6,440 | 0.98 | 0.57 | 0.42 |
| HR analyst | R$ 5,224 | R$ 5,530 | 1.06 | 0.54 | 0.40 |
| Production operator | R$ 2,594 | R$ 2,390 | 0.92 | 0.40 | 0.37 |
| Data scientist | R$ 12,413 | R$ 11,160 | 0.90 | 0.59 | 0.42 |
| Maintenance technician | R$ 4,639 | R$ 4,035 | 0.87 | 0.60 | 0.40 |
| Customer support | R$ 3,857 | R$ 3,130 | 0.81 | 0.72 | 0.40 |
| Sales rep | R$ 3,267 | R$ 5,960 | **1.82** | 0.84 | 0.42 |

* **Medians are close for most families.** Five of the eight are within 10 % of
  real pay, and maintenance is 13 % low.
* **Sales and support differ by definition, not by salary.** In the CBO codes,
  67 % of sales jobs are retail sellers, with a median of R$ 2,713, and 11 % are
  sales managers, at R$ 17,000. The synthetic family models B2B account
  executives. In support, IT support analysts (R$ 5,000) sit next to telemarketing
  operators (R$ 2,077 to R$ 2,937).
* **Real pay is more spread out.** Within a family, the real spread of log pay is
  0.54 to 0.84, except for production operators (0.40). The synthetic spread is
  about 0.40. Errors hide more easily in real data than in the synthetic set,
  so the synthetic recall is optimistic.
* **One index per city is too simple.** Production operators earn more in
  Campinas (R$ 3,087) and Sorocaba (R$ 2,964) than in São Paulo (R$ 2,474), while
  software engineers earn less (R$ 9,117 and R$ 7,495 against R$ 10,268). The
  generator applies one multiplier to every family in a city (0.92 and 0.85).

Nothing was recalibrated yet. Doing it would change every synthetic number in this
README. Report: [`reports/realism_rais.md`](reports/realism_rais.md).

## What I learned

1. **The bottleneck is titles, not anomaly detection.** Keyword rules map 100 %
   of common titles but only 4 % of long-tail ones (`SWE`, `HRBP`,
   `Account Executive`). That leaves 24 % of rows with no peer group, hiding 19 of
   the 81 statistical errors. With perfect titles, the same validator's recall
   rises from **0.88 to 0.97**. An LLM normalizer closed that gap entirely
   (recall 0.967, the oracle value) at zero cost.
2. **The LLM fails safe here.** It got 39 of 4,484 titled rows wrong, and every
   one was an abstention ("no family"), never a wrong family: an unmapped row is
   only left out of the peer comparison, while a wrong family would compare it
   against the wrong peers. I did not tune the prompt on these misses: tuning the
   prompt on the errors of the evaluation set would inflate the very number I am
   reporting.
3. **Rules should go first.** Seven of the nine error types reach 100 % recall
   with plain rules, at zero cost and with an explanation anyone can read.
4. **The ensemble mostly fixes IQR's false alarms.** Isolation Forest adds little
   on a one-dimensional problem like this one. The majority vote ends up about as
   good as the robust z-score alone, but noticeably more precise than the IQR fence.
   I kept all three in the report because a weak detector is a finding too.
5. **There is a detection floor.** Level mismatches smaller than about 2.5× the
   peer median sit inside normal pay dispersion (log-salary SD around 0.3 within a
   group) and are often missed. Catching them would need richer context, such as
   the company's own pay bands, not a better outlier detector.
6. **On a free tier, the limit picks the model.** The most accurate model on real
   titles could not finish a full run without rate limits, and a weaker model
   scored below plain rules on titles the rules already knew. A model is only as
   good as the share of the job it can do inside the quota.
7. **Real data finds the errors you did not plant.** The synthetic set measured
   the errors I imagined. Public files showed three I had not: monthly
   salaries in an annual field, legitimate top pay that looked like a typo, and
   rows copied under new IDs. Each fix was measured on the synthetic set first,
   so it could not quietly break what already worked.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m payroll_sentinel.cli run                     # generate + validate + evaluate (free, offline)
pytest                                                 # 82 tests (4 skip without the [ui] extra)
python -m payroll_sentinel.cli validate my_payroll.csv # your own file (same columns as data/submissions.csv)
python -m payroll_sentinel.cli eval-titles eval/heldout_titles.csv  # [--llm | --cbo] titles not in taxonomy.py
python -m payroll_sentinel.cli run --cbo               # keyword rules plus the official CBO titles
```

`validate` writes `issues.csv`, `companies.csv` and two files to send back to the
company: `accepted_rows.csv` (ok and warn rows) and `rows_to_fix.csv` (blocked rows),
both with the company's own columns plus `status` and `issues`.

With an LLM key (see below) you can also ask questions about the validated benchmark:

```bash
python -m payroll_sentinel.cli ask "qual a mediana de analista de dados sênior em Campinas?"
python -m payroll_sentinel.cli eval-ask eval/questions.csv  # query and answer accuracy
python -m payroll_sentinel.cli models                       # models your key can use
```

The LLM never writes code here. It only fills a fixed JSON form (filters, grouping,
metric, column); the code checks every field against allow-lists, including the
exact values each column may take, and runs it with pandas boolean masks. Only rows
the validator approved are used, salaries are full-time equivalents, every answer
states how many records it used, and fewer than 5 records gives "not enough data".

### Web UI (no terminal needed after setup)

```bash
pip install -e ".[ui]"
streamlit run app.py --server.address localhost   # then open http://localhost:8501
```

On Windows, double-click `run_ui.bat` instead: it starts the app from `.venv`
and opens the browser. The UI has two tabs, plus a third when an LLM key is set:

* **Evaluation on synthetic data**: pick a seed and a number of companies, run,
  and see the same metrics as `reports/evaluation.md`, with filterable issues and
  CSV/Markdown downloads.
* **Validate a CSV**: upload your own file. Uploads always use the keyword rules,
  so payroll data is never sent to an LLM. Download the accepted rows and the rows
  to fix, each with its reason, to send back to the company.
* **Ask the benchmark**: questions in Portuguese or English, answered as above.

With `--server.address localhost` (also used by `run_ui.bat`) only this computer
can open the app. Streamlit's usage statistics are off (`.streamlit/config.toml`).

**Public demo mode.** Set `DEMO_MODE=1` as an environment variable or as a
root-level key in Streamlit secrets. The upload tab and the LLM option disappear,
runs are capped at 50 companies, and an **LLM results** tab shows the saved report
`reports/evaluation_llm_gemini-3.5-flash-lite.md` instead of calling an LLM. This is
how the app runs on Streamlit Community Cloud, which installs it from
`requirements.txt`.

### Optional: LLM title normalization (free tiers)

The LLM client talks to any OpenAI-compatible endpoint, so switching provider is
an environment variable:

```bash
export LLM_PROVIDER=gemini LLM_API_KEY=...   # Google AI Studio key, free tier
# export LLM_PROVIDER=groq LLM_API_KEY=...   # GroqCloud, free tier
# export LLM_PROVIDER=ollama                 # local model, no key
# export LLM_MODEL=...                       # override the default (gemini-3.5-flash-lite)
# export LLM_REASONING_EFFORT=low            # needed for reasoning models such as Groq's gpt-oss
python -m payroll_sentinel.cli run --llm
```

`openai/gpt-oss-20b`, Groq's default here, is a reasoning model: with its default
effort it spent the whole 2,048-token answer budget thinking and returned no JSON.
`LLM_REASONING_EFFORT=low` fixes that; it is sent only when set.

Model names change often: `gemini-2.5-flash-lite`, the previous default, returned
HTTP 404 for a new key. List what your key can use with `GET /models` and set
`LLM_MODEL`.

Several choices keep it cheap and robust:

* Only **unique** cleaned titles are sent: 4,484 titled rows become 1,425 titles.
* Titles go out in batches of 40, so the default run makes 36 calls. Time per
  model is in [Comparing models](#comparing-models); cost R$ 0.
* Calls are throttled to stay under free-tier rate limits (at most one every 4.5 s).
* Results are cached to disk, one file per provider and model, so a re-run costs
  nothing and one model's answers never stand in for another's. Use
  `run --llm --no-cache` to time a model: every LLM report states calls, HTTP
  requests, rate-limit (429) responses and time.
* Every answer is validated against the taxonomy. Invalid or missing answers fall
  back to the rule result, and the report states the share of titles the LLM
  actually answered.
* A rejected request (bad key, unknown model) stops the run at the first call,
  with the provider's message. A batch the model answers with invalid JSON falls
  back to rules, like a rate-limited one. If every batch fails, the run fails
  instead of reporting rule results as LLM results.

Free tiers may use your prompts for training, which is fine for synthetic data but
not for real payroll.

## Project structure

```
src/payroll_sentinel/
  taxonomy.py   job families, levels, cities, minimum-wage rule
  generate.py   synthetic submissions + planted errors + ground truth
  normalize.py  keyword baseline (optionally + CBO) and LLM normalizer (batching, cache, validation)
  cbo_titles.py official CBO 2002 titles and synonyms per family (generated, do not edit)
  llm.py        small OpenAI-compatible client (Gemini / Groq / Ollama), with run stats
  validate.py   rules, peer-comparison ensemble, cause diagnosis, company decision
  evaluate.py   precision/recall per error type and per detector, title accuracy
  pipeline.py   the pipeline as plain functions, shared by the CLI and the web UI
  titles_eval.py  held-out title evaluation (abstention vs. wrong family)
  ask.py        questions over the benchmark: checked JSON query, pandas execution, evaluation
  cli.py        run, validate, eval-titles, ask, eval-ask and models commands
eval/           hand-written ground truth: held-out titles and questions
scripts/        public_data_check.py: titles and full validation on public salary files
                build_cbo_titles.py: rebuilds cbo_titles.py from the CBO tables (codes per family)
                state_of_data_check.py: synthetic salaries vs. the State of Data Brazil survey
                rais_check.py: synthetic salaries vs. RAIS official job records (streamed from .7z)
app.py          Streamlit web UI (`streamlit run app.py`, or run_ui.bat on Windows)
tests/          rules, normalizers, LLM parsing/caching (with a fake client), end-to-end quality, UI smoke test
```

## Limitations and next steps

* The data is synthetic. Level markers follow regular patterns, so level accuracy
  is 100 % here; on the 114 real held-out titles, LLM level accuracy is 89.5 %.
  Synthetic medians are close to real pay (a survey for the data families, RAIS
  for eight families), but real pay is more spread out, so the synthetic recall is
  optimistic. The sales and support families pool jobs with very different pay.
* The synthetic long-tail titles come from a fixed list of abbreviations and
  English titles (`SWE`, `HRBP`), which a large model has likely seen before.
  The 96.5 % long-tail accuracy is measured on that list. The real-title check
  (97.4 % family accuracy) uses only 130 titles, labeled by one person.
* Each model in the comparison ran once, on one seed. A local Ollama model is
  still unmeasured, because it needs an NVIDIA GPU.
* The question evaluation is 30 questions written by one person, run once. Answers
  use full-time-equivalent salaries, so an intern's 30 h stipend is shown scaled
  to 44 h (about 1.47×).

## License

[MIT](LICENSE)
