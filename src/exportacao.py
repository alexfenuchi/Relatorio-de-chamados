from io import BytesIO
import pandas as pd


def gerar_excel_relatorio(df):
    saida = BytesIO()

    with pd.ExcelWriter(saida, engine="openpyxl") as writer:
        df.to_excel(
            writer,
            index=False,
            sheet_name="Chamados",
        )

        resumo_problemas = (
            df.groupby("Problema", dropna=False)["N° Chamado"]
            .nunique()
            .reset_index(name="Quantidade")
            .sort_values("Quantidade", ascending=False)
        )

        resumo_lojas = (
            df.groupby("Localizacao", dropna=False)["N° Chamado"]
            .nunique()
            .reset_index(name="Quantidade")
            .sort_values("Quantidade", ascending=False)
        )

        resumo_problemas.to_excel(
            writer,
            index=False,
            sheet_name="Problemas",
        )

        resumo_lojas.to_excel(
            writer,
            index=False,
            sheet_name="Lojas",
        )

    saida.seek(0)
    return saida.getvalue()
