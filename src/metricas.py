import pandas as pd


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
        df["SLA_Normalizado"].isin(
            ["em dia", "dentro", "dentro do prazo"]
        ),
        "N° Chamado",
    ].nunique()

    fora_sla = df.loc[
        df["SLA_Normalizado"].isin(
            ["em atraso", "fora", "fora do prazo"]
        ),
        "N° Chamado",
    ].nunique()

    total_sla_classificado = dentro_sla + fora_sla

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
        "percentual_encerrado": (
            encerrados / total * 100
            if total
            else 0
        ),
        "dentro_sla": dentro_sla,
        "fora_sla": fora_sla,
        "sla_percentual": (
            dentro_sla / total_sla_classificado * 100
            if total_sla_classificado
            else 0
        ),
        "tempo_medio_horas": _valor_seguro(tempos.mean()),
        "tempo_mediano_horas": _valor_seguro(tempos.median()),
        "tempo_medio_dias": _valor_seguro(tempos.mean() / 8),
        "aging_medio_horas": _valor_seguro(aging.mean()),
        "aging_maximo_horas": _valor_seguro(aging.max()),
        "aging_medio_dias": _valor_seguro(aging.mean() / 8),
        "aging_maximo_dias": _valor_seguro(aging.max() / 8),
        "lojas": lojas,
    }
