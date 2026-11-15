# Evaluation report

4502 records from 25 companies; 242 planted errors. Title normalizer: **LLM (gemini-3.5-flash)**.

## 1. Title normalization

| subset           |   rows |   family_acc |   level_acc |   both_acc |   unmapped |
|:-----------------|-------:|-------------:|------------:|-----------:|-----------:|
| all              |   4484 |        0.959 |           1 |      0.959 |      0.041 |
| common titles    |   3375 |        1     |           1 |      1     |      0     |
| long-tail titles |   1109 |        0.835 |           1 |      0.835 |      0.165 |

Titles answered by the LLM: 75.5% (the rest fell back to keyword rules).

LLM run: 27 LLM calls (70 HTTP requests, 43 rate-limit (429) responses), 1068.8 s in LLM calls, 39.6 s per call; 318.4 s waiting for the API (4.5 s per request), the rest is pacing and retry back-off; title normalization took 1069.0 s in total.

## 2. Error detection (any flag on an errored row)

Overall: precision **0.962**, recall **0.946**, F1 **0.954**. False alarms on clean rows: 0.21%.

| error_type            |   planted |   detected |   recall |   correct_cause |   cause_accuracy |
|:----------------------|----------:|-----------:|---------:|----------------:|-----------------:|
| annual_as_monthly     |        36 |         33 |    0.917 |              32 |            0.97  |
| below_min_wage        |        27 |         27 |    1     |              27 |            1     |
| bonus_outlier         |        27 |         27 |    1     |              27 |            1     |
| decimal_shift         |        27 |         27 |    1     |              27 |            1     |
| duplicate_id          |        26 |         26 |    1     |              26 |            1     |
| future_hire_date      |        18 |         18 |    1     |              18 |            1     |
| level_salary_mismatch |        45 |         35 |    0.778 |              34 |            0.971 |
| missing_salary        |        18 |         18 |    1     |              18 |            1     |
| missing_title         |        18 |         18 |    1     |              18 |            1     |

## 3. Statistical detectors (annual-as-monthly + level mismatch)

Rows the peer comparison could see: 77/81 of the planted statistical errors (rows with unmapped titles are excluded).

|               |   precision |   recall |    f1 |   tp |   fp |   fn |   flagged |
|:--------------|------------:|---------:|------:|-----:|-----:|-----:|----------:|
| vote_z        |       0.882 |    0.87  | 0.876 |   67 |    9 |   10 |       101 |
| vote_iqr      |       0.708 |    0.974 | 0.82  |   75 |   31 |    2 |       134 |
| vote_iforest  |       0.471 |    0.519 | 0.494 |   40 |   45 |   37 |       127 |
| flag_ensemble |       0.883 |    0.883 | 0.883 |   68 |    9 |    9 |       102 |

## 4. How much do titles matter?

Same validator, but with perfect (oracle) titles:

- Overall recall: 0.946 with LLM (gemini-3.5-flash) vs 0.967 with oracle titles
- Statistical errors visible: 77/81 vs 81/81
- Ensemble F1: 0.883 vs 0.89

## 5. Company decisions

| company_id   |   rows |   blocked |   warnings |   blocked_share | decision                         |
|:-------------|-------:|----------:|-----------:|----------------:|:---------------------------------|
| EMP006       |     84 |         8 |          1 |      0.0952381  | REJECT - ask company to resubmit |
| EMP016       |    168 |        14 |          5 |      0.0833333  | REJECT - ask company to resubmit |
| EMP010       |    101 |         6 |          5 |      0.0594059  | REJECT - ask company to resubmit |
| EMP018       |    243 |        13 |          7 |      0.0534979  | REJECT - ask company to resubmit |
| EMP011       |    224 |        11 |         11 |      0.0491071  | ACCEPT without blocked rows      |
| EMP025       |    227 |        11 |         17 |      0.0484581  | ACCEPT without blocked rows      |
| EMP022       |    169 |         8 |         10 |      0.0473373  | ACCEPT without blocked rows      |
| EMP005       |     85 |         4 |          4 |      0.0470588  | ACCEPT without blocked rows      |
| EMP019       |    133 |         6 |          3 |      0.0451128  | ACCEPT without blocked rows      |
| EMP015       |    200 |         9 |         10 |      0.045      | ACCEPT without blocked rows      |
| EMP001       |    214 |         9 |          7 |      0.0420561  | ACCEPT without blocked rows      |
| EMP020       |    122 |         5 |          5 |      0.0409836  | ACCEPT without blocked rows      |
| EMP023       |    256 |        10 |         16 |      0.0390625  | ACCEPT without blocked rows      |
| EMP021       |    257 |        10 |         20 |      0.0389105  | ACCEPT without blocked rows      |
| EMP012       |    252 |         9 |         12 |      0.0357143  | ACCEPT without blocked rows      |
| EMP002       |    177 |         6 |         18 |      0.0338983  | ACCEPT without blocked rows      |
| EMP003       |    133 |         4 |         13 |      0.0300752  | ACCEPT without blocked rows      |
| EMP009       |    107 |         3 |         12 |      0.0280374  | ACCEPT without blocked rows      |
| EMP014       |    233 |         6 |         10 |      0.0257511  | ACCEPT without blocked rows      |
| EMP008       |    130 |         3 |          7 |      0.0230769  | ACCEPT without blocked rows      |
| EMP024       |    194 |         4 |         11 |      0.0206186  | ACCEPT without blocked rows      |
| EMP007       |    258 |         5 |         15 |      0.0193798  | ACCEPT without blocked rows      |
| EMP004       |    159 |         1 |          8 |      0.00628931 | ACCEPT without blocked rows      |
| EMP013       |    162 |         1 |          9 |      0.00617284 | ACCEPT without blocked rows      |
| EMP017       |    214 |         0 |         16 |      0          | ACCEPT                           |