---
title: Payroll Sentinel
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8501
pinned: false
license: mit
short_description: Confere folhas de pagamento antes do benchmark salarial
---

# Payroll Sentinel

Envie a folha de pagamento da sua empresa (CSV ou Excel) e veja, linha a linha, o
que aceitar, revisar e bloquear antes de ela entrar num benchmark salarial, com o
motivo, o que fazer e um relatório em Excel.

O arquivo é processado só em memória, durante a sua sessão, e nunca vai para um
LLM. As verificações não precisam de nome nem CPF: tire essas colunas antes de
enviar.

Código, método e resultados medidos:
[github.com/DanielznRtm/payroll-sentinel](https://github.com/DanielznRtm/payroll-sentinel).
Este Space instala um commit fixo desse repositório (veja o `Dockerfile`).
