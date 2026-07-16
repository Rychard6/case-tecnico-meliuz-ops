# Consolida dados brutos de cashback em métricas confiáveis para decisão.

import json
import re
from typing import Any, Dict

import pandas as pd


REQUIRED_COLUMNS = [
    "Data",
    "Grupos de usuários",
    "Parceiro",
    "compradores",
    "comissão",
    "cashback",
    "vendas totais",
]


# Normaliza valores financeiros exportados em formatos inconsistentes.
def clean_financial_string(value: Any) -> float:
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


# Bloqueia arquivos fora do schema antes de calcular métricas executivas.
def validate_required_columns(df: pd.DataFrame) -> None:
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]

    if missing_columns:
        raise ValueError(
            f"Colunas esperadas faltando no CSV: {missing_columns}\n"
            f"Colunas encontradas: {list(df.columns)}"
        )


# Aceita variações comuns de encoding e separador vindas de exportações manuais.
def load_and_validate_csv(file_path: str) -> pd.DataFrame:
    try:
        encodings = ["utf-8", "latin-1", "iso-8859-1", "cp1252"]
        df = None

        for encoding in encodings:
            for sep in [",", ";"]:
                try:
                    temp_df = pd.read_csv(file_path, encoding=encoding, sep=sep)
                    if len(temp_df.columns) > 1:
                        df = temp_df
                        break
                except UnicodeDecodeError:
                    continue
            if df is not None:
                break

        if df is None:
            raise ValueError("Não foi possível ler o CSV com nenhuma codificação")

        df.columns = df.columns.str.strip()

        validate_required_columns(df)
        return df

    except FileNotFoundError:
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {file_path}")
    except pd.errors.EmptyDataError:
        raise ValueError(f"Arquivo CSV vazio: {file_path}")


# Agrega o teste por grupo e calcula o lucro líquido de cashback.
def process_dataframe_data(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    validate_required_columns(df)
    df = df.copy()

    df["Grupos de usuários"] = df["Grupos de usuários"].astype(str).str.strip()
    df = df[df["Grupos de usuários"].str.lower() != "nan"]

    df["comissão_limpo"] = df["comissão"].apply(clean_financial_string)
    df["cashback_limpo"] = df["cashback"].apply(clean_financial_string)
    df["vendas_totais_limpo"] = df["vendas totais"].apply(clean_financial_string)

    df["compradores"] = pd.to_numeric(df["compradores"], errors="coerce").fillna(0).astype(int)

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


# Entrega a estrutura consumida pela camada de LLM.
def process_csv_data(file_path: str) -> Dict[str, Dict[str, Any]]:
    try:
        df = load_and_validate_csv(file_path)
        return process_dataframe_data(df)

    except (FileNotFoundError, ValueError, pd.errors.ParserError) as e:
        raise ValueError(f"Erro ao processar CSV ({file_path}): {e}")


# Protege integrações posteriores contra estruturas incompletas.
def validate_processed_data(data: Dict[str, Dict[str, Any]]) -> bool:
    required_keys = {
        "total_compradores",
        "total_vendas",
        "total_comissao",
        "total_cashback",
        "lucro_meliuz",
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


if __name__ == "__main__":
    try:
        data = process_csv_data("data/exemplo.csv")
        validate_processed_data(data)
        print("Dados processados com sucesso:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as error:
        print(f"Erro: {error}")
