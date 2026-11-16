"""Canonical job taxonomy, reference values and Brazilian labor constants.

All salary figures are synthetic and only meant to produce a realistic-looking
dataset. They are NOT market data.
"""

from __future__ import annotations

import datetime as dt

# --- Legal constants -------------------------------------------------------
# National minimum wage for 2026 (Decreto 12.797/2025), for a 44h/week contract.
MIN_WAGE = 1621.00
FULL_TIME_HOURS = 44

# Date the submissions refer to (e.g. the benchmark collection cut-off).
REFERENCE_DATE = dt.date(2026, 10, 31)

# --- Levels ----------------------------------------------------------------
LEVELS = ["intern", "junior", "mid", "senior", "lead"]
LEVEL_ORDINAL = {lvl: i for i, lvl in enumerate(LEVELS)}
LEVEL_MULTIPLIER = {"intern": 0.30, "junior": 0.65, "mid": 1.00, "senior": 1.45, "lead": 1.95}
# Internships are not CLT jobs, so RAIS has none to fit: stipends keep the v1.0 spread
# (a family's wide CLT spread would give stipends of R$ 200, which read as typos).
INTERN_PAY_SIGMA = 0.15

# --- Job families ----------------------------------------------------------
# mid_salary: synthetic monthly base salary (BRL) for a mid-level in São Paulo.
# pay_sigma: spread of individual pay around it (SD of log pay, on top of level,
# company and city). kind: "office" or "industrial", for the city index below.
# Since v1.1, pay_sigma and the mid_salary of sales_rep and customer_support are
# fitted to RAIS 2025 job records in São Paulo, and the Campinas and Sorocaba city
# index to same-occupation pay ratios, by scripts/calibrate_generator.py
# (reports/realism_rais.md). Data analyst and product manager have no CBO code and
# take the median office pay_sigma. The other mid_salary values are the v1.0 ones.
# easy / hard: raw title variants. "easy" are the common spellings a keyword
# baseline would cover; "hard" are the long tail (abbreviations, English
# jargon, sub-specialties) that need semantic understanding.
FAMILIES: dict[str, dict] = {
    "software_engineer": {
        "label": "Engenheiro(a) de Software",
        "mid_salary": 10500, "pay_sigma": 0.51, "kind": "office",
        "easy": ["Desenvolvedor", "Desenvolvedora", "Engenheiro de Software",
                 "Engenheira de Software", "Software Engineer", "Programador"],
        "hard": ["Dev Backend", "Dev Front-end", "SWE", "Eng. Software", "Fullstack Developer"],
    },
    "data_analyst": {
        "label": "Analista de Dados",
        "mid_salary": 7500, "pay_sigma": 0.49, "kind": "office",
        "easy": ["Analista de Dados", "Data Analyst"],
        "hard": ["Analista de BI", "Analista de Business Intelligence", "Analytics Analyst"],
    },
    "data_scientist": {
        "label": "Cientista de Dados",
        "mid_salary": 11000, "pay_sigma": 0.42, "kind": "office",
        "easy": ["Cientista de Dados", "Data Scientist"],
        "hard": ["Cientista de ML", "Machine Learning Scientist", "Applied Scientist"],
    },
    "product_manager": {
        "label": "Gerente de Produto",
        "mid_salary": 13000, "pay_sigma": 0.49, "kind": "office",
        "easy": ["Gerente de Produto", "Product Manager"],
        "hard": ["PM", "Product Owner", "PO"],
    },
    "hr_analyst": {
        "label": "Analista de RH",
        "mid_salary": 5800, "pay_sigma": 0.47, "kind": "office",
        "easy": ["Analista de RH", "Analista de Recursos Humanos"],
        "hard": ["Business Partner de Pessoas", "HRBP", "Analista de Gente e Gestão", "People Analyst"],
    },
    "financial_analyst": {
        "label": "Analista Financeiro",
        "mid_salary": 6500, "pay_sigma": 0.37, "kind": "office",
        "easy": ["Analista Financeiro", "Analista Financeira", "Financial Analyst"],
        "hard": ["Analista de FP&A", "Analista de Controladoria", "Analista de Tesouraria"],
    },
    "sales_rep": {
        "label": "Executivo(a) de Vendas",
        "mid_salary": 4450, "pay_sigma": 0.77, "kind": "office",
        "easy": ["Executivo de Vendas", "Executiva de Vendas", "Vendedor"],
        "hard": ["Account Executive", "Inside Sales", "Representante Comercial", "Consultor Comercial"],
    },
    "customer_support": {
        "label": "Analista de Suporte / Atendimento",
        "mid_salary": 3650, "pay_sigma": 0.73, "kind": "office",
        "easy": ["Analista de Suporte", "Atendente", "Analista de Atendimento"],
        "hard": ["Customer Success", "CS Specialist", "Analista de CX"],
    },
    "production_operator": {
        "label": "Operador(a) de Produção",
        "mid_salary": 2600, "pay_sigma": 0.20, "kind": "industrial",
        "easy": ["Operador de Produção", "Operadora de Produção", "Operador de Máquinas"],
        "hard": ["Op. Produção", "Operador CNC", "Auxiliar de Linha"],
    },
    "maintenance_technician": {
        "label": "Técnico(a) de Manutenção",
        "mid_salary": 4200, "pay_sigma": 0.53, "kind": "industrial",
        "easy": ["Técnico de Manutenção", "Técnica de Manutenção", "Técnico Eletromecânico"],
        "hard": ["Mecânico de Manutenção", "Eletricista de Manutenção", "Téc. Manutenção Industrial"],
    },
}

# Families that never hire interns in this synthetic world.
NO_INTERN_FAMILIES = {"production_operator", "maintenance_technician"}

# Which families each sector hires, with relative weights.
SECTORS: dict[str, dict[str, float]] = {
    "tech": {"software_engineer": 0.35, "data_analyst": 0.10, "data_scientist": 0.08,
             "product_manager": 0.08, "hr_analyst": 0.05, "financial_analyst": 0.06,
             "sales_rep": 0.14, "customer_support": 0.14},
    "industry": {"production_operator": 0.45, "maintenance_technician": 0.20, "data_analyst": 0.04,
                 "software_engineer": 0.04, "hr_analyst": 0.06, "financial_analyst": 0.08,
                 "sales_rep": 0.13},
    "services": {"customer_support": 0.40, "sales_rep": 0.22, "hr_analyst": 0.08,
                 "financial_analyst": 0.10, "data_analyst": 0.08, "software_engineer": 0.07,
                 "product_manager": 0.05},
}

# Synthetic cost-of-labor index relative to São Paulo, by job kind. The RAIS file
# used here covers São Paulo state only, so the other cities keep their v1.0 index
# for both kinds.
CITIES: dict[str, dict[str, float]] = {
    "São Paulo": {"office": 1.00, "industrial": 1.00},
    "Rio de Janeiro": {"office": 0.95, "industrial": 0.95},
    "Campinas": {"office": 0.94, "industrial": 1.11},   # fitted to RAIS 2025
    "Sorocaba": {"office": 0.80, "industrial": 1.14},   # fitted to RAIS 2025
    "Belo Horizonte": {"office": 0.85, "industrial": 0.85},
    "Curitiba": {"office": 0.88, "industrial": 0.88},
    "Porto Alegre": {"office": 0.86, "industrial": 0.86},
    "Recife": {"office": 0.78, "industrial": 0.78},
    "Fortaleza": {"office": 0.75, "industrial": 0.75},
    "Remoto": {"office": 0.95, "industrial": 0.95},
}


def city_index(city: str, family: str) -> float:
    """Pay index of a city relative to São Paulo for the kind of job a family is."""
    return CITIES[city][FAMILIES[family]["kind"]]


def legal_min_wage(weekly_hours: float) -> float:
    """Minimum monthly wage proportional to the contracted weekly hours."""
    hours = min(float(weekly_hours), FULL_TIME_HOURS)
    return MIN_WAGE * hours / FULL_TIME_HOURS
