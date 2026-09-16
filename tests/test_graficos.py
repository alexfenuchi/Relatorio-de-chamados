import unittest

import pandas as pd

from src.graficos import grafico_status


class GraficoStatusTest(unittest.TestCase):
    def test_separa_situacao_por_cd_e_loja(self):
        dados = pd.DataFrame(
            {
                "N° Chamado": ["1", "2", "3", "4", "4"],
                "Situacao": [
                    "Encerrado",
                    "Encerrado",
                    "Aberto",
                    "Aberto",
                    "Aberto",
                ],
                "Grupo_Localizacao": ["CD", "Loja", "CD", "Loja", "Loja"],
            }
        )

        figura = grafico_status(dados)

        self.assertEqual(
            set(figura.data[0].labels),
            {
                "Aberto — CD",
                "Aberto — Loja",
                "Encerrado — CD",
                "Encerrado — Loja",
            },
        )
        self.assertEqual(sum(figura.data[0].values), 4)
        self.assertEqual(
            figura.layout.title.text,
            "Distribuição por situação: CD x Loja",
        )


if __name__ == "__main__":
    unittest.main()
