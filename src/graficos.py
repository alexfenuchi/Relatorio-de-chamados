import pandas as pd
import plotly.express as px


def grafico_evolucao_semanal(df):
    abertura = (
        df.groupby("InicioSemana")["N° Chamado"]
        .nunique()
        .reset_index(name="Abertos")
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

    semanal = abertura.merge(
        encerrados,
        on="InicioSemana",
        how="outer",
    ).fillna(0).sort_values("InicioSemana")

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
        title=f"Top {top_n} lojas com mais chamados",
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
        return px.bar(title="Títulos de chamados não disponíveis")

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
        return px.bar(title="Nenhum título de chamado encontrado")

    limite_texto = 90

    titulos["Titulo_Grafico"] = titulos["Titulo_Resumo"].apply(
        lambda texto: (
            texto[:limite_texto] + "..."
            if len(texto) > limite_texto
            else texto
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
        return px.bar(title="Descrições de problemas não disponíveis")

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
        return px.bar(title="Nenhuma descrição de problema encontrada")

    limite_texto = 90

    descricoes["Descricao_Grafico"] = descricoes["Descricao_Resumo"].apply(
        lambda texto: (
            texto[:limite_texto] + "..."
            if len(texto) > limite_texto
            else texto
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

    dados = (
        df.loc[~df["Encerrado_Flag"]]
        .groupby("Faixa_Aging", dropna=False)["N° Chamado"]
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

    semanal["SLA_Percentual"] = (
        semanal["DentroSLA"]
        / semanal["Total"]
        * 100
    )

    figura = px.line(
        semanal,
        x="InicioSemana",
        y="SLA_Percentual",
        markers=True,
        title="Evolução semanal do SLA",
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
    )

    figura.update_layout(
        xaxis_title="Dia da semana",
        yaxis_title="Chamados",
    )

    return figura


def grafico_tempo_medio_problema(df, top_n=10):
    dados = (
        df.loc[
            df["Encerrado_Flag"]
            & df["Tempo_Resolucao_Horas"].notna()
        ]
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
    )

    figura.update_layout(
        xaxis_title="Prioridade",
        yaxis_title="Chamados",
    )

    return figura

