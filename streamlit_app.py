import streamlit as st

from src.leitura import carregar_excel
from src.tratamento import preparar_base
from src.filtros import aplicar_filtros, renderizar_filtros
from src.metricas import calcular_kpis
from src.graficos import (
    grafico_evolucao_semanal,
    grafico_top_problemas,
    grafico_top_lojas,
    grafico_status,
    grafico_sla,
    grafico_responsaveis,
)
from src.exportacao import gerar_excel_relatorio

st.set_page_config(
    page_title="Relatório de Chamados N2",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Relatório de Chamados — Suporte N2")
st.caption(
    "Envie a base anual em Excel. O sistema trata as datas, permite filtros "
    "e gera análises semanais, por loja, problema, status, SLA e responsável."
)

arquivo = st.file_uploader(
    "Selecione a base anual de chamados",
    type=["xlsx", "xls"],
)

if arquivo is None:
    st.info("Envie o arquivo Excel para iniciar a análise.")
    st.stop()

try:
    bruto, aba = carregar_excel(arquivo)
    df = preparar_base(bruto)
except Exception as erro:
    st.error(f"Não foi possível processar a base: {erro}")
    st.stop()

st.success(
    f"Base carregada: {len(df):,} linhas | Aba: {aba}".replace(",", ".")
)

filtros = renderizar_filtros(df)
df_filtrado = aplicar_filtros(df, filtros)

if df_filtrado.empty:
    st.warning("Nenhum chamado encontrado para os filtros selecionados.")
    st.stop()

kpis = calcular_kpis(df_filtrado)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total de chamados", f"{kpis['total']:,}".replace(",", "."))
c2.metric("Encerrados", f"{kpis['encerrados']:,}".replace(",", "."))
c3.metric("Pendentes", f"{kpis['pendentes']:,}".replace(",", "."))
c4.metric("Encerrados (%)", f"{kpis['percentual_encerrado']:.1f}%")

c5, c6, c7, c8 = st.columns(4)
c5.metric("Dentro do SLA", f"{kpis['dentro_sla']:,}".replace(",", "."))
c6.metric("Fora do SLA", f"{kpis['fora_sla']:,}".replace(",", "."))
c7.metric("Tempo médio (h)", f"{kpis['tempo_medio_horas']:.1f}")
c8.metric("Lojas impactadas", f"{kpis['lojas']:,}".replace(",", "."))

aba1, aba2, aba3, aba4, aba5 = st.tabs(
    [
        "Visão geral",
        "Análise semanal",
        "Problemas",
        "Lojas e responsáveis",
        "Detalhamento",
    ]
)

with aba1:
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(grafico_status(df_filtrado), use_container_width=True)
    with col2:
        st.plotly_chart(grafico_sla(df_filtrado), use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(grafico_top_problemas(df_filtrado), use_container_width=True)
    with col4:
        st.plotly_chart(grafico_top_lojas(df_filtrado), use_container_width=True)

with aba2:
    st.plotly_chart(
        grafico_evolucao_semanal(df_filtrado),
        use_container_width=True,
    )

    semana_atual = df_filtrado["InicioSemana"].max()
    semana_anterior = semana_atual - __import__("pandas").Timedelta(days=7)

    atual = df_filtrado.loc[
        df_filtrado["InicioSemana"] == semana_atual,
        "N° Chamado",
    ].nunique()

    anterior = df_filtrado.loc[
        df_filtrado["InicioSemana"] == semana_anterior,
        "N° Chamado",
    ].nunique()

    variacao = ((atual - anterior) / anterior * 100) if anterior else 0

    a1, a2, a3 = st.columns(3)
    a1.metric("Semana mais recente", atual)
    a2.metric("Semana anterior", anterior)
    a3.metric("Variação semanal", f"{variacao:.1f}%")

with aba3:
    st.plotly_chart(
        grafico_top_problemas(df_filtrado, top_n=15),
        use_container_width=True,
    )

    resumo_problemas = (
        df_filtrado.groupby(["Problema", "Produto"], dropna=False)
        .agg(
            Quantidade=("N° Chamado", "nunique"),
            Pendentes=("Status_Normalizado", lambda s: (~s.isin(["encerrado", "fechado", "concluído", "concluido", "resolvido", "finalizado"])).sum()),
            Tempo_Medio_Horas=("Tempo_Resolucao_Horas", "mean"),
        )
        .reset_index()
        .sort_values("Quantidade", ascending=False)
    )

    st.dataframe(
        resumo_problemas,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Quantidade": st.column_config.NumberColumn(format="%d"),
            "Pendentes": st.column_config.NumberColumn(format="%d"),
            "Tempo_Medio_Horas": st.column_config.NumberColumn(format="%.1f"),
        },
    )

with aba4:
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(grafico_top_lojas(df_filtrado, top_n=20), use_container_width=True)
    with col2:
        st.plotly_chart(grafico_responsaveis(df_filtrado), use_container_width=True)

    resumo_lojas = (
        df_filtrado.groupby("Localizacao", dropna=False)
        .agg(
            Quantidade=("N° Chamado", "nunique"),
            Problemas_Distintos=("Problema", "nunique"),
            Tempo_Medio_Horas=("Tempo_Resolucao_Horas", "mean"),
        )
        .reset_index()
        .sort_values("Quantidade", ascending=False)
    )

    st.dataframe(
        resumo_lojas,
        use_container_width=True,
        hide_index=True,
    )

with aba5:
    colunas_exibicao = [
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

    colunas_exibicao = [c for c in colunas_exibicao if c in df_filtrado.columns]

    st.dataframe(
        df_filtrado[colunas_exibicao],
        use_container_width=True,
        hide_index=True,
    )

    excel = gerar_excel_relatorio(df_filtrado)

    st.download_button(
        "Baixar relatório filtrado em Excel",
        data=excel,
        file_name="relatorio_chamados_filtrado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
