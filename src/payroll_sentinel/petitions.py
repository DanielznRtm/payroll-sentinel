"""Synthetic labor petitions with known claims, to measure claim extraction.

Each petition is a short labor complaint (reclamação trabalhista) written from
templates with random facts. The facts and the claims are kept as ground truth,
in the same shape the extractor must return (claims.py), so extraction can be
scored. People and companies are invented. Some sentences mention a right
without claiming it ("o 13º salário de 2024 foi pago corretamente"), which
keyword rules mistake for a claim.

Template text is easier than real petitions: these petitions are for development
and tests. The extraction is measured for real on petitions the user writes by hand.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from .claims import COMPUTED_CLAIMS, MONTHS_PT

FIRST_NAMES = ["Ana", "Bruno", "Carla", "Diego", "Elisa", "Fábio", "Gabriela", "Heitor", "Isabela", "Júlio",
               "Larissa", "Marcos", "Natália", "Otávio", "Paula", "Rafael", "Sílvia", "Tiago"]
SURNAMES = ["Almeida", "Barros", "Cardoso", "Duarte", "Esteves", "Freitas", "Gomes", "Lacerda", "Moraes",
            "Nogueira", "Pacheco", "Queiroz", "Rezende", "Teixeira"]
COMPANIES = ["Alfa Logística Ltda.", "Beta Sistemas S.A.", "Gama Alimentos Ltda.", "Delta Serviços Ltda.",
             "Ômega Varejo S.A.", "Sigma Metalúrgica Ltda."]
CITIES = ["São Paulo", "Campinas", "Sorocaba", "Santos"]
JOBS = ["auxiliar administrativo", "analista de suporte", "operador de produção", "vendedor",
        "assistente financeiro", "técnico de manutenção"]

COMPUTED = list(COMPUTED_CLAIMS)
# A resignation gives no paid notice and no 40 % fine.
ALLOWED = {"without_cause": COMPUTED, "resignation": [c for c in COMPUTED if c not in ("notice_pay", "fgts_fine")]}

FACTS = {
    "overtime": ["Durante todo o contrato, {ele} trabalhou em média {h} horas extras por mês, sem receber o "
                 "respectivo pagamento.",
                 "A jornada era habitualmente estendida, somando cerca de {h} horas extras mensais, nunca quitadas."],
    "unpaid_fgts": ["A Reclamada deixou de depositar o FGTS nos últimos {k} meses do contrato.",
                    "O extrato da conta vinculada mostra que {k} depósitos mensais do FGTS não foram feitos."],
    "late_severance_fine": ["As verbas rescisórias não foram pagas no prazo de 10 dias previsto em lei.",
                            "Até hoje a Reclamada não pagou as verbas rescisórias."],
}
REQUESTS = {
    "overtime": ["pagamento das horas extras, com adicional de 50%", "pagamento das horas extraordinárias não quitadas"],
    "unpaid_fgts": ["depósito do FGTS não recolhido no curso do contrato", "recolhimento dos depósitos de FGTS em atraso"],
    "fgts_fine": ["pagamento da multa de 40% sobre os depósitos do FGTS", "multa fundiária de 40%"],
    "notice_pay": ["aviso prévio indenizado proporcional ao tempo de serviço", "pagamento do aviso prévio indenizado"],
    "thirteenth": ["13º salário proporcional", "décimo terceiro salário proporcional"],
    "vacation": ["férias proporcionais acrescidas de 1/3", "férias proporcionais com o terço constitucional"],
    "late_severance_fine": ["multa do art. 477, § 8º, da CLT", "multa por atraso no pagamento das verbas rescisórias"],
}
# Sentences that mention a right without claiming it; used only when that claim is absent.
TRAPS = {
    "overtime": "A jornada contratual era cumprida sem horas extras.",
    "unpaid_fgts": "Os depósitos do FGTS foram feitos regularmente durante o contrato.",
    "notice_pay": "{Ele} cumpriu o aviso prévio trabalhado.",
    "thirteenth": "O 13º salário de {ano} foi pago corretamente.",
    "vacation": "As férias vencidas foram gozadas e pagas no prazo.",
}
OTHER = [("indenização por danos morais", "danos morais"), ("adicional de insalubridade", "adicional de insalubridade"),
         ("reconhecimento do vínculo de emprego no período sem registro", "vínculo de emprego"),
         ("reembolso do vale-transporte não fornecido", "vale-transporte")]


@dataclass(frozen=True)
class Petition:
    id: str
    text: str
    truth: dict   # the extraction JSON shape (claims.py), without quotes


def money_pt(value: Decimal) -> str:
    """6000 -> '6.000,00'."""
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def date_pt(day: date, numeric: bool) -> str:
    if numeric:
        return day.strftime("%d/%m/%Y")
    first = "1º" if day.day == 1 else str(day.day)
    return f"{first} de {MONTHS_PT[day.month - 1]} de {day.year}"


def _random_day(rng: random.Random, first: date, last: date) -> date:
    return first + timedelta(days=rng.randint(0, (last - first).days))


def _petition(i: int, rng: random.Random) -> Petition:
    female = rng.random() < 0.5
    pron = {"ele": "a Reclamante" if female else "o Reclamante", "Ele": "A Reclamante" if female else "O Reclamante"}
    name = f"{rng.choice(FIRST_NAMES)} {rng.choice(SURNAMES)} {rng.choice(SURNAMES)}"
    company, city, job = rng.choice(COMPANIES), rng.choice(CITIES), rng.choice(JOBS)

    filing = _random_day(rng, date(2026, 1, 5), date(2026, 11, 13))
    late = rng.random() < 0.1                     # filed more than 2 years after the end: time-barred
    gap = rng.randint(740, 1000) if late else rng.randint(10, 700)
    termination = min(filing - timedelta(days=gap), date(2026, 9, 30))
    admission = termination - timedelta(days=rng.randint(200, 9 * 365))
    salary = Decimal(rng.randrange(1700, 15001, 50))
    weekly = rng.choice([44, 44, 44, 40])
    kind = "without_cause" if rng.random() < 0.8 else "resignation"
    claims = sorted(rng.sample(ALLOWED[kind], rng.randint(2, min(6, len(ALLOWED[kind])))),
                    key=COMPUTED.index)
    other = rng.choice(OTHER) if rng.random() < 0.4 else None
    hours = rng.choice([8, 10, 12, 15, 20, 24, 30, 40])
    fgts_months = rng.randint(2, max(2, min(18, (termination - admission).days // 30)))
    numeric = rng.random() < 0.5

    facts = [f"{pron['Ele']} foi admitid{'a' if female else 'o'} em {date_pt(admission, numeric)} para exercer a "
             f"função de {job}, com salário mensal de R$ {money_pt(salary)}."]
    if "overtime" in claims or rng.random() < 0.5:
        facts.append(f"A jornada contratual era de {weekly} horas semanais.")
    if kind == "without_cause":
        facts.append(f"Foi dispensad{'a' if female else 'o'} sem justa causa em {date_pt(termination, numeric)}.")
    else:
        facts.append(f"Pediu demissão em {date_pt(termination, numeric)}.")
    fixed = len(facts)                            # admission, hours and termination stay first
    for claim in claims:
        if claim in FACTS:
            facts.append(rng.choice(FACTS[claim]).format(h=hours, k=fgts_months, **pron))
    for claim, trap in TRAPS.items():
        if claim not in claims and rng.random() < 0.35:
            if claim == "notice_pay" and kind == "without_cause":
                continue                          # a dismissed worker's notice trap would read oddly
            facts.append(trap.format(ano=termination.year - 1, **pron))
    rest = facts[fixed:]
    rng.shuffle(rest)
    facts = facts[:fixed] + rest

    requests = [rng.choice(REQUESTS[c]) for c in claims]
    if other:
        amount = f", no valor de R$ {money_pt(Decimal(rng.randrange(5000, 50001, 5000)))}" if other[1] == "danos morais" else ""
        requests.append(other[0] + amount)
    letters = "abcdefghij"
    cause = Decimal(rng.randrange(20000, 200001, 1000))
    text = "\n\n".join([
        f"EXCELENTÍSSIMO(A) SENHOR(A) JUIZ(A) DA VARA DO TRABALHO DE {city.upper()}",
        f"{name.upper()}, {job}, vem propor RECLAMAÇÃO TRABALHISTA em face de {company}, pelos fatos a seguir.",
        "DOS FATOS\n\n" + " ".join(facts),
        "DOS PEDIDOS\n\nDiante do exposto, requer:\n" + "\n".join(
            f"{letters[j]}) {r};" for j, r in enumerate(requests)),
        f"Dá-se à causa o valor de R$ {money_pt(cause)}.",
        f"{city}, {date_pt(filing, numeric=False)}.",
    ])

    truth = {
        "admission_date": admission.isoformat(), "termination_date": termination.isoformat(),
        "termination_type": kind, "monthly_salary": str(salary),
        "weekly_hours": str(weekly) if f"{weekly} horas semanais" in text else None,
        "filing_date": filing.isoformat(),
        "claims": [{"type": c, **({"hours_per_month": str(hours)} if c == "overtime" else {}),
                    **({"months": str(fgts_months)} if c == "unpaid_fgts" else {})} for c in claims]
        + ([{"type": "other", "label": other[1]}] if other else []),
    }
    return Petition(f"P{i:03d}", text, truth)


def generate_petitions(n: int = 60, seed: int = 7) -> list[Petition]:
    """``n`` petitions, the same for the same seed."""
    rng = random.Random(seed)
    return [_petition(i + 1, rng) for i in range(n)]
