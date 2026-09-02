import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.database import buscar_chamados, atualizar_chamados
from src.leitura import carregar_excel
from src.tratamento import SLA_NIVEIS_HORAS, preparar_base
from src.filtros import aplicar_filtros, renderizar_filtros
from src.metricas import (
    METAS_EXECUTIVAS,
    calcular_fluxo_periodo,
    calcular_kpis,
    calcular_periodo_anterior,
    calcular_variacao,
)
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
    aplicar_cor_base,
    COR_GRAFICO_PRINCIPAL,
)
from src.exportacao import gerar_excel_relatorio
from src.insights import (
    calcular_saude_dados,
    criar_painel_metas,
    gerar_insights_executivos,
)


def _formatar_delta(valor, sufixo="%"):
    if valor is None:
        return None
    return f"{valor:+.1f}{sufixo} vs. período anterior"


def _renderizar_resumo_executivo(df, kpis, fluxo, comparativo):
    """Apresenta os sinais que exigem decisão antes das análises detalhadas."""
    st.markdown(
        "<div class='section-kicker'>CENTRAL DE DECISÃO</div>",
        unsafe_allow_html=True,
    )
    st.markdown("## O que precisa de atenção agora")
    st.caption(
        "Leitura automática do recorte selecionado; use-a para orientar "
        "a reunião operacional."
    )

    st.markdown("### Resultado × meta")
    placar = criar_painel_metas(kpis, fluxo, METAS_EXECUTIVAS)
    st.dataframe(
        placar,
        width="stretch",
        hide_index=True,
        column_config={
            "Realizado": st.column_config.NumberColumn(format="%.1f"),
            "Meta": st.column_config.NumberColumn(format="%.1f"),
            "Desvio": st.column_config.NumberColumn(format="%+.1f"),
        },
    )

    f1, f2, f3, f4 = st.columns(4)
    f1.metric(
        "Demanda recebida",
        f"{fluxo['abertos']:,}".replace(",", "."),
        delta=_formatar_delta(comparativo["abertos"]),
        help="Chamados abertos dentro do período selecionado.",
    )
    f2.metric(
        "Capacidade entregue",
        f"{fluxo['encerrados']:,}".replace(",", "."),
        delta=_formatar_delta(comparativo["encerrados"]),
        help=(
            "Chamados encerrados dentro do período, inclusive os "
            "abertos anteriormente."
        ),
    )
    f3.metric(
        "Taxa de absorção",
        f"{fluxo['taxa_absorcao']:.1f}%",
        delta=_formatar_delta(comparativo["taxa_absorcao"]),
        help=(
            "Encerrados no período divididos pelos abertos no período. "
            "Meta: 100%."
        ),
    )
    f4.metric(
        "Saldo operacional",
        f"{fluxo['saldo']:+,}".replace(",", "."),
        help="Encerrados menos abertos. Resultado negativo indica pressão de backlog.",
    )

    insights = gerar_insights_executivos(df, kpis)
    colunas = st.columns(len(insights))
    icones = {
        "crítico": "↗",
        "atenção": "!",
        "positivo": "✓",
        "informativo": "→",
    }
    for coluna, insight in zip(colunas, insights):
        with coluna:
            st.markdown(
                f"""
                <div class="insight-card insight-{insight['nivel']}">
                    <span class="insight-icon">{icones[insight['nivel']]}</span>
                    <strong>{insight['titulo']}</strong>
                    <p>{insight['texto']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with st.expander("Qualidade e cobertura dos dados"):
        st.caption(
            "Campos críticos incompletos reduzem a confiabilidade dos "
            "relatórios e da priorização."
        )
        qualidade = calcular_saude_dados(df)
        st.dataframe(
            qualidade,
            width="stretch",
            hide_index=True,
            column_config={
                "Cobertura_Percentual": st.column_config.ProgressColumn(
                    "Cobertura", min_value=0, max_value=100, format="%.1f%%"
                )
            },
        )


def _formatar_periodo_filtrado(df):
    datas = df["Abertura"].dropna()
    if datas.empty:
        return "período filtrado"

    inicio = datas.min().strftime("%d/%m/%Y")
    fim = datas.max().strftime("%d/%m/%Y")
    if inicio == fim:
        return inicio
    return f"{inicio} a {fim}"


def _rotulo_mes_periodo(periodo):
    meses = {
        1: "jan",
        2: "fev",
        3: "mar",
        4: "abr",
        5: "mai",
        6: "jun",
        7: "jul",
        8: "ago",
        9: "set",
        10: "out",
        11: "nov",
        12: "dez",
    }
    return f"{meses[periodo.month]}-{str(periodo.year)[-2:]}"


def _tipo_operacional(df):
    tipo = df.get("Tipo do Chamado", pd.Series(index=df.index, dtype="object"))
    tipo_normalizado = tipo.fillna("").astype(str).str.lower()
    return tipo_normalizado.str.contains("requi", regex=False).map(
        {True: "Requisição", False: "Incidente"}
    )


def _calcular_resumo_mensal_recorte(df_recorte):
    dados = df_recorte.dropna(subset=["Abertura"]).copy()
    if dados.empty:
        return pd.DataFrame()

    dados["Mes_Periodo"] = dados["Abertura"].dt.to_period("M")
    dados["Mes_Label"] = dados["Mes_Periodo"].apply(_rotulo_mes_periodo)
    dados["Tipo_Operacional"] = _tipo_operacional(dados)

    mensal = (
        dados.groupby(["Mes_Periodo", "Mes_Label", "Tipo_Operacional"])["N° Chamado"]
        .nunique()
        .unstack(fill_value=0)
        .reset_index()
        .sort_values("Mes_Periodo")
    )

    for coluna in ["Incidente", "Requisição"]:
        if coluna not in mensal.columns:
            mensal[coluna] = 0

    sla_mensal = (
        dados[
            dados["SLA_Normalizado"].isin(
                [
                    "em dia",
                    "dentro",
                    "dentro do prazo",
                    "em atraso",
                    "fora",
                    "fora do prazo",
                ]
            )
        ]
        .assign(
            Dentro_SLA=lambda frame: frame["SLA_Normalizado"].isin(
                ["em dia", "dentro", "dentro do prazo"]
            )
        )
        .groupby("Mes_Periodo")
        .agg(
            Chamados_SLA=("N° Chamado", "nunique"),
            Dentro_SLA=("Dentro_SLA", "sum"),
        )
        .reset_index()
    )

    mensal = mensal.merge(sla_mensal, on="Mes_Periodo", how="left")
    mensal["Total"] = mensal["Incidente"] + mensal["Requisição"]
    mensal["SLA_Percentual"] = (
        mensal["Dentro_SLA"] / mensal["Chamados_SLA"].replace(0, pd.NA) * 100
    ).fillna(0)

    return mensal


def _grafico_evolutivo_chamados_recorte(df_recorte, nome_recorte):
    mensal = _calcular_resumo_mensal_recorte(df_recorte)
    if mensal.empty:
        return aplicar_cor_base(px.bar(title="Evolutivo de chamados sem dados"))

    figura = go.Figure()
    figura.add_bar(
        x=mensal["Mes_Label"],
        y=mensal["Incidente"],
        name="Incidente",
        marker_color="#6f6764",
        text=mensal["Incidente"],
        texttemplate="%{text:.0f}",
        textposition="inside",
    )
    figura.add_bar(
        x=mensal["Mes_Label"],
        y=mensal["Requisição"],
        name="Requisição",
        marker_color=COR_GRAFICO_PRINCIPAL,
        text=mensal["Requisição"],
        texttemplate="%{text:.0f}",
        textposition="inside",
    )
    figura.add_scatter(
        x=mensal["Mes_Label"],
        y=mensal["Total"],
        name="Total",
        mode="lines+markers+text",
        line={"color": "#3d3634", "width": 2},
        marker={"color": "white", "line": {"color": "#3d3634", "width": 1.5}},
        text=mensal["Total"],
        textposition="top center",
        yaxis="y",
    )
    figura.add_scatter(
        x=mensal["Mes_Label"],
        y=mensal["SLA_Percentual"],
        name="SLA (%)",
        mode="lines+markers+text",
        line={"color": "#111111", "width": 2},
        marker={"color": "#111111"},
        text=mensal["SLA_Percentual"].round(0).astype(int).astype(str) + "%",
        textposition="bottom center",
        yaxis="y2",
    )

    figura.update_layout(
        title=f"EVOLUTIVO DE CHAMADOS - {nome_recorte.upper()}",
        barmode="stack",
        height=360,
        margin={"l": 25, "r": 30, "t": 55, "b": 25},
        legend={"orientation": "h", "y": 1.15, "x": 0.2},
        plot_bgcolor="white",
        paper_bgcolor="white",
        yaxis={"title": "", "rangemode": "tozero", "gridcolor": "#eeeeee"},
        yaxis2={
            "title": "",
            "overlaying": "y",
            "side": "right",
            "range": [0, 100],
            "ticksuffix": "%",
            "showgrid": False,
        },
    )
    figura.update_xaxes(tickangle=-45)
    return figura


def _calcular_tabela_falhas_periodo(df_recorte, top_n=20):
    dados = df_recorte.dropna(subset=["Abertura"]).copy()
    if dados.empty:
        return pd.DataFrame()

    dados["Mes_Label"] = dados["Abertura"].dt.to_period("M").apply(_rotulo_mes_periodo)
    ordem_meses = (
        dados[["Abertura", "Mes_Label"]]
        .assign(Mes_Periodo=lambda frame: frame["Abertura"].dt.to_period("M"))
        .sort_values("Mes_Periodo")["Mes_Label"]
        .drop_duplicates()
        .tolist()
    )

    tabela = pd.pivot_table(
        dados,
        index="Problema",
        columns="Mes_Label",
        values="N° Chamado",
        aggfunc="nunique",
        fill_value=0,
    )
    tabela = tabela.reindex(columns=ordem_meses, fill_value=0)
    tabela["Total"] = tabela.sum(axis=1)
    total_geral = tabela["Total"].sum()
    tabela["%"] = (tabela["Total"] / total_geral * 100).fillna(0).round(1)
    tabela = tabela.sort_values("Total", ascending=False).head(top_n).reset_index()
    return tabela.rename(columns={"Problema": f"TOP {top_n} Categorias"})


def _renderizar_cards_recorte(
    kpis_recorte, percentual_top10, percentual_incidentes, percentual_requisicoes
):
    st.markdown(
        f"""
        <div class="recorte-kpi-grid">
            <div class="recorte-kpi-card">
                <div class="recorte-kpi-value">{kpis_recorte['total']:,}</div>
                <div class="recorte-kpi-label">Chamados abertos no período</div>
            </div>
            <div class="recorte-kpi-card">
                <div class="recorte-kpi-value">{percentual_top10:.0f}%</div>
                <div class="recorte-kpi-label">Chamados concentrados nas 10 principais categorias</div>
            </div>
            <div class="recorte-kpi-card recorte-kpi-split">
                <div>
                    <div class="recorte-kpi-value">{percentual_incidentes:.0f}%</div>
                    <div class="recorte-kpi-label">Incidentes no período</div>
                </div>
                <div>
                    <div class="recorte-kpi-value">{percentual_requisicoes:.0f}%</div>
                    <div class="recorte-kpi-label">Requisições no período</div>
                </div>
            </div>
            <div class="recorte-kpi-card recorte-kpi-split">
                <div>
                    <div class="recorte-kpi-value">{kpis_recorte['sla_percentual']:.0f}%</div>
                    <div class="recorte-kpi-label">Cumprimento do SLA</div>
                </div>
                <div>
                    <div class="recorte-kpi-value">{kpis_recorte['tempo_medio_horas']:.1f}</div>
                    <div class="recorte-kpi-label">MTTR Médio</div>
                </div>
            </div>
        </div>
        """.replace(",", "."),
        unsafe_allow_html=True,
    )


def _renderizar_recorte_operacao(df_recorte, nome_recorte):
    if df_recorte.empty:
        st.info(f"Nenhum chamado de {nome_recorte} no período selecionado.")
        return

    periodo = _formatar_periodo_filtrado(df_recorte)
    kpis_recorte = calcular_kpis(df_recorte)
    tipos = _tipo_operacional(df_recorte)
    total_chamados = max(kpis_recorte["total"], 1)
    percentual_incidentes = (tipos.eq("Incidente").sum() / total_chamados) * 100
    percentual_requisicoes = (tipos.eq("Requisição").sum() / total_chamados) * 100

    resumo_problemas = (
        df_recorte.groupby("Problema", dropna=False)["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
    )
    percentual_top10 = (
        resumo_problemas.head(10)["Quantidade"].sum()
        / resumo_problemas["Quantidade"].sum()
        * 100
    )

    st.markdown(
        f"<span class='recorte-eyebrow'>• Indicadores {nome_recorte}</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<h2 class='recorte-title'>Saúde da Operação – {nome_recorte}</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='recorte-periodo'>Período filtrado: {periodo}</div>",
        unsafe_allow_html=True,
    )

    _renderizar_cards_recorte(
        kpis_recorte,
        percentual_top10,
        percentual_incidentes,
        percentual_requisicoes,
    )

    col_grafico, col_tabela = st.columns([1.05, 0.95])
    with col_grafico:
        st.markdown("<div class='recorte-panel'>", unsafe_allow_html=True)
        st.plotly_chart(
            _grafico_evolutivo_chamados_recorte(df_recorte, nome_recorte),
            width="stretch",
            key=f"grafico_recorte_{nome_recorte.lower()}_evolutivo_formato",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_tabela:
        st.markdown("<div class='recorte-panel'>", unsafe_allow_html=True)
        st.subheader("Principais falhas do período")
        tabela_falhas = _calcular_tabela_falhas_periodo(df_recorte)
        st.dataframe(
            tabela_falhas,
            width="stretch",
            hide_index=True,
            column_config={
                "%": st.column_config.NumberColumn("%", format="%.1f%%"),
            },
        )
        st.markdown("</div>", unsafe_allow_html=True)

    resumo_localizacoes = (
        df_recorte.groupby("Localizacao", dropna=False)
        .agg(
            Chamados=("N° Chamado", "nunique"),
            Problemas_Distintos=("Problema", "nunique"),
            Pendentes=("Encerrado_Flag", lambda valores: (~valores).sum()),
            MTTR_Horas=("Tempo_Resolucao_Horas", "mean"),
        )
        .reset_index()
        .sort_values("Chamados", ascending=False)
    )
    st.markdown("<div class='recorte-panel'>", unsafe_allow_html=True)
    st.subheader("Chamados por localização")
    st.dataframe(
        resumo_localizacoes.head(20),
        width="stretch",
        hide_index=True,
        column_config={
            "MTTR_Horas": st.column_config.NumberColumn("MTTR (h)", format="%.1f"),
        },
    )
    st.markdown("</div>", unsafe_allow_html=True)


st.set_page_config(
    page_title="Relatorio de chamados - N2",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root {
        --accent: #ff6b4a;
        --accent-soft: #fff0ec;
        --navy: #16324f;
        --surface: rgba(255, 255, 255, 0.86);
        --border: rgba(255, 127, 102, 0.18);
        --text: #24232a;
        --muted: #6b6675;
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(255, 155, 128, 0.22), transparent 34rem),
            linear-gradient(135deg, #fff9f7 0%, #f7f9fc 52%, #ffffff 100%);
        color: var(--text);
    }

    h1, h2, h3 { color: var(--navy); letter-spacing: -.025em; }

    .hero {
        background: linear-gradient(120deg, #102a43 0%, #1f4e6d 72%, #ff6b4a 160%);
        border-radius: 24px;
        color: white;
        padding: 1.55rem 1.8rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 18px 42px rgba(16, 42, 67, .18);
    }
    .hero h1 { color: white; font-size: 2rem; margin: 0 0 .35rem; }
    .hero p { color: #d9e7f0; margin: 0; max-width: 760px; }
    .hero-badge { color: #ffb49f; font-size: .76rem; font-weight: 800; letter-spacing: .12em; }

    .section-kicker { color: var(--accent); font-size: .72rem; font-weight: 900; letter-spacing: .14em; margin-top: 1.4rem; }
    .insight-card { background: white; border: 1px solid #e5ebf0; border-top: 4px solid #6c8193; border-radius: 14px; min-height: 150px; padding: 1rem; box-shadow: 0 8px 24px rgba(16,42,67,.06); }
    .insight-card strong { color: var(--navy); display: block; margin: .45rem 0; }
    .insight-card p { color: var(--muted); font-size: .86rem; line-height: 1.45; margin: 0; }
    .insight-icon { align-items: center; background: #eef4f7; border-radius: 99px; display: flex; font-weight: 900; height: 28px; justify-content: center; width: 28px; }
    .insight-crítico { border-top-color: #c73e1d; }
    .insight-atenção { border-top-color: #ed9b27; }
    .insight-positivo { border-top-color: #278a67; }
    .insight-informativo { border-top-color: #3977a8; }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #fff7f4 0%, #ffffff 100%);
        border-right: 1px solid var(--border);
    }

    [data-testid="stMetric"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 18px;
        box-shadow: 0 16px 40px rgba(44, 38, 35, 0.08);
        padding: 1rem 1.1rem;
    }

    [data-testid="stMetricLabel"] p {
        color: var(--muted);
        font-weight: 700;
        letter-spacing: .01em;
    }

    [data-testid="stMetricValue"] {
        color: var(--text);
        font-weight: 800;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: .35rem;
        background: rgba(255, 255, 255, .72);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: .35rem;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 14px;
        padding: .6rem 1rem;
        font-weight: 700;
    }

    .stTabs [aria-selected="true"] {
        background: var(--accent-soft);
        color: var(--accent);
    }

    div[data-testid="stPlotlyChart"], div[data-testid="stDataFrame"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 18px;
        box-shadow: 0 16px 40px rgba(44, 38, 35, 0.06);
        padding: .35rem;
    }

    .recorte-eyebrow {
        color: var(--muted);
        font-size: .95rem;
        font-weight: 700;
    }

    .recorte-title {
        color: #221f20;
        font-size: 2.2rem;
        font-weight: 900;
        margin: .1rem 0 .15rem 0;
        border-bottom: 7px solid rgba(255, 127, 102, .72);
        padding-bottom: .35rem;
        box-shadow: 0 6px 4px -5px rgba(44, 38, 35, .6);
    }

    .recorte-periodo {
        color: var(--muted);
        font-size: .92rem;
        margin-bottom: 1rem;
    }

    .recorte-kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 1rem;
        margin: 1.15rem 0 1.35rem;
    }

    .recorte-kpi-card {
        background: rgba(255, 255, 255, .92);
        border: 1px solid rgba(108, 86, 78, .16);
        border-left: 7px solid var(--accent);
        border-radius: 16px;
        box-shadow: 0 8px 12px rgba(44, 38, 35, .18);
        min-height: 86px;
        padding: 1.05rem 1.1rem .85rem;
    }

    .recorte-kpi-split {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
    }

    .recorte-kpi-value {
        color: #221f20;
        font-size: 2rem;
        font-weight: 900;
        line-height: 1;
    }

    .recorte-kpi-label {
        color: var(--muted);
        font-size: .82rem;
        font-weight: 700;
        line-height: 1.2;
        margin-top: .45rem;
    }

    .recorte-panel {
        background: rgba(255, 255, 255, .94);
        border: 1px solid rgba(108, 86, 78, .16);
        border-radius: 32px;
        box-shadow: 0 8px 12px rgba(44, 38, 35, .16);
        padding: 1.1rem 1.2rem;
        margin-bottom: 1.1rem;
    }


    @media (max-width: 1100px) {
        .recorte-kpi-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
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
        "Localizações",
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
                f"{quantidade:,} chamados foram atualizados com sucesso.".replace(
                    ",", "."
                )
            )
        except Exception as erro:
            st.error(f"Erro ao atualizar o Supabase: {erro}")

    st.stop()


st.markdown(
    """
    <div class="hero">
        <div class="hero-badge">SERVICE OPERATIONS · N2</div>
        <h1>Relatório de chamados</h1>
        <p>Visão executiva de demanda, eficiência, SLA e riscos operacionais. Tempos em horas úteis, de segunda a sexta-feira.</p>
    </div>
    """,
    unsafe_allow_html=True,
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


st.success(f"Base consultada: {len(df):,} chamados".replace(",", "."))

if st.sidebar.button(
    "Atualizar dados agora",
    width="stretch",
):
    st.cache_data.clear()
    st.rerun()


filtros = renderizar_filtros(df)
df_filtrado = aplicar_filtros(df, filtros)
df_segmentado = aplicar_filtros(df, filtros, aplicar_periodo=False)

if df_filtrado.empty:
    st.warning("Nenhum chamado encontrado para os filtros selecionados.")
    st.stop()


kpis = calcular_kpis(df_filtrado)

periodo_selecionado = filtros["periodo"]
if isinstance(periodo_selecionado, tuple) and len(periodo_selecionado) == 2:
    inicio_periodo, fim_periodo = periodo_selecionado
else:
    inicio_periodo = df_filtrado["Abertura"].min().date()
    fim_periodo = df_filtrado["Abertura"].max().date()

fluxo = calcular_fluxo_periodo(df_segmentado, inicio_periodo, fim_periodo)
inicio_anterior, fim_anterior = calcular_periodo_anterior(
    inicio_periodo, fim_periodo
)
fluxo_anterior = calcular_fluxo_periodo(
    df_segmentado, inicio_anterior, fim_anterior
)
comparativo_fluxo = {
    indicador: calcular_variacao(fluxo[indicador], fluxo_anterior[indicador])
    for indicador in ["abertos", "encerrados", "taxa_absorcao"]
}


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
    "SLA no prazo",
    f"{kpis['sla_medido_percentual']:.1f}%",
    help=(
        "Percentual auditado pelo dashboard: tempo útil medido "
        "comparado à meta do nível SLA."
    ),
)

st.caption(
    "SLA principal recalculado pelo dashboard. O status recebido da origem "
    "permanece disponível para conferência e auditoria."
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
    "Chamados em atraso",
    f"{kpis['fora_sla_medido']:,}".replace(",", "."),
    help="Contagem recalculada pelo dashboard com base na meta do nível SLA.",
)
d4.metric(
    "Próximos de vencer",
    f"{kpis['proximos_vencer']:,}".replace(",", "."),
    help="Pendentes dentro da meta, mas com até 2 horas úteis restantes.",
)

_renderizar_resumo_executivo(df_filtrado, kpis, fluxo, comparativo_fluxo)


aba1, aba2, aba3, aba4, aba5, aba6, aba7, aba8 = st.tabs(
    [
        "Visão geral",
        "Tendência semanal",
        "Problemas",
        "Localizações e responsáveis",
        "SLA e backlog",
        "Recorte Loja",
        "Recorte CD",
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

    semanas_validas = df_filtrado["InicioSemana"].dropna().sort_values().unique()

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

        variacao = ((atual - anterior) / anterior * 100) if anterior > 0 else 0

        a1, a2, a3 = st.columns(3)
        a1.metric("Semana mais recente", atual)
        a2.metric("Semana anterior", anterior)
        a3.metric(
            "Variação semanal",
            f"{variacao:.1f}%",
            delta=f"{variacao:.1f}%",
        )

        st.caption(
            "Semana mais recente iniciada em " f"{semana_atual.strftime('%d/%m/%Y')}."
        )
    else:
        st.info("Não existem datas válidas para realizar " "a análise semanal.")

    st.plotly_chart(
        grafico_sla_semanal(df_filtrado),
        width="stretch",
        key="grafico_analise_sla_semanal",
    )


with aba3:
    aba_problemas_resumo, aba_problemas_nivelsla = st.tabs(
        [
            "Resumo",
            "Nível SLA",
        ]
    )

    with aba_problemas_resumo:
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

    with aba_problemas_nivelsla:
        st.subheader("Metas por nível SLA")
        st.caption("Referência usada para medir a coluna nivelsla dos chamados.")

        niveis_sla = pd.DataFrame(
            [
                {
                    "nivelsla": nivel,
                    "Meta": f"{horas} horas",
                }
                for nivel, horas in SLA_NIVEIS_HORAS.items()
            ]
        )

        st.dataframe(
            niveis_sla,
            width="stretch",
            hide_index=True,
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

    backlog = df_filtrado.loc[~df_filtrado["Encerrado_Flag"]].sort_values(
        "Idade_Pendente_Horas",
        ascending=False,
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
        backlog_priorizado["SLA_Medido_Status"].eq("Fora do SLA").astype(int)
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
    df_loja = df_filtrado[df_filtrado["Grupo_Localizacao"].eq("Loja")]
    _renderizar_recorte_operacao(df_loja, "Loja")


with aba7:
    df_cd = df_filtrado[df_filtrado["Grupo_Localizacao"].eq("CD")]
    _renderizar_recorte_operacao(df_cd, "CD")


with aba8:
    st.subheader("Análise dos títulos e descrições dos chamados")

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
        coluna for coluna in colunas_exibicao if coluna in df_filtrado.columns
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
            with st.spinner("Gerando relatório Excel..."):
                excel = gerar_excel_relatorio(df_filtrado)

            st.download_button(
                "Baixar relatório filtrado em Excel",
                data=excel,
                file_name=("relatorio_chamados_filtrado.xlsx"),
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                key="download_relatorio_excel",
            )
        except Exception as erro:
            st.error("Não foi possível gerar o relatório Excel: " f"{erro}")
