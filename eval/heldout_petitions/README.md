# Hand-written petitions

The synthetic petitions in `petitions.py` come from templates, so they are easy
for any extractor. The real measurement of claim extraction is on petitions
written here **by hand, by the project author, never by an LLM**: text an LLM
writes is the kind of text an LLM reads best, and the score would lose its
meaning. Nothing in this folder is used to tune the prompt.

## Rules

- Fictitious people, companies and facts only. Never a real petition, real
  names or real case numbers (free-tier LLMs may train on what they receive).
- 10 to 20 petitions, one UTF-8 `.txt` file each (`H01.txt`, `H02.txt`, ...),
  written the way real petitions read.
- `truth.json` holds the expected extraction of each file, keyed by file name.
  It is committed **before** the first run, so the history shows it was not
  adjusted after seeing results.

## truth.json

The same shape the extractor returns (see `src/payroll_sentinel/claims.py`),
without quotes:

```json
{
  "H01.txt": {
    "admission_date": "YYYY-MM-DD or null",
    "termination_date": "YYYY-MM-DD or null",
    "termination_type": "without_cause | resignation | with_cause | unknown",
    "monthly_salary": "6000.00 or null",
    "weekly_hours": "44 or null",
    "filing_date": "YYYY-MM-DD or null",
    "claims": [
      {"type": "overtime", "hours_per_month": "20"},
      {"type": "unpaid_fgts", "months": "8"},
      {"type": "fgts_fine"}, {"type": "notice_pay"}, {"type": "thirteenth"},
      {"type": "vacation"}, {"type": "late_severance_fine"},
      {"type": "other", "label": "short name, no digits"}
    ]
  }
}
```

A claim is a request the petition makes; a right only mentioned as a fact, or
said to be paid, is not one. `hours_per_month` and `months` are left out when the
petition does not state them.

The checks only accept dates and numbers written in the petition (dates like
15/03/2021 or 15 de março de 2021, numbers in digits like 6.000,00). If a value
appears only in words ("seis mil reais"), the safe answer is `null`: the code
sends it to a person instead of trusting a number it cannot find.
`eval-claims --heldout` refuses a `truth.json` that breaks this, and says which
value.

## Run

```bash
python -m payroll_sentinel.cli eval-claims --heldout eval/heldout_petitions          # keyword rules
python -m payroll_sentinel.cli eval-claims --heldout eval/heldout_petitions --llm    # needs LLM_API_KEY
```

Reports go to `reports/claims_heldout_<method>.md`.
