# How realistic are the synthetic salaries? (RAIS)

Source: RAIS microdata, file `RAIS_VINC_PUB_SP.7z` (Ministério do Trabalho e Emprego). Rows read: 25,497,764. Kept: CLT jobs active on 31 December, 40-44 h/week, not intermittent, in the approved CBO codes, in São Paulo, Campinas and Sorocaba: 509,542 jobs. Left out because December pay was empty or zero: 36,904.

RAIS December pay includes overtime and commissions paid that month (not the 13th salary); the synthetic `monthly_salary` is base pay. RAIS has no seniority level, so both sides pool every level and the medians also reflect the level mix. Synthetic: generate(seed=42, n_companies=200), clean full-time CLT rows. Groups with fewer than 30 rows are not shown.

`log-pay SD` is the spread of log pay inside a group: the peer comparison flags salaries far from their peers on this scale, so a wider real spread means real errors hide more easily.

| scope     | family                 |   rows |   median |   median (synthetic) |   synthetic / real median |   p25 |    p75 |   log-pay SD |   log-pay SD (synthetic) |
|:----------|:-----------------------|-------:|---------:|---------------------:|--------------------------:|------:|-------:|-------------:|-------------------------:|
| 3 cities  | customer_support       |  40901 |    3,857 |                3,130 |                      0.81 | 2,546 |  6,538 |         0.72 |                     0.4  |
| 3 cities  | data_scientist         |    958 |   12,413 |               11,160 |                      0.9  | 8,336 | 17,079 |         0.59 |                     0.42 |
| 3 cities  | financial_analyst      |  32158 |    6,573 |                6,440 |                      0.98 | 4,628 |  9,805 |         0.57 |                     0.42 |
| 3 cities  | hr_analyst             |  30348 |    5,224 |                5,530 |                      1.06 | 3,769 |  7,699 |         0.54 |                     0.4  |
| 3 cities  | maintenance_technician |  35853 |    4,639 |                4,035 |                      0.87 | 3,282 |  7,011 |         0.6  |                     0.4  |
| 3 cities  | production_operator    |  68863 |    2,594 |                2,390 |                      0.92 | 2,186 |  3,329 |         0.4  |                     0.37 |
| 3 cities  | sales_rep              | 189033 |    3,267 |                5,960 |                      1.82 | 2,276 |  6,823 |         0.84 |                     0.42 |
| 3 cities  | software_engineer      | 111428 |   10,093 |               10,100 |                      1    | 6,328 | 15,000 |         0.66 |                     0.42 |
| São Paulo | customer_support       |  37796 |    3,809 |                3,450 |                      0.91 | 2,519 |  6,495 |         0.72 |                     0.41 |
| São Paulo | data_scientist         |    884 |   12,719 |               10,530 |                      0.83 | 8,728 | 17,690 |         0.58 |                     0.41 |
| São Paulo | financial_analyst      |  30580 |    6,690 |                6,920 |                      1.03 | 4,725 |  9,943 |         0.57 |                     0.44 |
| São Paulo | hr_analyst             |  27428 |    5,272 |                5,770 |                      1.09 | 3,794 |  7,777 |         0.54 |                     0.38 |
| São Paulo | maintenance_technician |  28111 |    4,576 |                4,410 |                      0.96 | 3,236 |  6,863 |         0.6  |                     0.38 |
| São Paulo | production_operator    |  50135 |    2,474 |                2,540 |                      1.03 | 2,121 |  3,075 |         0.39 |                     0.37 |
| São Paulo | sales_rep              | 162257 |    3,264 |                6,450 |                      1.98 | 2,265 |  7,000 |         0.86 |                     0.42 |
| São Paulo | software_engineer      |  99865 |   10,268 |               10,830 |                      1.05 | 6,421 | 15,201 |         0.66 |                     0.42 |
| Campinas  | customer_support       |   2495 |    4,500 |                3,065 |                      0.68 | 3,042 |  7,347 |         0.64 |                     0.39 |
| Campinas  | data_scientist         |     71 |    7,665 |               12,235 |                      1.6  | 5,002 | 11,261 |         0.49 |                     0.44 |
| Campinas  | financial_analyst      |   1086 |    5,046 |                6,310 |                      1.25 | 3,830 |  7,265 |         0.51 |                     0.41 |
| Campinas  | hr_analyst             |   2002 |    5,000 |                5,265 |                      1.05 | 3,735 |  7,122 |         0.5  |                     0.4  |
| Campinas  | maintenance_technician |   4187 |    4,761 |                3,780 |                      0.79 | 3,389 |  7,581 |         0.61 |                     0.41 |
| Campinas  | production_operator    |   7537 |    3,087 |                2,385 |                      0.77 | 2,491 |  4,106 |         0.42 |                     0.37 |
| Campinas  | sales_rep              |  18299 |    3,560 |                5,760 |                      1.62 | 2,455 |  6,550 |         0.76 |                     0.42 |
| Campinas  | software_engineer      |  10336 |    9,117 |               10,360 |                      1.14 | 5,960 | 13,316 |         0.58 |                     0.41 |
| Sorocaba  | customer_support       |    610 |    4,135 |                3,010 |                      0.73 | 2,511 |  6,778 |         0.7  |                     0.4  |
| Sorocaba  | financial_analyst      |    492 |    4,499 |                6,040 |                      1.34 | 3,404 |  5,885 |         0.46 |                     0.41 |
| Sorocaba  | hr_analyst             |    918 |    4,508 |                5,305 |                      1.18 | 3,273 |  6,415 |         0.53 |                     0.42 |
| Sorocaba  | maintenance_technician |   3555 |    4,963 |                3,600 |                      0.73 | 3,570 |  7,620 |         0.57 |                     0.4  |
| Sorocaba  | production_operator    |  11191 |    2,964 |                2,155 |                      0.73 | 2,418 |  3,774 |         0.41 |                     0.35 |
| Sorocaba  | sales_rep              |   8477 |    2,778 |                5,535 |                      1.99 | 2,139 |  4,792 |         0.71 |                     0.42 |
| Sorocaba  | software_engineer      |   1227 |    7,495 |                9,180 |                      1.22 | 4,301 | 12,165 |         0.64 |                     0.41 |

## By CBO code (3 cities)

A family pools several CBO occupations; their pay can differ a lot (for example retail sellers and sales managers in `sales_rep`).

| family                 |    cbo |   rows |   share of family |   median |
|:-----------------------|-------:|-------:|------------------:|---------:|
| customer_support       | 212420 |  25031 |             0.612 |    5,000 |
| customer_support       | 422310 |   6351 |             0.155 |    2,077 |
| customer_support       | 422315 |   3047 |             0.074 |    2,937 |
| customer_support       | 142365 |   1651 |             0.04  |    3,578 |
| customer_support       | 422320 |   1497 |             0.037 |    2,748 |
| customer_support       | 422335 |   1424 |             0.035 |    2,824 |
| customer_support       | 142360 |   1368 |             0.033 |    4,891 |
| customer_support       | 422305 |    532 |             0.013 |    2,363 |
| data_scientist         | 211220 |    958 |             1     |   12,413 |
| financial_analyst      | 252545 |  26844 |             0.835 |    6,507 |
| financial_analyst      | 252525 |   4721 |             0.147 |    7,188 |
| financial_analyst      | 252510 |    593 |             0.018 |    6,111 |
| hr_analyst             | 252405 |  30348 |             1     |    5,224 |
| maintenance_technician | 911305 |   7921 |             0.221 |    4,200 |
| maintenance_technician | 951105 |   6936 |             0.194 |    4,340 |
| maintenance_technician | 314410 |   3335 |             0.093 |    4,356 |
| maintenance_technician | 313205 |   2961 |             0.083 |    4,093 |
| maintenance_technician | 313120 |   2142 |             0.06  |    5,157 |
| maintenance_technician | 300305 |   1858 |             0.052 |    5,284 |
| maintenance_technician | 910105 |   1780 |             0.05  |    5,818 |
| maintenance_technician | 950110 |   1603 |             0.045 |    6,363 |
| maintenance_technician | 954125 |   1081 |             0.03  |    3,751 |
| maintenance_technician | 950105 |   1016 |             0.028 |    6,493 |
| maintenance_technician | 300105 |    803 |             0.022 |    5,997 |
| maintenance_technician | 313210 |    708 |             0.02  |    5,494 |
| maintenance_technician | 314405 |    632 |             0.018 |    4,612 |
| maintenance_technician | 950305 |    626 |             0.017 |   11,211 |
| maintenance_technician | 313125 |    446 |             0.012 |    4,985 |
| maintenance_technician | 919105 |    427 |             0.012 |    3,298 |
| maintenance_technician | 911120 |    421 |             0.012 |    3,921 |
| maintenance_technician | 911110 |    357 |             0.01  |    4,221 |
| maintenance_technician | 911320 |    265 |             0.007 |    4,794 |
| maintenance_technician | 911325 |    229 |             0.006 |    4,515 |
| maintenance_technician | 911310 |     91 |             0.003 |    3,874 |
| maintenance_technician | 911115 |     87 |             0.002 |    4,386 |
| maintenance_technician | 911105 |     66 |             0.002 |    3,237 |
| production_operator    | 784205 |  56090 |             0.815 |    2,458 |
| production_operator    | 721215 |   6831 |             0.099 |    3,851 |
| production_operator    | 813125 |   2125 |             0.031 |    4,607 |
| production_operator    | 721430 |   1468 |             0.021 |    3,928 |
| production_operator    | 721405 |   1255 |             0.018 |    4,485 |
| production_operator    | 721410 |    481 |             0.007 |    5,155 |
| production_operator    | 721425 |    424 |             0.006 |    4,043 |
| production_operator    | 721420 |    119 |             0.002 |    3,228 |
| production_operator    | 721415 |     70 |             0.001 |    6,950 |
| sales_rep              | 521110 | 126879 |             0.671 |    2,713 |
| sales_rep              | 142320 |  21226 |             0.112 |   17,000 |
| sales_rep              | 521105 |  16413 |             0.087 |    3,944 |
| sales_rep              | 354120 |   8336 |             0.044 |    4,392 |
| sales_rep              | 354135 |   7501 |             0.04  |    8,721 |
| sales_rep              | 354140 |   5495 |             0.029 |    3,972 |
| sales_rep              | 354145 |   2822 |             0.015 |    6,781 |
| sales_rep              | 354705 |    361 |             0.002 |    4,728 |
| software_engineer      | 212405 |  84842 |             0.761 |   10,422 |
| software_engineer      | 317110 |  15742 |             0.141 |    8,114 |
| software_engineer      | 212205 |   3776 |             0.034 |   16,146 |
| software_engineer      | 212430 |   3291 |             0.03  |    7,000 |
| software_engineer      | 212425 |   2223 |             0.02  |   17,135 |
| software_engineer      | 317105 |   1022 |             0.009 |    6,990 |
| software_engineer      | 317120 |    532 |             0.005 |    7,490 |
