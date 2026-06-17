from __future__ import annotations

from urllib.parse import urlparse

import pandas as pd
import streamlit as st
from supabase import Client, create_client


NOME_TABELA = "chamados_n2"
TAMANHO_PAGINA = 1000
TAMANHO_LOTE = 300


def _normalizar_url_supabase(valor: str) -> str:
    """
    Aceita tanto a URL raiz quanto uma URL copiada com caminhos extras
    e devolve somente a origem do projeto:
    https://id-do-projeto.supabase.co
    """
    url = str(valor or "").strip().strip('"').strip("'")

    if not url:
        raise ValueError("SUPABASE_URL não foi configurada.")

    if "://" not in url:
        url = f"https://{url}"

    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            "SUPABASE_URL inválida. Use a URL do projeto, por exemplo: "
            "https://seu-projeto.supabase.co"
        )

    host = parsed.netloc.strip().lower()

    if "supabase.co" not in host and "supabase.in" not in host:
        raise ValueError(
            "SUPABASE_URL não parece ser uma URL válida de projeto Supabase."
        )

    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


@st.cache_resource
def obter_supabase() -> Client:
    try:
        url_bruta = st.secrets["SUPABASE_URL"]
        chave = str(st.secrets["SUPABASE_KEY"]).strip()
    except KeyError as erro:
        raise ValueError(
            f"Secret não configurado: {erro}. "
            "Configure SUPABASE_URL e SUPABASE_KEY no Streamlit Cloud."
        ) from erro

    url = _normalizar_url_supabase(url_bruta)

    if not chave:
        raise ValueError("SUPABASE_KEY não foi configurada.")

    return create_client(url, chave)


def testar_conexao() -> int:
    """
    Testa a leitura da tabela e retorna a quantidade total de registros.
    """
    supabase = obter_supabase()

    resposta = (
        supabase.table(NOME_TABELA)
        .select("numero_chamado", count="exact")
        .limit(1)
        .execute()
    )

    return int(resposta.count or 0)


def buscar_chamados() -> pd.DataFrame:
    supabase = obter_supabase()
    registros: list[dict] = []
    inicio = 0

    while True:
        resposta = (
            supabase.table(NOME_TABELA)
            .select("*")
            .order("abertura", desc=False)
            .range(inicio, inicio + TAMANHO_PAGINA - 1)
            .execute()
        )

        pagina = resposta.data or []

        if not pagina:
            break

        registros.extend(pagina)

        if len(pagina) < TAMANHO_PAGINA:
            break

        inicio += TAMANHO_PAGINA

    df = pd.DataFrame(registros)

    if df.empty:
        return df

    for coluna in ["abertura", "encerramento", "atualizado_em"]:
        if coluna in df.columns:
            serie = pd.to_datetime(
                df[coluna],
                errors="coerce",
                utc=True,
            )
            df[coluna] = serie.dt.tz_convert(None)

    return df


def preparar_registros_supabase(df: pd.DataFrame) -> list[dict]:
    mapa_colunas = {
        "N° Chamado": "numero_chamado",
        "Título": "titulo",
        "prioridade": "prioridade",
        "Tipo do Chamado": "tipo_chamado",
        "TipoLocalizacao": "tipo_localizacao",
        "Localizacao": "localizacao",
        "Abertura": "abertura",
        "Situacao": "situacao",
        "StatusSLA": "status_sla",
        "Equipe Responsavel": "equipe_responsavel",
        "Responsavel": "responsavel",
        "Categoria": "categoria",
        "Produto": "produto",
        "Problema": "problema",
        "Encerramento": "encerramento",
        "descricao": "descricao",
        "solucao": "solucao",
        "Código de solução": "codigo_solucao",
    }

    dados = df.rename(columns=mapa_colunas).copy()
    colunas_banco = list(mapa_colunas.values())

    for coluna in colunas_banco:
        if coluna not in dados.columns:
            dados[coluna] = None

    dados = dados[colunas_banco].copy()

    dados["numero_chamado"] = (
        dados["numero_chamado"]
        .astype(str)
        .str.strip()
    )

    dados = dados[
        dados["numero_chamado"].notna()
        & dados["numero_chamado"].ne("")
        & dados["numero_chamado"].str.lower().ne("nan")
        & dados["numero_chamado"].str.lower().ne("none")
    ]

    dados = dados.drop_duplicates(
        subset=["numero_chamado"],
        keep="last",
    )

    for coluna in ["abertura", "encerramento"]:
        dados[coluna] = pd.to_datetime(
            dados[coluna],
            errors="coerce",
        )

        dados[coluna] = dados[coluna].apply(
            lambda valor: valor.isoformat()
            if pd.notna(valor)
            else None
        )

    for coluna in dados.columns:
        if coluna not in {"abertura", "encerramento"}:
            dados[coluna] = dados[coluna].apply(
                lambda valor: None
                if pd.isna(valor)
                else str(valor).strip()
            )

    return dados.to_dict(orient="records")


def atualizar_chamados(df: pd.DataFrame) -> int:
    supabase = obter_supabase()
    registros = preparar_registros_supabase(df)

    if not registros:
        return 0

    for inicio in range(0, len(registros), TAMANHO_LOTE):
        lote = registros[inicio:inicio + TAMANHO_LOTE]

        (
            supabase.table(NOME_TABELA)
            .upsert(
                lote,
                on_conflict="numero_chamado",
            )
            .execute()
        )

    return len(registros)
