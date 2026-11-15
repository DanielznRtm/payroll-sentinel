# How realistic are the synthetic salaries? (State of Data Brazil)

Survey: State of Data Brazil 2025-2026 (Data Hackers and Bain, Kaggle), 3495 answers. Used: CLT employees who are not managers, in the four mapped jobs: 1037 answers. Open band (over R$ 40,000, left out): 12. Malformed band ('R$ 25.001 a R$ 3000'): 1.

Monthly salary medians in R$. Survey medians are grouped-data medians over salary bands, shown only with at least 15 answers. Synthetic medians come from generate(seed=42, n_companies=200), clean full-time CLT rows only.

## Median salary by family and level

| scope     | family            | level   |   survey answers | survey median   |   synthetic median |   synthetic / survey |
|:----------|:------------------|:--------|-----------------:|:----------------|-------------------:|---------------------:|
| Brazil    | data_analyst      | junior  |              113 | 4,200           |              4,210 |                 1    |
| Brazil    | data_analyst      | mid     |              246 | 6,457           |              6,550 |                 1.01 |
| Brazil    | data_analyst      | senior  |              184 | 9,563           |              9,410 |                 0.98 |
| Brazil    | data_analyst      | lead    |               59 | 13,100          |             12,915 |                 0.99 |
| Brazil    | data_scientist    | junior  |               45 | 6,875           |              6,280 |                 0.91 |
| Brazil    | data_scientist    | mid     |              116 | 9,241           |              9,520 |                 1.03 |
| Brazil    | data_scientist    | senior  |              125 | 14,714          |             13,770 |                 0.94 |
| Brazil    | data_scientist    | lead    |               61 | 17,059          |             18,565 |                 1.09 |
| Brazil    | product_manager   | mid     |                4 | -               |             11,250 |               nan    |
| Brazil    | product_manager   | senior  |               12 | -               |             16,120 |               nan    |
| Brazil    | product_manager   | lead    |                8 | -               |             21,140 |               nan    |
| Brazil    | software_engineer | junior  |               11 | -               |              5,990 |               nan    |
| Brazil    | software_engineer | mid     |               18 | 6,400           |              9,190 |                 1.44 |
| Brazil    | software_engineer | senior  |               24 | 13,091          |             13,200 |                 1.01 |
| Brazil    | software_engineer | lead    |               11 | -               |             17,700 |               nan    |
| São Paulo | data_analyst      | junior  |               37 | 4,833           |              4,800 |                 0.99 |
| São Paulo | data_analyst      | mid     |              104 | 6,774           |              7,720 |                 1.14 |
| São Paulo | data_analyst      | senior  |               89 | 10,375          |             10,350 |                 1    |
| São Paulo | data_analyst      | lead    |               32 | 13,600          |             15,270 |                 1.12 |
| São Paulo | data_scientist    | junior  |               17 | 8,250           |              7,820 |                 0.95 |
| São Paulo | data_scientist    | mid     |               42 | 10,000          |             10,855 |                 1.09 |
| São Paulo | data_scientist    | senior  |               63 | 14,818          |             15,690 |                 1.06 |
| São Paulo | data_scientist    | lead    |               31 | 18,200          |             21,540 |                 1.18 |
| São Paulo | product_manager   | mid     |                1 | -               |             13,545 |               nan    |
| São Paulo | product_manager   | senior  |                7 | -               |             17,885 |               nan    |
| São Paulo | product_manager   | lead    |                6 | -               |             24,905 |               nan    |
| São Paulo | software_engineer | junior  |                3 | -               |              6,840 |               nan    |
| São Paulo | software_engineer | mid     |                9 | -               |             10,520 |               nan    |
| São Paulo | software_engineer | senior  |                6 | -               |             16,220 |               nan    |
| São Paulo | software_engineer | lead    |                6 | -               |             22,080 |               nan    |

## Pay by level relative to mid level

The synthetic generator uses fixed multipliers (junior 0.65, senior 1.45, lead 1.95).

| scope     | family            | level / mid   |   survey |   synthetic |
|:----------|:------------------|:--------------|---------:|------------:|
| Brazil    | data_analyst      | junior        |     0.65 |        0.64 |
| Brazil    | data_analyst      | senior        |     1.48 |        1.44 |
| Brazil    | data_analyst      | lead          |     2.03 |        1.97 |
| Brazil    | data_scientist    | junior        |     0.74 |        0.66 |
| Brazil    | data_scientist    | senior        |     1.59 |        1.45 |
| Brazil    | data_scientist    | lead          |     1.85 |        1.95 |
| Brazil    | software_engineer | senior        |     2.05 |        1.44 |
| São Paulo | data_analyst      | junior        |     0.71 |        0.62 |
| São Paulo | data_analyst      | senior        |     1.53 |        1.34 |
| São Paulo | data_analyst      | lead          |     2.01 |        1.98 |
| São Paulo | data_scientist    | junior        |     0.82 |        0.72 |
| São Paulo | data_scientist    | senior        |     1.48 |        1.45 |
| São Paulo | data_scientist    | lead          |     1.82 |        1.98 |
