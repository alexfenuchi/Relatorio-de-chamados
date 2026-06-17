import re
import unicodedata

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
    "concluido",
    "resolvido",
    "finalizado",
}


def _normalizar_nome_coluna(nome: object) -> str:
    texto = str(nome).strip()
    texto = unicodedata.normalize("NFKC", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto


def _sem_acento(valor: object) -> str:
    texto = "" if pd.isna(valor) else str(valor)
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c)).lower().strip()


def _limpar_texto(valor: object):
    if pd.isna(valor):
        return None
    texto = str(valor).replace("_x000D_", " ")
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto or None


def _converter_data_excel(serie: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(serie):
        return pd.to_datetime(serie, errors="coerce")

    numerica = pd.to_numeric(serie, errors="coerce")
    datas_excel = pd.to_datetime(
        numerica,
        unit="D",
        origin="1899-12-30",
        errors="coerce",
    )
    datas_texto = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return datas_excel.fillna(datas_texto)


def preparar_base(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        raise ValueError("A base enviada está vazia.")

    dados = df.copy()
    dados.columns = [_normalizar_nome_coluna(c) for c in dados.columns]

    # Elimina milhares de colunas vazias/formatadas existentes no Excel.
    dados = dados.dropna(axis=1, how="all").dropna(axis=0, how="all")

    colunas_existentes = [c for c in COLUNAS_PERMITIDAS if c in dados.columns]
    dados = dados.loc[:, colunas_existentes].copy()

    obrigatorias = ["N° Chamado", "Abertura", "Situacao", "Localizacao", "Problema"]
    faltantes = [c for c in obrigatorias if c not in dados.columns]
    if faltantes:
        raise ValueError(
            "Colunas obrigatórias não encontradas: " + ", ".join(faltantes)
        )

    dados["N° Chamado"] = (
        dados["N° Chamado"]
        .astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )
    dados = dados[
        dados["N° Chamado"].notna()
        & dados["N° Chamado"].ne("")
        & dados["N° Chamado"].str.lower().ne("nan")
    ]
    dados = dados.drop_duplicates(subset=["N° Chamado"], keep="last")

    for coluna in COLUNAS_DATA:
        if coluna in dados.columns:
            dados[coluna] = _converter_data_excel(dados[coluna])

    if dados["Abertura"].notna().sum() == 0:
        raise ValueError("Nenhuma data válida foi encontrada na coluna Abertura.")

    for coluna in dados.select_dtypes(include="object").columns:
        if coluna != "N° Chamado":
            dados[coluna] = dados[coluna].apply(_limpar_texto)

    dados["Status_Normalizado"] = dados["Situacao"].apply(_sem_acento)

    if "StatusSLA" not in dados.columns:
        dados["StatusSLA"] = None
    dados["SLA_Normalizado"] = dados["StatusSLA"].apply(_sem_acento)

    dados["Encerrado_Flag"] = dados["Status_Normalizado"].isin(STATUS_ENCERRADOS)
    dados["Data_Abertura"] = dados["Abertura"].dt.date
    dados["Ano"] = dados["Abertura"].dt.year.astype("Int64")
    dados["Mes"] = dados["Abertura"].dt.to_period("M").astype(str)
    dados["InicioSemana"] = (
        dados["Abertura"]
        - pd.to_timedelta(dados["Abertura"].dt.weekday, unit="D")
    ).dt.normalize()

    if "Encerramento" in dados.columns:
        diferenca = (
            dados["Encerramento"] - dados["Abertura"]
        ).dt.total_seconds() / 3600
        dados["Tempo_Resolucao_Horas"] = diferenca.where(diferenca >= 0)
    else:
        dados["Encerramento"] = pd.NaT
        dados["Tempo_Resolucao_Horas"] = pd.NA

    return dados.reset_index(drop=True)
