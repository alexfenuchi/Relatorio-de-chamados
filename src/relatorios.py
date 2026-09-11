import pandas as pd


def calcular_resumo_localizacoes(df: pd.DataFrame) -> pd.DataFrame:
    """Resume os chamados por localização sem incluir métricas de tempo."""
    return (
        df.groupby("Localizacao", dropna=False)
        .agg(
            Quantidade=("N° Chamado", "nunique"),
            Pendentes=("Encerrado_Flag", lambda valores: (~valores).sum()),
            Problemas_Distintos=("Problema", "nunique"),
        )
        .reset_index()
        .sort_values("Quantidade", ascending=False)
        .reset_index(drop=True)
    )


def calcular_problemas_localizacao(
    df: pd.DataFrame, localizacao: object
) -> pd.DataFrame:
    """Lista os problemas e suas quantidades para a localização selecionada."""
    if pd.isna(localizacao):
        recorte = df[df["Localizacao"].isna()]
    else:
        recorte = df[df["Localizacao"].eq(localizacao)]

    return (
        recorte.groupby("Problema", dropna=False)
        .agg(
            Quantidade=("N° Chamado", "nunique"),
            Pendentes=("Encerrado_Flag", lambda valores: (~valores).sum()),
        )
        .reset_index()
        .sort_values(["Quantidade", "Problema"], ascending=[False, True])
        .reset_index(drop=True)
    )
