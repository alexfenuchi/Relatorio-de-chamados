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
    colunas = [c for c in COLUNAS_EXPORTACAO if c in df.columns]
    dados = df.loc[:, colunas].copy()

    for coluna in dados.columns:
        if pd.api.types.is_datetime64_any_dtype(dados[coluna]):
            try:
                dados[coluna] = dados[coluna].dt.tz_localize(None)
            except (TypeError, AttributeError):
                pass
        elif dados[coluna].dtype == "object":
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
    if dados.shape[1] > 16384:
        raise ValueError("A quantidade de colunas excede o limite do Excel.")

    resumo_semanal = (
        df.dropna(subset=["InicioSemana"])
        .groupby("InicioSemana")["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
        .sort_values("InicioSemana")
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

    saida = BytesIO()
    with pd.ExcelWriter(
        saida,
        engine="xlsxwriter",
        datetime_format="dd/mm/yyyy hh:mm",
        date_format="dd/mm/yyyy",
    ) as writer:
        tabelas = {
            "Chamados": dados,
            "Semanal": resumo_semanal,
            "Problemas": resumo_problemas,
            "Lojas": resumo_lojas,
        }
        for nome_aba, tabela in tabelas.items():
            tabela.to_excel(writer, index=False, sheet_name=nome_aba)
            worksheet = writer.sheets[nome_aba]
            worksheet.freeze_panes(1, 0)
            worksheet.autofilter(0, 0, max(len(tabela), 1), max(len(tabela.columns) - 1, 0))
            for indice, coluna in enumerate(tabela.columns):
                amostra = tabela[coluna].astype(str).head(100)
                largura = max([len(str(coluna))] + amostra.map(len).tolist()) + 2
                worksheet.set_column(indice, indice, min(max(largura, 12), 50))

    saida.seek(0)
    return saida.getvalue()
