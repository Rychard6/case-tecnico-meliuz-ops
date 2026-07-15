"""
data_processor.py - Módulo responsável pela limpeza e processamento de dados CSV.

Responsabilidades:
    - Ler arquivo CSV
    - Limpar strings financeiras (R$, formatação brasileira)
    - Agrupar dados por "Grupos de usuários"
    - Calcular métricas finais (compradores, vendas, comissão, cashback, lucro)
    - Retornar dados estruturados em dicionário

Type Hints: Todas as funções possuem anotações de tipo.
Docstrings: Padrão Google.
"""

import re
from typing import Any, Dict

import pandas as pd
import json


REQUIRED_COLUMNS = [
    "Data",
    "Grupos de usuários",
    "Parceiro",
    "compradores",
    "comissão",
    "cashback",
    "vendas totais",
]


def clean_financial_string(value: Any) -> float:
    """
    Limpa strings financeiras em formato brasileiro e converte para float.
    
    Transforma:
        "R$ 1.234,56" -> 1234.56
        "R$ 1.516" -> 1516.0
        "1.516 R$" -> 1516.0
        "93.390 R$" -> 93390.0
        "  " ou "" -> 0.0
    
    Args:
        value: String contendo valor financeiro com R$, espaços, etc.
        
    Returns:
        float: Valor numérico limpo.
        
    Raises:
        ValueError: Se a conversão não for possível.
    """
    
    if pd.isna(value):
        return 0.0

    original_value = str(value)
    text = original_value.strip()

    if not text or text.lower() == "nan":
        return 0.0

    numeric_text = re.sub(r"[^0-9,.-]", "", text)
    if not numeric_text or numeric_text in {"-", ".", ",", "-.", "-,"}:
        return 0.0

    sign = "-" if numeric_text.startswith("-") else ""
    numeric_text = numeric_text.replace("-", "")

    if "," in numeric_text:
        normalized_value = numeric_text.replace(".", "").replace(",", ".")
    else:
        parts = numeric_text.split(".")
        has_thousand_groups = len(parts) > 1 and all(len(part) == 3 for part in parts[1:])
        normalized_value = "".join(parts) if has_thousand_groups else numeric_text

    try:
        return float(f"{sign}{normalized_value}")
    except ValueError as exc:
        raise ValueError(
            f"Não foi possível converter '{original_value}' para float"
        ) from exc


def validate_required_columns(df: pd.DataFrame) -> None:
    """
    Valida se o DataFrame contém todas as colunas obrigatórias do schema.

    Args:
        df: DataFrame com dados brutos do teste A/B.

    Raises:
        ValueError: Se alguma coluna obrigatória estiver ausente.
    """

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]

    if missing_columns:
        raise ValueError(
            f"Colunas esperadas faltando no CSV: {missing_columns}\n"
            f"Colunas encontradas: {list(df.columns)}"
        )


def load_and_validate_csv(file_path: str) -> pd.DataFrame:
    """
    Carrega um arquivo CSV e valida que as colunas esperadas existem.
    Tenta múltiplos encodings e separadores para maior robustez.
    """
    try:
        encodings = ["utf-8", "latin-1", "iso-8859-1", "cp1252"]
        df = None
        
        # Tenta descobrir o encoding e o separador (, ou ;)
        for encoding in encodings:
            for sep in [",", ";"]: 
                try:
                    temp_df = pd.read_csv(file_path, encoding=encoding, sep=sep)
                    # Se separou em mais de 1 coluna, achamos o formato certo!
                    if len(temp_df.columns) > 1:
                        df = temp_df
                        break
                except UnicodeDecodeError:
                    continue
            if df is not None:
                break
                
        if df is None:
            raise ValueError("Não foi possível ler o CSV com nenhuma codificação")
        
        # BLINDAGEM: Remove espaços em branco invisíveis dos nomes das colunas
        df.columns = df.columns.str.strip()
        
        validate_required_columns(df)
        return df
    
    except FileNotFoundError:
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {file_path}")
    except pd.errors.EmptyDataError:
        raise ValueError(f"Arquivo CSV vazio: {file_path}")


def process_dataframe_data(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    # ... (docstring original) ...
    validate_required_columns(df)
    df = df.copy()

    # BLINDAGEM: Limpa espaços do nome dos grupos e remove valores nulos
    df["Grupos de usuários"] = df["Grupos de usuários"].astype(str).str.strip()
    df = df[df["Grupos de usuários"].str.lower() != "nan"]

    # Limpar dados financeiros
    df["comissão_limpo"] = df["comissão"].apply(clean_financial_string)
    df["cashback_limpo"] = df["cashback"].apply(clean_financial_string)
    df["vendas_totais_limpo"] = df["vendas totais"].apply(clean_financial_string)

    validate_required_columns(df)
    df = df.copy()

    # Limpar dados financeiros
    df["comissão_limpo"] = df["comissão"].apply(clean_financial_string)
    df["cashback_limpo"] = df["cashback"].apply(clean_financial_string)
    df["vendas_totais_limpo"] = df["vendas totais"].apply(clean_financial_string)

    # Garantir que compradores é int
    df["compradores"] = pd.to_numeric(df["compradores"], errors="coerce").fillna(0).astype(int)

    # Agrupar por "Grupos de usuários" e calcular métricas
    grouped_data: Dict[str, Dict[str, Any]] = {}

    for grupo, group_df in df.groupby("Grupos de usuários"):
        total_compradores = int(group_df["compradores"].sum())
        total_vendas = float(group_df["vendas_totais_limpo"].sum())
        total_comissao = float(group_df["comissão_limpo"].sum())
        total_cashback = float(group_df["cashback_limpo"].sum())
        lucro_meliuz = total_comissao - total_cashback

        grouped_data[str(grupo)] = {
            "total_compradores": total_compradores,
            "total_vendas": round(total_vendas, 2),
            "total_comissao": round(total_comissao, 2),
            "total_cashback": round(total_cashback, 2),
            "lucro_meliuz": round(lucro_meliuz, 2)
        }

    if not grouped_data:
        raise ValueError("Nenhum dado foi processado do CSV")

    return grouped_data


def process_csv_data(file_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Processa dados brutos do CSV: leitura, limpeza e cálculo de métricas.

    Args:
        file_path: Caminho do arquivo CSV.

    Returns:
        Dict com métricas consolidadas por "Grupos de usuários".

    Raises:
        ValueError: Se arquivo ou dados não podem ser processados.
    """

    try:
        df = load_and_validate_csv(file_path)
        return process_dataframe_data(df)

    except (FileNotFoundError, ValueError, pd.errors.ParserError) as e:
        raise ValueError(f"Erro ao processar CSV ({file_path}): {e}")


def validate_processed_data(data: Dict[str, Dict[str, Any]]) -> bool:
    """
    Valida a estrutura dos dados processados.
    
    Args:
        data: Dicionário de dados processados.
        
    Returns:
        bool: True se estrutura é válida.
        
    Raises:
        ValueError: Se estrutura é inválida.
    """
    
    required_keys = {
        "total_compradores",
        "total_vendas",
        "total_comissao",
        "total_cashback",
        "lucro_meliuz"
    }
    
    for grupo, metrics in data.items():
        if not isinstance(metrics, dict):
            raise ValueError(f"Grupo '{grupo}' não é um dicionário")
        
        missing_keys = required_keys - set(metrics.keys())
        if missing_keys:
            raise ValueError(f"Grupo '{grupo}' faltam chaves: {missing_keys}")
        
        for key, value in metrics.items():
            if not isinstance(value, (int, float)):
                raise ValueError(
                    f"Grupo '{grupo}', chave '{key}': valor '{value}' não é numérico"
                )
    
    return True


# Exemplo de uso (descomente para testes locais)
if __name__ == "__main__":
    # Teste local
    try:
        data = process_csv_data("data/exemplo.csv")
        validate_processed_data(data)
        print("✓ Dados processados com sucesso:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"✗ Erro: {e}")
