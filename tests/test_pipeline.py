# Testes do pipeline de limpeza e agregação dos dados de cashback.

from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

import main as pipeline_main  # noqa: E402
from data_processor import clean_financial_string, process_dataframe_data  # noqa: E402


class TestCashbackPipeline(unittest.TestCase):
    # Valida a limpeza financeira e o agrupamento por grupo de usuários.

    def test_clean_financial_string_with_real_dirty_examples(self) -> None:
        # Deve converter formatos reais com R$ antes/depois e pontos de milhar.
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
        # Deve somar métricas por grupo e calcular lucro_meliuz corretamente.
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

    def test_save_markdown_report_creates_expected_artifact(self) -> None:
        # Deve materializar o veredito no padrão exigido para auditoria.
        original_reports_dir = pipeline_main.REPORTS_DIR

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                pipeline_main.REPORTS_DIR = Path(temp_dir)
                csv_file = Path("data/dataset_01_parceiroA.csv")

                report_path = pipeline_main.save_markdown_report(csv_file, "## Veredito\nEscalar variante B.")

                self.assertEqual(report_path.name, "relatorio_dataset_01_parceiroA.md")
                self.assertTrue(report_path.exists())
                self.assertEqual(
                    report_path.read_text(encoding="utf-8"),
                    "## Veredito\nEscalar variante B.\n",
                )
        finally:
            pipeline_main.REPORTS_DIR = original_reports_dir


if __name__ == "__main__":
    unittest.main()
