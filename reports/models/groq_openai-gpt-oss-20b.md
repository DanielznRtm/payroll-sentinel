# Evaluation report

4502 records from 25 companies; 242 planted errors. Title normalizer: **LLM (openai/gpt-oss-20b, reasoning_effort=low)**.

## 1. Title normalization

| subset           |   rows |   family_acc |   level_acc |   both_acc |   unmapped |
|:-----------------|-------:|-------------:|------------:|-----------:|-----------:|
| all              |   4484 |        0.855 |       0.982 |      0.841 |      0.145 |
| common titles    |   3375 |        0.965 |       0.983 |      0.948 |      0.035 |
| long-tail titles |   1109 |        0.521 |       0.981 |      0.516 |      0.479 |

Titles answered by the LLM: 100.0% (the rest fell back to keyword rules).

LLM run: 36 LLM calls (76 HTTP requests, 39 rate-limit (429) responses), 496.8 s in LLM calls, 13.8 s per call; 130.1 s waiting for the API (1.7 s per request), the rest is pacing and retry back-off; title normalization took 497.0 s in total.

## 2. Error detection (any flag on an errored row)

Overall: precision **0.925**, recall **0.917**, F1 **0.921**. False alarms on clean rows: 0.42%.

| error_type            |   planted |   detected |   recall |   correct_cause |   cause_accuracy |
|:----------------------|----------:|-----------:|---------:|----------------:|-----------------:|
| annual_as_monthly     |        36 |         32 |    0.889 |              32 |            1     |
| below_min_wage        |        27 |         27 |    1     |              27 |            1     |
| bonus_outlier         |        27 |         27 |    1     |              27 |            1     |
| decimal_shift         |        27 |         27 |    1     |              27 |            1     |
| duplicate_id          |        26 |         26 |    1     |              26 |            1     |
| future_hire_date      |        18 |         18 |    1     |              18 |            1     |
| level_salary_mismatch |        45 |         29 |    0.644 |              28 |            0.966 |
| missing_salary        |        18 |         18 |    1     |              18 |            1     |
| missing_title         |        18 |         18 |    1     |              18 |            1     |

## 3. Statistical detectors (annual-as-monthly + level mismatch)

Rows the peer comparison could see: 71/81 of the planted statistical errors (rows with unmapped titles are excluded).

|               |   precision |   recall |    f1 |   tp |   fp |   fn |   flagged |
|:--------------|------------:|---------:|------:|-----:|-----:|-----:|----------:|
| vote_z        |       0.763 |    0.817 | 0.789 |   58 |   18 |   13 |        99 |
| vote_iqr      |       0.642 |    0.958 | 0.768 |   68 |   38 |    3 |       130 |
| vote_iforest  |       0.513 |    0.563 | 0.537 |   40 |   38 |   31 |       114 |
| flag_ensemble |       0.772 |    0.859 | 0.813 |   61 |   18 |   10 |       102 |

## 4. How much do titles matter?

Same validator, but with perfect (oracle) titles:

- Overall recall: 0.917 with LLM (openai/gpt-oss-20b, reasoning_effort=low) vs 0.967 with oracle titles
- Statistical errors visible: 71/81 vs 81/81
- Ensemble F1: 0.813 vs 0.89

## 5. Company decisions

| company_id   |   rows |   blocked |   warnings |   blocked_share | decision                         |
|:-------------|-------:|----------:|-----------:|----------------:|:---------------------------------|
| EMP006       |     84 |         8 |         12 |      0.0952381  | REJECT - ask company to resubmit |
| EMP016       |    168 |        14 |         22 |      0.0833333  | REJECT - ask company to resubmit |
| EMP010       |    101 |         6 |         17 |      0.0594059  | REJECT - ask company to resubmit |
| EMP018       |    243 |        13 |         41 |      0.0534979  | REJECT - ask company to resubmit |
| EMP011       |    224 |        11 |         25 |      0.0491071  | ACCEPT without blocked rows      |
| EMP025       |    227 |        11 |         40 |      0.0484581  | ACCEPT without blocked rows      |
| EMP022       |    169 |         8 |         38 |      0.0473373  | ACCEPT without blocked rows      |
| EMP005       |     85 |         4 |         12 |      0.0470588  | ACCEPT without blocked rows      |
| EMP019       |    133 |         6 |         14 |      0.0451128  | ACCEPT without blocked rows      |
| EMP015       |    200 |         9 |         32 |      0.045      | ACCEPT without blocked rows      |
| EMP001       |    214 |         9 |         24 |      0.0420561  | ACCEPT without blocked rows      |
| EMP020       |    122 |         5 |         24 |      0.0409836  | ACCEPT without blocked rows      |
| EMP023       |    256 |        10 |         47 |      0.0390625  | ACCEPT without blocked rows      |
| EMP021       |    257 |        10 |         43 |      0.0389105  | ACCEPT without blocked rows      |
| EMP012       |    252 |         9 |         30 |      0.0357143  | ACCEPT without blocked rows      |
| EMP002       |    177 |         6 |         25 |      0.0338983  | ACCEPT without blocked rows      |
| EMP003       |    133 |         4 |         19 |      0.0300752  | ACCEPT without blocked rows      |
| EMP009       |    107 |         3 |         13 |      0.0280374  | ACCEPT without blocked rows      |
| EMP014       |    233 |         6 |         52 |      0.0257511  | ACCEPT without blocked rows      |
| EMP008       |    130 |         3 |         15 |      0.0230769  | ACCEPT without blocked rows      |
| EMP024       |    194 |         4 |         31 |      0.0206186  | ACCEPT without blocked rows      |
| EMP007       |    258 |         5 |         50 |      0.0193798  | ACCEPT without blocked rows      |
| EMP004       |    159 |         1 |         32 |      0.00628931 | ACCEPT without blocked rows      |
| EMP013       |    162 |         1 |         24 |      0.00617284 | ACCEPT without blocked rows      |
| EMP017       |    214 |         0 |         23 |      0          | ACCEPT                           |