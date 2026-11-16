# One company's file: alone vs. with reference peers

Seed 7, 25 companies, each validated on its own with the offline rules. Reference peers: the clean rows of generate(seed=42, n_companies=25), as in the web UI. Unrecognized-title warnings are not counted as detections.

## Overall

| mode                 |   caught |   planted |   recall | false alarms on clean rows   |
|:---------------------|---------:|----------:|---------:|:-----------------------------|
| alone                |      152 |       218 |    0.697 | 0.21%                        |
| with reference peers |      172 |       218 |    0.789 | 0.39%                        |

## Planted errors caught, by type

| error_type            |   planted |   alone |   with reference peers |
|:----------------------|----------:|--------:|-----------------------:|
| annual_as_monthly     |        33 |       4 |                     22 |
| below_min_wage        |        24 |      24 |                     24 |
| bonus_outlier         |        24 |      24 |                     24 |
| decimal_shift         |        24 |      24 |                     24 |
| duplicate_id          |        24 |      24 |                     24 |
| future_hire_date      |        16 |      16 |                     16 |
| level_salary_mismatch |        41 |       4 |                      6 |
| missing_salary        |        16 |      16 |                     16 |
| missing_title         |        16 |      16 |                     16 |
