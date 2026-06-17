from io import BytesIO

import pandas as pd


COLUNAS_EXPORTACAO = [
    "N° Chamado",
    "Título",
    "prioridade",
    "Tipo do Chamado",
    "TipoLocalizacao",
    "Localizacao",
    "Abertura",
    "Situacao",
    "StatusSLA",
    "Equipe Responsavel",
    "Responsavel",
    "Categoria",
    "Produto",
    "Problema",
    "Encerramento",
    "Tempo_Resolucao_Horas",
    "descricao",
    "solucao",
    "Código de solução",
]


def _preparar_para_excel(df: pd.DataFrame) -> pd.DataFrame:
    colunas = [
        coluna
        for coluna in COLUNAS_EXPORTACAO
        if coluna in df.columns
    ]

    dados = df[colunas].copy()

    for coluna in dados.columns:
        if pd.api.types.is_datetime64_any_dtype(dados[coluna]):
            try:
                dados[coluna] = dados[coluna].dt.tz_localize(None)
            except (TypeError, AttributeError):
                pass

        if dados[coluna].dtype == "object":
            dados[coluna] = dados[coluna].apply(
                lambda valor: str(valor)
                if isinstance(valor, (list, dict, tuple, set))
                else valor
            )

    return dados


def gerar_excel_relatorio(df: pd.DataFrame) -> bytes:
    if df is None or df.empty:
        raise ValueError("Não existem dados para gerar o relatório Excel.")

    dados = _preparar_para_excel(df)

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

    resumo_semanal = (
        df.groupby("InicioSemana", dropna=False)["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
        .sort_values("InicioSemana")
    )

    saida = BytesIO()

    with pd.ExcelWriter(
        saida,
        engine="xlsxwriter",
        datetime_format="dd/mm/yyyy hh:mm",
        date_format="dd/mm/yyyy",
    ) as writer:
        dados.to_excel(
            writer,
            index=False,
            sheet_name="Chamados",
        )

        resumo_semanal.to_excel(
            writer,
            index=False,
            sheet_name="Semanal",
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

        tabelas = {
            "Chamados": dados,
            "Semanal": resumo_semanal,
            "Problemas": resumo_problemas,
            "Lojas": resumo_lojas,
        }

        for nome_aba, tabela in tabelas.items():
            planilha = writer.sheets[nome_aba]

            for indice, coluna in enumerate(tabela.columns):
                largura = min(
                    max(len(str(coluna)) + 2, 12),
                    45,
                )

                planilha.set_column(
                    indice,
                    indice,
                    largura,
                )

    saida.seek(0)
    return saida.getvalue()
