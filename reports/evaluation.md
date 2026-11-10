# Evaluation report

4502 records from 25 companies; 242 planted errors. Title normalizer: **keyword rules**.

## 1. Title normalization

| subset           |   rows |   family_acc |   level_acc |   both_acc |   unmapped |
|:-----------------|-------:|-------------:|------------:|-----------:|-----------:|
| all              |   4484 |        0.763 |           1 |      0.763 |      0.237 |
| common titles    |   3375 |        1     |           1 |      1     |      0     |
| long-tail titles |   1109 |        0.042 |           1 |      0.042 |      0.958 |

## 2. Error detection (any flag on an errored row)

Overall: precision **0.96**, recall **0.884**, F1 **0.92**. False alarms on clean rows: 0.21%.

| error_type            |   planted |   detected |   recall |   correct_cause |   cause_accuracy |
|:----------------------|----------:|-----------:|---------:|----------------:|-----------------:|
| annual_as_monthly     |        36 |         27 |    0.75  |              27 |            1     |
| below_min_wage        |        27 |         27 |    1     |              27 |            1     |
| bonus_outlier         |        27 |         27 |    1     |              27 |            1     |
| decimal_shift         |        27 |         27 |    1     |              27 |            1     |
| duplicate_id          |        26 |         26 |    1     |              26 |            1     |
| future_hire_date      |        18 |         18 |    1     |              18 |            1     |
| level_salary_mismatch |        45 |         26 |    0.578 |              25 |            0.962 |
| missing_salary        |        18 |         18 |    1     |              18 |            1     |
| missing_title         |        18 |         18 |    1     |              18 |            1     |

## 3. Statistical detectors (annual-as-monthly + level mismatch)

Rows the peer comparison could see: 62/81 of the planted statistical errors (rows with unmapped titles are excluded).

|               |   precision |   recall |    f1 |   tp |   fp |   fn |   flagged |
|:--------------|------------:|---------:|------:|-----:|-----:|-----:|----------:|
| vote_z        |       0.852 |    0.839 | 0.846 |   52 |    9 |   10 |        81 |
| vote_iqr      |       0.702 |    0.952 | 0.808 |   59 |   25 |    3 |       106 |
| vote_iforest  |       0.507 |    0.548 | 0.527 |   34 |   33 |   28 |       101 |
| flag_ensemble |       0.855 |    0.855 | 0.855 |   53 |    9 |    9 |        82 |

## 4. How much do titles matter?

Same validator, but with perfect (oracle) titles:

- Overall recall: 0.884 with keyword rules vs 0.967 with oracle titles
- Statistical errors visible: 62/81 vs 81/81
- Ensemble F1: 0.855 vs 0.89

## 5. Company decisions

| company_id   |   rows |   blocked |   warnings |   blocked_share | decision                         |
|:-------------|-------:|----------:|-----------:|----------------:|:---------------------------------|
| EMP006       |     84 |         8 |         11 |      0.0952381  | REJECT - ask company to resubmit |
| EMP016       |    168 |        14 |         41 |      0.0833333  | REJECT - ask company to resubmit |
| EMP010       |    101 |         6 |         16 |      0.0594059  | REJECT - ask company to resubmit |
| EMP018       |    243 |        12 |         57 |      0.0493827  | ACCEPT without blocked rows      |
| EMP011       |    224 |        11 |         54 |      0.0491071  | ACCEPT without blocked rows      |
| EMP025       |    227 |        11 |         52 |      0.0484581  | ACCEPT without blocked rows      |
| EMP022       |    169 |         8 |         50 |      0.0473373  | ACCEPT without blocked rows      |
| EMP005       |     85 |         4 |         17 |      0.0470588  | ACCEPT without blocked rows      |
| EMP019       |    133 |         6 |         22 |      0.0451128  | ACCEPT without blocked rows      |
| EMP015       |    200 |         9 |         56 |      0.045      | ACCEPT without blocked rows      |
| EMP020       |    122 |         5 |         40 |      0.0409836  | ACCEPT without blocked rows      |
| EMP001       |    214 |         8 |         51 |      0.0373832  | ACCEPT without blocked rows      |
| EMP012       |    252 |         9 |         62 |      0.0357143  | ACCEPT without blocked rows      |
| EMP023       |    256 |         9 |         55 |      0.0351562  | ACCEPT without blocked rows      |
| EMP021       |    257 |         9 |         55 |      0.0350195  | ACCEPT without blocked rows      |
| EMP003       |    133 |         4 |         36 |      0.0300752  | ACCEPT without blocked rows      |
| EMP002       |    177 |         5 |         38 |      0.0282486  | ACCEPT without blocked rows      |
| EMP009       |    107 |         3 |         19 |      0.0280374  | ACCEPT without blocked rows      |
| EMP014       |    233 |         6 |         68 |      0.0257511  | ACCEPT without blocked rows      |
| EMP008       |    130 |         3 |         27 |      0.0230769  | ACCEPT without blocked rows      |
| EMP024       |    194 |         4 |         50 |      0.0206186  | ACCEPT without blocked rows      |
| EMP007       |    258 |         5 |         67 |      0.0193798  | ACCEPT without blocked rows      |
| EMP004       |    159 |         1 |         47 |      0.00628931 | ACCEPT without blocked rows      |
| EMP013       |    162 |         1 |         42 |      0.00617284 | ACCEPT without blocked rows      |
| EMP017       |    214 |         0 |         62 |      0          | ACCEPT                           |