import pandas as pd
import streamlit as st

from src.database import atualizar_chamados, buscar_chamados
from src.exportacao import gerar_excel_relatorio
from src.filtros import aplicar_filtros, renderizar_filtros
from src.graficos import (
    grafico_evolucao_semanal,
    grafico_responsaveis,
    grafico_sla,
    grafico_status,
    grafico_top_lojas,
    grafico_top_problemas,
)
from src.leitura import carregar_excel
from src.metricas import calcular_kpis
from src.tratamento import preparar_base

st.set_page_config(
    page_title="Relatório de Chamados N2",
    page_icon="📊",
    layout="wide",
)

MAPA_BANCO_DASHBOARD = {
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
}


def _segredo(nome: str, padrao=None):
    try:
        return st.secrets.get(nome, padrao)
    except Exception:
        return padrao


@st.cache_data(ttl=300, show_spinner=False)
def carregar_dados_supabase() -> pd.DataFrame:
    return buscar_chamados()


def pagina_atualizar_base() -> None:
    st.title("Atualizar base de chamados")
    st.caption(
        "Envie a base anual em Excel. Os chamados existentes serão atualizados "
        "e os novos serão incluídos no Supabase."
    )

    senha_configurada = _segredo("ADMIN_PASSWORD")
    if not senha_configurada:
        st.error("ADMIN_PASSWORD não foi configurada nos Secrets do Streamlit.")
        st.stop()

    senha = st.text_input("Senha de administrador", type="password")
    if not senha:
        st.info("Informe a senha de administrador.")
        st.stop()
    if senha != senha_configurada:
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
        with st.spinner("Lendo e tratando o arquivo..."):
            bruto, aba = carregar_excel(arquivo)
            tratado = preparar_base(bruto)
    except Exception as erro:
        st.error(f"Não foi possível processar o arquivo: {erro}")
        st.stop()

    st.success(
        f"Arquivo processado: {len(tratado):,} registros | Aba: {aba}".replace(
            ",", "."
        )
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros", f"{len(tratado):,}".replace(",", "."))
    c2.metric(
        "Chamados únicos",
        f"{tratado['N° Chamado'].nunique():,}".replace(",", "."),
    )
    c3.metric(
        "Lojas",
        f"{tratado['Localizacao'].nunique():,}".replace(",", "."),
    )
    c4.metric("Colunas utilizadas", len(tratado.columns))

    with st.expander("Visualizar amostra da base"):
        st.dataframe(tratado.head(100), width="stretch", hide_index=True)

    if st.button(
        "Atualizar base no Supabase",
        type="primary",
        width="stretch",
    ):
        try:
            with st.spinner("Atualizando base no Supabase..."):
                quantidade = atualizar_chamados(
                    tratado,
                    nome_arquivo=getattr(arquivo, "name", None),
                )
            st.cache_data.clear()
            st.success(
                f"{quantidade:,} chamados foram atualizados com sucesso.".replace(
                    ",", "."
                )
            )
        except Exception as erro:
            st.error(f"Erro ao atualizar o Supabase: {erro}")


def pagina_dashboard() -> None:
    st.title("📊 Relatório de Chamados — Suporte N2")
    st.caption("Dados consultados diretamente no Supabase.")

    try:
        with st.spinner("Buscando chamados no Supabase..."):
            df_banco = carregar_dados_supabase()
    except Exception as erro:
        st.error(f"Não foi possível consultar o Supabase: {erro}")
        st.info("Confira SUPABASE_URL e SUPABASE_KEY nos Secrets do aplicativo.")
        st.stop()

    if df_banco.empty:
        st.warning(
            "Nenhum registro foi encontrado. Acesse 'Atualizar base' e envie o Excel anual."
        )
        st.stop()

    try:
        df = preparar_base(df_banco.rename(columns=MAPA_BANCO_DASHBOARD))
    except Exception as erro:
        st.error(f"Erro ao preparar os dados do Supabase: {erro}")
        st.stop()

    st.sidebar.caption(
        f"Última consulta: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}"
    )
    if st.sidebar.button("Atualizar dados agora", width="stretch"):
        st.cache_data.clear()
        st.rerun()

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
            st.plotly_chart(grafico_status(df_filtrado), width="stretch")
        with col2:
            st.plotly_chart(grafico_sla(df_filtrado), width="stretch")

        col3, col4 = st.columns(2)
        with col3:
            st.plotly_chart(grafico_top_problemas(df_filtrado), width="stretch")
        with col4:
            st.plotly_chart(grafico_top_lojas(df_filtrado), width="stretch")

    with aba2:
        st.plotly_chart(grafico_evolucao_semanal(df_filtrado), width="stretch")
        semanas = pd.Series(df_filtrado["InicioSemana"].dropna().unique()).sort_values()
        if not semanas.empty:
            semana_atual = pd.Timestamp(semanas.iloc[-1])
            semana_anterior = semana_atual - pd.Timedelta(days=7)
            atual = df_filtrado.loc[
                df_filtrado["InicioSemana"] == semana_atual, "N° Chamado"
            ].nunique()
            anterior = df_filtrado.loc[
                df_filtrado["InicioSemana"] == semana_anterior, "N° Chamado"
            ].nunique()
            variacao = ((atual - anterior) / anterior * 100) if anterior else 0.0

            a1, a2, a3 = st.columns(3)
            a1.metric("Semana mais recente", atual)
            a2.metric("Semana anterior", anterior)
            a3.metric("Variação semanal", f"{variacao:.1f}%", delta=f"{variacao:.1f}%")
            st.caption(
                f"Semana mais recente iniciada em {semana_atual.strftime('%d/%m/%Y')}."
            )
        else:
            st.info("Não existem datas válidas para realizar a análise semanal.")

    with aba3:
        st.plotly_chart(
            grafico_top_problemas(df_filtrado, top_n=15), width="stretch"
        )
        resumo_problemas = (
            df_filtrado.groupby(["Problema", "Produto"], dropna=False)
            .agg(
                Quantidade=("N° Chamado", "nunique"),
                Pendentes=("Encerrado_Flag", lambda valores: int((~valores).sum())),
                Tempo_Medio_Horas=("Tempo_Resolucao_Horas", "mean"),
            )
            .reset_index()
            .sort_values("Quantidade", ascending=False)
        )
        st.dataframe(resumo_problemas, width="stretch", hide_index=True)

    with aba4:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(
                grafico_top_lojas(df_filtrado, top_n=20), width="stretch"
            )
        with col2:
            st.plotly_chart(grafico_responsaveis(df_filtrado), width="stretch")

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
        st.dataframe(resumo_lojas, width="stretch", hide_index=True)

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
            df_filtrado.loc[:, colunas_exibicao],
            width="stretch",
            hide_index=True,
        )

        assinatura_filtro = (
            len(df_filtrado),
            tuple(df_filtrado["N° Chamado"].astype(str).head(5)),
        )
        if st.session_state.get("assinatura_excel") != assinatura_filtro:
            st.session_state.pop("arquivo_excel", None)

        if st.button("Preparar relatório Excel", key="preparar_relatorio_excel"):
            try:
                with st.spinner("Gerando relatório Excel..."):
                    st.session_state["arquivo_excel"] = gerar_excel_relatorio(
                        df_filtrado
                    )
                    st.session_state["assinatura_excel"] = assinatura_filtro
            except Exception as erro:
                st.error(f"Não foi possível gerar o relatório Excel: {erro}")

        if "arquivo_excel" in st.session_state:
            st.download_button(
                "Baixar relatório filtrado em Excel",
                data=st.session_state["arquivo_excel"],
                file_name="relatorio_chamados_filtrado.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                key="download_relatorio_excel",
            )


pagina = st.sidebar.radio("Navegação", ["Dashboard", "Atualizar base"])
if pagina == "Atualizar base":
    pagina_atualizar_base()
else:
    pagina_dashboard()
