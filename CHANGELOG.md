# Changelog

## Unreleased

- **Web UI for companies, in Portuguese.** The main tab takes a company's payroll
  as it comes: CSV (comma or semicolon) or Excel, columns recognized by common
  names and editable, Brazilian values (`R$ 8.500,00`, `25/03/2020`, `Estágio`)
  read as such (`upload.py`). The result says what to accept, review and block,
  with the reason and what to do, plus an Excel report and the files to send back.
- **Reference peers for a single file.** One company rarely has 15 peers of the
  same family and level, so an uploaded file is validated together with the clean
  synthetic benchmark (`validate_against_reference`). Measured on seed 7, each
  company on its own: errors caught 69.7 % -> 78.9 % (annual salaries typed as
  monthly 4 -> 22 of 33), false alarms 0.21 % -> 0.39 %. Companies can give a
  family to titles the rules do not know.
- **Uploads on the public demo**, processed in memory for the session only, never
  sent to an LLM, capped at 5 MB and 20,000 rows. New `[ui]` dependency: openpyxl.
- **README in Portuguese and condensed**; the full English write-up moved to
  `docs/technical-report.md`.
- **Faster validation against reference peers**: row rules and title rules run on
  the file only, reference titles are read once (one validation 2.0 s -> about 1 s,
  results unchanged).
- **Static Hugging Face Space** (https://huggingface.co/spaces/Danielrtm1/payroll-sentinel): the same app runs in the visitor's
  browser with stlite, so the payroll never leaves their computer
  (`deploy/huggingface/`). Docker Spaces need a paid plan, so this one is static.
  First load about 80-90 s, sample validation 10 s.

## v1.1.0 (2026-11-15)

The synthetic salaries are now fitted to RAIS 2025 job records. Every synthetic
detection number went down, and the validator did not change.

- **CBO titles in the default rules.** Titles the keywords miss are looked up in
  the official CBO 2002 titles and synonyms (held-out family accuracy 61.4 % ->
  63.2 %, no new wrong family; synthetic F1 within noise: 0.920 both ways on v1.0
  data, 0.831 -> 0.835 on v1.1 data). `--no-cbo` gives the v1.0 keyword rules.
- **Generator fitted to RAIS** (`scripts/calibrate_generator.py`, targets in
  `reports/realism_rais.json`): each family's pay spread fitted in São Paulo (the
  median spread of log pay inside a peer group went from 0.21 to 0.50), a city
  index by kind of job (office or industrial) for Campinas and Sorocaba, and the
  base salary of sales (compared on B2B codes only; retail sellers and sales
  managers stay in the title lookup) and support (all codes). Interns keep the v1.0
  spread. Titles and planted errors are unchanged, so the LLM cache and the ground
  truth stay valid.
- **Measured effect (seed 42):** F1 0.920 -> 0.835 with rules and 0.963 -> 0.865
  with LLM titles; level mismatches caught with LLM titles 37 -> 4 of 45; false
  alarms 0.23 % -> 0.45 %. Factory pay in Campinas and Sorocaba is now within 8 %
  of RAIS (it was 21-27 % low). The question evaluation does not depend on salaries
  and is unchanged.

## v1.0.0 (2026-11-15)

Module A is complete, and every number in the README was checked against a report
in `reports/`.

- **Public demo** on Streamlit Community Cloud, in a demo mode with synthetic
  data only, no upload and no live LLM call; a worked example on top of the README.
- **Held-out titles:** 130 real job titles written by hand, scored with
  `eval-titles` (wrong family kept apart from abstention). LLM family accuracy
  97.4 %, keyword rules 61.4 %.
- **Model comparison:** one LLM cache per provider and model, and run stats
  (calls, 429s, API time apart from pacing). Two Gemini models and Groq's
  `gpt-oss-20b` compared; `gemini-3.5-flash-lite` stays the default. Optional
  `LLM_REASONING_EFFORT` for reasoning models.
- **Questions over the benchmark** (`ask`, `eval-ask`, and a web UI tab): the LLM
  only fills a fixed JSON query that the code checks and runs. 27 of 30
  hand-written questions right, 5 of 5 out-of-scope questions refused.
- **Files for companies:** `validate` writes `accepted_rows.csv` and
  `rows_to_fix.csv` with the company's own columns plus status and reasons.
- **Public data case study** (`scripts/public_data_check.py`) on three public
  salary datasets. It exposed three validator gaps, now fixed and measured with
  no change in synthetic precision or recall: unit errors are diagnosed both
  ways (`divided_by_12`, `extreme_value`), the 6–9× band goes to review instead
  of a block, and rows copied under a new ID get a `duplicate_record` warning.

## v0.2.0 (2026-11-10)

- Streamlit web UI on top of a pipeline module shared with the CLI.
- LLM title normalization (Gemini free tier by default), with measured results:
  recall 0.88 → 0.97.
- Clear failure when the LLM rejects requests; Isolation Forest skipped when no
  peer group is large enough.

## v0.1.0 (2026-11-10)

- Synthetic payroll generator with planted, labeled errors.
- Validator: deterministic rules (required fields, duplicate IDs, dates,
  prorated minimum wage, bonus ratio) and a peer comparison where robust
  z-score, IQR and Isolation Forest vote.
- Evaluation against the planted errors, CLI and tests.
