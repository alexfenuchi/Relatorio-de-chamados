import pandas as pd

METAS_EXECUTIVAS = {
    "sla_medido_percentual": 95.0,
    "percentual_backlog": 15.0,
    "tempo_medio_horas": 8.0,
    "taxa_absorcao": 100.0,
}


def _valor_seguro(valor):
    return 0 if pd.isna(valor) else float(valor)


def calcular_kpis(df):
    total = df["N° Chamado"].nunique()

    encerrados = df.loc[
        df["Encerrado_Flag"],
        "N° Chamado",
    ].nunique()

    pendentes = df.loc[
        ~df["Encerrado_Flag"],
        "N° Chamado",
    ].nunique()

    dentro_sla = df.loc[
        df["SLA_Normalizado"].isin(["em dia", "dentro", "dentro do prazo"]),
        "N° Chamado",
    ].nunique()

    fora_sla = df.loc[
        df["SLA_Normalizado"].isin(["em atraso", "fora", "fora do prazo"]),
        "N° Chamado",
    ].nunique()

    total_sla_classificado = dentro_sla + fora_sla

    if "SLA_Medido_Status" in df.columns:
        dentro_sla_medido = df.loc[
            df["SLA_Medido_Status"].eq("Dentro do SLA"),
            "N° Chamado",
        ].nunique()
        fora_sla_medido = df.loc[
            df["SLA_Medido_Status"].eq("Fora do SLA"),
            "N° Chamado",
        ].nunique()
    else:
        dentro_sla_medido = 0
        fora_sla_medido = 0

    total_sla_medido = dentro_sla_medido + fora_sla_medido

    hoje = pd.Timestamp.now().date()
    abertos_hoje = df.loc[
        df["Abertura"].dt.date.eq(hoje),
        "N° Chamado",
    ].nunique()

    if "Encerramento" in df.columns:
        encerrados_hoje = df.loc[
            df["Encerramento"].notna() & df["Encerramento"].dt.date.eq(hoje),
            "N° Chamado",
        ].nunique()
    else:
        encerrados_hoje = 0

    proximos_vencer = df.loc[
        ~df["Encerrado_Flag"]
        & df["SLA_Excedido_Horas"].eq(0)
        & df["SLA_Meta_Horas"].notna()
        & df["SLA_Tempo_Medido_Horas"].notna()
        & ((df["SLA_Meta_Horas"] - df["SLA_Tempo_Medido_Horas"]) <= 2),
        "N° Chamado",
    ].nunique()

    tempos = df.loc[
        df["Encerrado_Flag"],
        "Tempo_Resolucao_Horas",
    ].dropna()

    aging = df.loc[
        ~df["Encerrado_Flag"],
        "Idade_Pendente_Horas",
    ].dropna()

    lojas = df["Localizacao"].dropna().nunique()

    return {
        "total": total,
        "encerrados": encerrados,
        "pendentes": pendentes,
        "percentual_encerrado": (encerrados / total * 100 if total else 0),
        "percentual_backlog": (pendentes / total * 100 if total else 0),
        "dentro_sla": dentro_sla,
        "fora_sla": fora_sla,
        "sla_percentual": (
            dentro_sla / total_sla_classificado * 100 if total_sla_classificado else 0
        ),
        "dentro_sla_medido": dentro_sla_medido,
        "fora_sla_medido": fora_sla_medido,
        "sla_medido_percentual": (
            dentro_sla_medido / total_sla_medido * 100 if total_sla_medido else 0
        ),
        "abertos_hoje": abertos_hoje,
        "encerrados_hoje": encerrados_hoje,
        "proximos_vencer": proximos_vencer,
        "tempo_medio_horas": _valor_seguro(tempos.mean()),
        "tempo_mediano_horas": _valor_seguro(tempos.median()),
        "tempo_medio_dias": _valor_seguro(tempos.mean() / 8),
        "aging_medio_horas": _valor_seguro(aging.mean()),
        "aging_maximo_horas": _valor_seguro(aging.max()),
        "aging_medio_dias": _valor_seguro(aging.mean() / 8),
        "aging_maximo_dias": _valor_seguro(aging.max() / 8),
        "lojas": lojas,
    }


def calcular_resumo_sla_medido_por_nivel(df):
    """Resume a medição de SLA por nível usando chamados únicos.

    Mantém a quantidade total de chamados do nível separada dos contadores
    medidos, para evitar que totais sejam inflados por linhas/flags auxiliares
    e para deixar os indicadores de SLA consistentes em todas as visões.
    """
    resumo = (
        df.groupby("nivelsla", dropna=False)["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
    )

    for coluna, status in {
        "Dentro_SLA": "Dentro do SLA",
        "Fora_SLA": "Fora do SLA",
    }.items():
        contagem = (
            df.loc[df["SLA_Medido_Status"].eq(status)]
            .groupby("nivelsla", dropna=False)["N° Chamado"]
            .nunique()
            .reset_index(name=coluna)
        )
        resumo = resumo.merge(contagem, on="nivelsla", how="left")

    resumo[["Dentro_SLA", "Fora_SLA"]] = (
        resumo[["Dentro_SLA", "Fora_SLA"]].fillna(0).astype(int)
    )
    resumo["Chamados_Medidos"] = resumo["Dentro_SLA"] + resumo["Fora_SLA"]

    medias = (
        df.groupby("nivelsla", dropna=False)
        .agg(
            Meta_Horas=("SLA_Meta_Horas", "first"),
            Tempo_Medio_Medido_Horas=("SLA_Tempo_Medido_Horas", "mean"),
            Excedido_Medio_Horas=("SLA_Excedido_Horas", "mean"),
        )
        .reset_index()
    )
    resumo = resumo.merge(medias, on="nivelsla", how="left")
    resumo["Aderencia_Percentual"] = (
        resumo["Dentro_SLA"] / resumo["Chamados_Medidos"].replace(0, pd.NA) * 100
    ).fillna(0)

    return resumo.sort_values("nivelsla", na_position="last")


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
