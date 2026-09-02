import unittest

import pandas as pd

from src.insights import criar_painel_metas
from src.executivo import (
    METAS_EXECUTIVAS,
    calcular_fluxo_periodo,
    calcular_periodo_anterior,
    calcular_variacao,
)


class MetricasExecutivasTest(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame(
            {
                "N° Chamado": ["1", "2", "3", "4"],
                "Abertura": pd.to_datetime(
                    ["2026-08-01", "2026-08-10", "2026-07-20", "2026-08-30"]
                ),
                "Encerramento": pd.to_datetime(
                    ["2026-08-03", "2026-09-01", "2026-08-05", None]
                ),
            }
        )

    def test_fluxo_inclui_encerrado_aberto_antes_do_periodo(self):
        fluxo = calcular_fluxo_periodo(self.df, "2026-08-01", "2026-08-31")

        self.assertEqual(fluxo["abertos"], 3)
        self.assertEqual(fluxo["encerrados"], 2)
        self.assertEqual(fluxo["saldo"], -1)
        self.assertAlmostEqual(fluxo["taxa_absorcao"], 200 / 3)

    def test_periodo_anterior_tem_mesmo_numero_de_dias(self):
        inicio, fim = calcular_periodo_anterior("2026-08-01", "2026-08-31")

        self.assertEqual(inicio, pd.Timestamp("2026-07-01"))
        self.assertEqual(fim, pd.Timestamp("2026-07-31"))

    def test_variacao_sem_base_retorna_none(self):
        self.assertIsNone(calcular_variacao(10, 0))
        self.assertEqual(calcular_variacao(120, 100), 20)

    def test_painel_metas_classifica_direcoes_corretamente(self):
        kpis = {
            "sla_medido_percentual": 96.0,
            "percentual_backlog": 20.0,
            "tempo_medio_horas": 7.0,
        }
        fluxo = {"taxa_absorcao": 90.0}

        painel = criar_painel_metas(kpis, fluxo, METAS_EXECUTIVAS)

        self.assertEqual(
            painel.set_index("Indicador")["Status"].to_dict(),
            {
                "SLA medido": "Na meta",
                "Backlog": "Fora da meta",
                "MTTR médio": "Na meta",
                "Taxa de absorção": "Fora da meta",
            },
        )


if __name__ == "__main__":
    unittest.main()
