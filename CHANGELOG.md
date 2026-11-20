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
- **One-click demo link**: `?exemplo` opens the app with the sample payroll
  validated. The README now opens with that link, real screenshots
  (`docs/img/`), a summary of what the project demonstrates and a Mermaid
  architecture diagram.
- **Module B started: `salary_core`.** A deterministic monthly net-pay engine for
  CLT, Simples Nacional contractor (PJ) and internship, in its own package with
  only the standard library. The 2026 tax parameters live in
  `src/salary_core/params/2026.json`, with an official source for every block.
  43 tests: the five Receita Federal worked examples for Lei 15.270/2025 pass as
  published; reference case R$ 6,000 CLT -> INSS R$ 641.51, IRRF R$ 385.10.
- **Labor-claim triage.** `triage FILE [--llm]` reads a petition, finds what it
  asks for and prices seven claims with `salary_core/labor.py` (notice, 13th,
  vacation, overtime, unpaid FGTS, 40 % FGTS fine, CLT art. 477 fine), applying
  limitation periods and the rules for each way a contract ends. The extractor,
  rules or LLM, only fills a fixed JSON; any date, number or quote not written in
  the petition is dropped. On 60 synthetic petitions the priced total matches the
  truth in 48/60 with keyword rules and 59/60 with `gemini-3.5-flash-lite`
  (`reports/claims_synthetic_*.md`). Hand-written petitions for the real test go
  in `eval/heldout_petitions/`. Overtime after 2026-10-15 is left to a person
  because EC 141/2026 changed weekly hours and rest days.
- **Minimum wage follows EC 141/2026.** The prorated minimum uses the full normal
  week of the cut-off date: 44 h, then 42 h from 2026-12-16 (TST OJ 358 read with
  the amended limit), so a 42 h contract owes the whole R$ 1,621 from that date.
  The minimum wage and the steps of the week now come from
  `salary_core/params/2026.json` with their sources; a year without a file is
  refused. The 2026-10-31 cut-off is before the change: `reports/evaluation.md` is
  identical. As of 2026-12-16 the same data would block 14 more clean rows (40 h
  and 30 h contracts paid less than 4.8 % above the old proportion), and all
  27 planted errors are still caught. The Hugging Face Space now also loads
  `salary_core`.

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
