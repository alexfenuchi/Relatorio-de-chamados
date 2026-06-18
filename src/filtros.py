import pandas as pd
import streamlit as st


def _opcoes(df, coluna):
    if coluna not in df.columns:
        return []

    return sorted(
        df[coluna]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )


def renderizar_filtros(df):
    st.sidebar.header("Filtros")

    data_min = df["Abertura"].min().date()
    data_max = df["Abertura"].max().date()

    periodo = st.sidebar.date_input(
        "Período de abertura",
        value=(data_min, data_max),
        min_value=data_min,
        max_value=data_max,
    )

    grupos = st.sidebar.multiselect(
        "Grupo",
        _opcoes(df, "Grupo_Localizacao"),
    )

    lojas = st.sidebar.multiselect(
        "Loja",
        _opcoes(df, "Localizacao"),
    )

    problemas = st.sidebar.multiselect(
        "Problema",
        _opcoes(df, "Problema"),
    )

    status = st.sidebar.multiselect(
        "Situação",
        _opcoes(df, "Situacao"),
    )

    responsaveis = st.sidebar.multiselect(
        "Responsável",
        _opcoes(df, "Responsavel"),
    )

    sla = st.sidebar.multiselect(
        "Status SLA",
        _opcoes(df, "StatusSLA"),
    )

    return {
        "periodo": periodo,
        "grupos": grupos,
        "lojas": lojas,
        "problemas": problemas,
        "status": status,
        "responsaveis": responsaveis,
        "sla": sla,
    }


def aplicar_filtros(df, filtros):
    resultado = df.copy()

    periodo = filtros["periodo"]
    if isinstance(periodo, tuple) and len(periodo) == 2:
        inicio, fim = periodo
        resultado = resultado[
            resultado["Abertura"].dt.date.between(inicio, fim)
        ]

    mapas = {
        "grupos": "Grupo_Localizacao",
        "lojas": "Localizacao",
        "problemas": "Problema",
        "status": "Situacao",
        "responsaveis": "Responsavel",
        "sla": "StatusSLA",
    }

    for chave, coluna in mapas.items():
        selecionados = filtros[chave]
        if selecionados:
            resultado = resultado[
                resultado[coluna].astype(str).isin(selecionados)
            ]

    return resultado
