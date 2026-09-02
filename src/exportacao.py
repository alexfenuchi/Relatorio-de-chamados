from io import BytesIO
import pandas as pd

from src.tratamento import SLA_NIVEIS_HORAS
from src.metricas import calcular_resumo_sla_medido_por_nivel

def _preparar_para_excel(df: pd.DataFrame) -> pd.DataFrame:
    dados = df.copy()
    for coluna in dados.columns:
        if pd.api.types.is_datetime64_any_dtype(dados[coluna]):
            try:
                dados[coluna] = dados[coluna].dt.tz_localize(None)
            except (TypeError, AttributeError):
                pass
        if dados[coluna].dtype == 'object':
            dados[coluna] = dados[coluna].apply(
                lambda valor: str(valor) if isinstance(valor, (list, dict, tuple, set)) else valor
            )
    return dados

def gerar_excel_relatorio(df: pd.DataFrame) -> bytes:
    if df is None or df.empty:
        raise ValueError('Não existem dados para gerar o relatório Excel.')

    dados = _preparar_para_excel(df)
    resumo_problemas = (
        dados.groupby('Problema', dropna=False)['N° Chamado']
        .nunique().reset_index(name='Quantidade')
        .sort_values('Quantidade', ascending=False)
    )
    resumo_lojas = (
        dados.groupby('Localizacao', dropna=False)['N° Chamado']
        .nunique().reset_index(name='Quantidade')
        .sort_values('Quantidade', ascending=False)
    )
    resumo_semanal = (
        dados.groupby('InicioSemana', dropna=False)['N° Chamado']
        .nunique().reset_index(name='Quantidade')
        .sort_values('InicioSemana')
    )
    resumo_sla = calcular_resumo_sla_medido_por_nivel(dados)
    niveis_sla = pd.DataFrame(
        [
            {'nivelsla': nivel, 'Meta': f'{horas} horas'}
            for nivel, horas in SLA_NIVEIS_HORAS.items()
        ]
    )

    saida = BytesIO()
    with pd.ExcelWriter(saida, engine='xlsxwriter', datetime_format='dd/mm/yyyy hh:mm', date_format='dd/mm/yyyy') as writer:
        dados.to_excel(writer, index=False, sheet_name='Chamados')
        resumo_semanal.to_excel(writer, index=False, sheet_name='Semanal')
        resumo_problemas.to_excel(writer, index=False, sheet_name='Problemas')
        resumo_lojas.to_excel(writer, index=False, sheet_name='Lojas')
        resumo_sla.to_excel(writer, index=False, sheet_name='Medicao SLA')
        niveis_sla.to_excel(writer, index=False, sheet_name='NivelSLA')

        for nome_aba, dataframe in {
            'Chamados': dados,
            'Semanal': resumo_semanal,
            'Problemas': resumo_problemas,
            'Lojas': resumo_lojas,
            'Medicao SLA': resumo_sla,
            'NivelSLA': niveis_sla,
        }.items():
            worksheet = writer.sheets[nome_aba]
            for indice, coluna in enumerate(dataframe.columns):
                largura = min(max(len(str(coluna)) + 2, 12), 45)
                worksheet.set_column(indice, indice, largura)

    saida.seek(0)
    return saida.getvalue()
