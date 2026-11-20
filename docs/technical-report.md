# Payroll Sentinel: technical report

The full write-up behind the [README](../README.md), which is a short overview in
Portuguese: how the validator works, every measurement with its method, and the
limits. Every number comes from a report in [`reports/`](../reports/).

## How it works

```
 company CSV ──► title normalization ──► deterministic rules ──► peer comparison ──► report
                 (keyword + CBO rules     (required fields,        (same family+level,
                  or an LLM, cached)       duplicates, dates,       all companies)
                                           proportional minimum     robust z | IQR | Isolation Forest
                                           wage, bonus ratio)       └── majority vote (2 of 3)
                                                                    └── cause from peer ratio
```

* **Rules** catch structural errors one row at a time. They are cheap and easy to
  explain, and they get Brazilian labor details right. The minimum wage
  (R$ 1.621 in 2026) is prorated by weekly hours against the full normal week of
  the cut-off date, which EC 141/2026 shortens
  ([below](#minimum-wage-after-ec-1412026)), and internship stipends are
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

Default run: 4,502 records, 25 companies, 242 planted errors (seed 42), with
salaries whose spread is fitted to RAIS, Brazil's official job records (v1.1,
[below](#how-realistic-are-the-synthetic-salaries)). The same validator was run
twice, changing only how job titles are normalized: free, offline rules (keywords
plus the official CBO titles, [below](#official-brazilian-occupation-titles-cbo)),
and an LLM (`gemini-3.5-flash-lite`, Gemini free tier). With rules, results are
stable across seeds 7, 42 and 123 (F1 between 0.835 and 0.862); the LLM answers
come from one run on seed 42.

| Metric | Rules (keywords + CBO) | LLM titles |
|---|---|---|
| Precision (flagged rows that really had an error) | 0.892 | **0.913** |
| Recall (errored rows that got flagged) | 0.785 | **0.822** |
| F1 | 0.835 | **0.865** |
| False alarms on clean rows | 0.54 % | 0.45 % |
| Long-tail titles mapped to the right job family | 7.7 % | **99.5 %** |
| Real held-out titles mapped to the right job family ([below](#held-out-titles-from-real-job-postings)) | 63.2 % | **97.4 %** |
| Statistical errors visible to the peer comparison | 63 / 81 | **81 / 81** |
| Cause correctly identified, when detected | 85–100 % per error type | 85–100 % per error type |

With LLM titles, recall equals the recall with perfect (oracle) titles: 0.822.
What it still misses is the detection floor described below, not titles.

Peer-comparison detectors on the statistical error types (rules run):

| Detector | Precision | Recall | F1 |
|---|---|---|---|
| Robust z-score | 0.42 | 0.44 | 0.43 |
| IQR fence | 0.47 | 0.54 | 0.50 |
| Isolation Forest | 0.25 | 0.29 | 0.27 |
| **Majority vote** | **0.56** | **0.46** | **0.50** |

The full reports, including per-error-type numbers and company decisions, are in
[`reports/evaluation.md`](../reports/evaluation.md) (rules; keywords alone in
[`evaluation_keywords_only.md`](../reports/evaluation_keywords_only.md)) and
[`reports/evaluation_llm_gemini-3.5-flash-lite.md`](../reports/evaluation_llm_gemini-3.5-flash-lite.md) (LLM).
The LLM report reuses the cached answers of the `gemini-3.5-flash-lite` run in
[Comparing models](#comparing-models), so it made no API call.

### What a realistic pay spread does to detection

v1.0 drew each salary with a spread I chose (log-pay SD 0.15 per person). In v1.1
the spread is fitted to 361,437 real job records, and the median spread of log pay
inside a peer group (family and level) went from 0.21 to 0.50. The validator did
not change. Seed 42, same LLM answers in both columns:

| | v1.0 spread | v1.1 spread (RAIS) |
|---|---|---|
| F1, rules | 0.920 | 0.835 |
| F1, LLM titles | 0.963 | 0.865 |
| Recall, LLM titles (equal to perfect titles) | 0.967 | 0.822 |
| Level mismatches caught, LLM titles | 37 / 45 | 4 / 45 |
| Annual salaries typed as monthly caught, LLM titles | 36 / 36 | 34 / 36 |
| False alarms on clean rows, LLM titles | 0.23 % | 0.45 % |

A level mismatch is the salary of another level, about 2.4 to 3.3 times off, up or
down. With a spread of 0.50 that is only 1.7 to 2.4 standard deviations from the
peer median, among normal salaries. An annual salary typed as monthly (12 times) is
still about 5 standard deviations away and is still caught, and the rules are
untouched: seven of the nine error types stay at 100 % recall. RAIS has no
seniority level, so the generator keeps its level steps and puts the rest of the
real spread inside the peer group. If real levels are further apart than the
generator's, v1.1 is pessimistic and the truth lies between the two columns.

### Validating one company's file

The peer comparison needs at least 15 salaries of the same family and level. One
company rarely has that, so on its own a file gets almost no peer comparison. The
web UI therefore validates an uploaded file together with reference peers, the
clean rows of the synthetic benchmark (seed 42, 25 companies, salaries fitted to
RAIS), and reports only the file's rows
([`validate_against_reference`](../src/payroll_sentinel/pipeline.py)). Measured on
another seed (7), validating each of its 25 companies on its own, with rules:

| Each company validated on its own (seed 7) | Alone | With reference peers |
|---|---|---|
| Planted errors caught | 152 / 218 (69.7 %) | **172 / 218 (78.9 %)** |
| Annual salaries typed as monthly | 4 / 33 | **22 / 33** |
| Level mismatches | 4 / 41 | 6 / 41 |
| False alarms on clean rows | 0.21 % | 0.39 % |

Unrecognized-title warnings are not counted as detections here. The reference is
synthetic: it stands in for the validated benchmark a real deployment would
compare against. In the web UI a company can also give a family to titles the
rules do not know; the level still comes from the title. Report:
[`reports/reference_peers.md`](../reports/reference_peers.md), from
[`scripts/reference_check.py`](../scripts/reference_check.py).

### Minimum wage after EC 141/2026

EC 141/2026 (DOU 2026-10-16) lowers the normal week to 42 h from 2026-12-16 and
to 40 h from 2027-12-16, with no salary cut, minimum wages included (art. 2). The
minimum wage pays the full normal week, and a contract of fewer hours may be paid
it in proportion (TST OJ 358: hours below the constitutional limit). So the
proportion now depends on the date: from 2026-12-16 a 42 h contract owes
R$ 1,621.00 instead of R$ 1,547.32 (42/44), and a 40 h one R$ 1,543.81 instead of
R$ 1,473.64. The steps of the week and the minimum wage are read from
[`salary_core/params/2026.json`](../src/salary_core/params/2026.json), with their
sources; a date in a year without a file (2025, 2027) is refused instead of getting
the 2026 minimum.

The benchmark cut-off, 2026-10-31, comes before the first step, so
`reports/evaluation.md` is byte-identical before and after the change. Validating
the same seed-42 data as of 2026-12-16 (one run of `rule_checks` with
`validate.REFERENCE_DATE` moved to that date):

| Cut-off | Blocked below the minimum | Planted errors caught | Clean rows blocked |
|---|---|---|---|
| 2026-10-31 | 27 | 27 / 27 | 0 |
| 2026-12-16 | 41 | 27 / 27 | 14 (12 of 40 h, 2 of 30 h) |

The 14 rows were paid less than 4.8 % (44/42) above the old 44 h proportion, legal
on 2026-10-31 and below the 42 h one. Using the 42 h week for the proportion is
this project's reading (decided 2026-11-20): Decreto 12.797/2025 still states an
hourly minimum of R$ 7.37 (1,621 / 220), and the courts have not ruled on the
proportion after the amendment yet.

### Held-out titles from real job postings

The synthetic titles come from a fixed list, so I also wrote 130 titles by hand,
copied from real job postings (mostly Gupy, plus LinkedIn, Vagas.com and other
boards), with the source of each in [`eval/heldout_sources.csv`](../eval/heldout_sources.csv).
None of them is in `taxonomy.py`, and 16 are outside the taxonomy, where the right
answer is to abstain. The labels were committed before the first run, and the
prompt was not changed afterwards.

| Metric (114 titles inside the taxonomy, 16 outside) | Rules (keywords + CBO) | LLM titles |
|---|---|---|
| Right family | 63.2 % | **97.4 %** |
| Right family, when it answers | 98.6 % | 99.1 % |
| Right family and level | 51.8 % | **86.8 %** |
| Abstained (sent to human review) | 36.0 % | 1.8 % |
| Wrong family (silent error) | 0.9 % | 0.9 % |
| Outside titles correctly left unmapped | 13 / 16 | 14 / 16 |

Rules almost never pick a wrong family, but they leave more than a third of real
titles unmapped; the LLM maps nearly all of them. Its family errors are a data
scientist post focused on web development (mapped to software engineer), a product
marketing manager mapped to product manager, and a forklift operator mapped to
production operator. 12 of its 17 errors are levels: 5 are ranges such as
`Pleno/Sênior`, where my labels take the first level cited and the model took the
higher one, and 4 involve Roman numerals. One run of `gemini-3.5-flash-lite`:
4 calls, no 429s, 15 s. Reports: [rules](../reports/titles_heldout_rules_cbo.md),
[LLM](../reports/titles_heldout_llm_gemini-3.5-flash-lite.md).

### Official Brazilian occupation titles (CBO)

Keyword rules only know the spellings they were written with. The official
Brazilian classification of occupations (CBO 2002, Ministério do Trabalho e
Emprego) lists 2,725 occupations and 7,870 synonyms. I picked the CBO codes that
belong to each family: 64 codes, reviewed by hand. Data analyst and product
manager have none: the CBO's "gerente de produtos" is a marketing manager.
[`scripts/build_cbo_titles.py`](../scripts/build_cbo_titles.py) turns their titles and
synonyms into 276 phrases ([`cbo_titles.py`](../src/payroll_sentinel/cbo_titles.py)).
A title the keywords miss is looked up there, longest phrase first; the level
still comes from the title. This is part of the default rules since v1.1
(`--no-cbo` gives the keyword rules alone, as in v1.0).

| Metric | Keywords only (v1.0) | Keywords + CBO (default) |
|---|---|---|
| Held-out titles: right family (114 inside the taxonomy) | 61.4 % | 63.2 % |
| Held-out titles: wrong family | 0.9 % | 0.9 % |
| Held-out titles outside the taxonomy left unmapped | 13 / 16 | 13 / 16 |
| Synthetic long-tail titles: right family (seed 42) | 4 % | 7.7 % |
| Synthetic F1 (seed 42, v1.1 data) | 0.831 | 0.835 |

The CBO helps where companies write official Portuguese titles: it recovered
`Supervisor de Manutenção Industrial` and `Estagiário de Customer Success
Manager`, and it never mapped a title outside the taxonomy. It does not help with
English and tech jargon (`SWE`, `Account Executive`, `Analista de BI`), which is
where the long tail is. On seeds 7 and 123, F1 moves from 0.848 to 0.851 and from
0.865 to 0.862: within noise either way. On the three public files the share of titled rows did not change,
since their titles are in English or Italian. The gain is small, but it never
added a wrong family, so the CBO became part of the default rules in v1.1; the LLM
remains the main lever. Reports: held-out
[keywords + CBO](../reports/titles_heldout_rules_cbo.md) and
[keywords only](../reports/titles_heldout_rules.md); synthetic
[keywords + CBO](../reports/evaluation.md) and
[keywords only](../reports/evaluation_keywords_only.md).

### Comparing models

Each model ran once, on free tiers, through the same two tests: the full pipeline
(seed 42, `run --llm --no-cache`, 36 batches of 40 titles) and the 130 held-out
titles (`eval-titles --llm`, 4 batches). The pipeline runs used the v1.0 synthetic
data, the rules row too. The title columns do not depend on salaries; detection F1
does. With v1.1 data and the same cached answers, `gemini-3.5-flash-lite` scores
0.865 and the rules 0.835 ([Results](#results)); the other two models ran without
a cache, so their F1 was not recomputed. These pipeline reports also predate the
two-way cause diagnosis, which changes only their cause and company tables.

| Model (provider) | Long-tail family (synthetic, 1,109 rows) | Held-out family (114 real titles) | Wrong family on held-out (false mappings, of 16 outside) | Detection F1 | Titles answered by the LLM | 429 responses | Total time (pipeline titles) | Cost |
|---|---|---|---|---|---|---|---|---|
| **`gemini-3.5-flash-lite`** (Gemini) | **99.5 %** | 97.4 % | 0.9 % (2) | **0.963** | 100 % | 0 | **160 s** | R$ 0 |
| `gemini-3.5-flash` (Gemini) | 83.5 % | **99.1 %** | 0.9 % (0) | 0.954 | 75.5 % | 43 | 1,069 s | R$ 0 |
| `openai/gpt-oss-20b` (Groq, `reasoning_effort=low`) | 52.1 % | 87.7 % | 2.6 % (2) | 0.921 | 100 % | 39 | 497 s | R$ 0 |
| Rules: keywords + CBO (no LLM) | 7.7 % | 63.2 % | 0.9 % (3) | 0.92 | – | – | no API calls | R$ 0 |

**Default: `gemini-3.5-flash-lite`.** It is the only model that answered every
title at pipeline volume without a single 429, and it has the best long-tail
accuracy, the best F1 and the shortest time. `gemini-3.5-flash` is better on real
titles, but the free tier cannot sustain it for a 36-call run, and Groq's
`gpt-oss-20b` abstains too often to beat the offline rules on F1.

* **`gemini-3.5-flash` is limited by the free tier, not by the model.** On the
  held-out titles (4 calls, no 429s) it was the most accurate model and never
  forced an outside title into a family. In the pipeline, 43 rate-limit responses
  made 9 of the 36 batches fall back to the v1.0 keyword rules, which is why its long-tail score
  drops; it also waited 18.6 s per request on the held-out run.
* **`gpt-oss-20b` answers fast but abstains.** It waited only 1.7 s per request;
  the 497 s are back-off for Groq's 8,000 tokens-per-minute free limit. It left
  47.9 % of long-tail titles and 3.5 % of common ones unmapped. Because an LLM
  answer replaces the rule answer, it does worse than rules on common titles
  (96.5 % vs 100 %), and only 71 of the 81 statistical errors stay visible.
  False alarms nearly double: 18 clean rows flagged instead of 10 (0.42 % vs 0.23 %).
* **Single runs vary.** An earlier run of `gemini-3.5-flash-lite` on the same seed
  mapped 96.5 % of long-tail titles instead of 99.5 %, and its report fed the demo
  until v1.1. Treat differences of a few points between single runs as noise.
* A local Ollama model was not measured: it needs an NVIDIA GPU, and the
  development machine has none.

Reports: pipeline runs in [`reports/models/`](../reports/models/); held-out runs in
[flash-lite](../reports/titles_heldout_llm_gemini-3.5-flash-lite.md),
[flash](../reports/titles_heldout_llm_gemini-3.5-flash.md) and
[gpt-oss-20b](../reports/titles_heldout_llm_openai-gpt-oss-20b.md).

### Questions over the benchmark

I wrote 30 questions in Portuguese, the way an HR client would ask them
([`eval/questions.csv`](../eval/questions.csv)). 25 are in scope, and 3 of those
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
[`reports/ask_eval_gemini_gemini-3.5-flash-lite.md`](../reports/ask_eval_gemini_gemini-3.5-flash-lite.md).
These results do not depend on the salaries (two errors are refusals, the third
groups by family), so the v1.1 recalibration leaves them as they are.

### Public salary data (no ground truth)

Synthetic data only tests the errors I planted, so I also ran the pipeline on
three public salary files. They are not in the repository, and
[`scripts/public_data_check.py`](../scripts/public_data_check.py) takes their paths:

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
[`reports/public_data_gemini_gemini-3.5-flash-lite.md`](../reports/public_data_gemini_gemini-3.5-flash-lite.md).
It used the v1.0 keyword rules. With the CBO in the default rules, one US-style
row of 6,702 changes (`Customer Success Manager` now maps to support), and every
rule share below stays the same at one decimal.

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

The generator's salaries are made up, so I checked them against two real sources,
and in v1.1 fitted the generator to one of them.

**State of Data Brazil.** A 2025-2026 survey of Brazilian data professionals by
Data Hackers and Bain (Kaggle; not in the repository).
[`scripts/state_of_data_check.py`](../scripts/state_of_data_check.py) reads only six
columns: work status, manager flag, job, level, salary band and state. It never
reads age, gender or race. It keeps CLT employees who are not managers, the closest
match to a payroll file (1,037 answers). Salaries come in bands, so the survey
medians are grouped-data medians, interpolated inside the band that holds the
middle answer. The survey was not used for fitting, so it stays an independent
check.

| Brazil, monthly median (v1.1) | Junior | Mid | Senior | Lead (specialist/staff) |
|---|---|---|---|---|
| Data analyst, survey | R$ 4,200 | R$ 6,457 | R$ 9,563 | R$ 13,100 |
| Data analyst, synthetic | R$ 4,130 | R$ 6,775 | R$ 9,455 | R$ 12,775 |
| Data scientist, survey | R$ 6,875 | R$ 9,241 | R$ 14,714 | R$ 17,059 |
| Data scientist, synthetic | R$ 6,330 | R$ 9,225 | R$ 13,210 | R$ 18,075 |

For the two data families, synthetic medians are within 11 % of the survey
nationwide at every level, and the level steps are close: a senior data analyst
earns 1.48× the mid-level median in the survey and 1.40× in the synthetic data.
São Paulo, where the generator sets its base salaries, is less close: synthetic
medians run up to 28 % high, for mid-level data analysts. A data survey is a poor
sample of other roles. It has fewer than 15 product managers per level, and only
18 mid-level and 24 senior software engineers: their medians match the synthetic
data at senior level, while the synthetic mid level is 47 % higher. The survey also
had one malformed answer of its own: a salary band "from R$ 25,001 to R$ 3,000".
Report: [`reports/realism_state_of_data.md`](../reports/realism_state_of_data.md).

**RAIS.** RAIS is Brazil's official record of every formal job, published without
names or IDs. [`scripts/rais_check.py`](../scripts/rais_check.py) reads the 2025 São
Paulo file (25.5 million rows) as a stream from the `.7z` archive in under
3 minutes. It uses seven columns (occupation, municipality, active on 31 December,
hours, contract type, intermittent flag, December pay) and never age, sex, race,
nationality, disability or schooling. It keeps full-time CLT jobs in the CBO codes
approved for each family, in São Paulo, Campinas and Sorocaba: 509,542 jobs (36,904
more had no December pay). RAIS has no seniority level, so both sides pool every
level, and RAIS pay includes overtime and commissions while the synthetic salary is
base pay.

Compared with RAIS, v1.0 showed three gaps. Real pay is far more spread out
(log-pay SD 0.54 to 0.84, against about 0.40). One index per city cannot say that
factory jobs pay more outside São Paulo while office jobs pay less. And the sales
and support families pool jobs with very different pay. Two definitions settled the
last point. Sales is compared only on its B2B codes (wholesale, technical sales and
sales representatives): retail sellers (67 % of the CBO sales jobs, median
R$ 2,713) and sales managers (R$ 17,000) are not what the synthetic sales family
models, so they stay in the title lookup but leave the comparison, which keeps
361,437 jobs. Support keeps all its codes, IT support (R$ 5,000), contact centre
(R$ 2,077 to R$ 2,937) and customer success, because the synthetic titles cover all
three.

[`scripts/calibrate_generator.py`](../scripts/calibrate_generator.py) then fits three
things, and nothing else:

* **the spread** of each family (`pay_sigma`), so that the synthetic log-pay SD in
  São Paulo equals the real one. Data analyst and product manager have no CBO code
  and take the median of the office families. Interns keep the v1.0 spread: an
  internship is not a CLT job, so RAIS has none;
* **the city index by kind of job**, from the same occupation's pay in each city.
  Factory jobs pay 11 % more in Campinas and 14 % more in Sorocaba than in São
  Paulo, and office jobs 6 % and 20 % less. The other seven cities keep their v1.0
  index, because the RAIS file covers São Paulo state only;
* **the base salary of sales and support**, the two families whose definitions
  changed.

Medians and spreads are fitted in São Paulo, where the generator sets its base
salaries. Pooling the three cities would mix in each side's city mix: RAIS is
mostly São Paulo (73 to 92 % of the jobs, by family), while the generator spreads
rows evenly across cities.

| São Paulo | Real median | Synthetic median, v1.0 → v1.1 | Real log-pay SD | Synthetic log-pay SD, v1.0 → v1.1 |
|---|---|---|---|---|
| Software engineer | R$ 10,268 | R$ 10,830 → R$ 10,795 | 0.66 | 0.42 → 0.67 |
| Data scientist | R$ 12,719 | R$ 10,530 → R$ 11,350 | 0.58 | 0.41 → 0.57 |
| Financial analyst | R$ 6,690 | R$ 6,920 → R$ 7,220 | 0.57 | 0.44 → 0.57 |
| HR analyst | R$ 5,272 | R$ 5,770 → R$ 6,020 | 0.54 | 0.38 → 0.54 |
| Sales rep (B2B codes) | R$ 4,758 | R$ 6,450 → R$ 4,750 | 0.80 | 0.42 → 0.80 |
| Maintenance technician | R$ 4,576 | R$ 4,410 → R$ 4,700 | 0.60 | 0.38 → 0.60 |
| Customer support | R$ 3,809 | R$ 3,450 → R$ 3,825 | 0.72 | 0.41 → 0.72 |
| Production operator | R$ 2,474 | R$ 2,540 → R$ 2,540 | 0.39 | 0.37 → 0.39 |

* **In São Paulo the spread matches by construction**, since that is what the fit
  does. Medians that were not fitted moved by 8 % or less; the largest gaps left are
  HR analysts, 14 % high, and data scientists, 11 % low. Quartiles agree within
  21 %; the largest gap is the first quartile of support (R$ 2,000 against
  R$ 2,519).
* **Outside São Paulo the comparison is still a check.** Factory families now land
  within 8 % of real pay in Campinas and Sorocaba (v1.0: 21 to 27 % low). Office
  families still range from 0.73 (support) to 1.26 (financial analysts) of real
  pay, leaving aside 71 data scientists in Campinas: one index per kind of job
  cannot say that support pays more outside the capital while finance pays less.
* **The fit leans pessimistic.** RAIS December pay includes overtime and
  commissions, which widen the real spread (most of all in sales) beyond what base
  pay alone would show, and the generator puts all the spread its levels do not
  explain inside the peer group.

What this does to detection is in
[Results](#what-a-realistic-pay-spread-does-to-detection). Report:
[`reports/realism_rais.md`](../reports/realism_rais.md); the fitted targets are in
[`reports/realism_rais.json`](../reports/realism_rais.json).

## What I learned

1. **Titles were the first bottleneck.** Keyword rules map 100 % of common titles
   but only 4 % of long-tail ones (`SWE`, `HRBP`, `Account Executive`), and the
   official CBO titles raise that only to 7.7 %. That leaves 23 % of rows with no
   peer group, hiding 18 of the 81 statistical errors. An LLM normalizer closed
   that gap at zero cost: its recall equals the recall with perfect titles. With
   the v1.0 pay spread that lifted recall from 0.88 to 0.97; with the RAIS spread,
   from 0.785 to 0.822, because the detection floor (lesson 5) now hides most of
   what is left.
2. **The LLM fails safe here.** It got 6 of 4,484 titled rows wrong in the run
   behind these numbers (39 in an earlier run), and every one was an abstention ("no family"), never a wrong family: an unmapped row is
   only left out of the peer comparison, while a wrong family would compare it
   against the wrong peers. I did not tune the prompt on these misses: tuning the
   prompt on the errors of the evaluation set would inflate the very number I am
   reporting.
3. **Rules should go first.** Seven of the nine error types reach 100 % recall
   with plain rules, at zero cost and with an explanation anyone can read.
4. **The majority vote buys precision.** Isolation Forest is weak on a
   one-dimensional problem like this one (F1 0.27), but as a third vote it lets two
   detectors overrule one: the vote is the most precise detector (0.56, against
   0.42 for the robust z-score and 0.47 for the IQR fence, rules run). I kept all
   three in the report because a weak detector is a finding too.
5. **There is a detection floor, and real pay spread sets it.** A level mismatch
   (the salary of another level, about 2.4 to 3.3 times off) is a big error, but
   inside a peer group whose log pay spreads like RAIS (SD 0.50) it looks like a
   normal salary: with LLM titles, 4 of 45 are caught, against 37 of 45 with the
   v1.0 spread (0.21). Catching them would need richer context, such as the
   company's own pay bands, not a better outlier detector.
6. **On a free tier, the limit picks the model.** The most accurate model on real
   titles could not finish a full run without rate limits, and a weaker model
   scored below plain rules on titles the rules already knew. A model is only as
   good as the share of the job it can do inside the quota.
7. **Real data finds the errors you did not plant.** The synthetic set measured
   the errors I imagined. Public files showed three I had not: monthly
   salaries in an annual field, legitimate top pay that looked like a typo, and
   rows copied under new IDs. Each fix was measured on the synthetic set first,
   so it could not quietly break what already worked.
8. **A synthetic benchmark is only as honest as its noise.** v1.0 reported recall
   0.97 on salaries whose spread I made up. Fitting the spread to 361,437 real job
   records cut it to 0.82 without changing a line of the validator. The fitted
   number is the one to defend; the v1.0 one is a ceiling.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m payroll_sentinel.cli run                     # generate + validate + evaluate (free, offline)
pytest                                                 # 104 tests (7 skip without the [ui] extra)
python -m payroll_sentinel.cli validate my_payroll.csv # your own file (same columns as data/submissions.csv)
python -m payroll_sentinel.cli eval-titles eval/heldout_titles.csv  # [--llm | --no-cbo] titles not in taxonomy.py
python -m payroll_sentinel.cli run --no-cbo            # keyword rules only, without the CBO titles (v1.0)
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
and opens the browser. The UI is in Portuguese, for Brazilian companies:

* **Validar minha folha** (validate my payroll): upload a CSV or Excel file, or use
  the sample. Column names such as *Matrícula*, *Cargo* or *Salário* are recognized
  and can be changed by hand, and Brazilian values (`R$ 8.500,00`, `25/03/2020`,
  `Estágio`) are read as such ([`upload.py`](../src/payroll_sentinel/upload.py)). The
  file is compared with reference peers ([above](#validating-one-companys-file)),
  titles the rules do not know can be given a family, and the result says what to
  accept, review and block, with the reason and what to do, plus an Excel report
  and the two CSV files to send back.
* **Como medimos** (how it is measured): the evaluation on synthetic data, with the
  same metrics as `reports/evaluation.md`.

Adding `?exemplo` to the URL opens the app with the sample payroll already validated,
a one-click demo link (https://payroll-sentinel.streamlit.app/?exemplo).
* **Resultados com LLM**: the saved LLM report.
* **Perguntar ao benchmark**: questions in Portuguese or English, answered as above
  (needs an LLM key).

Uploads are processed in memory for the session only (no `st.cache_data`, no file
written) and always with the offline rules, never an LLM. Files are capped at 5 MB
(`.streamlit/config.toml`) and 20,000 rows.

With `--server.address localhost` (also used by `run_ui.bat`) only this computer
can open the app. Streamlit's usage statistics are off (`.streamlit/config.toml`).

**Public demo mode.** Set `DEMO_MODE=1` as an environment variable or as a
root-level key in Streamlit secrets. The LLM option and the question tab disappear,
runs are capped at 50 companies, and the **Resultados com LLM** tab shows the saved
report `reports/evaluation_llm_gemini-3.5-flash-lite.md` instead of calling an LLM.
Uploads stay on, with the limits above: payroll is personal data, so the page asks
for files without names or CPF (the required columns need neither). This is how
the app runs on Streamlit Community Cloud, which installs it from
`requirements.txt`.

**In the browser, on Hugging Face.** The same `app.py` also runs as a static
[Hugging Face Space](https://huggingface.co/spaces/Danielrtm1/payroll-sentinel) with [stlite](https://github.com/whitphx/stlite)
(Streamlit 1.65 on Pyodide, Python compiled to WebAssembly), so an uploaded payroll
never leaves the visitor's computer. Docker and Gradio Spaces need a paid plan, and
static Spaces are free. The Space holds two files,
[`deploy/huggingface/`](../deploy/huggingface/): a README with the Space settings and
an `index.html` that fetches the app, the package, the Streamlit config and the LLM
report from one pinned commit of this repository. Demo mode comes from a virtual
`.streamlit/secrets.toml`. Measured on the live Space: the first load takes about
80-90 s (Pyodide, pandas and scikit-learn are downloaded), and the sample payroll
validates in 10 s, against about 1 s on a server. While Python computes, the page
does not update, because Python and the page share one browser worker.

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
  taxonomy.py   job families, levels, cities (index by kind of job), pay parameters, minimum-wage rule
                (minimum wage and full week by date, from salary_core/params)
  generate.py   synthetic submissions + planted errors + ground truth
  normalize.py  keyword + CBO rules and LLM normalizer (batching, cache, validation)
  cbo_titles.py official CBO 2002 titles and synonyms per family (generated, do not edit)
  llm.py        small OpenAI-compatible client (Gemini / Groq / Ollama), with run stats
  validate.py   rules, peer-comparison ensemble, cause diagnosis, company decision
  evaluate.py   precision/recall per error type and per detector, title accuracy
  pipeline.py   the pipeline as plain functions, shared by the CLI and the web UI
  upload.py     reads company files as they come (CSV/Excel, Brazilian formats) and maps columns
  titles_eval.py  held-out title evaluation (abstention vs. wrong family)
  ask.py        questions over the benchmark: checked JSON query, pandas execution, evaluation
  cli.py        run, validate, eval-titles, ask, eval-ask and models commands
eval/           hand-written ground truth: held-out titles and questions
scripts/        public_data_check.py: titles and full validation on public salary files
                build_cbo_titles.py: rebuilds cbo_titles.py from the CBO tables (codes per family)
                state_of_data_check.py: synthetic salaries vs. the State of Data Brazil survey
                rais_check.py: synthetic salaries vs. RAIS official job records (streamed from .7z)
                calibrate_generator.py: fits the generator's pay spread, city index and two medians to RAIS
                reference_check.py: one company's file validated alone vs. with reference peers
app.py          Streamlit web UI (`streamlit run app.py`, or run_ui.bat on Windows)
tests/          rules, normalizers, LLM parsing/caching (with a fake client), end-to-end quality, UI smoke test
```

## Limitations and next steps

* The data is synthetic. Level markers follow regular patterns, so level accuracy
  is 100 % here; on the 114 real held-out titles, LLM level accuracy is 89.5 %.
  Pay spread is fitted to RAIS in São Paulo, but RAIS has no level, so how much of
  the real spread sits inside a peer group is an assumption (v1.1 puts all of it
  there). Seven cities keep an index no real data checked, and every family shares
  the same level steps.
* The synthetic long-tail titles come from a fixed list of abbreviations and
  English titles (`SWE`, `HRBP`), which a large model has likely seen before.
  The 99.5 % long-tail accuracy is measured on that list. The real-title check
  (97.4 % family accuracy) uses only 130 titles, labeled by one person.
* Each model in the comparison ran once, on one seed. A local Ollama model is
  still unmeasured, because it needs an NVIDIA GPU.
* The question evaluation is 30 questions written by one person, run once. Answers
  use full-time-equivalent salaries, so an intern's 30 h stipend is shown scaled
  to 44 h (about 1.47×).
* The cut-off is fixed at 2026-10-31. Moving it past 2026-12-16 also needs a
  generator that stops drawing 44 h contracts (the normal week is 42 h by then),
  and moving it into 2027 needs a `2027.json` with the 2027 minimum wage, not
  published yet. EC 141 (art. 5) lets a complementary law give micro and small
  companies a transition; the validator does not know company size.

## License

[MIT](../LICENSE)
