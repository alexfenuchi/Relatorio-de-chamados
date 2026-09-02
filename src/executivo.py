"""Metas e métricas específicas da visão executiva."""

from __future__ import annotations

import pandas as pd


METAS_EXECUTIVAS = {
    "sla_medido_percentual": 95.0,
    "percentual_backlog": 15.0,
    "tempo_medio_horas": 8.0,
    "taxa_absorcao": 100.0,
}


def calcular_fluxo_periodo(df, inicio, fim):
    """Compara demanda aberta e capacidade entregue dentro de um período."""
    inicio = pd.Timestamp(inicio).normalize()
    fim_exclusivo = pd.Timestamp(fim).normalize() + pd.Timedelta(days=1)
    abertos = df.loc[
        df["Abertura"].ge(inicio) & df["Abertura"].lt(fim_exclusivo), "N° Chamado"
    ].nunique()
    encerramento = df.get("Encerramento", pd.Series(pd.NaT, index=df.index))
    encerrados = df.loc[
        encerramento.ge(inicio) & encerramento.lt(fim_exclusivo), "N° Chamado"
    ].nunique()
    return {
        "abertos": int(abertos),
        "encerrados": int(encerrados),
        "saldo": int(encerrados - abertos),
        "taxa_absorcao": encerrados / abertos * 100 if abertos else 0.0,
    }


def calcular_periodo_anterior(inicio, fim):
    """Retorna o intervalo imediatamente anterior com a mesma quantidade de dias."""
    inicio = pd.Timestamp(inicio).normalize()
    fim = pd.Timestamp(fim).normalize()
    duracao = fim - inicio
    fim_anterior = inicio - pd.Timedelta(days=1)
    return fim_anterior - duracao, fim_anterior


def calcular_variacao(atual, anterior):
    """Calcula a variação percentual, preservando ausência de base comparável."""
    if anterior is None or pd.isna(anterior) or float(anterior) == 0:
        return None
    return (float(atual) - float(anterior)) / abs(float(anterior)) * 100
