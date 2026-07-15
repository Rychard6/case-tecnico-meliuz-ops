"""Testes do pipeline de limpeza e agregação dos dados de cashback."""

from pathlib import Path
import sys
import unittest

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from data_processor import clean_financial_string, process_dataframe_data  # noqa: E402


class TestCashbackPipeline(unittest.TestCase):
    """Valida a limpeza financeira e o agrupamento por grupo de usuários."""

    def test_clean_financial_string_with_real_dirty_examples(self) -> None:
        """Deve converter formatos reais com R$ antes/depois e pontos de milhar."""
        test_cases = {
            "R$ 1.516": 1516.0,
            "1.516 R$": 1516.0,
            "R$ 3.267": 3267.0,
            "93.390 R$": 93390.0,
            "R$ 93.390": 93390.0,
            "R$ 1.234,56": 1234.56,
            "": 0.0,
        }

        for raw_value, expected_value in test_cases.items():
            with self.subTest(raw_value=raw_value):
                self.assertEqual(clean_financial_string(raw_value), expected_value)

    def test_process_dataframe_data_groups_and_calculates_profit(self) -> None:
        """Deve somar métricas por grupo e calcular lucro_meliuz corretamente."""
        mock_df = pd.DataFrame(
            {
                "Data": ["2026-07-14", "2026-07-14", "2026-07-14"],
                "Grupos de usuários": ["Controle", "Controle", "Variante B"],
                "Parceiro": ["Parceiro A", "Parceiro A", "Parceiro A"],
                "compradores": [10, 15, 20],
                "comissão": ["R$ 1.516", "1.516 R$", "R$ 3.267"],
                "cashback": ["R$ 300", "300 R$", "R$ 1.000"],
                "vendas totais": ["93.390 R$", "R$ 93.390", "R$ 50.000"],
            }
        )

        result = process_dataframe_data(mock_df)

        self.assertEqual(result["Controle"]["total_compradores"], 25)
        self.assertEqual(result["Controle"]["total_comissao"], 3032.0)
        self.assertEqual(result["Controle"]["total_cashback"], 600.0)
        self.assertEqual(result["Controle"]["total_vendas"], 186780.0)
        self.assertEqual(result["Controle"]["lucro_meliuz"], 2432.0)

        self.assertEqual(result["Variante B"]["total_compradores"], 20)
        self.assertEqual(result["Variante B"]["total_comissao"], 3267.0)
        self.assertEqual(result["Variante B"]["total_cashback"], 1000.0)
        self.assertEqual(result["Variante B"]["total_vendas"], 50000.0)
        self.assertEqual(result["Variante B"]["lucro_meliuz"], 2267.0)


if __name__ == "__main__":
    unittest.main()
