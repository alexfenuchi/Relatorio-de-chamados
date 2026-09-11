import unittest

import pandas as pd

from src.relatorios import calcular_problemas_localizacao, calcular_resumo_localizacoes


class RelatoriosTest(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame(
            {
                "N° Chamado": ["1", "2", "3", "4", "5"],
                "Localizacao": ["Loja A", "Loja A", "Loja A", "Loja B", None],
                "Problema": ["Rede", "Rede", "Impressora", "Rede", "Acesso"],
                "Encerrado_Flag": [True, False, True, False, False],
                "Tempo_Resolucao_Horas": [1.0, 2.0, 3.0, 4.0, 5.0],
            }
        )

    def test_resumo_nao_inclui_tempo_medio(self):
        resumo = calcular_resumo_localizacoes(self.df)

        self.assertEqual(
            resumo.columns.tolist(),
            ["Localizacao", "Quantidade", "Pendentes", "Problemas_Distintos"],
        )
        loja_a = resumo[resumo["Localizacao"].eq("Loja A")].iloc[0]
        self.assertEqual(loja_a["Problemas_Distintos"], 2)

    def test_detalhe_lista_problemas_da_localizacao(self):
        problemas = calcular_problemas_localizacao(self.df, "Loja A")

        self.assertEqual(problemas["Problema"].tolist(), ["Rede", "Impressora"])
        self.assertEqual(problemas["Quantidade"].tolist(), [2, 1])

    def test_detalhe_aceita_localizacao_nao_informada(self):
        problemas = calcular_problemas_localizacao(self.df, None)

        self.assertEqual(problemas["Problema"].tolist(), ["Acesso"])


if __name__ == "__main__":
    unittest.main()
