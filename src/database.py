from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st
from supabase import Client, create_client

TABELA_CHAMADOS = "chamados_n2"
TABELA_CARGAS = "cargas_chamados"
TAMANHO_PAGINA = 1000
TAMANHO_LOTE = 300

MAPA_COLUNAS = {
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


@st.cache_resource
def obter_supabase() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        chave = st.secrets["SUPABASE_KEY"]
    except Exception as erro:
        raise RuntimeError(
            "Configure SUPABASE_URL e SUPABASE_KEY nos Secrets do Streamlit."
        ) from erro

    if not str(url).strip() or not str(chave).strip():
        raise RuntimeError("SUPABASE_URL ou SUPABASE_KEY está vazio.")

    return create_client(str(url).strip(), str(chave).strip())


def buscar_chamados() -> pd.DataFrame:
    supabase = obter_supabase()
    registros: list[dict[str, Any]] = []
    inicio = 0

    while True:
        resposta = (
            supabase.table(TABELA_CHAMADOS)
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
            df[coluna] = pd.to_datetime(df[coluna], errors="coerce", utc=True).dt.tz_convert(None)

    return df


def _valor_json(valor: Any):
    if valor is None or pd.isna(valor):
        return None
    if isinstance(valor, pd.Timestamp):
        return valor.isoformat()
    return str(valor).strip()


def preparar_registros_supabase(df: pd.DataFrame) -> list[dict]:
    dados = df.rename(columns=MAPA_COLUNAS).copy()
    colunas_banco = list(MAPA_COLUNAS.values())

    for coluna in colunas_banco:
        if coluna not in dados.columns:
            dados[coluna] = None

    dados = dados.loc[:, colunas_banco]
    dados["numero_chamado"] = (
        dados["numero_chamado"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    )
    dados = dados[
        dados["numero_chamado"].ne("")
        & dados["numero_chamado"].str.lower().ne("nan")
    ]
    dados = dados.drop_duplicates(subset=["numero_chamado"], keep="last")

    for coluna in ["abertura", "encerramento"]:
        dados[coluna] = pd.to_datetime(dados[coluna], errors="coerce")

    registros = []
    agora = datetime.now(timezone.utc).isoformat()
    for registro in dados.to_dict(orient="records"):
        convertido = {chave: _valor_json(valor) for chave, valor in registro.items()}
        convertido["atualizado_em"] = agora
        registros.append(convertido)

    return registros


def atualizar_chamados(df: pd.DataFrame, nome_arquivo: str | None = None) -> int:
    supabase = obter_supabase()
    registros = preparar_registros_supabase(df)
    if not registros:
        return 0

    for inicio in range(0, len(registros), TAMANHO_LOTE):
        lote = registros[inicio : inicio + TAMANHO_LOTE]
        (
            supabase.table(TABELA_CHAMADOS)
            .upsert(lote, on_conflict="numero_chamado")
            .execute()
        )

    if nome_arquivo:
        try:
            supabase.table(TABELA_CARGAS).insert(
                {
                    "nome_arquivo": nome_arquivo,
                    "quantidade_registros": len(registros),
                }
            ).execute()
        except Exception:
            # A tabela de controle é opcional e não pode impedir a carga principal.
            pass

    return len(registros)
