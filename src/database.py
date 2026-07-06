from __future__ import annotations

from datetime import date, datetime
from urllib.parse import urlparse
import math

import numpy as np
import pandas as pd
from postgrest.exceptions import APIError
import streamlit as st
from supabase import Client, create_client


NOME_TABELA = "chamados_n2"
TAMANHO_PAGINA = 1000
TAMANHO_LOTE = 300


class SchemaSupabaseDesatualizadoError(RuntimeError):
    """Erro amigável para quando o Supabase não reconhece uma coluna."""


def _erro_coluna_schema_cache(erro: APIError, coluna: str) -> bool:
    mensagem = str(getattr(erro, "message", ""))
    codigo = getattr(erro, "code", None)

    return codigo == "PGRST204" and f"'{coluna}' column" in mensagem


def _mensagem_coluna_nivelsla_ausente() -> str:
    return (
        "A coluna 'nivelsla' não foi encontrada na tabela 'chamados_n2' "
        "do Supabase. Abra o SQL Editor do Supabase, execute `ALTER TABLE "
        "public.chamados_n2 ADD COLUMN IF NOT EXISTS nivelsla TEXT;` e, "
        "se a coluna acabou de ser criada, recarregue o schema cache em "
        "Database > API > Reload schema. Depois tente atualizar a base "
        "novamente."
    )


def _normalizar_url_supabase(valor: str) -> str:
    url = str(valor or "").strip().strip('"').strip("'")

    if not url:
        raise ValueError("SUPABASE_URL não foi configurada.")

    if "://" not in url:
        url = f"https://{url}"

    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            "SUPABASE_URL inválida. Use, por exemplo: "
            "https://seu-projeto.supabase.co"
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
            "Configure SUPABASE_URL e SUPABASE_KEY."
        ) from erro

    url = _normalizar_url_supabase(url_bruta)

    if not chave:
        raise ValueError("SUPABASE_KEY não foi configurada.")

    return create_client(url, chave)


def testar_conexao() -> int:
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


def _valor_json_seguro(valor):
    """
    Converte valores do pandas/numpy em valores aceitos pelo JSON/PostgREST.
    NaN, NaT, pd.NA e infinito viram None.
    """
    if valor is None:
        return None

    if isinstance(valor, (datetime, date, pd.Timestamp)):
        if pd.isna(valor):
            return None
        return valor.isoformat()

    if isinstance(valor, (np.integer,)):
        return int(valor)

    if isinstance(valor, (np.floating, float)):
        numero = float(valor)
        if math.isnan(numero) or math.isinf(numero):
            return None
        return numero

    if isinstance(valor, (np.bool_,)):
        return bool(valor)

    try:
        resultado_nulo = pd.isna(valor)
        if isinstance(resultado_nulo, (bool, np.bool_)) and resultado_nulo:
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(valor, dict):
        return {
            str(chave): _valor_json_seguro(conteudo)
            for chave, conteudo in valor.items()
        }

    if isinstance(valor, (list, tuple, set)):
        return [_valor_json_seguro(item) for item in valor]

    return str(valor).strip()


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
        "nivelsla": "nivelsla",
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

    # Converte datas; datas inválidas se tornam NaT e depois None.
    for coluna in ["abertura", "encerramento"]:
        dados[coluna] = pd.to_datetime(
            dados[coluna],
            errors="coerce",
        )

    registros_brutos = dados.to_dict(orient="records")

    registros = [
        {
            chave: _valor_json_seguro(valor)
            for chave, valor in registro.items()
        }
        for registro in registros_brutos
    ]

    # Validação final: nenhum NaN ou infinito pode seguir para o Supabase.
    for indice, registro in enumerate(registros):
        for chave, valor in registro.items():
            if isinstance(valor, float) and (
                math.isnan(valor) or math.isinf(valor)
            ):
                raise ValueError(
                    f"Valor inválido ainda presente no registro "
                    f"{indice}, coluna '{chave}'."
                )

    return registros


def atualizar_chamados(df: pd.DataFrame) -> int:
    supabase = obter_supabase()
    registros = preparar_registros_supabase(df)

    if not registros:
        return 0

    for inicio in range(0, len(registros), TAMANHO_LOTE):
        lote = registros[inicio:inicio + TAMANHO_LOTE]

        try:
            (
                supabase.table(NOME_TABELA)
                .upsert(
                    lote,
                    on_conflict="numero_chamado",
                )
                .execute()
            )
        except APIError as erro:
            if _erro_coluna_schema_cache(erro, "nivelsla"):
                raise SchemaSupabaseDesatualizadoError(
                    _mensagem_coluna_nivelsla_ausente()
                ) from erro

            raise

    return len(registros)
