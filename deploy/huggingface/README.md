---
title: Payroll Sentinel
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: static
app_file: index.html
pinned: false
license: mit
short_description: Confere folhas de pagamento antes do benchmark salarial
---

# Payroll Sentinel

Envie a folha de pagamento da sua empresa (CSV ou Excel) e veja, linha a linha, o
que aceitar, revisar e bloquear antes de ela entrar num benchmark salarial, com o
motivo, o que fazer e um relatório em Excel.

Esta versão roda inteira no seu navegador (Streamlit com [stlite](https://github.com/whitphx/stlite)):
a folha nunca sai do seu computador e nunca vai para um LLM. Por isso a primeira
abertura leva cerca de um minuto, o tempo de baixar o Python, e cada validação
leva de 10 a 30 segundos. Para uma versão mais rápida, rodando num servidor, use
[payroll-sentinel.streamlit.app](https://payroll-sentinel.streamlit.app).

Código, método e resultados medidos:
[github.com/DanielznRtm/payroll-sentinel](https://github.com/DanielznRtm/payroll-sentinel).
O `index.html` carrega um commit fixo desse repositório.
