import pandas as pd


def carregar_excel(arquivo):
    planilha = pd.ExcelFile(arquivo)
    if not planilha.sheet_names:
        raise ValueError("O arquivo Excel não possui abas.")

    aba_preferida = next(
        (aba for aba in planilha.sheet_names if "base" in aba.lower()),
        planilha.sheet_names[0],
    )

    df = pd.read_excel(
        arquivo,
        sheet_name=aba_preferida,
        engine="openpyxl" if str(getattr(arquivo, "name", "")).lower().endswith(".xlsx") else None,
    )

    # Remove já na leitura colunas totalmente vazias.
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
    return df, aba_preferida
