# Evaluation report

4502 records from 25 companies; 242 planted errors. Title normalizer: **LLM**.

## 1. Title normalization

| subset           |   rows |   family_acc |   level_acc |   both_acc |   unmapped |
|:-----------------|-------:|-------------:|------------:|-----------:|-----------:|
| all              |   4484 |        0.991 |           1 |      0.991 |      0.009 |
| common titles    |   3375 |        1     |           1 |      1     |      0     |
| long-tail titles |   1109 |        0.965 |           1 |      0.965 |      0.035 |

Titles answered by the LLM: 100.0% (the rest fell back to keyword rules).

## 2. Error detection (any flag on an errored row)

Overall: precision **0.959**, recall **0.967**, F1 **0.963**. False alarms on clean rows: 0.23%.

| error_type            |   planted |   detected |   recall |   correct_cause |   cause_accuracy |
|:----------------------|----------:|-----------:|---------:|----------------:|-----------------:|
| annual_as_monthly     |        36 |         36 |    1     |              35 |            0.972 |
| below_min_wage        |        27 |         27 |    1     |              27 |            1     |
| bonus_outlier         |        27 |         27 |    1     |              27 |            1     |
| decimal_shift         |        27 |         27 |    1     |              27 |            1     |
| duplicate_id          |        26 |         26 |    1     |              26 |            1     |
| future_hire_date      |        18 |         18 |    1     |              18 |            1     |
| level_salary_mismatch |        45 |         37 |    0.822 |              36 |            0.973 |
| missing_salary        |        18 |         18 |    1     |              18 |            1     |
| missing_title         |        18 |         18 |    1     |              18 |            1     |

## 3. Statistical detectors (annual-as-monthly + level mismatch)

Rows the peer comparison could see: 81/81 of the planted statistical errors (rows with unmapped titles are excluded).

|               |   precision |   recall |    f1 |   tp |   fp |   fn |   flagged |
|:--------------|------------:|---------:|------:|-----:|-----:|-----:|----------:|
| vote_z        |       0.878 |    0.889 | 0.883 |   72 |   10 |    9 |       106 |
| vote_iqr      |       0.731 |    0.975 | 0.836 |   79 |   29 |    2 |       135 |
| vote_iforest  |       0.489 |    0.556 | 0.52  |   45 |   47 |   36 |       132 |
| flag_ensemble |       0.88  |    0.901 | 0.89  |   73 |   10 |    8 |       107 |

## 4. How much do titles matter?

Same validator, but with perfect (oracle) titles:

- Overall recall: 0.967 with LLM vs 0.967 with oracle titles
- Statistical errors visible: 81/81 vs 81/81
- Ensemble F1: 0.89 vs 0.89

## 5. Company decisions

| company_id   |   rows |   blocked |   warnings |   blocked_share | decision                         |
|:-------------|-------:|----------:|-----------:|----------------:|:---------------------------------|
| EMP006       |     84 |         8 |          1 |      0.0952381  | REJECT - ask company to resubmit |
| EMP016       |    168 |        14 |          3 |      0.0833333  | REJECT - ask company to resubmit |
| EMP010       |    101 |         6 |          1 |      0.0594059  | REJECT - ask company to resubmit |
| EMP018       |    243 |        13 |          3 |      0.0534979  | REJECT - ask company to resubmit |
| EMP011       |    224 |        11 |          8 |      0.0491071  | ACCEPT without blocked rows      |
| EMP025       |    227 |        11 |          4 |      0.0484581  | ACCEPT without blocked rows      |
| EMP022       |    169 |         8 |          9 |      0.0473373  | ACCEPT without blocked rows      |
| EMP005       |     85 |         4 |          1 |      0.0470588  | ACCEPT without blocked rows      |
| EMP019       |    133 |         6 |          2 |      0.0451128  | ACCEPT without blocked rows      |
| EMP015       |    200 |         9 |          6 |      0.045      | ACCEPT without blocked rows      |
| EMP023       |    256 |        11 |          4 |      0.0429688  | ACCEPT without blocked rows      |
| EMP021       |    257 |        11 |          5 |      0.0428016  | ACCEPT without blocked rows      |
| EMP001       |    214 |         9 |          1 |      0.0420561  | ACCEPT without blocked rows      |
| EMP020       |    122 |         5 |          4 |      0.0409836  | ACCEPT without blocked rows      |
| EMP002       |    177 |         7 |          5 |      0.039548   | ACCEPT without blocked rows      |
| EMP012       |    252 |         9 |          4 |      0.0357143  | ACCEPT without blocked rows      |
| EMP003       |    133 |         4 |          1 |      0.0300752  | ACCEPT without blocked rows      |
| EMP009       |    107 |         3 |          5 |      0.0280374  | ACCEPT without blocked rows      |
| EMP014       |    233 |         6 |          7 |      0.0257511  | ACCEPT without blocked rows      |
| EMP008       |    130 |         3 |          3 |      0.0230769  | ACCEPT without blocked rows      |
| EMP024       |    194 |         4 |          6 |      0.0206186  | ACCEPT without blocked rows      |
| EMP007       |    258 |         5 |         13 |      0.0193798  | ACCEPT without blocked rows      |
| EMP004       |    159 |         1 |          6 |      0.00628931 | ACCEPT without blocked rows      |
| EMP013       |    162 |         1 |          3 |      0.00617284 | ACCEPT without blocked rows      |
| EMP017       |    214 |         0 |          6 |      0          | ACCEPT                           |