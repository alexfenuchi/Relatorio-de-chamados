import pandas as pd


def carregar_excel(arquivo):
    planilha = pd.ExcelFile(arquivo)
    abas = planilha.sheet_names

    aba_preferida = next(
        (aba for aba in abas if "base" in aba.lower()),
        abas[0],
    )

    df = pd.read_excel(
        arquivo,
        sheet_name=aba_preferida,
    )

    return df, aba_preferida
