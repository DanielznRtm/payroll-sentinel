# Public salary files: titles and full validation

Titles: keyword rules and LLM (gemini-3.5-flash-lite), 1271 distinct titles. LLM run: 30 LLM calls (35 HTTP requests, 1 rate-limit (429) responses), 171.4 s in LLM calls, 5.7 s per call; 104.1 s waiting for the API (3.0 s per request), the rest is pacing and retry back-off; 171.6 s in total.

No ground truth: section 1 uses weak labels that ship with the data, and section 2 lists what the validator flags, for a human to judge. Adapter: annual salary / 12 in the original currency, 44 h/week, bonus 0, hire date 2020-01-01 for every row.

## 1. Job titles

### India file: family against the weak label (expected: software_engineer)

Share of distinct titles (`n` = titles):

| group             | titles   |   n |   software_engineer |   other family |   abstained |
|:------------------|:---------|----:|--------------------:|---------------:|------------:|
| 9 developer roles | LLM      | 885 |               0.958 |          0.018 |       0.024 |
| 9 developer roles | rules    | 885 |               0.101 |          0.002 |       0.897 |
| Database          | LLM      | 126 |               0.96  |          0.024 |       0.016 |
| Database          | rules    | 126 |               0.016 |          0     |       0.984 |
| Testing           | LLM      |  69 |               0.928 |          0     |       0.072 |
| Testing           | rules    |  69 |               0     |          0     |       1     |

Share of rows (`n` = rows; frequent titles weigh more):

| group             | titles   |     n |   software_engineer |   other family |   abstained |
|:------------------|:---------|------:|--------------------:|---------------:|------------:|
| 9 developer roles | LLM      | 20165 |               0.994 |          0.001 |       0.004 |
| 9 developer roles | rules    | 20165 |               0.031 |          0     |       0.969 |
| Database          | LLM      |   865 |               0.98  |          0.017 |       0.002 |
| Database          | rules    |   865 |               0.002 |          0     |       0.998 |
| Testing           | LLM      |  1740 |               0.994 |          0     |       0.006 |
| Testing           | rules    |  1740 |               0     |          0     |       1     |

LLM titles mapped to another family (19); many show the weak label is wrong:

| Job Roles   | Job Title                                             | family                 |   rows |
|:------------|:------------------------------------------------------|:-----------------------|-------:|
| Database    | Database Analyst                                      | data_analyst           |     10 |
| Mobile      | Mobile Technician                                     | maintenance_technician |      6 |
| Backend     | Backend Support Executive                             | customer_support       |      4 |
| Mobile      | Best Buy Mobile Sales Associate                       | sales_rep              |      4 |
| Database    | Senior Database Analyst                               | data_analyst           |      4 |
| Mobile      | Mobile Phone Technician                               | maintenance_technician |      2 |
| Java        | Java Production Support                               | customer_support       |      2 |
| Mobile      | Mobile Repair Technician                              | maintenance_technician |      2 |
| Backend     | Backend Support                                       | customer_support       |      1 |
| Frontend    | Front End Service Clerk/Cashier                       | customer_support       |      1 |
| Database    | Database Analyst Contractor                           | data_analyst           |      1 |
| Mobile      | Mobile Phone Repair Technician                        | maintenance_technician |      1 |
| Mobile      | Mobile Crane Operator                                 | production_operator    |      1 |
| Mobile      | Best Buy Mobile - Sales Consultant                    | sales_rep              |      1 |
| Mobile      | Mobile Technician Contractor                          | maintenance_technician |      1 |
| Mobile      | Senior Mobile Product Manager                         | product_manager        |      1 |
| Python      | Python Data scientist                                 | data_scientist         |      1 |
| Python      | Python and Machine Learning Analyst                   | data_analyst           |      1 |
| SDE         | Applications/Software Development/Support Or Engineer | customer_support       |      1 |

LLM abstentions (28), most frequent first:

| Job Roles   | Job Title                                   |   rows |
|:------------|:--------------------------------------------|-------:|
| Backend     | Backend Process                             |     42 |
| Frontend    | Front End Cashier                           |     14 |
| Testing     | Test Manager                                |      7 |
| Python      | Python Trainer                              |      4 |
| Backend     | Backend Operations                          |      3 |
| SDE         | Manager, Software Development & Engineering |      3 |
| Mobile      | Rakuten Mobile                              |      2 |
| Python      | Python Instructor                           |      2 |
| Java        | Java Trainer                                |      2 |
| Backend     | Backend Executive & Supporting Staff        |      1 |
| Database    | Manager, Database Administration            |      1 |
| Backend     | Backend Operation                           |      1 |
| Java        | Java Manager                                |      1 |
| IOS         | IOS App Review WWDR                         |      1 |
| Frontend    | Front End Chasier                           |      1 |
| Database    | Senior Clinical Database Programmer         |      1 |
| Backend     | Backend Process - Contractor                |      1 |
| Mobile      | Level II Mobile Technician                  |      1 |
| Mobile      | Mobile Marketing Manager                    |      1 |
| Mobile      | Mobile Device Management - Contractor       |      1 |

Rows with Employment Status `Intern`: 2106; given level `intern` by rules 100.0%, by the LLM 100.0%.

### US-style file: coverage (no labels)

Many titles (marketing, operations, directors) are outside the 10 families, so abstaining is often right.

| titles   |   rows with a family | distinct titles with a family   |
|:---------|---------------------:|:--------------------------------|
| rules    |                0.39  | 21 / 193                        |
| LLM      |                0.683 | 87 / 193                        |

Most frequent titles (family / level):

| title                     |   rows | rules                      | LLM                        |
|:--------------------------|-------:|:---------------------------|:---------------------------|
| Software Engineer         |    518 | software_engineer / mid    | software_engineer / mid    |
| Data Scientist            |    453 | data_scientist / mid       | data_scientist / mid       |
| Software Engineer Manager |    376 | software_engineer / mid    | software_engineer / lead   |
| Data Analyst              |    363 | data_analyst / mid         | data_analyst / mid         |
| Senior Project Engineer   |    318 | - / senior                 | - / senior                 |
| Product Manager           |    313 | product_manager / mid      | product_manager / mid      |
| Full Stack Engineer       |    309 | - / mid                    | software_engineer / mid    |
| Marketing Manager         |    255 | - / mid                    | - / lead                   |
| Senior Software Engineer  |    244 | software_engineer / senior | software_engineer / senior |
| Back end Developer        |    244 | - / mid                    | software_engineer / mid    |
| Front end Developer       |    241 | - / mid                    | software_engineer / mid    |
| Marketing Coordinator     |    158 | - / mid                    | - / mid                    |
| Junior Sales Associate    |    142 | - / junior                 | sales_rep / junior         |
| Financial Manager         |    134 | financial_analyst / mid    | financial_analyst / senior |
| Marketing Analyst         |    132 | - / mid                    | - / mid                    |
| Software Developer        |    125 | - / mid                    | software_engineer / mid    |
| Operations Manager        |    114 | - / mid                    | - / mid                    |
| Human Resources Manager   |    104 | - / mid                    | - / lead                   |
| Director of Marketing     |     88 | - / mid                    | - / senior                 |
| Web Developer             |     87 | - / mid                    | software_engineer / mid    |
| Product Designer          |     75 | - / mid                    | - / mid                    |
| Research Director         |     75 | - / mid                    | - / lead                   |
| Content Marketing Manager |     73 | - / mid                    | - / mid                    |
| Sales Associate           |     70 | - / mid                    | sales_rep / junior         |
| Research Scientist        |     69 | - / mid                    | data_scientist / mid       |

## 2. Full validation

### India (22770 rows, 11261 companies, INR)

Rows per cause (a row can have several):

| titles   | rows in peer comparison   |   blocked rows |   peer-comparison flags |   missing_salary |   missing_title |   duplicate_record |   decimal_shift |   below_min_wage |   extreme_value |   annual_as_monthly |   divided_by_12 |   level_salary_mismatch |   statistical_outlier |
|:---------|:--------------------------|---------------:|------------------------:|-----------------:|----------------:|-------------------:|----------------:|-----------------:|----------------:|--------------------:|----------------:|------------------------:|----------------------:|
| rules    | 2.7%                      |             17 |                       8 |                0 |               0 |                 64 |               1 |               12 |               0 |                   3 |               5 |                       0 |                     0 |
| LLM      | 99.4%                     |            143 |                     165 |                0 |               0 |                 64 |               1 |               12 |              15 |                  37 |             113 |                       0 |                     0 |

Peer-comparison causes with LLM titles:

| cause             | severity   |   rows |
|:------------------|:-----------|-------:|
| annual_as_monthly | block      |     29 |
| annual_as_monthly | warn       |      8 |
| divided_by_12     | block      |     98 |
| divided_by_12     | warn       |     15 |
| extreme_value     | block      |     15 |

Most extreme flags (LLM titles; salaries are annual):

| job_title                            | family            | level   |   annual salary |   peer median (annual) |   peer_ratio | cause         | severity   |
|:-------------------------------------|:------------------|:--------|----------------:|-----------------------:|-------------:|:--------------|:-----------|
| Software Development Engineer (SDE)  | software_engineer | mid     |           9e+07 |                 500000 |      180     | extreme_value | block      |
| Senior Java Developer Contractor     | software_engineer | senior  |       12000     |                 900000 |        0.013 | extreme_value | block      |
| Senior Software Development Engineer | software_engineer | senior  |       12000     |                 900000 |        0.013 | extreme_value | block      |
| Senior IOS Developer                 | software_engineer | senior  |       12000     |                 900000 |        0.013 | extreme_value | block      |
| Junior Java Developer                | software_engineer | junior  |        8448     |                 400000 |        0.021 | extreme_value | block      |
| Web Developer                        | software_engineer | mid     |       12000     |                 500000 |        0.024 | extreme_value | block      |
| Software Development Engineer        | software_engineer | mid     |       12000     |                 500000 |        0.024 | extreme_value | block      |
| Software Development Engineer (SDE)  | software_engineer | mid     |       12000     |                 500000 |        0.024 | extreme_value | block      |
| Android Developer                    | software_engineer | mid     |       12000     |                 500000 |        0.024 | extreme_value | block      |
| Web Developer                        | software_engineer | mid     |       12000     |                 500000 |        0.024 | extreme_value | block      |
| Software Development Engineer (SDE)  | software_engineer | mid     |       12000     |                 500000 |        0.024 | extreme_value | block      |
| Test Engineer                        | software_engineer | mid     |       12672     |                 500000 |        0.025 | extreme_value | block      |

Mildest flags (LLM titles):

| job_title                                       | family            | level   |   annual salary |   peer median (annual) |   peer_ratio | cause             | severity   |
|:------------------------------------------------|:------------------|:--------|----------------:|-----------------------:|-------------:|:------------------|:-----------|
| Senior Manager Software Development Engineering | software_engineer | senior  |         5.5e+06 |                 900000 |        6.111 | annual_as_monthly | warn       |
| Sr Software Development Engineer                | software_engineer | senior  |         5.6e+06 |                 900000 |        6.222 | annual_as_monthly | warn       |
| Senior Software Development Engineer            | software_engineer | senior  |    132000       |                 900000 |        0.147 | divided_by_12     | warn       |
| Software Development Engineer (SDE) III         | software_engineer | senior  |         6.2e+06 |                 900000 |        6.889 | annual_as_monthly | warn       |
| Senior Mobile Developer                         | software_engineer | senior  |         6.4e+06 |                 900000 |        7.111 | annual_as_monthly | warn       |
| Senior Android Developer Contractor             | software_engineer | senior  |    120384       |                 900000 |        0.134 | divided_by_12     | warn       |

Company decisions (LLM titles). Most companies here have one to three rows, so a single blocked row is more than the 5 % that rejects a file:

| decision                         |   companies |
|:---------------------------------|------------:|
| ACCEPT                           |       11126 |
| REJECT - ask company to resubmit |         118 |
| ACCEPT without blocked rows      |          17 |

### US-style (6704 rows, 1 companies, USD)

Rows per cause (a row can have several):

| titles   | rows in peer comparison   |   blocked rows |   peer-comparison flags |   missing_salary |   missing_title |   duplicate_record |   decimal_shift |   below_min_wage |   extreme_value |   annual_as_monthly |   divided_by_12 |   level_salary_mismatch |   statistical_outlier |
|:---------|:--------------------------|---------------:|------------------------:|-----------------:|----------------:|-------------------:|----------------:|-----------------:|----------------:|--------------------:|----------------:|------------------------:|----------------------:|
| rules    | 38.7%                     |              9 |                       3 |                5 |               2 |               6005 |               4 |                0 |               0 |                   0 |               0 |                       1 |                     2 |
| LLM      | 67.4%                     |              9 |                      74 |                5 |               2 |               6005 |               4 |                0 |               0 |                   0 |               0 |                      57 |                    17 |

Peer-comparison causes with LLM titles:

| cause                 | severity   |   rows |
|:----------------------|:-----------|-------:|
| level_salary_mismatch | warn       |     57 |
| statistical_outlier   | warn       |     17 |

Most extreme flags (LLM titles; salaries are annual):

| job_title     | family    | level   |   annual salary |   peer median (annual) |   peer_ratio | cause                 | severity   |
|:--------------|:----------|:--------|----------------:|-----------------------:|-------------:|:----------------------|:-----------|
| Sales Manager | sales_rep | lead    |           35000 |                 140000 |        0.25  | level_salary_mismatch | warn       |
| Sales Manager | sales_rep | lead    |           35000 |                 140000 |        0.25  | level_salary_mismatch | warn       |
| Sales Manager | sales_rep | lead    |           40000 |                 140000 |        0.286 | level_salary_mismatch | warn       |
| Sales Manager | sales_rep | lead    |           40000 |                 140000 |        0.286 | level_salary_mismatch | warn       |
| Sales Manager | sales_rep | lead    |           40000 |                 140000 |        0.286 | level_salary_mismatch | warn       |
| Sales Manager | sales_rep | lead    |           40000 |                 140000 |        0.286 | level_salary_mismatch | warn       |
| Sales Manager | sales_rep | lead    |           40000 |                 140000 |        0.286 | level_salary_mismatch | warn       |
| Sales Manager | sales_rep | lead    |           40000 |                 140000 |        0.286 | level_salary_mismatch | warn       |
| Sales Manager | sales_rep | lead    |           40000 |                 140000 |        0.286 | level_salary_mismatch | warn       |
| Sales Manager | sales_rep | lead    |           40000 |                 140000 |        0.286 | level_salary_mismatch | warn       |
| Sales Manager | sales_rep | lead    |           40000 |                 140000 |        0.286 | level_salary_mismatch | warn       |
| Sales Manager | sales_rep | lead    |           40000 |                 140000 |        0.286 | level_salary_mismatch | warn       |

Mildest flags (LLM titles):

| job_title                 | family            | level   |   annual salary |   peer median (annual) |   peer_ratio | cause               | severity   |
|:--------------------------|:------------------|:--------|----------------:|-----------------------:|-------------:|:--------------------|:-----------|
| Senior Software Architect | software_engineer | lead    |          120000 |                 183138 |        0.655 | statistical_outlier | warn       |
| Software Engineer Manager | software_engineer | lead    |          119836 |                 183138 |        0.654 | statistical_outlier | warn       |
| Software Engineer Manager | software_engineer | lead    |          119836 |                 183138 |        0.654 | statistical_outlier | warn       |
| Software Manager          | software_engineer | lead    |          110000 |                 183138 |        0.601 | statistical_outlier | warn       |
| Junior HR Generalist      | hr_analyst        | junior  |           60000 |                  35000 |        1.714 | statistical_outlier | warn       |
| Junior HR Generalist      | hr_analyst        | junior  |           60000 |                  35000 |        1.714 | statistical_outlier | warn       |
