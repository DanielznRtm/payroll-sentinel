# Held-out title normalization

File `eval/heldout_titles.csv`: 130 hand-written titles not listed in `taxonomy.py`; 114 inside the taxonomy, 16 outside it (empty family: the right answer is to abstain). Normalizer: **keyword rules**.

## 1. Titles inside the taxonomy

| metric                          | correct   | titles   | share   |
|:--------------------------------|:----------|:---------|:--------|
| family accuracy                 | 70        | 114      | 0.614   |
| level accuracy                  | 96        | 114      | 0.842   |
| family and level                | 58        | 114      | 0.509   |
| family accuracy when it answers | 70        | 71       | 0.986   |

"When it answers" leaves out the titles where the normalizer abstained.

## 2. Family outcome inside the taxonomy

`wrong family` puts a salary in the wrong peer group without any warning. `abstained` leaves the family empty, so the validator raises `unmapped_title` for human review.

| outcome      | titles   | share   |
|:-------------|:---------|:--------|
| correct      | 70       | 0.614   |
| wrong family | 1        | 0.009   |
| abstained    | 43       | 0.377   |

## 3. Titles outside the taxonomy

Here abstaining is correct; `false mapping` forces the title into a family.

| outcome            | titles   | share   |
|:-------------------|:---------|:--------|
| correct abstention | 13       | 0.812   |
| false mapping      | 3        | 0.188   |

## 4. Every error (59)

| title                                                                            | expected_family        | expected_level   | predicted_family    | predicted_level   | error                   |
|:---------------------------------------------------------------------------------|:-----------------------|:-----------------|:--------------------|:------------------|:------------------------|
| Pessoa Desenvolvedora Backend Peno I Open Banking                                | software_engineer      | mid              | software_engineer   | junior            | wrong level             |
| Pessoa Desenvolvedora Backend Sênior / Especialista | Store                      | software_engineer      | senior           | software_engineer   | lead              | wrong level             |
| Full Stack Developer (foco em back-end) Sênior | Dev III                         | software_engineer      | senior           | -                   | senior            | abstained               |
| Estágio em Desenvolvimento de Software                                           | software_engineer      | intern           | -                   | intern            | abstained               |
| Estágio em Desenvolvimento de Software / Data Mining                             | software_engineer      | intern           | -                   | intern            | abstained               |
| Analista de Dados Pleno/Sênior                                                   | data_analyst           | mid              | data_analyst        | senior            | wrong level             |
| Analista de Dados Pleno/Sênior de Produto                                        | data_analyst           | mid              | data_analyst        | senior            | wrong level             |
| Summer Job | Data & Analytics                                                    | data_analyst           | intern           | -                   | mid               | abstained + wrong level |
| Product Manager Pleno/ Senior Assessoria VIP                                     | product_manager        | mid              | product_manager     | senior            | wrong level             |
| Product Manager Specialist | Vaga afirmativa para mulheres                       | product_manager        | lead             | product_manager     | mid               | wrong level             |
| Product Owner Pleno                                                              | product_manager        | mid              | -                   | mid               | abstained               |
| Pessoa Analista de People Analytics                                              | hr_analyst             | mid              | -                   | mid               | abstained               |
| People Analytics Sr                                                              | hr_analyst             | senior           | -                   | senior            | abstained               |
| Analista de Gestão de Pessoas Pleno - Montes Claros/MG                           | hr_analyst             | mid              | -                   | mid               | abstained               |
| Analista de Compensation Sênior (Foco em ILP e Design Organizacional)            | hr_analyst             | senior           | -                   | senior            | abstained               |
| ANALISTA FP&A BU BRASIL SÊNIOR                                                   | financial_analyst      | senior           | -                   | senior            | abstained               |
| Analista FP&A Pl                                                                 | financial_analyst      | mid              | -                   | mid               | abstained               |
| Business Development Representative | BDR | Pleno                                | sales_rep              | mid              | -                   | mid               | abstained               |
| Banco de Talentos | Analista SDR - Inside Sales                                  | sales_rep              | mid              | -                   | mid               | abstained               |
| Assistente de Pré-Vendas SDR                                                     | sales_rep              | junior           | sales_rep           | mid               | wrong level             |
| Analista de Customer Success Pleno - Incentivo de Uso                            | customer_support       | mid              | -                   | mid               | abstained               |
| Analista Pleno de Customer Success — (RAF)                                       | customer_support       | mid              | -                   | mid               | abstained               |
| Analista de Customer Success Pleno | Espanhol Fluente                            | customer_support       | mid              | -                   | mid               | abstained               |
| Analista de Customer Success Ongoing Pleno                                       | customer_support       | mid              | -                   | mid               | abstained               |
| Analista de CX Pleno - Enablement (KCS e Automações)                             | customer_support       | mid              | -                   | mid               | abstained               |
| Team Leader de Suporte - Service Desk | São Paulo                                | customer_support       | lead             | customer_support    | mid               | wrong level             |
| Analista de Customer Success (Vaga afirmativa para Pessoa com Deficiência - PCD) | customer_support       | mid              | -                   | mid               | abstained               |
| Ambev I Operador (a) de Produção (Filial Vidros RJ)                              | production_operator    | mid              | production_operator | junior            | wrong level             |
| Técnico Manutenção Elétrica I - Anápolis                                         | maintenance_technician | junior           | -                   | junior            | abstained               |
| Técnico de Conservação Elétrica                                                  | maintenance_technician | mid              | -                   | mid               | abstained               |
| Técnico (a) de Manutenção Elétrica ou Automação PTG                              | maintenance_technician | mid              | -                   | mid               | abstained               |
| Técnico(a) de Manutenção Eletrônica                                              | maintenance_technician | mid              | -                   | mid               | abstained               |
| Técnico(a) de Manutenção Elétrica I                                              | maintenance_technician | junior           | -                   | junior            | abstained               |
| Data Engineer Senior - Vaga afirmativa para mulheres                             | software_engineer      | senior           | -                   | senior            | abstained               |
| Analista de Inteligência Comercial Sênior (501403)                               | data_analyst           | senior           | -                   | senior            | abstained               |
| Estágio em Ciência de Dados                                                      | data_scientist         | intern           | -                   | intern            | abstained               |
| Estágio em Machine Learning                                                      | data_scientist         | intern           | -                   | intern            | abstained               |
| Estágio em Sucesso do Cliente (CRM)                                              | customer_support       | intern           | -                   | intern            | abstained               |
| Estagiário de Customer Success Manager                                           | customer_support       | intern           | -                   | intern            | abstained               |
| Estagiário (a) - Experiência do Cliente                                          | customer_support       | intern           | -                   | intern            | abstained               |
| Estagiário de Manutenção e Automação                                             | maintenance_technician | intern           | -                   | intern            | abstained               |
| ESTÁGIO TÉCNICO EM MANUTENÇÃO MECÂNICA                                           | maintenance_technician | intern           | -                   | intern            | abstained               |
| Supervisor de Manutenção Industrial                                              | maintenance_technician | lead             | -                   | mid               | abstained + wrong level |
| Programa de Estágio Serasa Experian 2027: Product Management                     | product_manager        | intern           | -                   | intern            | abstained               |
| Estagiário Industrial - Produção                                                 | production_operator    | intern           | -                   | intern            | abstained               |
| Auxiliar de Operador de Máquinas - EFR (banco de talentos)                       | production_operator    | junior           | production_operator | mid               | wrong level             |
| GERENTE COMERCIAL                                                                | sales_rep              | lead             | -                   | mid               | abstained + wrong level |
| OPERADOR(A) DE TELEMARKETING                                                     | customer_support       | mid              | production_operator | mid               | wrong family            |
| Operador de Caixa                                                                | -                      | -                | production_operator | mid               | false mapping           |
| Operador de Empilhadeira                                                         | -                      | -                | production_operator | mid               | false mapping           |
| Operador de Cobrança                                                             | -                      | -                | production_operator | mid               | false mapping           |
| Especialista em Inteligência Artificial                                          | data_scientist         | lead             | -                   | lead              | abstained               |
| Coordenador (a) de Dados                                                         | data_analyst           | lead             | -                   | mid               | abstained + wrong level |
| Especialista de Dadosd - Customer Intelligence                                   | data_analyst           | lead             | -                   | lead              | abstained               |
| Líder de Produção - Processos - 114909                                           | production_operator    | lead             | -                   | lead              | abstained               |
| Supervisor de Controladoria                                                      | financial_analyst      | lead             | -                   | mid               | abstained + wrong level |
| Gerente Financeiro                                                               | financial_analyst      | lead             | financial_analyst   | mid               | wrong level             |
| Supervisor de Manutenção a - Miguel Pereira/RJ / Banco de Talentos               | maintenance_technician | lead             | -                   | mid               | abstained + wrong level |
| Coordenador de RH                                                                | hr_analyst             | lead             | hr_analyst          | mid               | wrong level             |
