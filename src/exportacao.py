from io import BytesIO
import pandas as pd

from src.tratamento import SLA_NIVEIS_HORAS
from src.metricas import calcular_resumo_sla_medido_por_nivel
from src.executivo import METAS_EXECUTIVAS, calcular_fluxo_periodo
from src.metricas import calcular_kpis
from src.insights import (
    calcular_saude_dados,
    criar_painel_metas,
    criar_resumo_executivo,
)


def _preparar_para_excel(df: pd.DataFrame) -> pd.DataFrame:
    dados = df.copy()
    for coluna in dados.columns:
        if pd.api.types.is_datetime64_any_dtype(dados[coluna]):
            try:
                dados[coluna] = dados[coluna].dt.tz_localize(None)
            except (TypeError, AttributeError):
                pass
        if dados[coluna].dtype == "object":
            dados[coluna] = dados[coluna].apply(
                lambda valor: (
                    str(valor) if isinstance(valor, (list, dict, tuple, set)) else valor
                )
            )
    return dados


def _resumo_por_grupo(
    dados: pd.DataFrame,
    grupo: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    recorte = dados[dados["Grupo_Localizacao"].eq(grupo)].copy()

    resumo_problemas = (
        recorte.groupby("Problema", dropna=False)["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
    )

    resumo_localizacoes = (
        recorte.groupby("Localizacao", dropna=False)
        .agg(
            Chamados=("N° Chamado", "nunique"),
            Problemas_Distintos=("Problema", "nunique"),
            Pendentes=("Encerrado_Flag", lambda valores: (~valores).sum()),
            MTTR_Horas=("Tempo_Resolucao_Horas", "mean"),
        )
        .reset_index()
        .sort_values("Chamados", ascending=False)
    )

    resumo_semanal = (
        recorte.groupby("InicioSemana", dropna=False)["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
        .sort_values("InicioSemana")
    )

    return recorte, resumo_problemas, resumo_localizacoes, resumo_semanal


def gerar_excel_relatorio(df: pd.DataFrame) -> bytes:
    if df is None or df.empty:
        raise ValueError("Não existem dados para gerar o relatório Excel.")

    dados = _preparar_para_excel(df)
    kpis = calcular_kpis(dados)
    resumo_executivo = criar_resumo_executivo(dados, kpis)
    fluxo = calcular_fluxo_periodo(
        dados,
        dados["Abertura"].min(),
        dados["Abertura"].max(),
    )
    painel_metas = criar_painel_metas(kpis, fluxo, METAS_EXECUTIVAS)
    saude_dados = calcular_saude_dados(dados)
    resumo_problemas = (
        dados.groupby("Problema", dropna=False)["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
    )
    resumo_lojas = (
        dados.groupby("Localizacao", dropna=False)["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
    )
    resumo_semanal = (
        dados.groupby("InicioSemana", dropna=False)["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
        .sort_values("InicioSemana")
    )
    resumo_sla = calcular_resumo_sla_medido_por_nivel(dados)
    loja, problemas_loja, localizacoes_loja, semanal_loja = _resumo_por_grupo(
        dados,
        "Loja",
    )
    cd, problemas_cd, localizacoes_cd, semanal_cd = _resumo_por_grupo(
        dados,
        "CD",
    )
    niveis_sla = pd.DataFrame(
        [
            {"nivelsla": nivel, "Meta": f"{horas} horas"}
            for nivel, horas in SLA_NIVEIS_HORAS.items()
        ]
    )

    saida = BytesIO()
    with pd.ExcelWriter(
        saida,
        engine="xlsxwriter",
        datetime_format="dd/mm/yyyy hh:mm",
        date_format="dd/mm/yyyy",
    ) as writer:
        resumo_executivo.to_excel(writer, index=False, sheet_name="Resumo Executivo")
        saude_dados.to_excel(
            writer,
            index=False,
            sheet_name="Resumo Executivo",
            startrow=len(resumo_executivo) + len(painel_metas) + 6,
        )
        painel_metas.to_excel(
            writer,
            index=False,
            sheet_name="Resumo Executivo",
            startrow=len(resumo_executivo) + 3,
        )
        dados.to_excel(writer, index=False, sheet_name="Chamados")
        resumo_semanal.to_excel(writer, index=False, sheet_name="Semanal")
        resumo_problemas.to_excel(writer, index=False, sheet_name="Problemas")
        resumo_lojas.to_excel(writer, index=False, sheet_name="Lojas")
        resumo_sla.to_excel(writer, index=False, sheet_name="Medicao SLA")
        loja.to_excel(writer, index=False, sheet_name="Chamados Loja")
        problemas_loja.to_excel(writer, index=False, sheet_name="Problemas Loja")
        localizacoes_loja.to_excel(writer, index=False, sheet_name="Locais Loja")
        semanal_loja.to_excel(writer, index=False, sheet_name="Semanal Loja")
        cd.to_excel(writer, index=False, sheet_name="Chamados CD")
        problemas_cd.to_excel(writer, index=False, sheet_name="Problemas CD")
        localizacoes_cd.to_excel(writer, index=False, sheet_name="Locais CD")
        semanal_cd.to_excel(writer, index=False, sheet_name="Semanal CD")
        niveis_sla.to_excel(writer, index=False, sheet_name="NivelSLA")

        for nome_aba, dataframe in {
            "Resumo Executivo": resumo_executivo,
            "Chamados": dados,
            "Semanal": resumo_semanal,
            "Problemas": resumo_problemas,
            "Lojas": resumo_lojas,
            "Medicao SLA": resumo_sla,
            "Chamados Loja": loja,
            "Problemas Loja": problemas_loja,
            "Locais Loja": localizacoes_loja,
            "Semanal Loja": semanal_loja,
            "Chamados CD": cd,
            "Problemas CD": problemas_cd,
            "Locais CD": localizacoes_cd,
            "Semanal CD": semanal_cd,
            "NivelSLA": niveis_sla,
        }.items():
            worksheet = writer.sheets[nome_aba]
            workbook = writer.book
            cabecalho = workbook.add_format(
                {
                    "bold": True,
                    "font_color": "#FFFFFF",
                    "bg_color": "#16324F",
                    "border": 0,
                    "align": "left",
                }
            )
            worksheet.freeze_panes(1, 0)
            worksheet.autofilter(
                0, 0, len(dataframe), max(len(dataframe.columns) - 1, 0)
            )
            for indice, coluna in enumerate(dataframe.columns):
                worksheet.write(0, indice, coluna, cabecalho)
            for indice, coluna in enumerate(dataframe.columns):
                largura = min(max(len(str(coluna)) + 2, 12), 45)
                worksheet.set_column(indice, indice, largura)

        resumo_ws = writer.sheets["Resumo Executivo"]
        linha_metas = len(resumo_executivo) + 3
        for indice, coluna in enumerate(painel_metas.columns):
            resumo_ws.write(linha_metas, indice, coluna, cabecalho)
        linha_qualidade = len(resumo_executivo) + len(painel_metas) + 6
        resumo_ws.write(linha_qualidade, 0, "Campo", cabecalho)
        resumo_ws.write(linha_qualidade, 1, "Preenchidos", cabecalho)
        resumo_ws.write(linha_qualidade, 2, "Cobertura_Percentual", cabecalho)

    saida.seek(0)
    return saida.getvalue()
