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
