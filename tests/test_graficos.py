import unittest

import pandas as pd

from src.graficos import (
    CORES_GRUPO_LOCALIZACAO,
    COR_GRAFICO_PRINCIPAL,
    grafico_aberturas_dia_semana,
    grafico_prioridades,
    grafico_sla,
    grafico_status,
    grafico_tendencia_anual,
    grafico_top_lojas,
    grafico_top_problemas,
)
from src.tema import CORES_LOCALIZACAO, COR_PRIMARIA, COR_TEXTO, COR_TITULO


class GraficoStatusTest(unittest.TestCase):
    def setUp(self):
        self.dados = pd.DataFrame(
            {
                "N° Chamado": ["1", "2", "3", "4", "5"],
                "Situacao": ["Encerrado", "Encerrado", "Aberto", "Aberto", "Aberto"],
                "Grupo_Localizacao": ["CD", "Loja", "CD", "Loja", "Loja"],
                "StatusSLA": ["Em dia", "Em dia", "Atrasado", "Em dia", "Atrasado"],
                "Problema": ["Rede", "Rede", "Sistema", "Sistema", "Rede"],
                "Localizacao": ["CD 1", "Loja 1", "CD 1", "Loja 2", "Loja 1"],
                "prioridade": ["P1", "P1", "P2", "P2", "P1"],
                "DiaSemana": ["Segunda", "Segunda", "Terça", "Terça", "Quarta"],
                "Abertura": pd.to_datetime(
                    [
                        "2025-01-05",
                        "2025-01-10",
                        "2025-02-03",
                        "2025-02-12",
                        "2025-03-01",
                    ]
                ),
            }
        )

    def test_separa_situacao_por_cd_e_loja(self):
        figura = grafico_status(self.dados)

        self.assertEqual(
            set(figura.data[0].labels),
            {
                "Aberto — CD",
                "Aberto — Loja",
                "Encerrado — CD",
                "Encerrado — Loja",
            },
        )
        self.assertEqual(sum(figura.data[0].values), 5)
        self.assertEqual(
            figura.layout.title.text,
            "Distribuição por situação: CD x Loja",
        )

    def test_todos_os_graficos_da_visao_geral_separam_cd_e_loja(self):
        graficos = [
            grafico_sla(self.dados),
            grafico_top_problemas(self.dados),
            grafico_top_lojas(self.dados),
            grafico_prioridades(self.dados),
            grafico_aberturas_dia_semana(self.dados),
        ]

        for figura in graficos:
            with self.subTest(titulo=figura.layout.title.text):
                self.assertEqual({trace.name for trace in figura.data}, {"CD", "Loja"})

    def test_tendencia_anual_agrega_por_mes_e_grupo(self):
        figura = grafico_tendencia_anual(self.dados)

        self.assertEqual({trace.name for trace in figura.data}, {"CD", "Loja"})
        self.assertEqual(sum(sum(trace.y) for trace in figura.data), 5)
        self.assertEqual(figura.layout.xaxis.dtick, "M1")

    def test_graficos_usam_a_identidade_visual_compartilhada(self):
        figura = grafico_top_problemas(self.dados)

        self.assertEqual(COR_GRAFICO_PRINCIPAL, COR_PRIMARIA)
        self.assertEqual(CORES_GRUPO_LOCALIZACAO, CORES_LOCALIZACAO)
        self.assertEqual(
            {trace.name: trace.marker.color for trace in figura.data},
            {"CD": CORES_LOCALIZACAO["CD"], "Loja": CORES_LOCALIZACAO["Loja"]},
        )
        self.assertEqual(figura.layout.template.layout.font.color, COR_TEXTO)
        self.assertEqual(figura.layout.template.layout.title.font.color, COR_TITULO)


if __name__ == "__main__":
    unittest.main()
