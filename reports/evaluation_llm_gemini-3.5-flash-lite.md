# Evaluation report

4502 records from 25 companies; 242 planted errors. Title normalizer: **LLM (gemini-3.5-flash-lite)**.

## 1. Title normalization

| subset           |   rows |   family_acc |   level_acc |   both_acc |   unmapped |
|:-----------------|-------:|-------------:|------------:|-----------:|-----------:|
| all              |   4484 |        0.999 |           1 |      0.999 |      0.001 |
| common titles    |   3375 |        1     |           1 |      1     |      0     |
| long-tail titles |   1109 |        0.995 |           1 |      0.995 |      0.005 |

Titles answered by the LLM: 100.0% (the rest fell back to the rules).

LLM run: 0 LLM calls (0 HTTP requests, 0 rate-limit (429) responses), 0.0 s in LLM calls, n/a per call; 0.0 s waiting for the API (n/a per request), the rest is pacing and retry back-off; title normalization took 0.3 s in total (every title came from the cache, so this is not a timing measurement).

## 2. Error detection (any flag on an errored row)

Overall: precision **0.913**, recall **0.822**, F1 **0.865**. False alarms on clean rows: 0.45%.

| error_type            |   planted |   detected |   recall |   correct_cause |   cause_accuracy |
|:----------------------|----------:|-----------:|---------:|----------------:|-----------------:|
| annual_as_monthly     |        36 |         34 |    0.944 |              29 |            0.853 |
| below_min_wage        |        27 |         27 |    1     |              27 |            1     |
| bonus_outlier         |        27 |         27 |    1     |              27 |            1     |
| decimal_shift         |        27 |         27 |    1     |              27 |            1     |
| duplicate_id          |        26 |         26 |    1     |              26 |            1     |
| future_hire_date      |        18 |         18 |    1     |              18 |            1     |
| level_salary_mismatch |        45 |          4 |    0.089 |               4 |            1     |
| missing_salary        |        18 |         18 |    1     |              18 |            1     |
| missing_title         |        18 |         18 |    1     |              18 |            1     |

## 3. Statistical detectors (annual-as-monthly + level mismatch)

Rows the peer comparison could see: 81/81 of the planted statistical errors (rows with unmapped titles are excluded).

|               |   precision |   recall |    f1 |   tp |   fp |   fn |   flagged |
|:--------------|------------:|---------:|------:|-----:|-----:|-----:|----------:|
| vote_z        |       0.528 |    0.469 | 0.497 |   38 |   34 |   43 |        79 |
| vote_iqr      |       0.548 |    0.568 | 0.558 |   46 |   38 |   35 |       100 |
| vote_iforest  |       0.287 |    0.333 | 0.309 |   27 |   67 |   54 |       133 |
| flag_ensemble |       0.667 |    0.469 | 0.551 |   38 |   19 |   43 |        66 |

## 4. How much do titles matter?

Same validator, but with perfect (oracle) titles:

- Overall recall: 0.822 with LLM (gemini-3.5-flash-lite) vs 0.822 with oracle titles
- Statistical errors visible: 81/81 vs 81/81
- Ensemble F1: 0.551 vs 0.551

## 5. Company decisions

| company_id   |   rows |   blocked |   warnings |   blocked_share | decision                         |
|:-------------|-------:|----------:|-----------:|----------------:|:---------------------------------|
| EMP006       |     84 |         7 |          0 |      0.0833333  | REJECT - ask company to resubmit |
| EMP016       |    168 |        14 |          0 |      0.0833333  | REJECT - ask company to resubmit |
| EMP010       |    101 |         6 |          2 |      0.0594059  | REJECT - ask company to resubmit |
| EMP018       |    243 |        13 |          0 |      0.0534979  | REJECT - ask company to resubmit |
| EMP011       |    224 |        11 |          5 |      0.0491071  | ACCEPT without blocked rows      |
| EMP025       |    227 |        11 |          1 |      0.0484581  | ACCEPT without blocked rows      |
| EMP022       |    169 |         8 |          2 |      0.0473373  | ACCEPT without blocked rows      |
| EMP005       |     85 |         4 |          1 |      0.0470588  | ACCEPT without blocked rows      |
| EMP015       |    200 |         9 |          4 |      0.045      | ACCEPT without blocked rows      |
| EMP012       |    252 |        11 |          2 |      0.0436508  | ACCEPT without blocked rows      |
| EMP023       |    256 |        11 |          3 |      0.0429688  | ACCEPT without blocked rows      |
| EMP001       |    214 |         9 |          1 |      0.0420561  | ACCEPT without blocked rows      |
| EMP020       |    122 |         5 |          0 |      0.0409836  | ACCEPT without blocked rows      |
| EMP021       |    257 |        10 |          6 |      0.0389105  | ACCEPT without blocked rows      |
| EMP019       |    133 |         5 |          1 |      0.037594   | ACCEPT without blocked rows      |
| EMP014       |    233 |         8 |          3 |      0.0343348  | ACCEPT without blocked rows      |
| EMP002       |    177 |         6 |          5 |      0.0338983  | ACCEPT without blocked rows      |
| EMP003       |    133 |         4 |          1 |      0.0300752  | ACCEPT without blocked rows      |
| EMP009       |    107 |         3 |          3 |      0.0280374  | ACCEPT without blocked rows      |
| EMP024       |    194 |         5 |          3 |      0.0257732  | ACCEPT without blocked rows      |
| EMP008       |    130 |         3 |          1 |      0.0230769  | ACCEPT without blocked rows      |
| EMP007       |    258 |         5 |          4 |      0.0193798  | ACCEPT without blocked rows      |
| EMP004       |    159 |         1 |          2 |      0.00628931 | ACCEPT without blocked rows      |
| EMP013       |    162 |         1 |          1 |      0.00617284 | ACCEPT without blocked rows      |
| EMP017       |    214 |         0 |          3 |      0          | ACCEPT                           |