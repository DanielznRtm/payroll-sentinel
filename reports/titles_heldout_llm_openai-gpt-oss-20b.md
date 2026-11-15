# Held-out title normalization

File `eval/heldout_titles.csv`: 130 hand-written titles not listed in `taxonomy.py`; 114 inside the taxonomy, 16 outside it (empty family: the right answer is to abstain). Normalizer: **LLM (openai/gpt-oss-20b, reasoning_effort=low)**.

Titles answered by the LLM: 100.0% (the rest fell back to keyword rules).

LLM run: 4 LLM calls (4 HTTP requests, 0 rate-limit (429) responses), 14.8 s in LLM calls, 3.7 s per call; 7.5 s waiting for the API (1.9 s per request), the rest is pacing and retry back-off; 14.8 s in total.

## 1. Titles inside the taxonomy

| metric                          | correct   | titles   | share   |
|:--------------------------------|:----------|:---------|:--------|
| family accuracy                 | 100       | 114      | 0.877   |
| level accuracy                  | 97        | 114      | 0.851   |
| family and level                | 89        | 114      | 0.781   |
| family accuracy when it answers | 100       | 103      | 0.971   |

"When it answers" leaves out the titles where the normalizer abstained.

## 2. Family outcome inside the taxonomy

`wrong family` puts a salary in the wrong peer group without any warning. `abstained` leaves the family empty, so the validator raises `unmapped_title` for human review.

| outcome      | titles   | share   |
|:-------------|:---------|:--------|
| correct      | 100      | 0.877   |
| wrong family | 3        | 0.026   |
| abstained    | 11       | 0.096   |

## 3. Titles outside the taxonomy

Here abstaining is correct; `false mapping` forces the title into a family.

| outcome            | titles   | share   |
|:-------------------|:---------|:--------|
| correct abstention | 14       | 0.875   |
| false mapping      | 2        | 0.125   |

## 4. Every error (27)

| title                                                                 | expected_family        | expected_level   | predicted_family       | predicted_level   | error                   |
|:----------------------------------------------------------------------|:-----------------------|:-----------------|:-----------------------|:------------------|:------------------------|
| Pessoa Desenvolvedora Backend Peno I Open Banking                     | software_engineer      | mid              | software_engineer      | junior            | wrong level             |
| Analista de Dados Pleno/Sênior                                        | data_analyst           | mid              | data_analyst           | senior            | wrong level             |
| Analista de Dados Pleno/Sênior de Produto                             | data_analyst           | mid              | data_analyst           | senior            | wrong level             |
| Product Manager Pleno/ Senior Assessoria VIP                          | product_manager        | mid              | product_manager        | senior            | wrong level             |
| Pessoa Analista de People Analytics                                   | hr_analyst             | mid              | data_analyst           | mid               | wrong family            |
| People Analytics Sr                                                   | hr_analyst             | senior           | data_analyst           | senior            | wrong family            |
| ANALISTA INTELIGENCIA E INOVACAO DE RH III                            | hr_analyst             | senior           | hr_analyst             | lead              | wrong level             |
| Analista de Compensation Sênior (Foco em ILP e Design Organizacional) | hr_analyst             | senior           | -                      | senior            | abstained               |
| Executivo(a) de Vendas – Field Sales | Claro S.A.                     | sales_rep              | mid              | sales_rep              | senior            | wrong level             |
| Business Development Representative | BDR | Pleno                     | sales_rep              | mid              | -                      | mid               | abstained               |
| Banco de Talentos | Analista SDR - Inside Sales                       | sales_rep              | mid              | sales_rep              | junior            | wrong level             |
| Assistente de Pré-Vendas SDR                                          | sales_rep              | junior           | -                      | junior            | abstained               |
| Ambev I Operador (a) de Produção (Filial Vidros RJ)                   | production_operator    | mid              | production_operator    | junior            | wrong level             |
| Product Marketing Manager (PMM) – Remoto                              | -                      | -                | product_manager        | mid               | false mapping           |
| Data Engineer Senior - Vaga afirmativa para mulheres                  | software_engineer      | senior           | -                      | senior            | abstained               |
| Analista de Inteligência Comercial Sênior (501403)                    | data_analyst           | senior           | sales_rep              | senior            | wrong family            |
| Supervisor de Manutenção Industrial                                   | maintenance_technician | lead             | maintenance_technician | mid               | wrong level             |
| GERENTE COMERCIAL                                                     | sales_rep              | lead             | -                      | senior            | abstained + wrong level |
| OPERADOR(A) DE TELEMARKETING                                          | customer_support       | mid              | -                      | mid               | abstained               |
| Operador de Empilhadeira                                              | -                      | -                | production_operator    | mid               | false mapping           |
| Especialista em Inteligência Artificial                               | data_scientist         | lead             | -                      | mid               | abstained + wrong level |
| Coordenador (a) de Dados                                              | data_analyst           | lead             | -                      | senior            | abstained + wrong level |
| Especialista de Dadosd - Customer Intelligence                        | data_analyst           | lead             | -                      | mid               | abstained + wrong level |
| Supervisor de Controladoria                                           | financial_analyst      | lead             | -                      | mid               | abstained + wrong level |
| Gerente Financeiro                                                    | financial_analyst      | lead             | financial_analyst      | mid               | wrong level             |
| Supervisor de Manutenção a - Miguel Pereira/RJ / Banco de Talentos    | maintenance_technician | lead             | maintenance_technician | mid               | wrong level             |
| Coordenador de RH                                                     | hr_analyst             | lead             | -                      | senior            | abstained + wrong level |
