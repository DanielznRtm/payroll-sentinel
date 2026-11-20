# Claim extraction: LLM gemini-3.5-flash-lite

Petitions: 60 (synthetic, seed 7; template text, easier than real petitions). Time: 0.1 s.

LLM calls made in this run (answers already in the cache are reused, not counted): 0 LLM calls (0 HTTP requests, 0 rate-limit (429) responses), 0.0 s in LLM calls, n/a per call; 0.0 s waiting for the API (n/a per request), the rest is pacing and retry back-off.

## Money

- Priced total equal to the truth's: 59/60 (98.3 %)
- Sum of the differences: R$ 10,032.00

## Claims found

Overall: precision 100.0 %, recall 98.2 % (271 right, 0 invented, 5 missed).

| Claim | Right | Invented | Missed | Precision | Recall |
|---|---|---|---|---|---|
| overtime | 37 | 0 | 1 | 100.0 % | 97.4 % |
| unpaid_fgts | 39 | 0 | 1 | 100.0 % | 97.5 % |
| fgts_fine | 31 | 0 | 1 | 100.0 % | 96.9 % |
| notice_pay | 31 | 0 | 0 | 100.0 % | 100.0 % |
| thirteenth | 40 | 0 | 0 | 100.0 % | 100.0 % |
| vacation | 34 | 0 | 0 | 100.0 % | 100.0 % |
| late_severance_fine | 32 | 0 | 1 | 100.0 % | 97.0 % |
| other | 27 | 0 | 1 | 100.0 % | 96.4 % |

## Facts

A missing value goes to a person; a wrong one would be priced.

| Fact | Right | Missing | Wrong |
|---|---|---|---|
| admission_date | 59 | 1 | 0 |
| termination_date | 59 | 1 | 0 |
| termination_type | 59 | 1 | 0 |
| monthly_salary | 59 | 1 | 0 |
| weekly_hours | 59 | 1 | 0 |
| filing_date | 59 | 1 | 0 |

Claim details (overtime hours, months without FGTS): 75/76 right.

## Checks

1 petitions had something dropped by the checks (1 items): a date or number not written in the petition, a quote not copied from it, or an unknown claim.

## Every error

- P004: months None (truth 11)
- P004: priced total R$ 13933.33 (truth R$ 23965.33)
- P015: missed claim: fgts_fine
- P015: missed claim: late_severance_fine
- P015: missed claim: other
- P015: missed claim: overtime
- P015: missed claim: unpaid_fgts
- P015: admission_date missing (truth 2019-11-13)
- P015: termination_date missing (truth 2024-02-07)
- P015: termination_type missing (truth without_cause)
- P015: monthly_salary missing (truth 9950)
- P015: weekly_hours missing (truth 44)
- P015: filing_date missing (truth 2026-08-21)
- P015: dropped by the checks: answer is not a JSON object
