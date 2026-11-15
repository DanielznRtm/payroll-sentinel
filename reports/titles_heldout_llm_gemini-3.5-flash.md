# Held-out title normalization

File `eval/heldout_titles.csv`: 130 hand-written titles not listed in `taxonomy.py`; 114 inside the taxonomy, 16 outside it (empty family: the right answer is to abstain). Normalizer: **LLM (gemini-3.5-flash)**.

Titles answered by the LLM: 100.0% (the rest fell back to keyword rules).

LLM run: 4 LLM calls (4 HTTP requests, 0 rate-limit (429) responses), 74.2 s in LLM calls, 18.6 s per call; 74.2 s waiting for the API (18.6 s per request), the rest is pacing and retry back-off; 74.2 s in total.

## 1. Titles inside the taxonomy

| metric                          | correct   | titles   | share   |
|:--------------------------------|:----------|:---------|:--------|
| family accuracy                 | 113       | 114      | 0.991   |
| level accuracy                  | 108       | 114      | 0.947   |
| family and level                | 107       | 114      | 0.939   |
| family accuracy when it answers | 113       | 114      | 0.991   |

"When it answers" leaves out the titles where the normalizer abstained.

## 2. Family outcome inside the taxonomy

`wrong family` puts a salary in the wrong peer group without any warning. `abstained` leaves the family empty, so the validator raises `unmapped_title` for human review.

| outcome      | titles   | share   |
|:-------------|:---------|:--------|
| correct      | 113      | 0.991   |
| wrong family | 1        | 0.009   |
| abstained    | 0        | 0.000   |

## 3. Titles outside the taxonomy

Here abstaining is correct; `false mapping` forces the title into a family.

| outcome            | titles   | share   |
|:-------------------|:---------|:--------|
| correct abstention | 16       | 1.000   |
| false mapping      | 0        | 0.000   |

## 4. Every error (7)

| title                                                       | expected_family     | expected_level   | predicted_family    | predicted_level   | error        |
|:------------------------------------------------------------|:--------------------|:-----------------|:--------------------|:------------------|:-------------|
| Pessoa Desenvolvedora Backend Sênior / Especialista | Store | software_engineer   | senior           | software_engineer   | lead              | wrong level  |
| Analista de Dados Pleno/Sênior                              | data_analyst        | mid              | data_analyst        | senior            | wrong level  |
| Analista de Dados Pleno/Sênior de Produto                   | data_analyst        | mid              | data_analyst        | senior            | wrong level  |
| Product Manager Pleno/ Senior Assessoria VIP                | product_manager     | mid              | product_manager     | senior            | wrong level  |
| Assistente de Pré-Vendas SDR                                | sales_rep           | junior           | sales_rep           | mid               | wrong level  |
| Analista de Inteligência Comercial Sênior (501403)          | data_analyst        | senior           | sales_rep           | senior            | wrong family |
| Auxiliar de Operador de Máquinas - EFR (banco de talentos)  | production_operator | junior           | production_operator | mid               | wrong level  |
