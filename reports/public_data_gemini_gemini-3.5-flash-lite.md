# Public salary files: titles and full validation

Titles: keyword rules and LLM (gemini-3.5-flash-lite), 1387 distinct titles. LLM run: 32 LLM calls (33 HTTP requests, 0 rate-limit (429) responses), 147.1 s in LLM calls, 4.6 s per call; 101.1 s waiting for the API (3.1 s per request), the rest is pacing and retry back-off; 147.4 s in total.

No ground truth: section 1 uses weak labels that ship with the data, and section 2 lists what the validator flags, for a human to judge. Adapter: annual salary / 12 in the original currency, 44 h/week, bonus 0; hire date 2020-01-01 for the India and US-style files, and the reference date minus months of experience for the Italian survey.

## 1. Job titles

### India file: family against the weak label (expected: software_engineer)

Share of distinct titles (`n` = titles):

| group             | titles   |   n |   software_engineer |   other family |   abstained |
|:------------------|:---------|----:|--------------------:|---------------:|------------:|
| 9 developer roles | LLM      | 885 |               0.96  |          0.02  |       0.019 |
| 9 developer roles | rules    | 885 |               0.101 |          0.002 |       0.897 |
| Database          | LLM      | 126 |               0.937 |          0.024 |       0.04  |
| Database          | rules    | 126 |               0.016 |          0     |       0.984 |
| Testing           | LLM      |  69 |               0.768 |          0     |       0.232 |
| Testing           | rules    |  69 |               0     |          0     |       1     |

Share of rows (`n` = rows; frequent titles weigh more):

| group             | titles   |     n |   software_engineer |   other family |   abstained |
|:------------------|:---------|------:|--------------------:|---------------:|------------:|
| 9 developer roles | LLM      | 20165 |               0.994 |          0.002 |       0.004 |
| 9 developer roles | rules    | 20165 |               0.031 |          0     |       0.969 |
| Database          | LLM      |   865 |               0.968 |          0.017 |       0.015 |
| Database          | rules    |   865 |               0.002 |          0     |       0.998 |
| Testing           | LLM      |  1740 |               0.982 |          0     |       0.018 |
| Testing           | rules    |  1740 |               0     |          0     |       1     |

LLM titles mapped to another family (21); many show the weak label is wrong:

| Job Roles   | Job Title                            | family                 |   rows |
|:------------|:-------------------------------------|:-----------------------|-------:|
| Database    | Database Analyst                     | data_analyst           |     10 |
| Mobile      | Mobile Technician                    | maintenance_technician |      6 |
| Database    | Senior Database Analyst              | data_analyst           |      4 |
| Mobile      | Best Buy Mobile Sales Associate      | sales_rep              |      4 |
| Backend     | Backend Support Executive            | customer_support       |      4 |
| Mobile      | Mobile Repair Technician             | maintenance_technician |      2 |
| Java        | Java Production Support              | customer_support       |      2 |
| Mobile      | Mobile Phone Technician              | maintenance_technician |      2 |
| Backend     | Backend Support                      | customer_support       |      1 |
| Database    | Database Analyst Contractor          | data_analyst           |      1 |
| Mobile      | Level II Mobile Technician           | maintenance_technician |      1 |
| Mobile      | Best Buy Mobile - Sales Consultant   | sales_rep              |      1 |
| Frontend    | Front End Service Clerk/Cashier      | customer_support       |      1 |
| Mobile      | Mobile Phone Repair Technician       | maintenance_technician |      1 |
| Mobile      | Mobile Crane Operator                | production_operator    |      1 |
| Mobile      | Mobile Technician Contractor         | maintenance_technician |      1 |
| Mobile      | Senior Mobile Product Manager        | product_manager        |      1 |
| Python      | Lead Python Developer (Data Science) | data_scientist         |      1 |
| Python      | Python Analyst                       | data_analyst           |      1 |
| Python      | Python Data scientist                | data_scientist         |      1 |
| Python      | Python and Machine Learning Analyst  | data_scientist         |      1 |

LLM abstentions (38), most frequent first:

| Job Roles   | Job Title                             |   rows |
|:------------|:--------------------------------------|-------:|
| Backend     | Backend Process                       |     42 |
| Frontend    | Front End Cashier                     |     14 |
| Testing     | QA Tester                             |      6 |
| Testing     | QA Test Engineer                      |      6 |
| Database    | Database Manager                      |      4 |
| Database    | Associate Database Engineer           |      4 |
| Python      | Python Trainer                        |      4 |
| Testing     | QA Test Lead                          |      4 |
| Backend     | Backend Operations                    |      3 |
| Database    | Applications Database Administrator   |      2 |
| Testing     | QA Test Analyst                       |      2 |
| Database    | Associate Database Administrator      |      2 |
| Mobile      | Rakuten Mobile                        |      2 |
| Java        | Java Trainer                          |      2 |
| Testing     | QA Analyst/ETL Tester                 |      2 |
| Python      | Python Instructor                     |      2 |
| Backend     | Backend Operation                     |      1 |
| Java        | Java Manager                          |      1 |
| Mobile      | Mobile Marketing Manager              |      1 |
| Mobile      | Mobile Device Management - Contractor |      1 |

Rows with Employment Status `Intern`: 2106; given level `intern` by rules 100.0%, by the LLM 100.0%.

### US-style file: coverage (no labels)

Many titles (marketing, operations, directors) are outside the 10 families, so abstaining is often right.

| titles   |   rows with a family | distinct titles with a family   |
|:---------|---------------------:|:--------------------------------|
| rules    |                0.39  | 21 / 193                        |
| LLM      |                0.734 | 87 / 193                        |

Most frequent titles (family / level):

| title                     |   rows | rules                      | LLM                        |
|:--------------------------|-------:|:---------------------------|:---------------------------|
| Software Engineer         |    518 | software_engineer / mid    | software_engineer / mid    |
| Data Scientist            |    453 | data_scientist / mid       | data_scientist / mid       |
| Software Engineer Manager |    376 | software_engineer / mid    | software_engineer / lead   |
| Data Analyst              |    363 | data_analyst / mid         | data_analyst / mid         |
| Senior Project Engineer   |    318 | - / senior                 | software_engineer / senior |
| Product Manager           |    313 | product_manager / mid      | product_manager / mid      |
| Full Stack Engineer       |    309 | - / mid                    | software_engineer / mid    |
| Marketing Manager         |    255 | - / mid                    | - / lead                   |
| Senior Software Engineer  |    244 | software_engineer / senior | software_engineer / senior |
| Back end Developer        |    244 | - / mid                    | software_engineer / mid    |
| Front end Developer       |    241 | - / mid                    | software_engineer / mid    |
| Marketing Coordinator     |    158 | - / mid                    | - / mid                    |
| Junior Sales Associate    |    142 | - / junior                 | sales_rep / junior         |
| Financial Manager         |    134 | financial_analyst / mid    | financial_analyst / lead   |
| Marketing Analyst         |    132 | - / mid                    | - / mid                    |
| Software Developer        |    125 | - / mid                    | software_engineer / mid    |
| Operations Manager        |    114 | - / mid                    | - / senior                 |
| Human Resources Manager   |    104 | - / mid                    | hr_analyst / lead          |
| Director of Marketing     |     88 | - / mid                    | - / senior                 |
| Web Developer             |     87 | - / mid                    | software_engineer / mid    |
| Product Designer          |     75 | - / mid                    | - / mid                    |
| Research Director         |     75 | - / mid                    | - / senior                 |
| Content Marketing Manager |     73 | - / mid                    | - / mid                    |
| Sales Associate           |     70 | - / mid                    | sales_rep / junior         |
| Research Scientist        |     69 | - / mid                    | - / mid                    |

### Italian survey: coverage (no labels)

117 job categories chosen from a list (no seniority in them, so every row is `mid` unless the title implies a level). Many IT roles (project manager, IT consultant, solutions architect) are outside the 10 families.

| titles   |   rows with a family | distinct titles with a family   |
|:---------|---------------------:|:--------------------------------|
| rules    |                0.156 | 8 / 117                         |
| LLM      |                0.663 | 62 / 117                        |

Most frequent titles (family / level):

| title                     |   rows | rules                 | LLM                      |
|:--------------------------|-------:|:----------------------|:-------------------------|
| software developer        |   3137 | - / mid               | software_engineer / mid  |
| it consultant             |   2605 | - / mid               | - / mid                  |
| project manager           |   2113 | - / mid               | - / mid                  |
| fullstack developer       |   1937 | - / mid               | software_engineer / mid  |
| data analyst              |   1843 | data_analyst / mid    | data_analyst / mid       |
| data scientist            |   1760 | data_scientist / mid  | data_scientist / mid     |
| data engineer             |   1255 | - / mid               | software_engineer / mid  |
| backend developer         |   1086 | - / mid               | software_engineer / mid  |
| frontend developer        |    940 | - / mid               | software_engineer / mid  |
| solutions architect       |    730 | - / mid               | software_engineer / lead |
| it manager                |    604 | - / mid               | - / senior               |
| ai engineer               |    528 | - / mid               | software_engineer / mid  |
| researcher                |    445 | - / mid               | - / mid                  |
| product manager           |    421 | product_manager / mid | product_manager / mid    |
| .net developer            |    407 | - / mid               | software_engineer / mid  |
| cybersecurity specialist  |    388 | - / mid               | software_engineer / lead |
| ui/ux designer            |    364 | - / mid               | - / mid                  |
| business analyst          |    352 | - / mid               | - / mid                  |
| web developer             |    322 | - / mid               | software_engineer / mid  |
| machine learning engineer |    294 | - / mid               | data_scientist / mid     |
| it specialist             |    273 | - / mid               | - / senior               |
| java developer            |    271 | - / mid               | software_engineer / mid  |
| app developer             |    257 | - / mid               | software_engineer / mid  |
| product owner             |    247 | - / mid               | product_manager / mid    |
| system engineer           |    240 | - / mid               | software_engineer / mid  |
| engineer (non tech)       |    215 | - / mid               | - / mid                  |
| devops engineer           |    210 | - / mid               | software_engineer / mid  |
| quality assurance         |    192 | - / mid               | - / mid                  |
| product designer          |    181 | - / mid               | - / mid                  |
| sales specialist          |    178 | - / mid               | sales_rep / mid          |

## 2. Full validation

### India (22770 rows, 11261 companies, INR)

Rows per cause (a row can have several):

| titles   | rows in peer comparison   |   blocked rows |   peer-comparison flags |   missing_salary |   missing_title |   duplicate_record |   decimal_shift |   below_min_wage |   extreme_value |   annual_as_monthly |   divided_by_12 |   level_salary_mismatch |   statistical_outlier |   future_hire_date |
|:---------|:--------------------------|---------------:|------------------------:|-----------------:|----------------:|-------------------:|----------------:|-----------------:|----------------:|--------------------:|----------------:|------------------------:|----------------------:|-------------------:|
| rules    | 2.7%                      |             17 |                       8 |                0 |               0 |                 64 |               1 |               12 |               0 |                   3 |               5 |                       0 |                     0 |                  0 |
| LLM      | 99.2%                     |            146 |                     168 |                0 |               0 |                 64 |               1 |               12 |              16 |                  41 |             111 |                       0 |                     0 |                  0 |

Peer-comparison causes with LLM titles:

| cause             | severity   |   rows |
|:------------------|:-----------|-------:|
| annual_as_monthly | block      |     33 |
| annual_as_monthly | warn       |      8 |
| divided_by_12     | block      |     96 |
| divided_by_12     | warn       |     15 |
| extreme_value     | block      |     16 |

Most extreme flags (LLM titles; salaries are annual):

| job_title                            | family            | level   |   annual salary |   peer median (annual) |   peer_ratio | cause         | severity   |
|:-------------------------------------|:------------------|:--------|----------------:|-----------------------:|-------------:|:--------------|:-----------|
| Software Development Engineer (SDE)  | software_engineer | mid     |           9e+07 |                 500000 |      180     | extreme_value | block      |
| Senior Java Developer Contractor     | software_engineer | senior  |       12000     |                 900000 |        0.013 | extreme_value | block      |
| Senior IOS Developer                 | software_engineer | senior  |       12000     |                 900000 |        0.013 | extreme_value | block      |
| Senior Software Development Engineer | software_engineer | senior  |       12000     |                 900000 |        0.013 | extreme_value | block      |
| Junior Java Developer                | software_engineer | junior  |        8448     |                 400000 |        0.021 | extreme_value | block      |
| Android Developer                    | software_engineer | mid     |       12000     |                 500000 |        0.024 | extreme_value | block      |
| Software Development Engineer (SDE)  | software_engineer | mid     |       12000     |                 500000 |        0.024 | extreme_value | block      |
| Software Development Engineer        | software_engineer | mid     |       12000     |                 500000 |        0.024 | extreme_value | block      |
| Web Developer                        | software_engineer | mid     |       12000     |                 500000 |        0.024 | extreme_value | block      |
| Software Development Engineer (SDE)  | software_engineer | mid     |       12000     |                 500000 |        0.024 | extreme_value | block      |
| Web Developer                        | software_engineer | mid     |       12000     |                 500000 |        0.024 | extreme_value | block      |
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
| ACCEPT                           |       11123 |
| REJECT - ask company to resubmit |         121 |
| ACCEPT without blocked rows      |          17 |

### US-style (6704 rows, 1 companies, USD)

Rows per cause (a row can have several):

| titles   | rows in peer comparison   |   blocked rows |   peer-comparison flags |   missing_salary |   missing_title |   duplicate_record |   decimal_shift |   below_min_wage |   extreme_value |   annual_as_monthly |   divided_by_12 |   level_salary_mismatch |   statistical_outlier |   future_hire_date |
|:---------|:--------------------------|---------------:|------------------------:|-----------------:|----------------:|-------------------:|----------------:|-----------------:|----------------:|--------------------:|----------------:|------------------------:|----------------------:|-------------------:|
| rules    | 38.7%                     |              9 |                       3 |                5 |               2 |               6005 |               4 |                0 |               0 |                   0 |               0 |                       1 |                     2 |                  0 |
| LLM      | 72.4%                     |              9 |                      70 |                5 |               2 |               6005 |               4 |                0 |               0 |                   0 |               0 |                      47 |                    23 |                  0 |

Peer-comparison causes with LLM titles:

| cause                 | severity   |   rows |
|:----------------------|:-----------|-------:|
| level_salary_mismatch | warn       |     47 |
| statistical_outlier   | warn       |     23 |

Most extreme flags (LLM titles; salaries are annual):

| job_title                 | family            | level   |   annual salary |   peer median (annual) |   peer_ratio | cause                 | severity   |
|:--------------------------|:------------------|:--------|----------------:|-----------------------:|-------------:|:----------------------|:-----------|
| Sales Executive           | sales_rep         | mid     |          160000 |                  35000 |        4.571 | level_salary_mismatch | warn       |
| Software Engineer Manager | software_engineer | lead    |           52612 |                 182392 |        0.288 | level_salary_mismatch | warn       |
| Software Engineer Manager | software_engineer | lead    |           52612 |                 182392 |        0.288 | level_salary_mismatch | warn       |
| Software Engineer Manager | software_engineer | lead    |           52612 |                 182392 |        0.288 | level_salary_mismatch | warn       |
| Software Engineer Manager | software_engineer | lead    |           52612 |                 182392 |        0.288 | level_salary_mismatch | warn       |
| Software Engineer Manager | software_engineer | lead    |           52779 |                 182392 |        0.289 | level_salary_mismatch | warn       |
| Software Engineer Manager | software_engineer | lead    |           52779 |                 182392 |        0.289 | level_salary_mismatch | warn       |
| Software Engineer Manager | software_engineer | lead    |           52779 |                 182392 |        0.289 | level_salary_mismatch | warn       |
| Software Engineer Manager | software_engineer | lead    |           52779 |                 182392 |        0.289 | level_salary_mismatch | warn       |
| Senior Project Engineer   | software_engineer | senior  |           51831 |                 170000 |        0.305 | level_salary_mismatch | warn       |
| Senior Project Engineer   | software_engineer | senior  |           52731 |                 170000 |        0.31  | level_salary_mismatch | warn       |
| Senior Project Engineer   | software_engineer | senior  |           52731 |                 170000 |        0.31  | level_salary_mismatch | warn       |

Mildest flags (LLM titles):

| job_title                 | family            | level   |   annual salary |   peer median (annual) |   peer_ratio | cause               | severity   |
|:--------------------------|:------------------|:--------|----------------:|-----------------------:|-------------:|:--------------------|:-----------|
| Senior Software Architect | software_engineer | lead    |          120000 |                 182392 |        0.658 | statistical_outlier | warn       |
| Software Engineer Manager | software_engineer | lead    |          119836 |                 182392 |        0.657 | statistical_outlier | warn       |
| Software Engineer Manager | software_engineer | lead    |          119836 |                 182392 |        0.657 | statistical_outlier | warn       |
| Software Manager          | software_engineer | lead    |          110000 |                 182392 |        0.603 | statistical_outlier | warn       |
| Software Engineer Manager | software_engineer | lead    |          106686 |                 182392 |        0.585 | statistical_outlier | warn       |
| Software Engineer Manager | software_engineer | lead    |          106686 |                 182392 |        0.585 | statistical_outlier | warn       |

### Italian survey (26551 rows, 1 companies, EUR)

Rows per cause (a row can have several):

| titles   | rows in peer comparison   |   blocked rows |   peer-comparison flags |   missing_salary |   missing_title |   duplicate_record |   decimal_shift |   below_min_wage |   extreme_value |   annual_as_monthly |   divided_by_12 |   level_salary_mismatch |   statistical_outlier |   future_hire_date |
|:---------|:--------------------------|---------------:|------------------------:|-----------------:|----------------:|-------------------:|----------------:|-----------------:|----------------:|--------------------:|----------------:|------------------------:|----------------------:|-------------------:|
| rules    | 15.6%                     |             10 |                      88 |                0 |               0 |                344 |               6 |                0 |               0 |                   4 |               2 |                      82 |                     0 |                  1 |
| LLM      | 66.2%                     |             26 |                     325 |                0 |               0 |                344 |               6 |                0 |               0 |                  24 |               8 |                     293 |                     0 |                  1 |

Peer-comparison causes with LLM titles:

| cause                 | severity   |   rows |
|:----------------------|:-----------|-------:|
| annual_as_monthly     | block      |     17 |
| annual_as_monthly     | warn       |      7 |
| divided_by_12         | block      |      2 |
| divided_by_12         | warn       |      6 |
| level_salary_mismatch | warn       |    293 |

Most extreme flags (LLM titles; salaries are annual):

| job_title           | family            | level   |   annual salary |   peer median (annual) |   peer_ratio | cause             | severity   |
|:--------------------|:------------------|:--------|----------------:|-----------------------:|-------------:|:------------------|:-----------|
| software developer  | software_engineer | mid     |          470000 |                  33000 |       14.242 | annual_as_monthly | block      |
| fullstack developer | software_engineer | mid     |          460000 |                  33000 |       13.939 | annual_as_monthly | block      |
| ai engineer         | software_engineer | mid     |          444600 |                  33000 |       13.473 | annual_as_monthly | block      |
| fullstack developer | software_engineer | mid     |          370000 |                  33000 |       11.212 | annual_as_monthly | block      |
| frontend developer  | software_engineer | mid     |          370000 |                  33000 |       11.212 | annual_as_monthly | block      |
| network engineer    | software_engineer | mid     |          360000 |                  33000 |       10.909 | annual_as_monthly | block      |
| software developer  | software_engineer | mid     |          360000 |                  33000 |       10.909 | annual_as_monthly | block      |
| .net developer      | software_engineer | mid     |          350000 |                  33000 |       10.606 | annual_as_monthly | block      |
| software developer  | software_engineer | mid     |          350000 |                  33000 |       10.606 | annual_as_monthly | block      |
| system engineer     | software_engineer | mid     |          350000 |                  33000 |       10.606 | annual_as_monthly | block      |
| data analyst        | data_analyst      | mid     |          345000 |                  33000 |       10.455 | annual_as_monthly | block      |
| software developer  | software_engineer | mid     |          340000 |                  33000 |       10.303 | annual_as_monthly | block      |

Mildest flags (LLM titles):

| job_title                  | family            | level   |   annual salary |   peer median (annual) |   peer_ratio | cause                 | severity   |
|:---------------------------|:------------------|:--------|----------------:|-----------------------:|-------------:|:----------------------|:-----------|
| human resources specialist | hr_analyst        | lead    |           70000 |                  33000 |        2.121 | level_salary_mismatch | warn       |
| fullstack developer        | software_engineer | mid     |           70000 |                  33000 |        2.121 | level_salary_mismatch | warn       |
| software developer         | software_engineer | mid     |           70000 |                  33000 |        2.121 | level_salary_mismatch | warn       |
| software developer         | software_engineer | mid     |           70200 |                  33000 |        2.127 | level_salary_mismatch | warn       |
| software developer         | software_engineer | mid     |           72000 |                  33000 |        2.182 | level_salary_mismatch | warn       |
| software developer         | software_engineer | mid     |           73000 |                  33000 |        2.212 | level_salary_mismatch | warn       |

Validator outcome (LLM titles) against the publisher's `valid` flag:

| publisher          |   blocked |   no issue |   review |
|:-------------------|----------:|-----------:|---------:|
| publisher: invalid |         2 |         81 |        1 |
| publisher: valid   |        24 |      25794 |      649 |

Causes among the 84 rows the publisher marks invalid:

| cause             |   rows |
|:------------------|-------:|
| annual_as_monthly |      1 |
| duplicate_record  |      1 |
| future_hire_date  |      1 |

The same outcome by annual salary band:

| publisher          | annual salary     |   blocked |   no issue |   review |
|:-------------------|:------------------|----------:|-----------:|---------:|
| publisher: invalid | 10,000 to 200,000 |         1 |         81 |        1 |
| publisher: invalid | over 200,000      |         1 |          0 |        0 |
| publisher: valid   | 10,000 to 200,000 |         0 |      25739 |      560 |
| publisher: valid   | over 200,000      |        16 |          7 |        6 |
| publisher: valid   | under 10,000      |         8 |         48 |       83 |
