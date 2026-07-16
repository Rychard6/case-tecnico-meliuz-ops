import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

# Carrega variáveis antes de inicializar integrações externas.
load_dotenv()

from data_processor import process_csv_data
from llm_analyzer import analyze_with_llm
from sheets_integration import RESULTADOS_CSV, SHEETS_SUCCESS, save_fallback_csv, save_to_sheets


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "relatorios"


# Garante que a entrada seja um CSV válido antes de acionar o pipeline.
def validate_file_path(file_path: str) -> Path:
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
    
    if path.suffix.lower() != ".csv":
        raise ValueError(f"Arquivo deve ser CSV. Recebido: {path.suffix}")
    
    return path


# Mantém nomes de relatórios previsíveis e seguros para o sistema de arquivos.
def build_report_path(csv_file: Path) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", csv_file.stem).strip("._")
    report_name = f"relatorio_{safe_name or 'dataset'}.md"
    return REPORTS_DIR / report_name


# Materializa a decisão da IA para auditoria e compartilhamento executivo.
def save_markdown_report(csv_file: Path, verdict: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = build_report_path(csv_file)
    report_path.write_text(verdict.rstrip() + "\n", encoding="utf-8")
    return report_path


def orchestrate_pipeline(
    csv_file: Path,
    save_to_sheets_flag: bool = True,
    verbose: bool = True,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "file_name": csv_file.name,
        "data_processed": {},
        "llm_verdict": "",
        "persistence_status": "not_started",
        "report_path": "",
    }

    try:
        if verbose:
            print(f"\n[1/5] Processando arquivo: {csv_file.name}")

        processed_data = process_csv_data(str(csv_file))
        result["data_processed"] = processed_data

        if verbose:
            print("Dados processados com sucesso")
            print(f"Grupos encontrados: {list(processed_data.keys())}")

        if verbose:
            print("\n[2/5] Enviando dados para análise com IA")

        llm_verdict = analyze_with_llm(processed_data)
        result["llm_verdict"] = llm_verdict

        if verbose:
            print("Análise concluída com sucesso")
            print("\n[3/5] Salvando relatório Markdown")

        report_path = save_markdown_report(csv_file, llm_verdict)
        result["report_path"] = str(report_path)

        if verbose:
            print(f"Relatório salvo em: {report_path}")

        if save_to_sheets_flag:
            if verbose:
                print("\n[4/5] Enviando decisão para o Google Sheets")

            try:
                sheets_status = save_to_sheets(
                    timestamp=result["timestamp"],
                    dataset_name=csv_file.stem,
                    verdict=llm_verdict,
                )
                result["persistence_status"] = sheets_status

                if sheets_status == SHEETS_SUCCESS:
                    if verbose:
                        print("Resultado salvo no Google Sheets com sucesso")
                else:
                    if verbose:
                        print("Salvando fallback local")
                    if save_fallback_csv(result["timestamp"], csv_file.stem, llm_verdict):
                        result["status"] = "fallback_used"
                        result["persistence_status"] = "fallback_csv"
                        if verbose:
                            print(f"Fallback salvo em {RESULTADOS_CSV}")
                    else:
                        result["status"] = "error"
                        result["persistence_status"] = "fallback_failed"
                        result["error"] = "Falha ao persistir resultado no Sheets e no CSV local"
            except Exception as error:
                if verbose:
                    print(f"Erro ao salvar no Google Sheets: {error}")
                    print("Salvando fallback local")

                if save_fallback_csv(result["timestamp"], csv_file.stem, llm_verdict):
                    result["status"] = "fallback_used"
                    result["persistence_status"] = "fallback_csv"
                    if verbose:
                        print(f"Fallback salvo em {RESULTADOS_CSV}")
                else:
                    result["status"] = "error"
                    result["persistence_status"] = "fallback_failed"
                    result["error"] = str(error)
        else:
            result["persistence_status"] = "local_report_only"
            if verbose:
                print("\n[4/5] Integração com Google Sheets desativada")

        if verbose:
            print("\n[5/5] Consolidando retorno da análise\n")
            print("=" * 80)
            print("RELATORIO DE ANALISE A/B - CASHBACK")
            print("=" * 80)
            print(f"Dataset: {csv_file.name}")
            print(f"Data da Analise: {result['timestamp']}")
            print(f"Relatorio Markdown: {result['report_path']}")
            print("-" * 80)
            print("\nDADOS PROCESSADOS:\n")
            print(json.dumps(processed_data, indent=2, ensure_ascii=False))
            print("\n" + "-" * 80)
            print("\nVEREDITO DA IA:\n")
            print(llm_verdict)
            print("\n" + "=" * 80 + "\n")

        return result

    except FileNotFoundError as error:
        result["status"] = "error"
        result["error"] = str(error)
        if verbose:
            print(f"\nERRO: {error}")
        return result

    except ValueError as error:
        result["status"] = "error"
        result["error"] = str(error)
        if verbose:
            print(f"\nERRO de validação: {error}")
        return result

    except Exception as error:
        result["status"] = "error"
        result["error"] = str(error)
        if verbose:
            print(f"\nERRO inesperado: {error}")
        return result


def main() -> None:
    parser = argparse.ArgumentParser(
    description="Sistema de Análise A/B para Cashback (Méliuz)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
    python src/main.py --file data/dataset_01_parceiroA.csv
    python src/main.py --file data/dataset_02_parceiroB.csv --output sheets
    python src/main.py --file data/dataset_03_parceiroC.csv --output local --quiet
        """,
    )
    
    parser.add_argument(
        "--file",
        "-f",
        type=str,
        required=True,
        help="Caminho do arquivo CSV a ser analisado",
    )
    
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        choices=["sheets", "local"],
        default="sheets",
        help="Destino de saída: sheets ou local",
    )
    
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Executa sem logs detalhados no terminal",
    )
    
    args = parser.parse_args()
    
    try:
        csv_file = validate_file_path(args.file)
    except (FileNotFoundError, ValueError) as error:
        print(f"Erro ao validar arquivo: {error}", file=sys.stderr)
        sys.exit(1)

    save_to_sheets = (args.output == "sheets")
    verbose = not args.quiet
    
    result = orchestrate_pipeline(
        csv_file=csv_file,
        save_to_sheets_flag=save_to_sheets,
        verbose=verbose,
    )
    
    if result["status"] == "error":
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
