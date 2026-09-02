import pandas as pd
import plotly.express as px

COR_GRAFICO_PRINCIPAL = "#ff9b80"
PALETA_GRAFICOS = [
    COR_GRAFICO_PRINCIPAL,
    "#ffb39f",
    "#e77f67",
    "#ffc8bb",
    "#c96a55",
    "#ffe0d8",
]
COR_GRAFICO_TEXTO = "#2f2f2f"


def aplicar_cor_base(figura):
    """Aplica a cor base informada aos traços sem cor categórica explícita."""
    for trace in figura.data:
        if getattr(trace, "type", None) == "bar":
            trace.update(marker_color=COR_GRAFICO_PRINCIPAL)
        elif getattr(trace, "type", None) in {"scatter", "scattergl"}:
            trace.update(
                line={"color": COR_GRAFICO_PRINCIPAL},
                marker={"color": COR_GRAFICO_PRINCIPAL},
            )
    return figura


def grafico_evolucao_semanal(df):
    abertura = (
        df.groupby("InicioSemana")["N° Chamado"].nunique().reset_index(name="Abertos")
    )

    encerrados = (
        df.dropna(subset=["Encerramento"])
        .assign(
            SemanaEncerramento=lambda d: (
                d["Encerramento"]
                - pd.to_timedelta(d["Encerramento"].dt.weekday, unit="D")
            ).dt.normalize()
        )
        .groupby("SemanaEncerramento")["N° Chamado"]
        .nunique()
        .reset_index(name="Encerrados")
        .rename(columns={"SemanaEncerramento": "InicioSemana"})
    )

    semanal = (
        abertura.merge(
            encerrados,
            on="InicioSemana",
            how="outer",
        )
        .fillna(0)
        .sort_values("InicioSemana")
    )

    longo = semanal.melt(
        id_vars="InicioSemana",
        value_vars=["Abertos", "Encerrados"],
        var_name="Tipo",
        value_name="Quantidade",
    )

    fig = px.line(
        longo,
        x="InicioSemana",
        y="Quantidade",
        color="Tipo",
        markers=True,
        title="Evolução semanal de chamados",
        color_discrete_sequence=PALETA_GRAFICOS,
    )

    fig.update_layout(
        xaxis_title="Semana",
        yaxis_title="Quantidade",
        legend_title="",
    )

    return fig


def grafico_top_problemas(df, top_n=10):
    dados = (
        df.groupby("Problema", dropna=False)["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
        .head(top_n)
        .sort_values("Quantidade")
    )

    fig = px.bar(
        dados,
        x="Quantidade",
        y="Problema",
        orientation="h",
        text="Quantidade",
        title=f"Top {top_n} problemas",
        color_discrete_sequence=[COR_GRAFICO_PRINCIPAL],
    )

    fig.update_layout(
        xaxis_title="Chamados",
        yaxis_title="",
    )

    return fig


def grafico_top_lojas(df, top_n=15):
    dados = (
        df.groupby("Localizacao", dropna=False)["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
        .head(top_n)
        .sort_values("Quantidade")
    )

    fig = px.bar(
        dados,
        x="Quantidade",
        y="Localizacao",
        orientation="h",
        text="Quantidade",
        title=f"Top {top_n} localizações com mais chamados",
        color_discrete_sequence=[COR_GRAFICO_PRINCIPAL],
    )

    fig.update_layout(
        xaxis_title="Chamados",
        yaxis_title="",
    )

    return fig


def grafico_status(df):
    dados = (
        df.groupby("Situacao", dropna=False)["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
    )

    return px.pie(
        dados,
        names="Situacao",
        values="Quantidade",
        hole=0.55,
        title="Distribuição por situação",
        color_discrete_sequence=PALETA_GRAFICOS,
    )


def grafico_sla(df):
    dados = (
        df.groupby("StatusSLA", dropna=False)["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
    )

    fig = px.bar(
        dados,
        x="StatusSLA",
        y="Quantidade",
        text="Quantidade",
        title="Chamados por status de SLA",
        color_discrete_sequence=[COR_GRAFICO_PRINCIPAL],
    )

    fig.update_layout(
        xaxis_title="Status SLA",
        yaxis_title="Chamados",
    )

    return fig


def grafico_responsaveis(df, top_n=15):
    dados = (
        df.groupby("Responsavel", dropna=False)["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
        .head(top_n)
        .sort_values("Quantidade")
    )

    fig = px.bar(
        dados,
        x="Quantidade",
        y="Responsavel",
        orientation="h",
        text="Quantidade",
        title="Chamados por responsável",
        color_discrete_sequence=[COR_GRAFICO_PRINCIPAL],
    )

    fig.update_layout(
        xaxis_title="Chamados",
        yaxis_title="",
    )

    return fig


def grafico_top_titulos(df, top_n=10):
    """
    Cria um gráfico horizontal com os títulos de chamados mais recorrentes.

    Títulos iguais são agrupados. Textos longos são reduzidos no eixo,
    mas permanecem completos no tooltip.
    """
    if "Título" not in df.columns:
        return aplicar_cor_base(px.bar(title="Títulos de chamados não disponíveis"))

    dados = df.copy()

    dados["Titulo_Resumo"] = (
        dados["Título"]
        .fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    dados = dados[
        dados["Titulo_Resumo"].ne("")
        & dados["Titulo_Resumo"].str.lower().ne("nan")
        & dados["Titulo_Resumo"].str.lower().ne("none")
    ]

    titulos = (
        dados.groupby("Titulo_Resumo", dropna=False)["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
        .head(top_n)
        .copy()
    )

    if titulos.empty:
        return aplicar_cor_base(px.bar(title="Nenhum título de chamado encontrado"))

    limite_texto = 90

    titulos["Titulo_Grafico"] = titulos["Titulo_Resumo"].apply(
        lambda texto: (
            texto[:limite_texto] + "..." if len(texto) > limite_texto else texto
        )
    )

    titulos = titulos.sort_values(
        "Quantidade",
        ascending=True,
    )

    figura = px.bar(
        titulos,
        x="Quantidade",
        y="Titulo_Grafico",
        orientation="h",
        text="Quantidade",
        title=f"Top {top_n} títulos dos chamados",
        custom_data=["Titulo_Resumo"],
        color_discrete_sequence=[COR_GRAFICO_PRINCIPAL],
    )

    figura.update_traces(
        hovertemplate=(
            "<b>Título</b><br>"
            "%{customdata[0]}<br><br>"
            "<b>Chamados:</b> %{x}"
            "<extra></extra>"
        )
    )

    figura.update_layout(
        xaxis_title="Quantidade de chamados",
        yaxis_title="",
        height=max(500, top_n * 42),
        margin=dict(l=20, r=20, t=60, b=40),
    )

    return figura


def grafico_descricoes_problemas(df, top_n=10):
    """
    Cria um gráfico horizontal com as descrições de problemas mais recorrentes.

    Descrições iguais são agrupadas. Textos longos são reduzidos no eixo,
    mas permanecem completos no tooltip.
    """
    if "descricao" not in df.columns:
        return aplicar_cor_base(px.bar(title="Descrições de problemas não disponíveis"))

    dados = df.copy()

    dados["Descricao_Resumo"] = (
        dados["descricao"]
        .fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    dados = dados[
        dados["Descricao_Resumo"].ne("")
        & dados["Descricao_Resumo"].str.lower().ne("nan")
        & dados["Descricao_Resumo"].str.lower().ne("none")
    ]

    descricoes = (
        dados.groupby("Descricao_Resumo", dropna=False)["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
        .head(top_n)
        .copy()
    )

    if descricoes.empty:
        return aplicar_cor_base(
            px.bar(title="Nenhuma descrição de problema encontrada")
        )

    limite_texto = 90

    descricoes["Descricao_Grafico"] = descricoes["Descricao_Resumo"].apply(
        lambda texto: (
            texto[:limite_texto] + "..." if len(texto) > limite_texto else texto
        )
    )

    descricoes = descricoes.sort_values(
        "Quantidade",
        ascending=True,
    )

    figura = px.bar(
        descricoes,
        x="Quantidade",
        y="Descricao_Grafico",
        orientation="h",
        text="Quantidade",
        title=f"Top {top_n} descrições de problemas",
        custom_data=["Descricao_Resumo"],
        color_discrete_sequence=[COR_GRAFICO_PRINCIPAL],
    )

    figura.update_traces(
        hovertemplate=(
            "<b>Descrição</b><br>"
            "%{customdata[0]}<br><br>"
            "<b>Chamados:</b> %{x}"
            "<extra></extra>"
        )
    )

    figura.update_layout(
        xaxis_title="Quantidade de chamados",
        yaxis_title="",
        height=max(500, top_n * 42),
        margin=dict(l=20, r=20, t=60, b=40),
    )

    return figura


def grafico_aging_backlog(df):
    ordem = [
        "Até 1 dia",
        "2 a 3 dias",
        "4 a 5 dias",
        "6 a 10 dias",
        "Acima de 10 dias",
    ]

    dados = df.copy()

    if "Faixa_Aging" not in dados.columns:
        dados["Faixa_Aging"] = pd.cut(
            dados["Idade_Pendente_Dias"],
            bins=[-float("inf"), 1, 3, 5, 10, float("inf")],
            labels=ordem,
        )

    dados = (
        dados.loc[~dados["Encerrado_Flag"]]
        .groupby("Faixa_Aging", dropna=False, observed=False)["N° Chamado"]
        .nunique()
        .reindex(ordem, fill_value=0)
        .reset_index(name="Quantidade")
    )

    figura = px.bar(
        dados,
        x="Faixa_Aging",
        y="Quantidade",
        text="Quantidade",
        title="Backlog por faixa de idade",
        color_discrete_sequence=[COR_GRAFICO_PRINCIPAL],
    )

    figura.update_layout(
        xaxis_title="Idade do chamado (1 dia = 8 horas)",
        yaxis_title="Chamados pendentes",
    )

    return figura


def grafico_sla_semanal(df):
    dados = df.copy()
    dados["Dentro_SLA_Flag"] = dados["SLA_Normalizado"].isin(
        ["em dia", "dentro", "dentro do prazo"]
    )
    dados["SLA_Classificado"] = dados["SLA_Normalizado"].isin(
        [
            "em dia",
            "dentro",
            "dentro do prazo",
            "em atraso",
            "fora",
            "fora do prazo",
        ]
    )

    semanal = (
        dados.loc[dados["SLA_Classificado"]]
        .groupby("InicioSemana")
        .agg(
            Total=("N° Chamado", "nunique"),
            DentroSLA=("Dentro_SLA_Flag", "sum"),
        )
        .reset_index()
    )

    semanal["SLA_Percentual"] = semanal["DentroSLA"] / semanal["Total"] * 100

    figura = px.line(
        semanal,
        x="InicioSemana",
        y="SLA_Percentual",
        markers=True,
        title="Evolução semanal do SLA",
        color_discrete_sequence=[COR_GRAFICO_PRINCIPAL],
    )

    figura.update_layout(
        xaxis_title="Semana",
        yaxis_title="SLA dentro do prazo (%)",
    )

    figura.update_yaxes(range=[0, 100])

    return figura


def grafico_aberturas_dia_semana(df):
    ordem = [
        "Segunda",
        "Terça",
        "Quarta",
        "Quinta",
        "Sexta",
        "Sábado",
        "Domingo",
    ]

    dados = (
        df.groupby("DiaSemana")["N° Chamado"]
        .nunique()
        .reindex(ordem, fill_value=0)
        .reset_index(name="Quantidade")
    )

    figura = px.bar(
        dados,
        x="DiaSemana",
        y="Quantidade",
        text="Quantidade",
        title="Chamados abertos por dia da semana",
        color_discrete_sequence=[COR_GRAFICO_PRINCIPAL],
    )

    figura.update_layout(
        xaxis_title="Dia da semana",
        yaxis_title="Chamados",
    )

    return figura


def grafico_tempo_medio_problema(df, top_n=10):
    dados = (
        df.loc[df["Encerrado_Flag"] & df["Tempo_Resolucao_Horas"].notna()]
        .groupby("Problema")
        .agg(
            Quantidade=("N° Chamado", "nunique"),
            Tempo_Medio_Horas=("Tempo_Resolucao_Horas", "mean"),
        )
        .reset_index()
    )

    # Evita destacar médias de grupos com apenas um chamado.
    dados = dados[dados["Quantidade"] >= 2]

    dados = (
        dados.sort_values(
            "Tempo_Medio_Horas",
            ascending=False,
        )
        .head(top_n)
        .sort_values("Tempo_Medio_Horas")
    )

    figura = px.bar(
        dados,
        x="Tempo_Medio_Horas",
        y="Problema",
        orientation="h",
        text="Tempo_Medio_Horas",
        title=f"Top {top_n} problemas com maior tempo médio",
        custom_data=["Quantidade"],
        color_discrete_sequence=[COR_GRAFICO_PRINCIPAL],
    )

    figura.update_traces(
        texttemplate="%{text:.1f} h",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Tempo médio: %{x:.1f} h<br>"
            "Chamados: %{customdata[0]}"
            "<extra></extra>"
        ),
    )

    figura.update_layout(
        xaxis_title="Tempo médio útil (horas)",
        yaxis_title="",
    )

    return figura


def grafico_prioridades(df):
    dados = (
        df.groupby("prioridade", dropna=False)["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
    )

    figura = px.bar(
        dados,
        x="prioridade",
        y="Quantidade",
        text="Quantidade",
        title="Chamados por prioridade",
        color_discrete_sequence=[COR_GRAFICO_PRINCIPAL],
    )

    figura.update_layout(
        xaxis_title="Prioridade",
        yaxis_title="Chamados",
    )

    return figura


def grafico_sla_por_nivel(df):
    dados = (
        df[df["SLA_Medido_Status"].isin(["Dentro do SLA", "Fora do SLA"])]
        .groupby(["nivelsla", "SLA_Medido_Status"], dropna=False)["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
    )

    if dados.empty:
        return aplicar_cor_base(
            px.bar(title="Medição de SLA por nível sem dados classificados")
        )

    figura = px.bar(
        dados,
        x="nivelsla",
        y="Quantidade",
        color="SLA_Medido_Status",
        text="Quantidade",
        barmode="group",
        title="Medição de SLA por nível",
        color_discrete_map={
            "Dentro do SLA": COR_GRAFICO_PRINCIPAL,
            "Fora do SLA": "#c96a55",
        },
    )

    figura.update_layout(
        xaxis_title="Nível SLA",
        yaxis_title="Chamados",
        legend_title="Status medido",
    )

    return figura


def grafico_percentual_sla_por_nivel(df):
    dados = df[df["SLA_Medido_Status"].isin(["Dentro do SLA", "Fora do SLA"])].copy()

    if dados.empty:
        return aplicar_cor_base(
            px.bar(title="Percentual de SLA por nível sem dados classificados")
        )

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
        color_discrete_sequence=[COR_GRAFICO_PRINCIPAL],
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
