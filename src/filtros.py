import pandas as pd
import streamlit as st


def _opcoes(df: pd.DataFrame, coluna: str) -> list[str]:
    if coluna not in df.columns:
        return []
    return sorted(df[coluna].dropna().astype(str).unique().tolist())


def renderizar_filtros(df: pd.DataFrame) -> dict:
    st.sidebar.header("Filtros")

    datas_validas = df["Abertura"].dropna()
    if datas_validas.empty:
        periodo = None
    else:
        data_min = datas_validas.min().date()
        data_max = datas_validas.max().date()
        periodo = st.sidebar.date_input(
            "Período de abertura",
            value=(data_min, data_max),
            min_value=data_min,
            max_value=data_max,
        )

    return {
        "periodo": periodo,
        "lojas": st.sidebar.multiselect("Loja", _opcoes(df, "Localizacao")),
        "problemas": st.sidebar.multiselect("Problema", _opcoes(df, "Problema")),
        "status": st.sidebar.multiselect("Situação", _opcoes(df, "Situacao")),
        "responsaveis": st.sidebar.multiselect("Responsável", _opcoes(df, "Responsavel")),
        "sla": st.sidebar.multiselect("Status SLA", _opcoes(df, "StatusSLA")),
    }


def aplicar_filtros(df: pd.DataFrame, filtros: dict) -> pd.DataFrame:
    resultado = df.copy()

    periodo = filtros.get("periodo")
    if isinstance(periodo, (tuple, list)) and len(periodo) == 2:
        inicio, fim = periodo
        resultado = resultado[
            resultado["Abertura"].dt.date.between(inicio, fim)
        ]

    mapas = {
        "lojas": "Localizacao",
        "problemas": "Problema",
        "status": "Situacao",
        "responsaveis": "Responsavel",
        "sla": "StatusSLA",
    }

    for chave, coluna in mapas.items():
        selecionados = filtros.get(chave, [])
        if selecionados and coluna in resultado.columns:
            resultado = resultado[
                resultado[coluna].astype(str).isin(selecionados)
            ]

    return resultado.reset_index(drop=True)
