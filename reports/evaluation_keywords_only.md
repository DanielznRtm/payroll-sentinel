# Evaluation report

4502 records from 25 companies; 242 planted errors. Title normalizer: **keyword rules only**.

## 1. Title normalization

| subset           |   rows |   family_acc |   level_acc |   both_acc |   unmapped |
|:-----------------|-------:|-------------:|------------:|-----------:|-----------:|
| all              |   4484 |        0.763 |           1 |      0.763 |      0.237 |
| common titles    |   3375 |        1     |           1 |      1     |      0     |
| long-tail titles |   1109 |        0.042 |           1 |      0.042 |      0.958 |

## 2. Error detection (any flag on an errored row)

Overall: precision **0.887**, recall **0.781**, F1 **0.831**. False alarms on clean rows: 0.56%.

| error_type            |   planted |   detected |   recall |   correct_cause |   cause_accuracy |
|:----------------------|----------:|-----------:|---------:|----------------:|-----------------:|
| annual_as_monthly     |        36 |         25 |    0.694 |              21 |             0.84 |
| below_min_wage        |        27 |         27 |    1     |              27 |             1    |
| bonus_outlier         |        27 |         27 |    1     |              27 |             1    |
| decimal_shift         |        27 |         27 |    1     |              27 |             1    |
| duplicate_id          |        26 |         26 |    1     |              26 |             1    |
| future_hire_date      |        18 |         18 |    1     |              18 |             1    |
| level_salary_mismatch |        45 |          3 |    0.067 |               3 |             1    |
| missing_salary        |        18 |         18 |    1     |              18 |             1    |
| missing_title         |        18 |         18 |    1     |              18 |             1    |

## 3. Statistical detectors (annual-as-monthly + level mismatch)

Rows the peer comparison could see: 62/81 of the planted statistical errors (rows with unmapped titles are excluded).

|               |   precision |   recall |    f1 |   tp |   fp |   fn |   flagged |
|:--------------|------------:|---------:|------:|-----:|-----:|-----:|----------:|
| vote_z        |       0.418 |    0.452 | 0.434 |   28 |   39 |   34 |        73 |
| vote_iqr      |       0.452 |    0.532 | 0.489 |   33 |   40 |   29 |        83 |
| vote_iforest  |       0.254 |    0.29  | 0.271 |   18 |   53 |   44 |       101 |
| flag_ensemble |       0.538 |    0.452 | 0.491 |   28 |   24 |   34 |        59 |

## 4. How much do titles matter?

Same validator, but with perfect (oracle) titles:

- Overall recall: 0.781 with keyword rules only vs 0.822 with oracle titles
- Statistical errors visible: 62/81 vs 81/81
- Ensemble F1: 0.491 vs 0.551

## 5. Company decisions

| company_id   |   rows |   blocked |   warnings |   blocked_share | decision                         |
|:-------------|-------:|----------:|-----------:|----------------:|:---------------------------------|
| EMP006       |     84 |         7 |         11 |      0.0833333  | REJECT - ask company to resubmit |
| EMP016       |    168 |        14 |         39 |      0.0833333  | REJECT - ask company to resubmit |
| EMP010       |    101 |         6 |         19 |      0.0594059  | REJECT - ask company to resubmit |
| EMP018       |    243 |        12 |         56 |      0.0493827  | ACCEPT without blocked rows      |
| EMP011       |    224 |        11 |         54 |      0.0491071  | ACCEPT without blocked rows      |
| EMP025       |    227 |        11 |         51 |      0.0484581  | ACCEPT without blocked rows      |
| EMP022       |    169 |         8 |         49 |      0.0473373  | ACCEPT without blocked rows      |
| EMP005       |     85 |         4 |         17 |      0.0470588  | ACCEPT without blocked rows      |
| EMP015       |    200 |         9 |         56 |      0.045      | ACCEPT without blocked rows      |
| EMP012       |    252 |        11 |         61 |      0.0436508  | ACCEPT without blocked rows      |
| EMP020       |    122 |         5 |         39 |      0.0409836  | ACCEPT without blocked rows      |
| EMP019       |    133 |         5 |         22 |      0.037594   | ACCEPT without blocked rows      |
| EMP001       |    214 |         8 |         53 |      0.0373832  | ACCEPT without blocked rows      |
| EMP023       |    256 |         9 |         54 |      0.0351562  | ACCEPT without blocked rows      |
| EMP021       |    257 |         9 |         55 |      0.0350195  | ACCEPT without blocked rows      |
| EMP003       |    133 |         4 |         36 |      0.0300752  | ACCEPT without blocked rows      |
| EMP014       |    233 |         7 |         69 |      0.0300429  | ACCEPT without blocked rows      |
| EMP002       |    177 |         5 |         38 |      0.0282486  | ACCEPT without blocked rows      |
| EMP009       |    107 |         3 |         18 |      0.0280374  | ACCEPT without blocked rows      |
| EMP008       |    130 |         3 |         28 |      0.0230769  | ACCEPT without blocked rows      |
| EMP024       |    194 |         4 |         49 |      0.0206186  | ACCEPT without blocked rows      |
| EMP007       |    258 |         5 |         63 |      0.0193798  | ACCEPT without blocked rows      |
| EMP004       |    159 |         1 |         47 |      0.00628931 | ACCEPT without blocked rows      |
| EMP017       |    214 |         0 |         60 |      0          | ACCEPT                           |
| EMP013       |    162 |         0 |         41 |      0          | ACCEPT                           |