import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def _vazio(titulo: str, mensagem: str = "Sem dados para os filtros selecionados"):
    fig = go.Figure()
    fig.update_layout(title=titulo)
    fig.add_annotation(text=mensagem, showarrow=False, x=0.5, y=0.5)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def grafico_evolucao_semanal(df: pd.DataFrame):
    abertura = (
        df.dropna(subset=["InicioSemana"])
        .groupby("InicioSemana")["N° Chamado"]
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

    semanal = abertura.merge(encerrados, on="InicioSemana", how="outer")
    if semanal.empty:
        return _vazio("Evolução semanal de chamados")

    semanal = semanal.fillna(0).sort_values("InicioSemana")
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
    fig.update_layout(xaxis_title="Semana", yaxis_title="Quantidade", legend_title="")
    return fig


def grafico_top_problemas(df: pd.DataFrame, top_n: int = 10):
    dados = (
        df.dropna(subset=["Problema"])
        .groupby("Problema")["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
        .head(top_n)
        .sort_values("Quantidade")
    )
    if dados.empty:
        return _vazio(f"Top {top_n} problemas")
    fig = px.bar(
        dados,
        x="Quantidade",
        y="Problema",
        orientation="h",
        text="Quantidade",
        title=f"Top {top_n} problemas",
    )
    fig.update_layout(xaxis_title="Chamados", yaxis_title="")
    return fig


def grafico_top_lojas(df: pd.DataFrame, top_n: int = 15):
    dados = (
        df.dropna(subset=["Localizacao"])
        .groupby("Localizacao")["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
        .head(top_n)
        .sort_values("Quantidade")
    )
    if dados.empty:
        return _vazio(f"Top {top_n} lojas com mais chamados")
    fig = px.bar(
        dados,
        x="Quantidade",
        y="Localizacao",
        orientation="h",
        text="Quantidade",
        title=f"Top {top_n} lojas com mais chamados",
    )
    fig.update_layout(xaxis_title="Chamados", yaxis_title="")
    return fig


def grafico_status(df: pd.DataFrame):
    dados = (
        df.assign(Situacao=df["Situacao"].fillna("Não informado"))
        .groupby("Situacao")["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
    )
    if dados.empty:
        return _vazio("Distribuição por situação")
    return px.pie(
        dados,
        names="Situacao",
        values="Quantidade",
        hole=0.55,
        title="Distribuição por situação",
    )


def grafico_sla(df: pd.DataFrame):
    dados = (
        df.assign(StatusSLA=df["StatusSLA"].fillna("Não informado"))
        .groupby("StatusSLA")["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
    )
    if dados.empty:
        return _vazio("Chamados por status de SLA")
    fig = px.bar(
        dados,
        x="StatusSLA",
        y="Quantidade",
        text="Quantidade",
        title="Chamados por status de SLA",
    )
    fig.update_layout(xaxis_title="Status SLA", yaxis_title="Chamados")
    return fig


def grafico_responsaveis(df: pd.DataFrame, top_n: int = 15):
    dados = (
        df.dropna(subset=["Responsavel"])
        .groupby("Responsavel")["N° Chamado"]
        .nunique()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
        .head(top_n)
        .sort_values("Quantidade")
    )
    if dados.empty:
        return _vazio("Chamados por responsável")
    fig = px.bar(
        dados,
        x="Quantidade",
        y="Responsavel",
        orientation="h",
        text="Quantidade",
        title="Chamados por responsável",
    )
    fig.update_layout(xaxis_title="Chamados", yaxis_title="")
    return fig
