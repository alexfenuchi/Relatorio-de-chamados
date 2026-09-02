"""Indicadores executivos e alertas acionáveis para o dashboard."""

from __future__ import annotations

import pandas as pd

CAMPOS_CRITICOS = {
    "Localizacao": "localização",
    "Problema": "problema",
    "Responsavel": "responsável",
    "nivelsla": "nível SLA",
}


def calcular_saude_dados(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula a cobertura dos campos usados nas decisões operacionais."""
    total = max(df["N° Chamado"].nunique(), 1)
    linhas = []
    for coluna, rotulo in CAMPOS_CRITICOS.items():
        serie = df.get(coluna, pd.Series(index=df.index, dtype="object"))
        preenchidos = serie.notna() & serie.astype(str).str.strip().ne("")
        quantidade = df.loc[preenchidos, "N° Chamado"].nunique()
        linhas.append(
            {
                "Campo": rotulo.title(),
                "Preenchidos": quantidade,
                "Cobertura_Percentual": quantidade / total * 100,
            }
        )
    return pd.DataFrame(linhas).sort_values("Cobertura_Percentual")


def gerar_insights_executivos(df: pd.DataFrame, kpis: dict) -> list[dict[str, str]]:
    """Gera uma lista curta de achados, com evidência e ação recomendada."""
    insights: list[dict[str, str]] = []
    total = max(kpis["total"], 1)
    backlog_pct = kpis["pendentes"] / total * 100

    if kpis["fora_sla_medido"]:
        insights.append(
            {
                "nivel": (
                    "crítico" if kpis["sla_medido_percentual"] < 90 else "atenção"
                ),
                "titulo": "Risco de SLA",
                "texto": (
                    f"{kpis['fora_sla_medido']:,} chamados estão em atraso medido "
                    f"e a aderência é de {kpis['sla_medido_percentual']:.1f}%. "
                    "Priorize a fila por "
                    "excedente e criticidade."
                ),
            }
        )

    insights.append(
        {
            "nivel": "atenção" if backlog_pct >= 20 else "positivo",
            "titulo": "Pressão de backlog",
            "texto": (
                f"{backlog_pct:.1f}% dos chamados do recorte permanecem abertos "
                f"({kpis['pendentes']:,}). Aging máximo: "
                f"{kpis['aging_maximo_dias']:.1f} dias úteis."
            ),
        }
    )

    problemas = (
        df.dropna(subset=["Problema"])
        .groupby("Problema")["N° Chamado"]
        .nunique()
        .sort_values(ascending=False)
    )
    if not problemas.empty:
        top = str(problemas.index[0])
        qtd = int(problemas.iloc[0])
        insights.append(
            {
                "nivel": "informativo",
                "titulo": "Principal ofensor",
                "texto": (
                    f"“{top}” concentra {qtd:,} chamados ({qtd / total * 100:.1f}%). "
                    "Avalie causa raiz, automação e artigo de conhecimento."
                ),
            }
        )

    qualidade = calcular_saude_dados(df)
    pior = qualidade.iloc[0]
    if pior["Cobertura_Percentual"] < 95:
        insights.append(
            {
                "nivel": "atenção",
                "titulo": "Qualidade dos dados",
                "texto": (
                    f"O campo {pior['Campo'].lower()} tem "
                    f"{pior['Cobertura_Percentual']:.1f}% de cobertura. "
                    "Torne o preenchimento obrigatório para análises confiáveis."
                ),
            }
        )

    return insights[:4]


def criar_resumo_executivo(df: pd.DataFrame, kpis: dict) -> pd.DataFrame:
    """Cria uma tabela vertical, pronta para leitura e exportação."""
    total = max(kpis["total"], 1)
    return pd.DataFrame(
        [
            ("Volume", "Total de chamados", kpis["total"]),
            ("Fluxo", "Encerrados", kpis["encerrados"]),
            ("Fluxo", "Backlog", kpis["pendentes"]),
            ("Fluxo", "Backlog (%)", kpis["pendentes"] / total * 100),
            ("SLA", "Aderência medida (%)", kpis["sla_medido_percentual"]),
            ("SLA", "Chamados em atraso medido", kpis["fora_sla_medido"]),
            ("Eficiência", "MTTR médio (h úteis)", kpis["tempo_medio_horas"]),
            ("Eficiência", "MTTR mediano (h úteis)", kpis["tempo_mediano_horas"]),
            ("Backlog", "Aging médio (dias úteis)", kpis["aging_medio_dias"]),
            ("Backlog", "Aging máximo (dias úteis)", kpis["aging_maximo_dias"]),
        ],
        columns=["Dimensão", "Indicador", "Valor"],
    )


def criar_painel_metas(kpis: dict, fluxo: dict, metas: dict) -> pd.DataFrame:
    """Monta o placar executivo com realizado, meta, desvio e semáforo."""
    indicadores = [
        (
            "SLA medido",
            kpis["sla_medido_percentual"],
            metas["sla_medido_percentual"],
            True,
            "%",
        ),
        (
            "Backlog",
            kpis["percentual_backlog"],
            metas["percentual_backlog"],
            False,
            "%",
        ),
        (
            "MTTR médio",
            kpis["tempo_medio_horas"],
            metas["tempo_medio_horas"],
            False,
            "h",
        ),
        ("Taxa de absorção", fluxo["taxa_absorcao"], metas["taxa_absorcao"], True, "%"),
    ]
    linhas = []
    for indicador, realizado, meta, maior_melhor, unidade in indicadores:
        desvio = realizado - meta
        atingiu = realizado >= meta if maior_melhor else realizado <= meta
        linhas.append(
            {
                "Indicador": indicador,
                "Realizado": realizado,
                "Meta": meta,
                "Desvio": desvio,
                "Unidade": unidade,
                "Status": "Na meta" if atingiu else "Fora da meta",
            }
        )
    return pd.DataFrame(linhas)
