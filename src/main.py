import argparse
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import json
from datetime import datetime

# 1. Importar o load_dotenv
from dotenv import load_dotenv

# 2. Carregar o arquivo .env IMEDIATAMENTE antes de chamar nossos próprios módulos
load_dotenv()

# 3. Importações dos módulos do projeto (agora eles vão enxergar a chave!)
from data_processor import process_csv_data
from llm_analyzer import analyze_with_llm
from sheets_integration import RESULTADOS_CSV, save_to_sheets, save_fallback_csv
from llm_analyzer import analyze_with_llm
from sheets_integration import RESULTADOS_CSV, save_to_sheets, save_fallback_csv


def validate_file_path(file_path: str) -> Path:
    """
    Valida se o arquivo CSV existe e é acessível.
    
    Args:
        file_path: Caminho do arquivo CSV (string).
        
    Returns:
        Path: Objeto pathlib.Path do arquivo validado.
        
    Raises:
        FileNotFoundError: Se o arquivo não existe.
        ValueError: Se o arquivo não tem extensão .csv.
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
    
    if path.suffix.lower() != ".csv":
        raise ValueError(f"Arquivo deve ser CSV. Recebido: {path.suffix}")
    
    return path


def orchestrate_pipeline(
    csv_file: Path,
    save_to_sheets_flag: bool = True,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Orquestra o pipeline completo de análise A/B para cashback.
    
    Fluxo:
        1. Lê e processa dados do CSV
        2. Envia para LLM para análise
        3. Salva resultado no Google Sheets (ou fallback local)
        4. Retorna relatório final
    
    Args:
        csv_file: Path do arquivo CSV.
        save_to_sheets_flag: Se True, salva resultado no Google Sheets.
        verbose: Se True, imprime logs detalhados no console.
        
    Returns:
        Dict contendo:
            - "status": "success" ou "error"
            - "data_processed": dados processados
            - "llm_verdict": veredito da IA
            - "timestamp": data/hora da execução
            - "file_name": nome do arquivo processado
    """
    
    result = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "file_name": csv_file.name,
        "data_processed": {},
        "llm_verdict": ""
    }
    
    try:
        # ============= ETAPA 1: PROCESSAMENTO DE DADOS =============
        if verbose:
            print(f"\n[1/4] Processando arquivo: {csv_file.name}")
        
        processed_data = process_csv_data(str(csv_file))
        result["data_processed"] = processed_data
        
        if verbose:
            print(f"✓ Dados processados com sucesso")
            print(f"  Grupos encontrados: {list(processed_data.keys())}")
        
        
        # ============= ETAPA 2: ANÁLISE COM LLM =============
        if verbose:
            print(f"\n[2/4] Enviando dados para análise com IA...")
        
        llm_verdict = analyze_with_llm(processed_data)
        result["llm_verdict"] = llm_verdict
        
        if verbose:
            print(f"✓ Análise concluída com sucesso")
        
        
        # ============= ETAPA 3: SALVAMENTO NO SHEETS =============
        if save_to_sheets_flag:
            if verbose:
                print(f"\n[3/4] Salvando resultado no Google Sheets...")
            
            try:
                success = save_to_sheets(
                    timestamp=result["timestamp"],
                    dataset_name=csv_file.stem,
                    verdict=llm_verdict
                )
                
                if success and verbose:
                    print(f"✓ Resultado salvo no Google Sheets com sucesso")
                elif not success and verbose:
                    print(f"⚠ Falha ao salvar no Sheets. Salvando fallback local...")
                    save_fallback_csv(
                        timestamp=result["timestamp"],
                        dataset_name=csv_file.stem,
                        verdict=llm_verdict
                    )
                    print(f"✓ Fallback salvo em {RESULTADOS_CSV}")
            except Exception as e:
                if verbose:
                    print(f"⚠ Erro ao salvar no Sheets: {e}")
                    print(f"  Salvando fallback local...")
                
                try:
                    save_fallback_csv(
                        timestamp=result["timestamp"],
                        dataset_name=csv_file.stem,
                        verdict=llm_verdict
                    )
                    if verbose:
                        print(f"✓ Fallback salvo em {RESULTADOS_CSV}")
                except Exception as fallback_error:
                    if verbose:
                        print(f"✗ Erro ao salvar fallback: {fallback_error}")
                    result["status"] = "partial"
        else:
            if verbose:
                print(f"\n[3/4] Salvamento em Sheets desativado (--output local)")
        
        
        # ============= ETAPA 4: RELATÓRIO FINAL =============
        if verbose:
            print(f"\n[4/4] Gerando relatório final...\n")
            print("=" * 80)
            print(f"RELATÓRIO DE ANÁLISE A/B - CASHBACK")
            print("=" * 80)
            print(f"Dataset: {csv_file.name}")
            print(f"Data da Análise: {result['timestamp']}")
            print("-" * 80)
            print("\n📊 DADOS PROCESSADOS:\n")
            print(json.dumps(processed_data, indent=2, ensure_ascii=False))
            print("\n" + "-" * 80)
            print("\n🤖 VEREDITO DA IA:\n")
            print(llm_verdict)
            print("\n" + "=" * 80 + "\n")
        
        return result
    
    except FileNotFoundError as e:
        result["status"] = "error"
        result["error"] = str(e)
        if verbose:
            print(f"\n✗ ERRO: {e}")
        return result
    
    except ValueError as e:
        result["status"] = "error"
        result["error"] = str(e)
        if verbose:
            print(f"\n✗ ERRO de validação: {e}")
        return result
    
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        if verbose:
            print(f"\n✗ ERRO inesperado: {e}")
        return result


def main() -> None:
    """
    Função principal. Configura argparse e inicia o pipeline.
    """
    
    parser = argparse.ArgumentParser(
        description="Sistema de Análise A/B para Cashback (Meliuz)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python src/main.py --file data/parceiro_A.csv
  python src/main.py --file data/parceiro_B.csv --output sheets
  python src/main.py --file data/parceiro_C.csv --output local --quiet
        """
    )
    
    parser.add_argument(
        "--file",
        "-f",
        type=str,
        required=True,
        help="Caminho do arquivo CSV a ser analisado (ex: data/parceiro_A.csv)"
    )
    
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        choices=["sheets", "local"],
        default="sheets",
        help="Destino de saída: 'sheets' (Google Sheets) ou 'local' (apenas console)"
    )
    
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Desativa verbose mode (não imprime logs detalhados)"
    )
    
    args = parser.parse_args()
    
    # Validar arquivo
    try:
        csv_file = validate_file_path(args.file)
    except (FileNotFoundError, ValueError) as e:
        print(f"✗ Erro ao validar arquivo: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Executar pipeline
    save_to_sheets = (args.output == "sheets")
    verbose = not args.quiet
    
    result = orchestrate_pipeline(
        csv_file=csv_file,
        save_to_sheets_flag=save_to_sheets,
        verbose=verbose
    )
    
    # Retornar código de saída apropriado
    if result["status"] == "error":
        sys.exit(1)
    elif result["status"] == "partial":
        sys.exit(0)  # Sucesso parcial
    else:
        sys.exit(0)  # Sucesso completo


if __name__ == "__main__":
    main()
