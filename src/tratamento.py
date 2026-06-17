import re

import pandas as pd


COLUNAS_PERMITIDAS = [
    "N° Chamado",
    "Título",
    "prioridade",
    "Tipo do Chamado",
    "TipoLocalizacao",
    "Localizacao",
    "Abertura",
    "Situacao",
    "StatusSLA",
    "SLA Atendimento",
    "ExecucaoAtendimento",
    "Equipe Responsavel",
    "Responsavel",
    "Categoria",
    "Produto",
    "Problema",
    "Encerramento",
    "descricao",
    "solucao",
    "Código de solução",
]

COLUNAS_DATA = [
    "Abertura",
    "Encerramento",
    "SLA Atendimento",
    "ExecucaoAtendimento",
]

STATUS_ENCERRADOS = {
    "encerrado",
    "fechado",
    "concluído",
    "concluido",
    "resolvido",
    "finalizado",
}


def _limpar_texto(valor):
    if pd.isna(valor):
        return None

    texto = str(valor)
    texto = texto.replace("_x000D_", " ")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def _converter_data_excel(serie):
    numerica = pd.to_numeric(serie, errors="coerce")

    datas_excel = pd.to_datetime(
        numerica,
        unit="D",
        origin="1899-12-30",
        errors="coerce",
    )

    datas_texto = pd.to_datetime(
        serie,
        dayfirst=True,
        errors="coerce",
    )

    return datas_excel.fillna(datas_texto)


def preparar_base(df):
    dados = df.copy()
    dados.columns = dados.columns.astype(str).str.strip()

    colunas_existentes = [
        coluna
        for coluna in COLUNAS_PERMITIDAS
        if coluna in dados.columns
    ]

    dados = dados[colunas_existentes].copy()
    dados = dados.dropna(how="all")

    colunas_obrigatorias = [
        "N° Chamado",
        "Abertura",
        "Situacao",
        "Localizacao",
        "Problema",
    ]

    faltantes = [
        coluna
        for coluna in colunas_obrigatorias
        if coluna not in dados.columns
    ]

    if faltantes:
        raise ValueError(
            "Colunas obrigatórias não encontradas: "
            + ", ".join(faltantes)
        )

    dados["N° Chamado"] = (
        dados["N° Chamado"]
        .astype(str)
        .str.strip()
    )

    dados = dados[
        dados["N° Chamado"].ne("")
        & dados["N° Chamado"].str.lower().ne("nan")
    ]

    dados = dados.drop_duplicates(
        subset=["N° Chamado"],
        keep="last",
    )

    for coluna in COLUNAS_DATA:
        if coluna in dados.columns:
            dados[coluna] = _converter_data_excel(dados[coluna])

    for coluna in [
        "Título",
        "descricao",
        "solucao",
        "Problema",
        "Produto",
        "Categoria",
        "Responsavel",
        "Equipe Responsavel",
        "Localizacao",
        "Situacao",
        "StatusSLA",
        "Código de solução",
    ]:
        if coluna in dados.columns:
            dados[coluna] = dados[coluna].apply(_limpar_texto)

    if "StatusSLA" not in dados.columns:
        dados["StatusSLA"] = None

    if "Produto" not in dados.columns:
        dados["Produto"] = None

    if "Responsavel" not in dados.columns:
        dados["Responsavel"] = None

    dados["Status_Normalizado"] = (
        dados["Situacao"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    dados["SLA_Normalizado"] = (
        dados["StatusSLA"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    dados["Encerrado_Flag"] = dados["Status_Normalizado"].isin(
        STATUS_ENCERRADOS
    )

    dados["Data_Abertura"] = dados["Abertura"].dt.date
    dados["Ano"] = dados["Abertura"].dt.year
    dados["Mes"] = dados["Abertura"].dt.to_period("M").astype(str)

    dados["InicioSemana"] = (
        dados["Abertura"]
        - pd.to_timedelta(
            dados["Abertura"].dt.weekday,
            unit="D",
        )
    ).dt.normalize()

    if "Encerramento" in dados.columns:
        diferenca = (
            dados["Encerramento"] - dados["Abertura"]
        ).dt.total_seconds() / 3600

        dados["Tempo_Resolucao_Horas"] = diferenca.where(
            diferenca >= 0
        )
    else:
        dados["Encerramento"] = pd.NaT
        dados["Tempo_Resolucao_Horas"] = pd.NA

    return dados
