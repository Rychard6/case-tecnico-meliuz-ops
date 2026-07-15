"""
llm_analyzer.py - Módulo responsável pela análise com IA (LLM).

Responsabilidades:
    - Receber dados processados
    - Criar system prompt forte (Head de Operações, foco em lucro)
    - Chamar API do LLM (Google Gemini ou OpenAI)
    - Retornar análise em Markdown com veredito final

Type Hints: Todas as funções possuem anotações de tipo.
Docstrings: Padrão Google.
"""

import os
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Importações condicionais baseadas na API disponível
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


def get_system_prompt() -> str:
    """
    Retorna um system prompt forte para o LLM atuar como Head de Operações.
    
    O prompt define:
        - Papel: Head de Operações focado em rentabilidade
        - Objetivo: Recomendar qual variante escalar para 100% do tráfego
        - Métricas principais: Lucro Meliuz, Volume de Vendas, ROI
        - Formato de saída: Markdown estruturado
    
    Returns:
        str: System prompt completo.
    """
    
    return """
Você é um **Head de Operações sênior** focado em rentabilidade e escalabilidade.

Sua missão é analisar dados de testes A/B de cashback e fornecer uma recomendação clara sobre qual variante deve ser escalada para 100% do tráfego.

**Critérios de Decisão (em ordem de prioridade):**
1. **Lucro Meliuz (comissão - cashback)**: Maior lucro líquido é melhor.
2. **Volume de Vendas**: Variantes que mantêm alto volume enquanto aumentam lucro são preferidas.
3. **Eficiência de Cashback**: Taxa de cashback por venda (cashback / vendas). Menor = mais eficiente.
4. **Número de Compradores**: Validar que a variante não está alienando clientes.

**Formato de Resposta (OBRIGATÓRIO):**
Retorne um relatório em Markdown com estas seções:

1. **📊 Resumo Executivo**
   - Objetivo do teste
   - Grupos testados
   - Período de análise (se disponível)

2. **📈 Análise Comparativa**
   - Tabela com métricas de cada grupo
   - Destaques e anomalias

3. **🎯 Veredito Final**
   - Qual variante vencer
   - Por qual razão (baseado nos critérios)
   - Confiança da recomendação (Alta/Média/Baixa)
   - Riscos identificados (se houver)

4. **⚡ Próximos Passos**
   - Recomendações de monitoramento
   - Testes sugeridos para futuro

**Tom:** Profissional, direto e focado em números. Use emojis para destacar seções, mas mantenha a credibilidade analítica.
"""


def format_data_for_llm(data: Dict[str, Dict[str, Any]]) -> str:
    """
    Formata os dados processados em um texto bem estruturado para enviar ao LLM.
    
    Args:
        data: Dicionário com dados agrupados por "Grupos de usuários".
        
    Returns:
        str: String formatada com as métricas organizadas.
    """
    
    text = "**DADOS DO TESTE A/B (CASHBACK):**\n\n"
    
    for i, (grupo, metrics) in enumerate(data.items(), 1):
        text += f"### Grupo {i}: {grupo}\n\n"
        text += f"- **Total de Compradores:** {metrics['total_compradores']:,}\n"
        text += f"- **Total de Vendas:** R$ {metrics['total_vendas']:,.2f}\n"
        text += f"- **Total de Comissão:** R$ {metrics['total_comissao']:,.2f}\n"
        text += f"- **Total de Cashback:** R$ {metrics['total_cashback']:,.2f}\n"
        text += f"- **Lucro Meliuz (comissão - cashback):** R$ {metrics['lucro_meliuz']:,.2f}\n"
        
        # Calcular taxas adicionais para facilitar análise
        if metrics['total_vendas'] > 0:
            taxa_cashback = (metrics['total_cashback'] / metrics['total_vendas']) * 100
            roi = (metrics['lucro_meliuz'] / metrics['total_vendas']) * 100
            text += f"- **Taxa de Cashback:** {taxa_cashback:.2f}% das vendas\n"
            text += f"- **ROI Meliuz:** {roi:.2f}% das vendas\n"
        
        text += "\n"
    
    return text


def call_gemini_api(data: Dict[str, Dict[str, Any]]) -> str:
    """
    Chama a API do Google Gemini para análise.
    
    Args:
        data: Dicionário com dados processados.
        
    Returns:
        str: Resposta do LLM em Markdown.
        
    Raises:
        RuntimeError: Se a API key não estiver configurada.
        Exception: Se a chamada à API falhar.
    """
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY não encontrada nas variáveis de ambiente. "
            "Configure em .env"
        )
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3-flash-preview")
    
    system_prompt = get_system_prompt()
    formatted_data = format_data_for_llm(data)
    
    user_message = f"""
{formatted_data}

Com base nesses dados, forneça uma análise detalhada seguindo o formato especificado no system prompt.
"""
    
    try:
        response = model.generate_content(
            f"{system_prompt}\n\n{user_message}",
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
        )
        
        return response.text
    
    except Exception as e:
        raise Exception(f"Erro ao chamar API Gemini: {e}")


def call_openai_api(data: Dict[str, Dict[str, Any]]) -> str:
    """
    Chama a API da OpenAI (GPT) para análise.
    
    Args:
        data: Dicionário com dados processados.
        
    Returns:
        str: Resposta do LLM em Markdown.
        
    Raises:
        RuntimeError: Se a API key não estiver configurada.
        Exception: Se a chamada à API falhar.
    """
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY não encontrada nas variáveis de ambiente. "
            "Configure em .env"
        )
    
    client = OpenAI(api_key=api_key)
    
    system_prompt = get_system_prompt()
    formatted_data = format_data_for_llm(data)
    
    user_message = f"""
{formatted_data}

Com base nesses dados, forneça uma análise detalhada seguindo o formato especificado.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=2048,
            top_p=0.95
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        raise Exception(f"Erro ao chamar API OpenAI: {e}")


def analyze_with_llm(data: Dict[str, Dict[str, Any]]) -> str:
    """
    Orquestra a análise com LLM, tentando APIs na ordem: Gemini > OpenAI.
    
    Args:
        data: Dicionário com dados processados por `process_csv_data`.
        
    Returns:
        str: Análise completa em formato Markdown.
        
    Raises:
        RuntimeError: Se nenhuma API estiver configurada.
        Exception: Se ambas as APIs falharem.
    """
    
    # Validar dados de entrada
    if not isinstance(data, dict) or not data:
        raise ValueError("Dados inválidos ou vazios para análise")
    
    # Tentar Gemini primeiro
    if HAS_GEMINI:
        try:
            return call_gemini_api(data)
        except RuntimeError:
            pass  # API key não configurada, tentar próxima
        except Exception as e:
            print(f"⚠ Gemini falhou: {e}. Tentando OpenAI...")
    
    # Tentar OpenAI depois
    if HAS_OPENAI:
        try:
            return call_openai_api(data)
        except RuntimeError:
            pass  # API key não configurada
        except Exception as e:
            print(f"⚠ OpenAI falhou: {e}")
    
    # Se nenhuma API funcionou
    raise RuntimeError(
        "Nenhuma API de LLM disponível. Configure GEMINI_API_KEY ou OPENAI_API_KEY em .env"
    )


# Exemplo de uso (descomente para testes locais)
if __name__ == "__main__":
    # Dados de exemplo para teste
    sample_data = {
        "Grupo A (Controle)": {
            "total_compradores": 1000,
            "total_vendas": 50000.00,
            "total_comissao": 5000.00,
            "total_cashback": 3000.00,
            "lucro_meliuz": 2000.00
        },
        "Grupo B (10% Cashback)": {
            "total_compradores": 1100,
            "total_vendas": 55000.00,
            "total_comissao": 5500.00,
            "total_cashback": 5500.00,
            "lucro_meliuz": 0.00
        },
        "Grupo C (5% Cashback)": {
            "total_compradores": 1050,
            "total_vendas": 52500.00,
            "total_comissao": 5250.00,
            "total_cashback": 2625.00,
            "lucro_meliuz": 2625.00
        }
    }
    
    try:
        verdict = analyze_with_llm(sample_data)
        print("✓ Análise gerada com sucesso:")
        print(verdict)
    except Exception as e:
        print(f"✗ Erro: {e}")
