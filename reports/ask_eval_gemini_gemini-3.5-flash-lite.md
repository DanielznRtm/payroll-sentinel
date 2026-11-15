# Ask the benchmark: evaluation

File `eval/questions.csv`: 30 questions, 25 in scope and 5 out of scope. Model: **gemini-3.5-flash-lite**. Right answers are computed by the code from the expected query.

LLM run: 30 LLM calls (32 HTTP requests, 2 rate-limit (429) responses), 143.3 s in LLM calls, 4.8 s per call; 46.8 s waiting for the API (1.5 s per request), the rest is pacing and retry back-off; 143.4 s in total.

## 1. Accuracy

| metric                          | correct   | questions   | share   |
|:--------------------------------|:----------|:------------|:--------|
| query accuracy (all questions)  | 27        | 30          | 0.900   |
| answer accuracy (all questions) | 27        | 30          | 0.900   |
| in-scope answers right          | 22        | 25          | 0.880   |
| out-of-scope questions refused  | 5         | 5           | 1.000   |

A wrong query can still give the right answer (for example, an extra filter that changes nothing); that counts for the answer, not for the query.

## 2. Every error (3)

| question                                                            | expected_query                                                                                                                                                                                                                                                      | llm_query                                                                                                                                                                                                                                       | query_ok   | answer_ok   |
|:--------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------|:------------|
| Qual o percentil 75 do salário de coordenador de manutenção?        | {"in_scope": true, "filters": [{"column": "family", "op": "eq", "value": "maintenance_technician"}, {"column": "level", "op": "eq", "value": "lead"}], "group_by": null, "metric": "p75", "column": "monthly_salary"}                                               | {"in_scope": false}                                                                                                                                                                                                                             | False      | False       |
| Quanto ganha um HRBP sênior em Curitiba?                            | {"in_scope": true, "filters": [{"column": "city", "op": "eq", "value": "Curitiba"}, {"column": "family", "op": "eq", "value": "hr_analyst"}, {"column": "level", "op": "eq", "value": "senior"}], "group_by": null, "metric": "median", "column": "monthly_salary"} | {"in_scope": false}                                                                                                                                                                                                                             | False      | False       |
| Qual a mediana salarial de devs e cientistas de dados em São Paulo? | {"in_scope": true, "filters": [{"column": "city", "op": "eq", "value": "São Paulo"}, {"column": "family", "op": "in", "value": ["data_scientist", "software_engineer"]}], "group_by": null, "metric": "median", "column": "monthly_salary"}                         | {"in_scope": true, "filters": [{"column": "city", "op": "eq", "value": "São Paulo"}, {"column": "family", "op": "in", "value": ["data_scientist", "software_engineer"]}], "group_by": "family", "metric": "median", "column": "monthly_salary"} | False      | False       |
