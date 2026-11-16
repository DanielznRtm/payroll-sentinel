# How realistic are the synthetic salaries? (State of Data Brazil)

Survey: State of Data Brazil 2025-2026 (Data Hackers and Bain, Kaggle), 3495 answers. Used: CLT employees who are not managers, in the four mapped jobs: 1037 answers. Open band (over R$ 40,000, left out): 12. Malformed band ('R$ 25.001 a R$ 3000'): 1.

Monthly salary medians in R$. Survey medians are grouped-data medians over salary bands, shown only with at least 15 answers. Synthetic medians come from generate(seed=42, n_companies=200), clean full-time CLT rows only.

## Median salary by family and level

| scope     | family            | level   |   survey answers | survey median   |   synthetic median |   synthetic / survey |
|:----------|:------------------|:--------|-----------------:|:----------------|-------------------:|---------------------:|
| Brazil    | data_analyst      | junior  |              113 | 4,200           |              4,130 |                 0.98 |
| Brazil    | data_analyst      | mid     |              246 | 6,457           |              6,775 |                 1.05 |
| Brazil    | data_analyst      | senior  |              184 | 9,563           |              9,455 |                 0.99 |
| Brazil    | data_analyst      | lead    |               59 | 13,100          |             12,775 |                 0.98 |
| Brazil    | data_scientist    | junior  |               45 | 6,875           |              6,330 |                 0.92 |
| Brazil    | data_scientist    | mid     |              116 | 9,241           |              9,225 |                 1    |
| Brazil    | data_scientist    | senior  |              125 | 14,714          |             13,210 |                 0.9  |
| Brazil    | data_scientist    | lead    |               61 | 17,059          |             18,075 |                 1.06 |
| Brazil    | product_manager   | mid     |                4 | -               |             11,730 |               nan    |
| Brazil    | product_manager   | senior  |               12 | -               |             15,985 |               nan    |
| Brazil    | product_manager   | lead    |                8 | -               |             20,730 |               nan    |
| Brazil    | software_engineer | junior  |               11 | -               |              5,870 |               nan    |
| Brazil    | software_engineer | mid     |               18 | 6,400           |              9,390 |                 1.47 |
| Brazil    | software_engineer | senior  |               24 | 13,091          |             13,060 |                 1    |
| Brazil    | software_engineer | lead    |               11 | -               |             18,340 |               nan    |
| São Paulo | data_analyst      | junior  |               37 | 4,833           |              4,990 |                 1.03 |
| São Paulo | data_analyst      | mid     |              104 | 6,774           |              8,650 |                 1.28 |
| São Paulo | data_analyst      | senior  |               89 | 10,375          |             10,440 |                 1.01 |
| São Paulo | data_analyst      | lead    |               32 | 13,600          |             15,960 |                 1.17 |
| São Paulo | data_scientist    | junior  |               17 | 8,250           |              7,700 |                 0.93 |
| São Paulo | data_scientist    | mid     |               42 | 10,000          |              9,530 |                 0.95 |
| São Paulo | data_scientist    | senior  |               63 | 14,818          |             13,840 |                 0.93 |
| São Paulo | data_scientist    | lead    |               31 | 18,200          |             20,780 |                 1.14 |
| São Paulo | product_manager   | mid     |                1 | -               |             14,885 |               nan    |
| São Paulo | product_manager   | senior  |                7 | -               |             17,820 |               nan    |
| São Paulo | product_manager   | lead    |                6 | -               |             22,130 |               nan    |
| São Paulo | software_engineer | junior  |                3 | -               |              6,830 |               nan    |
| São Paulo | software_engineer | mid     |                9 | -               |             10,470 |               nan    |
| São Paulo | software_engineer | senior  |                6 | -               |             17,260 |               nan    |
| São Paulo | software_engineer | lead    |                6 | -               |             24,210 |               nan    |

## Pay by level relative to mid level

The synthetic generator uses fixed multipliers (junior 0.65, senior 1.45, lead 1.95).

| scope     | family            | level / mid   |   survey |   synthetic |
|:----------|:------------------|:--------------|---------:|------------:|
| Brazil    | data_analyst      | junior        |     0.65 |        0.61 |
| Brazil    | data_analyst      | senior        |     1.48 |        1.4  |
| Brazil    | data_analyst      | lead          |     2.03 |        1.89 |
| Brazil    | data_scientist    | junior        |     0.74 |        0.69 |
| Brazil    | data_scientist    | senior        |     1.59 |        1.43 |
| Brazil    | data_scientist    | lead          |     1.85 |        1.96 |
| Brazil    | software_engineer | senior        |     2.05 |        1.39 |
| São Paulo | data_analyst      | junior        |     0.71 |        0.58 |
| São Paulo | data_analyst      | senior        |     1.53 |        1.21 |
| São Paulo | data_analyst      | lead          |     2.01 |        1.85 |
| São Paulo | data_scientist    | junior        |     0.82 |        0.81 |
| São Paulo | data_scientist    | senior        |     1.48 |        1.45 |
| São Paulo | data_scientist    | lead          |     1.82 |        2.18 |
