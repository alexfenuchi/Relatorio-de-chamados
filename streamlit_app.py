import pandas as pd
import plotly.express as px
import streamlit as st

from src.database import buscar_chamados, atualizar_chamados
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
    grafico_top_titulos,
    grafico_descricoes_problemas,
    grafico_aging_backlog,
    grafico_sla_semanal,
    grafico_aberturas_dia_semana,
    grafico_tempo_medio_problema,
    grafico_prioridades,
)
from src.exportacao import gerar_excel_relatorio


def grafico_sla_por_nivel(df):
    dados = (
        df[df["SLA_Medido_Status"].isin(["Dentro do SLA", "Fora do SLA"])]
        .groupby(["nivelsla", "SLA_Medido_Status"], dropna=False)["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
    )

    if dados.empty:
        return px.bar(title="Medição de SLA por nível sem dados classificados")

    figura = px.bar(
        dados,
        x="nivelsla",
        y="Quantidade",
        color="SLA_Medido_Status",
        text="Quantidade",
        barmode="group",
        title="Medição de SLA por nível",
        color_discrete_map={
            "Dentro do SLA": "#2ca02c",
            "Fora do SLA": "#d62728",
        },
    )

    figura.update_layout(
        xaxis_title="Nível SLA",
        yaxis_title="Chamados",
        legend_title="Status medido",
    )

    return figura


def grafico_percentual_sla_por_nivel(df):
    dados = df[
        df["SLA_Medido_Status"].isin(["Dentro do SLA", "Fora do SLA"])
    ].copy()

    if dados.empty:
        return px.bar(title="Percentual de SLA por nível sem dados classificados")

    resumo = (
        dados.groupby("nivelsla", dropna=False)
        .agg(
            Total=("N° Chamado", "nunique"),
            Dentro=(
                "SLA_Medido_Status",
                lambda valores: (valores == "Dentro do SLA").sum(),
            ),
        )
        .reset_index()
    )
    resumo["Percentual_Dentro"] = resumo["Dentro"] / resumo["Total"] * 100
    resumo = resumo.sort_values("Percentual_Dentro")

    figura = px.bar(
        resumo,
        x="Percentual_Dentro",
        y="nivelsla",
        orientation="h",
        text="Percentual_Dentro",
        title="Percentual dentro do SLA por nível",
        custom_data=["Total"],
    )

    figura.update_traces(
        texttemplate="%{text:.1f}%",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Dentro do SLA: %{x:.1f}%<br>"
            "Chamados: %{customdata[0]}"
            "<extra></extra>"
        ),
    )
    figura.update_layout(
        xaxis_title="Dentro do SLA (%)",
        yaxis_title="",
    )
    figura.update_xaxes(range=[0, 100])

    return figura


st.set_page_config(
    page_title="Relatório de Chamados N2",
    page_icon="📊",
    layout="wide",
)

pagina = st.sidebar.radio(
    "Navegação",
    ["Dashboard", "Atualizar base"],
)

if pagina == "Atualizar base":
    st.title("Atualizar base de chamados")
    st.caption(
        "Envie a base anual em Excel para inserir ou atualizar "
        "os chamados no Supabase."
    )

    senha = st.text_input(
        "Senha de administrador",
        type="password",
    )

    if not senha:
        st.info("Informe a senha de administrador.")
        st.stop()

    if senha != st.secrets["ADMIN_PASSWORD"]:
        st.error("Senha de administrador inválida.")
        st.stop()

    arquivo = st.file_uploader(
        "Selecione a base anual de chamados",
        type=["xlsx", "xls"],
        key="upload_atualizacao",
    )

    if arquivo is None:
        st.info("Selecione o arquivo Excel para continuar.")
        st.stop()

    try:
        bruto, aba = carregar_excel(arquivo)
        tratado = preparar_base(bruto)
    except Exception as erro:
        st.error(f"Não foi possível processar o arquivo: {erro}")
        st.stop()

    st.success(
        f"Arquivo processado: {len(tratado):,} registros | "
        f"Aba: {aba}".replace(",", ".")
    )

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Registros",
        f"{len(tratado):,}".replace(",", "."),
    )
    col2.metric(
        "Chamados únicos",
        f"{tratado['N° Chamado'].nunique():,}".replace(",", "."),
    )
    col3.metric(
        "Lojas",
        f"{tratado['Localizacao'].nunique():,}".replace(",", "."),
    )

    with st.expander("Visualizar amostra da base"):
        st.dataframe(
            tratado.head(100),
            width="stretch",
            hide_index=True,
        )

    if st.button(
        "Atualizar base no Supabase",
        type="primary",
        width="stretch",
    ):
        try:
            with st.spinner("Atualizando base no Supabase..."):
                quantidade = atualizar_chamados(tratado)

            st.cache_data.clear()

            st.success(
                f"{quantidade:,} chamados foram atualizados com sucesso."
                .replace(",", ".")
            )
        except Exception as erro:
            st.error(f"Erro ao atualizar o Supabase: {erro}")

    st.stop()


st.title("📊 Relatório de Chamados — Suporte N2")
st.caption(
    "Tempos calculados em horas úteis, considerando "
    "segunda a sexta-feira e 1 dia de trabalho = 8 horas."
)


@st.cache_data(ttl=300)
def carregar_dados_supabase():
    return buscar_chamados()


try:
    with st.spinner("Buscando chamados no Supabase..."):
        df_banco = carregar_dados_supabase()
except Exception as erro:
    st.error(f"Não foi possível consultar o Supabase: {erro}")
    st.stop()


if df_banco.empty:
    st.warning(
        "Nenhum registro foi encontrado no Supabase. "
        "Acesse 'Atualizar base' e envie o arquivo anual."
    )
    st.stop()


df_banco = df_banco.rename(
    columns={
        "numero_chamado": "N° Chamado",
        "titulo": "Título",
        "prioridade": "prioridade",
        "tipo_chamado": "Tipo do Chamado",
        "tipo_localizacao": "TipoLocalizacao",
        "localizacao": "Localizacao",
        "abertura": "Abertura",
        "situacao": "Situacao",
        "status_sla": "StatusSLA",
        "equipe_responsavel": "Equipe Responsavel",
        "responsavel": "Responsavel",
        "categoria": "Categoria",
        "produto": "Produto",
        "problema": "Problema",
        "encerramento": "Encerramento",
        "descricao": "descricao",
        "solucao": "solucao",
        "codigo_solucao": "Código de solução",
        "nivelsla": "nivelsla",
    }
)


try:
    df = preparar_base(df_banco)
except Exception as erro:
    st.error(f"Erro ao preparar os dados do Supabase: {erro}")
    st.stop()


st.success(
    f"Base consultada: {len(df):,} chamados".replace(",", ".")
)

if st.sidebar.button(
    "Atualizar dados agora",
    width="stretch",
):
    st.cache_data.clear()
    st.rerun()


filtros = renderizar_filtros(df)
df_filtrado = aplicar_filtros(df, filtros)

if df_filtrado.empty:
    st.warning(
        "Nenhum chamado encontrado para os filtros selecionados."
    )
    st.stop()


kpis = calcular_kpis(df_filtrado)


c1, c2, c3, c4 = st.columns(4)
c1.metric(
    "Total de chamados",
    f"{kpis['total']:,}".replace(",", "."),
)
c2.metric(
    "Encerrados",
    f"{kpis['encerrados']:,}".replace(",", "."),
)
c3.metric(
    "Pendentes",
    f"{kpis['pendentes']:,}".replace(",", "."),
)
c4.metric(
    "SLA medido no prazo",
    f"{kpis['sla_medido_percentual']:.1f}%",
    help=(
        "Indicador recalculado pelo dashboard com base no nível SLA, "
        "tempo útil de resolução dos encerrados e aging dos pendentes."
    ),
)

st.caption(
    "SLA principal recalculado pelo dashboard. A aba 'SLA e backlog' "
    "também mantém a visão do StatusSLA recebido da base de origem."
)

c5, c6, c7, c8 = st.columns(4)
c5.metric(
    "Tempo médio",
    f"{kpis['tempo_medio_horas']:.1f} h",
    help="1 dia útil equivale a 8 horas.",
)
c6.metric(
    "Tempo mediano",
    f"{kpis['tempo_mediano_horas']:.1f} h",
)
c7.metric(
    "Aging médio",
    f"{kpis['aging_medio_dias']:.1f} dias",
    help="Idade média dos chamados ainda pendentes.",
)
c8.metric(
    "Maior aging",
    f"{kpis['aging_maximo_dias']:.1f} dias",
    help="Chamado pendente mais antigo, em dias de 8 horas.",
)

d1, d2, d3, d4 = st.columns(4)
d1.metric(
    "Abertos hoje",
    f"{kpis['abertos_hoje']:,}".replace(",", "."),
)
d2.metric(
    "Encerrados hoje",
    f"{kpis['encerrados_hoje']:,}".replace(",", "."),
)
d3.metric(
    "Fora do SLA medido",
    f"{kpis['fora_sla_medido']:,}".replace(",", "."),
)
d4.metric(
    "Próximos de vencer",
    f"{kpis['proximos_vencer']:,}".replace(",", "."),
    help="Pendentes dentro da meta, mas com até 2 horas úteis restantes.",
)


aba1, aba2, aba3, aba4, aba5, aba6, aba7 = st.tabs(
    [
        "Visão geral",
        "Análise semanal",
        "Problemas",
        "Lojas e responsáveis",
        "SLA e backlog",
        "Medição SLA",
        "Detalhamento",
    ]
)


with aba1:
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(
            grafico_status(df_filtrado),
            width="stretch",
            key="grafico_visao_status",
        )

    with col2:
        st.plotly_chart(
            grafico_sla(df_filtrado),
            width="stretch",
            key="grafico_visao_sla",
        )

    col3, col4 = st.columns(2)

    with col3:
        st.plotly_chart(
            grafico_top_problemas(df_filtrado),
            width="stretch",
            key="grafico_visao_top_problemas",
        )

    with col4:
        st.plotly_chart(
            grafico_top_lojas(df_filtrado),
            width="stretch",
            key="grafico_visao_top_lojas",
        )

    col5, col6 = st.columns(2)

    with col5:
        st.plotly_chart(
            grafico_prioridades(df_filtrado),
            width="stretch",
            key="grafico_visao_prioridades",
        )

    with col6:
        st.plotly_chart(
            grafico_aberturas_dia_semana(df_filtrado),
            width="stretch",
            key="grafico_visao_dia_semana",
        )


with aba2:
    st.plotly_chart(
        grafico_evolucao_semanal(df_filtrado),
        width="stretch",
        key="grafico_analise_evolucao_semanal",
    )

    semanas_validas = (
        df_filtrado["InicioSemana"]
        .dropna()
        .sort_values()
        .unique()
    )

    if len(semanas_validas) > 0:
        semana_atual = pd.Timestamp(semanas_validas[-1])
        semana_anterior = semana_atual - pd.Timedelta(days=7)

        atual = df_filtrado.loc[
            df_filtrado["InicioSemana"] == semana_atual,
            "N° Chamado",
        ].nunique()

        anterior = df_filtrado.loc[
            df_filtrado["InicioSemana"] == semana_anterior,
            "N° Chamado",
        ].nunique()

        variacao = (
            ((atual - anterior) / anterior * 100)
            if anterior > 0
            else 0
        )

        a1, a2, a3 = st.columns(3)
        a1.metric("Semana mais recente", atual)
        a2.metric("Semana anterior", anterior)
        a3.metric(
            "Variação semanal",
            f"{variacao:.1f}%",
            delta=f"{variacao:.1f}%",
        )

        st.caption(
            "Semana mais recente iniciada em "
            f"{semana_atual.strftime('%d/%m/%Y')}."
        )
    else:
        st.info(
            "Não existem datas válidas para realizar "
            "a análise semanal."
        )

    st.plotly_chart(
        grafico_sla_semanal(df_filtrado),
        width="stretch",
        key="grafico_analise_sla_semanal",
    )


with aba3:
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(
            grafico_top_problemas(
                df_filtrado,
                top_n=15,
            ),
            width="stretch",
            key="grafico_problemas_top15",
        )

    with col2:
        st.plotly_chart(
            grafico_tempo_medio_problema(
                df_filtrado,
                top_n=10,
            ),
            width="stretch",
            key="grafico_problemas_tempo_medio",
        )

    resumo_problemas = (
        df_filtrado.groupby(
            ["Problema", "Produto"],
            dropna=False,
        )
        .agg(
            Quantidade=("N° Chamado", "nunique"),
            Pendentes=(
                "Encerrado_Flag",
                lambda valores: (~valores).sum(),
            ),
            Tempo_Medio_Horas=(
                "Tempo_Resolucao_Horas",
                "mean",
            ),
            Tempo_Medio_Dias=(
                "Tempo_Resolucao_Dias",
                "mean",
            ),
        )
        .reset_index()
        .sort_values(
            "Quantidade",
            ascending=False,
        )
    )

    st.dataframe(
        resumo_problemas,
        width="stretch",
        hide_index=True,
        column_config={
            "Tempo_Medio_Horas": st.column_config.NumberColumn(
                "Tempo médio (h)",
                format="%.1f",
            ),
            "Tempo_Medio_Dias": st.column_config.NumberColumn(
                "Tempo médio (dias de 8h)",
                format="%.1f",
            ),
        },
    )


with aba4:
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(
            grafico_top_lojas(
                df_filtrado,
                top_n=20,
            ),
            width="stretch",
            key="grafico_lojas_top20",
        )

    with col2:
        st.plotly_chart(
            grafico_responsaveis(df_filtrado),
            width="stretch",
            key="grafico_responsaveis",
        )

    resumo_lojas = (
        df_filtrado.groupby(
            "Localizacao",
            dropna=False,
        )
        .agg(
            Quantidade=("N° Chamado", "nunique"),
            Pendentes=(
                "Encerrado_Flag",
                lambda valores: (~valores).sum(),
            ),
            Problemas_Distintos=("Problema", "nunique"),
            Tempo_Medio_Horas=(
                "Tempo_Resolucao_Horas",
                "mean",
            ),
        )
        .reset_index()
        .sort_values(
            "Quantidade",
            ascending=False,
        )
    )

    st.dataframe(
        resumo_lojas,
        width="stretch",
        hide_index=True,
    )


with aba5:
    b1, b2, b3, b4 = st.columns(4)

    b1.metric(
        "Dentro do SLA",
        f"{kpis['dentro_sla']:,}".replace(",", "."),
    )
    b2.metric(
        "Fora do SLA",
        f"{kpis['fora_sla']:,}".replace(",", "."),
    )
    b3.metric(
        "Backlog",
        f"{kpis['pendentes']:,}".replace(",", "."),
    )
    b4.metric(
        "Aging máximo",
        f"{kpis['aging_maximo_horas']:.1f} h",
    )

    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(
            grafico_aging_backlog(df_filtrado),
            width="stretch",
            key="grafico_backlog_aging",
        )

    with col2:
        st.plotly_chart(
            grafico_sla_semanal(df_filtrado),
            width="stretch",
            key="grafico_backlog_sla_semanal",
        )

    backlog = (
        df_filtrado.loc[
            ~df_filtrado["Encerrado_Flag"]
        ]
        .sort_values(
            "Idade_Pendente_Horas",
            ascending=False,
        )
    )

    st.subheader("Fila de prioridade operacional")
    st.caption(
        "Ordenação sugerida para o dia a dia: primeiro chamados fora do SLA "
        "medido, depois maior aging, prioridade e nível SLA."
    )

    prioridade_ordem = {
        "P1": 1,
        "1": 1,
        "P2": 2,
        "2": 2,
        "P3": 3,
        "3": 3,
        "P4": 4,
        "4": 4,
        "P5": 5,
        "5": 5,
    }
    backlog_priorizado = backlog.copy()
    backlog_priorizado["Prioridade_Ordenacao"] = (
        backlog_priorizado["prioridade"]
        .fillna("")
        .astype(str)
        .str.upper()
        .str.extract(r"(P?[1-5])", expand=False)
        .map(prioridade_ordem)
        .fillna(99)
    )
    backlog_priorizado["Fora_SLA_Ordenacao"] = (
        backlog_priorizado["SLA_Medido_Status"]
        .eq("Fora do SLA")
        .astype(int)
    )
    backlog_priorizado = backlog_priorizado.sort_values(
        [
            "Fora_SLA_Ordenacao",
            "Idade_Pendente_Horas",
            "Prioridade_Ordenacao",
            "nivelsla",
        ],
        ascending=[False, False, True, True],
    )

    colunas_backlog = [
        "N° Chamado",
        "Localizacao",
        "Abertura",
        "Problema",
        "Responsavel",
        "StatusSLA",
        "Idade_Pendente_Horas",
        "Idade_Pendente_Dias",
        "Faixa_Aging",
    ]

    st.dataframe(
        backlog_priorizado[
            [
                coluna
                for coluna in colunas_backlog
                if coluna in backlog_priorizado.columns
            ]
        ].head(100),
        width="stretch",
        hide_index=True,
        column_config={
            "Idade_Pendente_Horas": st.column_config.NumberColumn(
                "Aging (h)",
                format="%.1f",
            ),
            "Idade_Pendente_Dias": st.column_config.NumberColumn(
                "Aging (dias de 8h)",
                format="%.1f",
            ),
        },
    )


with aba6:
    st.subheader("Medição de SLA por nível")
    st.caption(
        "A medição usa a coluna nivelsla e compara a meta cadastrada "
        "com o tempo útil de resolução dos encerrados ou o aging dos pendentes."
    )

    sla_classificados = df_filtrado[
        df_filtrado["SLA_Medido_Status"].isin([
            "Dentro do SLA",
            "Fora do SLA",
        ])
    ]
    total_medido = sla_classificados["N° Chamado"].nunique()
    dentro_medido = sla_classificados.loc[
        sla_classificados["SLA_Medido_Status"] == "Dentro do SLA",
        "N° Chamado",
    ].nunique()
    fora_medido = sla_classificados.loc[
        sla_classificados["SLA_Medido_Status"] == "Fora do SLA",
        "N° Chamado",
    ].nunique()
    percentual_medido = (
        dentro_medido / total_medido * 100
        if total_medido
        else 0
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Chamados medidos", f"{total_medido:,}".replace(",", "."))
    m2.metric("Dentro do SLA", f"{dentro_medido:,}".replace(",", "."))
    m3.metric("Fora do SLA", f"{fora_medido:,}".replace(",", "."))
    m4.metric("Aderência", f"{percentual_medido:.1f}%")

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            grafico_sla_por_nivel(df_filtrado),
            width="stretch",
            key="grafico_medicao_sla_nivel",
        )
    with col2:
        st.plotly_chart(
            grafico_percentual_sla_por_nivel(df_filtrado),
            width="stretch",
            key="grafico_percentual_sla_nivel",
        )

    resumo_sla = (
        df_filtrado.groupby("nivelsla", dropna=False)
        .agg(
            Meta_Horas=("SLA_Meta_Horas", "first"),
            Quantidade=("N° Chamado", "nunique"),
            Dentro_SLA=(
                "SLA_Medido_Status",
                lambda valores: (valores == "Dentro do SLA").sum(),
            ),
            Fora_SLA=(
                "SLA_Medido_Status",
                lambda valores: (valores == "Fora do SLA").sum(),
            ),
            Tempo_Medio_Medido_Horas=("SLA_Tempo_Medido_Horas", "mean"),
            Excedido_Medio_Horas=("SLA_Excedido_Horas", "mean"),
        )
        .reset_index()
        .sort_values("nivelsla", na_position="last")
    )
    resumo_sla["Aderencia_Percentual"] = (
        resumo_sla["Dentro_SLA"]
        / (resumo_sla["Dentro_SLA"] + resumo_sla["Fora_SLA"]).replace(0, pd.NA)
        * 100
    ).fillna(0)

    st.dataframe(
        resumo_sla,
        width="stretch",
        hide_index=True,
        column_config={
            "Meta_Horas": st.column_config.NumberColumn("Meta (h)", format="%.1f"),
            "Tempo_Medio_Medido_Horas": st.column_config.NumberColumn("Tempo médio medido (h)", format="%.1f"),
            "Excedido_Medio_Horas": st.column_config.NumberColumn("Excedido médio (h)", format="%.1f"),
            "Aderencia_Percentual": st.column_config.NumberColumn("Aderência (%)", format="%.1f"),
        },
    )


with aba7:
    st.subheader(
        "Análise dos títulos e descrições dos chamados"
    )

    col_titulos, col_descricoes = st.columns(2)

    with col_titulos:
        quantidade_titulos = st.selectbox(
            "Quantidade de títulos no gráfico",
            options=[5, 10, 15, 20],
            index=1,
            key="quantidade_titulos",
        )

        st.plotly_chart(
            grafico_top_titulos(
                df_filtrado,
                top_n=quantidade_titulos,
            ),
            width="stretch",
            key="grafico_detalhamento_titulos",
        )

    with col_descricoes:
        quantidade_descricoes = st.selectbox(
            "Quantidade de descrições no gráfico",
            options=[5, 10, 15, 20],
            index=1,
            key="quantidade_descricoes",
        )

        st.plotly_chart(
            grafico_descricoes_problemas(
                df_filtrado,
                top_n=quantidade_descricoes,
            ),
            width="stretch",
            key="grafico_detalhamento_descricoes",
        )

    st.divider()
    st.subheader("Detalhamento dos chamados")

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
        "nivelsla",
        "SLA_Meta_Horas",
        "SLA_Tempo_Medido_Horas",
        "SLA_Medido_Status",
        "SLA_Excedido_Horas",
        "Equipe Responsavel",
        "Responsavel",
        "Categoria",
        "Produto",
        "Problema",
        "Encerramento",
        "Tempo_Resolucao_Horas",
        "Tempo_Resolucao_Dias",
        "Idade_Pendente_Horas",
        "Idade_Pendente_Dias",
        "Faixa_Aging",
        "descricao",
        "solucao",
        "Código de solução",
    ]

    colunas_exibicao = [
        coluna
        for coluna in colunas_exibicao
        if coluna in df_filtrado.columns
    ]

    st.dataframe(
        df_filtrado[colunas_exibicao],
        width="stretch",
        hide_index=True,
        column_config={
            "SLA_Meta_Horas": st.column_config.NumberColumn(
                "Meta SLA (h)",
                format="%.1f",
            ),
            "SLA_Tempo_Medido_Horas": st.column_config.NumberColumn(
                "Tempo medido SLA (h)",
                format="%.1f",
            ),
            "SLA_Excedido_Horas": st.column_config.NumberColumn(
                "SLA excedido (h)",
                format="%.1f",
            ),
            "Tempo_Resolucao_Horas": st.column_config.NumberColumn(
                "Resolução (h úteis)",
                format="%.1f",
            ),
            "Tempo_Resolucao_Dias": st.column_config.NumberColumn(
                "Resolução (dias de 8h)",
                format="%.1f",
            ),
            "Idade_Pendente_Horas": st.column_config.NumberColumn(
                "Aging (h úteis)",
                format="%.1f",
            ),
            "Idade_Pendente_Dias": st.column_config.NumberColumn(
                "Aging (dias de 8h)",
                format="%.1f",
            ),
        },
    )

    if st.button(
        "Preparar relatório Excel",
        key="preparar_relatorio_excel",
    ):
        try:
            with st.spinner(
                "Gerando relatório Excel..."
            ):
                excel = gerar_excel_relatorio(
                    df_filtrado
                )

            st.download_button(
                "Baixar relatório filtrado em Excel",
                data=excel,
                file_name=(
                    "relatorio_chamados_filtrado.xlsx"
                ),
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                key="download_relatorio_excel",
            )
        except Exception as erro:
            st.error(
                "Não foi possível gerar o relatório Excel: "
                f"{erro}"
            )
