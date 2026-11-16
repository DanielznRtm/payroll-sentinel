# How realistic are the synthetic salaries? (RAIS)

Source: RAIS microdata, file `RAIS_VINC_PUB_SP.7z` (Ministério do Trabalho e Emprego). Rows read: 25,497,764. Kept: CLT jobs active on 31 December, 40-44 h/week, not intermittent, in the approved CBO codes, in São Paulo, Campinas and Sorocaba: 509,542 jobs, of which 361,437 are compared (retail sellers and sales managers are not: the synthetic sales family is B2B selling). Left out because December pay was empty or zero: 36,904.

RAIS December pay includes overtime and commissions paid that month (not the 13th salary); the synthetic `monthly_salary` is base pay. RAIS has no seniority level, so both sides pool every level and the medians also reflect the level mix. Synthetic: generate(seed=42, n_companies=200), clean full-time CLT rows. Groups with fewer than 30 rows are not shown.

`log-pay SD` is the spread of log pay inside a group: the peer comparison flags salaries far from their peers on this scale, so a wider real spread means real errors hide more easily.

| scope     | family                 |   rows |   median |   median (synthetic) |   synthetic / real median |   p25 |   p25 (synthetic) |    p75 |   p75 (synthetic) |   log-pay SD |   log-pay SD (synthetic) |
|:----------|:-----------------------|-------:|---------:|---------------------:|--------------------------:|------:|------------------:|-------:|------------------:|-------------:|-------------------------:|
| 3 cities  | customer_support       |  40901 |    3,857 |                3,320 |                      0.86 | 2,546 |             1,895 |  6,538 |             5,860 |         0.72 |                     0.69 |
| 3 cities  | data_scientist         |    958 |   12,413 |               10,890 |                      0.88 | 8,336 |             7,040 | 17,079 |            15,600 |         0.59 |                     0.58 |
| 3 cities  | financial_analyst      |  32158 |    6,573 |                6,350 |                      0.97 | 4,628 |             4,430 |  9,805 |             9,250 |         0.57 |                     0.55 |
| 3 cities  | hr_analyst             |  30348 |    5,224 |                5,620 |                      1.08 | 3,769 |             3,680 |  7,699 |             8,025 |         0.54 |                     0.59 |
| 3 cities  | maintenance_technician |  35853 |    4,639 |                4,675 |                      1.01 | 3,282 |             2,902 |  7,011 |             7,362 |         0.6  |                     0.62 |
| 3 cities  | production_operator    |  68863 |    2,594 |                2,780 |                      1.07 | 2,186 |             1,970 |  3,329 |             3,990 |         0.4  |                     0.42 |
| 3 cities  | sales_rep              |  40928 |    4,772 |                4,400 |                      0.92 | 2,771 |             2,428 |  9,196 |             7,955 |         0.79 |                     0.78 |
| 3 cities  | software_engineer      | 111428 |   10,093 |                9,680 |                      0.96 | 6,328 |             6,282 | 15,000 |            15,518 |         0.66 |                     0.66 |
| São Paulo | customer_support       |  37796 |    3,809 |                3,825 |                      1    | 2,519 |             2,000 |  6,495 |             6,402 |         0.72 |                     0.72 |
| São Paulo | data_scientist         |    884 |   12,719 |               11,350 |                      0.89 | 8,728 |             7,050 | 17,690 |            14,760 |         0.58 |                     0.57 |
| São Paulo | financial_analyst      |  30580 |    6,690 |                7,220 |                      1.08 | 4,725 |             4,620 |  9,943 |            10,688 |         0.57 |                     0.57 |
| São Paulo | hr_analyst             |  27428 |    5,272 |                6,020 |                      1.14 | 3,794 |             4,340 |  7,777 |             8,470 |         0.54 |                     0.54 |
| São Paulo | maintenance_technician |  28111 |    4,576 |                4,700 |                      1.03 | 3,236 |             2,920 |  6,863 |             7,070 |         0.6  |                     0.6  |
| São Paulo | production_operator    |  50135 |    2,474 |                2,540 |                      1.03 | 2,121 |             1,865 |  3,075 |             3,605 |         0.39 |                     0.39 |
| São Paulo | sales_rep              |  35059 |    4,758 |                4,750 |                      1    | 2,745 |             2,610 |  9,312 |             8,840 |         0.8  |                     0.8  |
| São Paulo | software_engineer      |  99865 |   10,268 |               10,795 |                      1.05 | 6,421 |             6,808 | 15,201 |            18,048 |         0.66 |                     0.67 |
| Campinas  | customer_support       |   2495 |    4,500 |                3,275 |                      0.73 | 3,042 |             1,930 |  7,347 |             6,098 |         0.64 |                     0.7  |
| Campinas  | data_scientist         |     71 |    7,665 |               11,685 |                      1.52 | 5,002 |             7,350 | 11,261 |            16,948 |         0.49 |                     0.59 |
| Campinas  | financial_analyst      |   1086 |    5,046 |                6,355 |                      1.26 | 3,830 |             4,655 |  7,265 |             8,952 |         0.51 |                     0.53 |
| Campinas  | hr_analyst             |   2002 |    5,000 |                5,670 |                      1.13 | 3,735 |             3,832 |  7,122 |             8,368 |         0.5  |                     0.6  |
| Campinas  | maintenance_technician |   4187 |    4,761 |                4,625 |                      0.97 | 3,389 |             2,792 |  7,581 |             7,478 |         0.61 |                     0.63 |
| Campinas  | production_operator    |   7537 |    3,087 |                2,855 |                      0.92 | 2,491 |             2,090 |  4,106 |             4,178 |         0.42 |                     0.42 |
| Campinas  | sales_rep              |   4425 |    5,051 |                4,270 |                      0.85 | 3,096 |             2,360 |  9,087 |             7,850 |         0.75 |                     0.78 |
| Campinas  | software_engineer      |  10336 |    9,117 |               10,530 |                      1.15 | 5,960 |             6,870 | 13,316 |            16,160 |         0.58 |                     0.65 |
| Sorocaba  | customer_support       |    610 |    4,135 |                3,070 |                      0.74 | 2,511 |             1,840 |  6,778 |             5,290 |         0.7  |                     0.65 |
| Sorocaba  | financial_analyst      |    492 |    4,499 |                5,650 |                      1.26 | 3,404 |             4,035 |  5,885 |             8,315 |         0.46 |                     0.52 |
| Sorocaba  | hr_analyst             |    918 |    4,508 |                5,160 |                      1.14 | 3,273 |             3,282 |  6,415 |             7,500 |         0.53 |                     0.59 |
| Sorocaba  | maintenance_technician |   3555 |    4,963 |                4,570 |                      0.92 | 3,570 |             2,930 |  7,620 |             7,370 |         0.57 |                     0.63 |
| Sorocaba  | production_operator    |  11191 |    2,964 |                2,900 |                      0.98 | 2,418 |             2,030 |  3,774 |             4,265 |         0.41 |                     0.43 |
| Sorocaba  | sales_rep              |   1444 |    4,302 |                4,175 |                      0.97 | 2,612 |             2,352 |  7,769 |             7,548 |         0.72 |                     0.74 |
| Sorocaba  | software_engineer      |   1227 |    7,495 |                8,280 |                      1.1  | 4,301 |             5,585 | 12,165 |            12,670 |         0.64 |                     0.63 |

## City index by kind of job

Pay in the city relative to São Paulo for the same CBO occupation (codes with at least 30 jobs in both cities), averaged in log space and weighted by the city's jobs. `index (generator)` is the value in taxonomy.py.

| city     | kind       |   codes |   jobs |   index |   index (generator) |
|:---------|:-----------|--------:|-------:|--------:|--------------------:|
| Campinas | industrial |      22 |  11610 |   1.106 |                1.11 |
| Campinas | office     |      22 |  20361 |   0.942 |                0.94 |
| Sorocaba | industrial |      24 |  14636 |   1.142 |                1.14 |
| Sorocaba | office     |      16 |   4585 |   0.797 |                0.8  |

## By CBO code (3 cities)

A family pools several CBO occupations; their pay can differ a lot. Codes marked `compared: no` are listed here and left out of every other table.

| family                 |    cbo |   rows |   share of family |   median | compared          |
|:-----------------------|-------:|-------:|------------------:|---------:|:------------------|
| customer_support       | 212420 |  25031 |             0.612 |    5,000 | yes               |
| customer_support       | 422310 |   6351 |             0.155 |    2,077 | yes               |
| customer_support       | 422315 |   3047 |             0.074 |    2,937 | yes               |
| customer_support       | 142365 |   1651 |             0.04  |    3,578 | yes               |
| customer_support       | 422320 |   1497 |             0.037 |    2,748 | yes               |
| customer_support       | 422335 |   1424 |             0.035 |    2,824 | yes               |
| customer_support       | 142360 |   1368 |             0.033 |    4,891 | yes               |
| customer_support       | 422305 |    532 |             0.013 |    2,363 | yes               |
| data_scientist         | 211220 |    958 |             1     |   12,413 | yes               |
| financial_analyst      | 252545 |  26844 |             0.835 |    6,507 | yes               |
| financial_analyst      | 252525 |   4721 |             0.147 |    7,188 | yes               |
| financial_analyst      | 252510 |    593 |             0.018 |    6,111 | yes               |
| hr_analyst             | 252405 |  30348 |             1     |    5,224 | yes               |
| maintenance_technician | 911305 |   7921 |             0.221 |    4,200 | yes               |
| maintenance_technician | 951105 |   6936 |             0.194 |    4,340 | yes               |
| maintenance_technician | 314410 |   3335 |             0.093 |    4,356 | yes               |
| maintenance_technician | 313205 |   2961 |             0.083 |    4,093 | yes               |
| maintenance_technician | 313120 |   2142 |             0.06  |    5,157 | yes               |
| maintenance_technician | 300305 |   1858 |             0.052 |    5,284 | yes               |
| maintenance_technician | 910105 |   1780 |             0.05  |    5,818 | yes               |
| maintenance_technician | 950110 |   1603 |             0.045 |    6,363 | yes               |
| maintenance_technician | 954125 |   1081 |             0.03  |    3,751 | yes               |
| maintenance_technician | 950105 |   1016 |             0.028 |    6,493 | yes               |
| maintenance_technician | 300105 |    803 |             0.022 |    5,997 | yes               |
| maintenance_technician | 313210 |    708 |             0.02  |    5,494 | yes               |
| maintenance_technician | 314405 |    632 |             0.018 |    4,612 | yes               |
| maintenance_technician | 950305 |    626 |             0.017 |   11,211 | yes               |
| maintenance_technician | 313125 |    446 |             0.012 |    4,985 | yes               |
| maintenance_technician | 919105 |    427 |             0.012 |    3,298 | yes               |
| maintenance_technician | 911120 |    421 |             0.012 |    3,921 | yes               |
| maintenance_technician | 911110 |    357 |             0.01  |    4,221 | yes               |
| maintenance_technician | 911320 |    265 |             0.007 |    4,794 | yes               |
| maintenance_technician | 911325 |    229 |             0.006 |    4,515 | yes               |
| maintenance_technician | 911310 |     91 |             0.003 |    3,874 | yes               |
| maintenance_technician | 911115 |     87 |             0.002 |    4,386 | yes               |
| maintenance_technician | 911105 |     66 |             0.002 |    3,237 | yes               |
| production_operator    | 784205 |  56090 |             0.815 |    2,458 | yes               |
| production_operator    | 721215 |   6831 |             0.099 |    3,851 | yes               |
| production_operator    | 813125 |   2125 |             0.031 |    4,607 | yes               |
| production_operator    | 721430 |   1468 |             0.021 |    3,928 | yes               |
| production_operator    | 721405 |   1255 |             0.018 |    4,485 | yes               |
| production_operator    | 721410 |    481 |             0.007 |    5,155 | yes               |
| production_operator    | 721425 |    424 |             0.006 |    4,043 | yes               |
| production_operator    | 721420 |    119 |             0.002 |    3,228 | yes               |
| production_operator    | 721415 |     70 |             0.001 |    6,950 | yes               |
| sales_rep              | 521110 | 126879 |             0.671 |    2,713 | no: retail seller |
| sales_rep              | 142320 |  21226 |             0.112 |   17,000 | no: sales manager |
| sales_rep              | 521105 |  16413 |             0.087 |    3,944 | yes               |
| sales_rep              | 354120 |   8336 |             0.044 |    4,392 | yes               |
| sales_rep              | 354135 |   7501 |             0.04  |    8,721 | yes               |
| sales_rep              | 354140 |   5495 |             0.029 |    3,972 | yes               |
| sales_rep              | 354145 |   2822 |             0.015 |    6,781 | yes               |
| sales_rep              | 354705 |    361 |             0.002 |    4,728 | yes               |
| software_engineer      | 212405 |  84842 |             0.761 |   10,422 | yes               |
| software_engineer      | 317110 |  15742 |             0.141 |    8,114 | yes               |
| software_engineer      | 212205 |   3776 |             0.034 |   16,146 | yes               |
| software_engineer      | 212430 |   3291 |             0.03  |    7,000 | yes               |
| software_engineer      | 212425 |   2223 |             0.02  |   17,135 | yes               |
| software_engineer      | 317105 |   1022 |             0.009 |    6,990 | yes               |
| software_engineer      | 317120 |    532 |             0.005 |    7,490 | yes               |
