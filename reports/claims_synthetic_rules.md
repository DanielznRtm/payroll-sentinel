# Claim extraction: keyword rules

Petitions: 60 (synthetic, seed 7; template text, easier than real petitions). Time: 0.1 s.

## Money

- Priced total equal to the truth's: 48/60 (80.0 %)
- Sum of the differences: R$ 62,800.01

## Claims found

Overall: precision 87.6 %, recall 100.0 % (276 right, 39 invented, 0 missed).

| Claim | Right | Invented | Missed | Precision | Recall |
|---|---|---|---|---|---|
| overtime | 38 | 8 | 0 | 82.6 % | 100.0 % |
| unpaid_fgts | 40 | 7 | 0 | 85.1 % | 100.0 % |
| fgts_fine | 32 | 0 | 0 | 100.0 % | 100.0 % |
| notice_pay | 31 | 7 | 0 | 81.6 % | 100.0 % |
| thirteenth | 40 | 7 | 0 | 85.1 % | 100.0 % |
| vacation | 34 | 10 | 0 | 77.3 % | 100.0 % |
| late_severance_fine | 33 | 0 | 0 | 100.0 % | 100.0 % |
| other | 28 | 0 | 0 | 100.0 % | 100.0 % |

## Facts

A missing value goes to a person; a wrong one would be priced.

| Fact | Right | Missing | Wrong |
|---|---|---|---|
| admission_date | 60 | 0 | 0 |
| termination_date | 60 | 0 | 0 |
| termination_type | 60 | 0 | 0 |
| monthly_salary | 60 | 0 | 0 |
| weekly_hours | 60 | 0 | 0 |
| filing_date | 60 | 0 | 0 |

Claim details (overtime hours, months without FGTS): 78/78 right.

## Checks

0 petitions had something dropped by the checks (0 items): a date or number not written in the petition, a quote not copied from it, or an unknown claim.

## Every error

- P002: invented claim: overtime
- P007: invented claim: thirteenth
- P007: priced total R$ 22012.67 (truth R$ 17596.00)
- P008: invented claim: overtime
- P011: invented claim: thirteenth
- P011: invented claim: vacation
- P011: priced total R$ 68770.06 (truth R$ 61096.45)
- P012: invented claim: thirteenth
- P012: invented claim: vacation
- P012: priced total R$ 17336.98 (truth R$ 11134.20)
- P013: invented claim: overtime
- P013: invented claim: unpaid_fgts
- P015: invented claim: vacation
- P018: invented claim: notice_pay
- P020: invented claim: notice_pay
- P021: invented claim: thirteenth
- P021: priced total R$ 82601.66 (truth R$ 81393.33)
- P022: invented claim: thirteenth
- P022: invented claim: vacation
- P022: priced total R$ 206892.67 (truth R$ 202526.00)
- P023: invented claim: vacation
- P023: priced total R$ 59067.17 (truth R$ 50500.50)
- P024: invented claim: unpaid_fgts
- P027: invented claim: unpaid_fgts
- P028: invented claim: notice_pay
- P028: invented claim: unpaid_fgts
- P029: invented claim: notice_pay
- P031: invented claim: notice_pay
- P032: invented claim: overtime
- P032: invented claim: thirteenth
- P032: priced total R$ 15418.17 (truth R$ 14430.67)
- P037: invented claim: vacation
- P037: priced total R$ 11293.95 (truth R$ 11043.95)
- P038: invented claim: unpaid_fgts
- P038: invented claim: vacation
- P038: priced total R$ 140613.75 (truth R$ 127563.75)
- P041: invented claim: overtime
- P041: invented claim: unpaid_fgts
- P041: invented claim: vacation
- P041: priced total R$ 5881.94 (truth R$ 3437.50)
- P044: invented claim: vacation
- P044: priced total R$ 39495.90 (truth R$ 37229.23)
- P046: invented claim: overtime
- P052: invented claim: overtime
- P054: invented claim: thirteenth
- P058: invented claim: notice_pay
- P059: invented claim: notice_pay
- P060: invented claim: overtime
- P060: invented claim: unpaid_fgts
- P060: invented claim: vacation
- P060: priced total R$ 32942.67 (truth R$ 21576.00)
