# Held-out title normalization

File `eval/heldout_titles.csv`: 130 hand-written titles not listed in `taxonomy.py`; 114 inside the taxonomy, 16 outside it (empty family: the right answer is to abstain). Normalizer: **LLM (gemini-3.5-flash-lite)**.

Titles answered by the LLM: 100.0% (the rest fell back to keyword rules).

LLM run: 4 LLM calls (4 HTTP requests, 0 rate-limit (429) responses), 15.1 s in LLM calls, 3.8 s per call; 15.2 s in total.

## 1. Titles inside the taxonomy

| metric                          | correct   | titles   | share   |
|:--------------------------------|:----------|:---------|:--------|
| family accuracy                 | 111       | 114      | 0.974   |
| level accuracy                  | 102       | 114      | 0.895   |
| family and level                | 99        | 114      | 0.868   |
| family accuracy when it answers | 111       | 112      | 0.991   |

"When it answers" leaves out the titles where the normalizer abstained.

## 2. Family outcome inside the taxonomy

`wrong family` puts a salary in the wrong peer group without any warning. `abstained` leaves the family empty, so the validator raises `unmapped_title` for human review.

| outcome      | titles   | share   |
|:-------------|:---------|:--------|
| correct      | 111      | 0.974   |
| wrong family | 1        | 0.009   |
| abstained    | 2        | 0.018   |

## 3. Titles outside the taxonomy

Here abstaining is correct; `false mapping` forces the title into a family.

| outcome            | titles   | share   |
|:-------------------|:---------|:--------|
| correct abstention | 14       | 0.875   |
| false mapping      | 2        | 0.125   |

## 4. Every error (17)

| title                                                                 | expected_family        | expected_level   | predicted_family       | predicted_level   | error         |
|:----------------------------------------------------------------------|:-----------------------|:-----------------|:-----------------------|:------------------|:--------------|
| Pessoa Desenvolvedora Backend Peno I Open Banking                     | software_engineer      | mid              | software_engineer      | junior            | wrong level   |
| Pessoa Desenvolvedora Backend Sênior / Especialista | Store           | software_engineer      | senior           | software_engineer      | lead              | wrong level   |
| Analista de Dados Pleno/Sênior                                        | data_analyst           | mid              | data_analyst           | senior            | wrong level   |
| Analista de Dados Pleno/Sênior de Produto                             | data_analyst           | mid              | data_analyst           | senior            | wrong level   |
| Contratação: PJ | Cientista de Dados Sênior (Foco: Dev Web Fullstack) | data_scientist         | senior           | software_engineer      | senior            | wrong family  |
| Product Manager Pleno/ Senior Assessoria VIP                          | product_manager        | mid              | product_manager        | senior            | wrong level   |
| Associate Product Manager Júnior | Pleno                              | product_manager        | junior           | product_manager        | mid               | wrong level   |
| ANALISTA INTELIGENCIA E INOVACAO DE RH III                            | hr_analyst             | senior           | hr_analyst             | lead              | wrong level   |
| EXECUTIVO (A) DE VENDAS ISP II                                        | sales_rep              | mid              | sales_rep              | senior            | wrong level   |
| Ambev I Operador (a) de Produção (Filial Vidros RJ)                   | production_operator    | mid              | production_operator    | junior            | wrong level   |
| Técnico (a) de Manutenção Elétrica ou Automação PTG                   | maintenance_technician | mid              | maintenance_technician | junior            | wrong level   |
| Técnico(a) de Manutenção Eletrônica                                   | maintenance_technician | mid              | maintenance_technician | junior            | wrong level   |
| Product Marketing Manager (PMM) – Remoto                              | -                      | -                | product_manager        | mid               | false mapping |
| Analista de Inteligência Comercial Sênior (501403)                    | data_analyst           | senior           | -                      | senior            | abstained     |
| GERENTE COMERCIAL                                                     | sales_rep              | lead             | -                      | lead              | abstained     |
| Operador de Empilhadeira                                              | -                      | -                | production_operator    | mid               | false mapping |
| Gerente Financeiro                                                    | financial_analyst      | lead             | financial_analyst      | senior            | wrong level   |
