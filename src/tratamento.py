import re
import unicodedata
from datetime import datetime

import numpy as np
import pandas as pd


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

SLA_NIVEIS_HORAS = {
    "Suporte_TI_P1": 2,
    "Suporte_TI_P2": 4,
    "Suporte_TI_P3": 8,
    "Suporte_TI_P4": 24,
    "Suporte_TI_P5": 72,
    "SuporteAdm_P1": 4,
    "SuporteAdm_P2": 8,
    "SuporteAdm_P3": 16,
    "SuporteAdm_P4": 32,
}


DIAS_SEMANA_PT = {
    0: "Segunda",
    1: "Terça",
    2: "Quarta",
    3: "Quinta",
    4: "Sexta",
    5: "Sábado",
    6: "Domingo",
}


def _normalizar_para_comparacao(valor):
    if pd.isna(valor):
        return ""

    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip().lower()


def _grupo_localizacao(linha):
    tipo = _normalizar_para_comparacao(
        linha.get("TipoLocalizacao")
    )
    localizacao = _normalizar_para_comparacao(
        linha.get("Localizacao")
    )

    if "loja" in tipo or "loja" in localizacao:
        return "Loja"

    return "CD"


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


def _horas_uteis_8h(inicio, fim):
    """
    Calcula duração em horas considerando:
    - segunda a sexta-feira;
    - cada dia útil equivalente a 8 horas;
    - diferença do horário de início e fim preservada.

    Exemplo:
    segunda 09:00 até terça 09:00 = 8 horas.
    sexta 14:00 até segunda 10:00 = 4 horas.

    Feriados não são descontados nesta versão.
    """
    if pd.isna(inicio) or pd.isna(fim) or fim < inicio:
        return np.nan

    inicio = pd.Timestamp(inicio)
    fim = pd.Timestamp(fim)

    if inicio.date() == fim.date():
        if inicio.weekday() >= 5:
            return 0.0
        return min(max((fim - inicio).total_seconds() / 3600, 0.0), 8.0)

    dias_uteis = np.busday_count(
        inicio.date(),
        fim.date(),
        weekmask="1111100",
    )

    diferenca_horario = (
        (
            fim.hour
            + fim.minute / 60
            + fim.second / 3600
        )
        -
        (
            inicio.hour
            + inicio.minute / 60
            + inicio.second / 3600
        )
    )

    horas = float(dias_uteis * 8 + diferenca_horario)

    dias_uteis_inclusivos = np.busday_count(
        inicio.date(),
        (fim + pd.Timedelta(days=1)).date(),
        weekmask="1111100",
    )
    limite_maximo = float(dias_uteis_inclusivos * 8)

    return min(max(horas, 0.0), limite_maximo)


def _faixa_aging(horas):
    if pd.isna(horas):
        return "Sem informação"
    if horas <= 8:
        return "Até 1 dia"
    if horas <= 24:
        return "2 a 3 dias"
    if horas <= 40:
        return "4 a 5 dias"
    if horas <= 80:
        return "6 a 10 dias"
    return "Acima de 10 dias"


def preparar_base(df):
    dados = df.copy()
    dados.columns = dados.columns.astype(str).str.strip()

    # Remove colunas completamente vazias, inclusive as milhares de colunas
    # formatadas sem conteúdo que podem existir no Excel.
    dados = dados.dropna(axis=1, how="all")
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
        "prioridade",
        "Tipo do Chamado",
        "TipoLocalizacao",
        "nivelsla",
    ]:
        if coluna in dados.columns:
            dados[coluna] = dados[coluna].apply(_limpar_texto)

    for coluna in [
        "StatusSLA",
        "Produto",
        "Categoria",
        "Responsavel",
        "Equipe Responsavel",
        "prioridade",
        "Tipo do Chamado",
        "descricao",
        "solucao",
        "TipoLocalizacao",
        "nivelsla",
    ]:
        if coluna not in dados.columns:
            dados[coluna] = None

    dados["Grupo_Localizacao"] = dados.apply(
        _grupo_localizacao,
        axis=1,
    )

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

    dados["DiaSemana"] = (
        dados["Abertura"]
        .dt.weekday
        .map(DIAS_SEMANA_PT)
    )

    dados["HoraAbertura"] = dados["Abertura"].dt.hour

    if "Encerramento" not in dados.columns:
        dados["Encerramento"] = pd.NaT

    dados["Tempo_Resolucao_Horas"] = dados.apply(
        lambda linha: _horas_uteis_8h(
            linha["Abertura"],
            linha["Encerramento"],
        ),
        axis=1,
    )

    dados["Tempo_Resolucao_Dias"] = (
        dados["Tempo_Resolucao_Horas"] / 8
    )

    agora = pd.Timestamp.now().tz_localize(None)

    dados["Idade_Pendente_Horas"] = dados.apply(
        lambda linha: (
            _horas_uteis_8h(linha["Abertura"], agora)
            if not linha["Encerrado_Flag"]
            else np.nan
        ),
        axis=1,
    )

    dados["Idade_Pendente_Dias"] = (
        dados["Idade_Pendente_Horas"] / 8
    )

    dados["Faixa_Aging"] = np.select(
        [
            dados["Idade_Pendente_Dias"].le(1),
            dados["Idade_Pendente_Dias"].between(
                1,
                3,
                inclusive="right",
            ),
            dados["Idade_Pendente_Dias"].between(
                3,
                5,
                inclusive="right",
            ),
            dados["Idade_Pendente_Dias"].between(
                5,
                10,
                inclusive="right",
            ),
            dados["Idade_Pendente_Dias"].gt(10),
        ],
        [
            "Até 1 dia",
            "2 a 3 dias",
            "4 a 5 dias",
            "6 a 10 dias",
            "Acima de 10 dias",
        ],
        default=None,
    )

    dados["SLA_Meta_Horas"] = dados["nivelsla"].map(SLA_NIVEIS_HORAS)

    dados["SLA_Tempo_Medido_Horas"] = np.where(
        dados["Encerrado_Flag"],
        dados["Tempo_Resolucao_Horas"],
        dados["Idade_Pendente_Horas"],
    )

    dados["SLA_Medido_Status"] = np.select(
        [
            dados["SLA_Meta_Horas"].isna(),
            dados["SLA_Tempo_Medido_Horas"].isna(),
            dados["SLA_Tempo_Medido_Horas"] <= dados["SLA_Meta_Horas"],
        ],
        [
            "Sem meta cadastrada",
            "Sem tempo calculado",
            "Dentro do SLA",
        ],
        default="Fora do SLA",
    )

    dados["SLA_Excedido_Horas"] = (
        dados["SLA_Tempo_Medido_Horas"] - dados["SLA_Meta_Horas"]
    ).clip(lower=0)

    return dados
