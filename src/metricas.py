def calcular_kpis(df):
    total = df["N° Chamado"].nunique()
    encerrados = df.loc[df["Encerrado_Flag"], "N° Chamado"].nunique()
    pendentes = df.loc[~df["Encerrado_Flag"], "N° Chamado"].nunique()

    dentro_sla = df.loc[
        df["SLA_Normalizado"].isin(["em dia", "dentro", "dentro do prazo"]),
        "N° Chamado",
    ].nunique()

    fora_sla = df.loc[
        df["SLA_Normalizado"].isin(["em atraso", "fora", "fora do prazo"]),
        "N° Chamado",
    ].nunique()

    tempo_medio = df["Tempo_Resolucao_Horas"].dropna().mean()
    lojas = df["Localizacao"].dropna().nunique()

    return {
        "total": total,
        "encerrados": encerrados,
        "pendentes": pendentes,
        "percentual_encerrado": (encerrados / total * 100) if total else 0,
        "dentro_sla": dentro_sla,
        "fora_sla": fora_sla,
        "tempo_medio_horas": 0 if tempo_medio != tempo_medio else tempo_medio,
        "lojas": lojas,
    }
