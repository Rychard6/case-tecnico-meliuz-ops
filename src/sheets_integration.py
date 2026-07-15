"""
sheets_integration.py - Módulo responsável pela integração com Google Sheets.

Responsabilidades:
    - Autenticar com Google Sheets via Service Account (JSON)
    - Anexar resultado a uma planilha
    - Implementar fallback robusto para arquivo local CSV se Google falhar

Type Hints: Todas as funções possuem anotações de tipo.
Docstrings: Padrão Google.
"""

import os
import csv
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Importação condicional de gspread
try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False


# Constantes
RESULTADOS_CSV = os.getenv("RESULTADOS_CSV", "resultados.csv")
FALLBACK_HEADERS = ["Data Análise", "Dataset", "Veredito IA"]


def get_sheets_credentials() -> Optional[Credentials]:
    """
    Carrega credenciais do Google Sheets a partir de arquivo JSON (Service Account).
    
    Espera uma variável de ambiente apontando para o arquivo JSON ou o JSON em si.
    Variáveis suportadas:
        - GOOGLE_SERVICE_ACCOUNT_JSON: Caminho do arquivo JSON
        - GOOGLE_SERVICE_ACCOUNT_JSON_CONTENT: Conteúdo do JSON (em string)
    
    Returns:
        Credentials: Objeto de credenciais autenticadas.
        None: Se as credenciais não estiverem disponíveis.
    """
    
    if not HAS_GSPREAD:
        return None
    
    try:
        # Tentar carregar de arquivo
        json_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if json_path and os.path.exists(json_path):
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            credentials = Credentials.from_service_account_file(json_path, scopes=scopes)
            return credentials
        
        # Tentar carregar de variável de ambiente com conteúdo JSON
        json_content = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_CONTENT")
        if json_content:
            import json as json_lib
            json_dict = json_lib.loads(json_content)
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            credentials = Credentials.from_service_account_info(json_dict, scopes=scopes)
            return credentials
        
        return None
    
    except Exception as e:
        print(f"⚠ Erro ao carregar credenciais do Google: {e}")
        return None


def save_to_sheets(
    timestamp: str,
    dataset_name: str,
    verdict: str
) -> bool:
    """
    Salva o resultado da análise no Google Sheets.
    
    Operações:
        1. Autentica com Service Account
        2. Abre a planilha especificada (via GOOGLE_SHEETS_ID)
        3. Acessa a primeira aba
        4. Anexa uma linha com: [timestamp, dataset_name, verdict]
    
    Args:
        timestamp: Data/hora da análise (ISO format).
        dataset_name: Nome do arquivo/dataset analisado.
        verdict: Veredito da IA (texto completo).
        
    Returns:
        bool: True se sucesso, False caso contrário.
    """
    
    if not HAS_GSPREAD:
        print("⚠ gspread não está instalado. Pulando salvamento no Sheets.")
        return False
    
    try:
        # Obter credenciais
        credentials = get_sheets_credentials()
        if not credentials:
            print("⚠ Credenciais do Google Sheets não configuradas.")
            return False
        
        # Obter ID da planilha
        sheet_id = os.getenv("GOOGLE_SHEETS_ID")
        if not sheet_id:
            print("⚠ GOOGLE_SHEETS_ID não configurado em .env")
            return False
        
        # Autenticar e abrir planilha
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.sheet1  # Primeira aba
        
        # Preparar linha
        new_row = [
            timestamp,
            dataset_name,
            verdict[:500]  # Limitar tamanho do veredito para caber na célula
        ]
        
        # Anexar linha
        worksheet.append_row(new_row)
        
        print(f"✓ Resultado salvo no Google Sheets com sucesso")
        return True
    
    except Exception as e:
        print(f"✗ Erro ao salvar no Google Sheets: {e}")
        return False


def save_fallback_csv(
    timestamp: str,
    dataset_name: str,
    verdict: str
) -> bool:
    """
    Salva resultado em arquivo CSV local como fallback.
    
    Operações:
        1. Verifica se arquivo resultados.csv existe
        2. Se não existe, cria com headers
        3. Anexa linha com dados

    Args:
        timestamp: Data/hora da análise.
        dataset_name: Nome do dataset.
        verdict: Veredito da IA.
        
    Returns:
        bool: True se sucesso, False caso contrário.
    """
    
    try:
        file_exists = os.path.exists(RESULTADOS_CSV)
        
        with open(RESULTADOS_CSV, mode="a", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            
            # Escrever headers se arquivo é novo
            if not file_exists:
                writer.writerow(FALLBACK_HEADERS)
            
            # Escrever linha de dados
            writer.writerow([
                timestamp,
                dataset_name,
                verdict[:500]  # Limitar tamanho
            ])
        
        print(f"✓ Fallback salvo em {RESULTADOS_CSV}")
        return True
    
    except Exception as e:
        print(f"✗ Erro ao salvar fallback CSV: {e}")
        return False


def load_resultados_csv() -> list:
    """
    Carrega histórico de resultados do arquivo CSV local.
    
    Returns:
        list: Lista de dicionários com histórico.
    """
    
    try:
        if not os.path.exists(RESULTADOS_CSV):
            return []
        
        with open(RESULTADOS_CSV, mode="r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            return list(reader) if reader else []
    
    except Exception as e:
        print(f"✗ Erro ao carregar histórico CSV: {e}")
        return []


# Exemplo de uso (descomente para testes locais)
if __name__ == "__main__":
    # Teste de fallback
    try:
        success = save_fallback_csv(
            timestamp=datetime.now().isoformat(),
            dataset_name="teste_cashback_exemplo",
            verdict="Recomendação: Escalar Grupo C para 100% do tráfego. Lucro 31% superior."
        )
        
        if success:
            print("\n✓ Teste de fallback completado")
            resultados = load_resultados_csv()
            print(f"Registros no fallback: {len(resultados)}")
    except Exception as e:
        print(f"✗ Erro: {e}")
