# Registra decisões no Google Sheets e mantém CSV local como contingência.

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

from dotenv import load_dotenv

# Carrega credenciais locais sem exigir configuração global do ambiente.
load_dotenv()

# Mantém o fallback local ativo mesmo quando a integração não está instalada.
try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
RESULTADOS_CSV = os.getenv("RESULTADOS_CSV", "resultados.csv")
FALLBACK_HEADERS = ["Data Análise", "Dataset", "Veredito IA"]
SHEETS_SUCCESS = "success"
SHEETS_FALLBACK_REQUIRED = "fallback_required"
SHEETS_ERROR = "error"
SheetsSaveStatus = Literal["success", "fallback_required", "error"]


# Aceita arquivo JSON ou conteúdo JSON para facilitar execução local e CI.
def get_sheets_credentials() -> Optional[Any]:
    if not HAS_GSPREAD:
        return None

    try:
        json_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if json_path and os.path.exists(json_path):
            return Credentials.from_service_account_file(json_path, scopes=SCOPES)

        json_content = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_CONTENT")
        if json_content:
            return Credentials.from_service_account_info(json.loads(json_content), scopes=SCOPES)

        return None

    except Exception as error:
        print(f"Erro ao carregar credenciais do Google Sheets: {error}")
        return None


def save_to_sheets(
    timestamp: str,
    dataset_name: str,
    verdict: str
) -> SheetsSaveStatus:
    if not HAS_GSPREAD:
        print("gspread não está instalado. Iniciando fallback local.")
        return SHEETS_FALLBACK_REQUIRED

    try:
        credentials = get_sheets_credentials()
        if not credentials:
            print("Credenciais do Sheets ausentes. Iniciando fallback local.")
            return SHEETS_FALLBACK_REQUIRED

        sheet_id = os.getenv("GOOGLE_SHEETS_ID")
        if not sheet_id:
            print("Credenciais do Sheets ausentes. Iniciando fallback local.")
            return SHEETS_FALLBACK_REQUIRED

        client = gspread.authorize(credentials)
        worksheet = client.open_by_key(sheet_id).sheet1
        worksheet.append_row([timestamp, dataset_name, verdict], value_input_option="RAW")

        return SHEETS_SUCCESS

    except Exception as error:
        print(f"Erro ao salvar no Google Sheets: {error}")
        return SHEETS_ERROR


def save_fallback_csv(
    timestamp: str,
    dataset_name: str,
    verdict: str
) -> bool:
    try:
        fallback_path = Path(RESULTADOS_CSV)
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        file_exists = fallback_path.exists()

        with fallback_path.open(mode="a", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)

            if not file_exists:
                writer.writerow(FALLBACK_HEADERS)

            writer.writerow([timestamp, dataset_name, verdict[:500]])

        return True

    except Exception as error:
        print(f"Erro ao salvar fallback CSV: {error}")
        return False


# Carrega o histórico local para auditoria simples em execuções sem Sheets.
def load_resultados_csv() -> list:
    try:
        fallback_path = Path(RESULTADOS_CSV)
        if not fallback_path.exists():
            return []

        with fallback_path.open(mode="r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            return list(reader) if reader else []

    except Exception as error:
        print(f"Erro ao carregar histórico CSV: {error}")
        return []


if __name__ == "__main__":
    try:
        success = save_fallback_csv(
            timestamp=datetime.now().isoformat(),
            dataset_name="teste_cashback_exemplo",
            verdict="Recomendação: Escalar Grupo C para 100% do tráfego. Lucro 31% superior."
        )

        if success:
            print("\nTeste de fallback completado")
            resultados = load_resultados_csv()
            print(f"Registros no fallback: {len(resultados)}")
    except Exception as error:
        print(f"Erro: {error}")
