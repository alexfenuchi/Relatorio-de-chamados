import pandas as pd


def calcular_kpis(df: pd.DataFrame) -> dict:
    total = df["N° Chamado"].nunique()
    encerrados = df.loc[df["Encerrado_Flag"], "N° Chamado"].nunique()
    pendentes = df.loc[~df["Encerrado_Flag"], "N° Chamado"].nunique()

    dentro_sla = df.loc[
        df["SLA_Normalizado"].isin(
            ["em dia", "dentro", "dentro do prazo", "cumprido", "no prazo"]
        ),
        "N° Chamado",
    ].nunique()
    fora_sla = df.loc[
        df["SLA_Normalizado"].isin(
            ["em atraso", "fora", "fora do prazo", "vencido", "estourado"]
        ),
        "N° Chamado",
    ].nunique()

    tempo_medio = pd.to_numeric(
        df["Tempo_Resolucao_Horas"], errors="coerce"
    ).dropna().mean()

    return {
        "total": int(total),
        "encerrados": int(encerrados),
        "pendentes": int(pendentes),
        "percentual_encerrado": (encerrados / total * 100) if total else 0.0,
        "dentro_sla": int(dentro_sla),
        "fora_sla": int(fora_sla),
        "tempo_medio_horas": 0.0 if pd.isna(tempo_medio) else float(tempo_medio),
        "lojas": int(df["Localizacao"].dropna().nunique()),
    }
