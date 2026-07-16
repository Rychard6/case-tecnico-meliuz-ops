# Centraliza a chamada às LLMs para transformar métricas em recomendação executiva.

import os
from typing import Any, Dict

from dotenv import load_dotenv

# Carrega chaves locais sem exigir acoplamento com a CLI.
load_dotenv()

# Permite executar com Gemini ou OpenAI conforme dependências instaladas.
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


class MissingLLMConfigurationError(RuntimeError):
    pass


GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def get_system_prompt() -> str:
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

1. **Resumo Executivo**
   - Objetivo do teste
   - Grupos testados
   - Período de análise (se disponível)

2. **Análise Comparativa**
   - Tabela com métricas de cada grupo
   - Destaques e anomalias

3. **Veredito Final**
   - Qual variante vencer
   - Por qual razão (baseado nos critérios)
   - Confiança da recomendação (Alta/Média/Baixa)
   - Riscos identificados (se houver)

4. **Próximos Passos**
   - Recomendações de monitoramento
   - Testes sugeridos para futuro

**Tom:** Profissional, direto e focado em números. Não use emojis, slogans ou linguagem promocional.
"""


# Organiza as métricas de negócio para reduzir ambiguidade na decisão da LLM.
def format_data_for_llm(data: Dict[str, Dict[str, Any]]) -> str:
    text = "**DADOS DO TESTE A/B (CASHBACK):**\n\n"
    
    for i, (grupo, metrics) in enumerate(data.items(), 1):
        text += f"### Grupo {i}: {grupo}\n\n"
        text += f"- **Total de Compradores:** {metrics['total_compradores']:,}\n"
        text += f"- **Total de Vendas:** R$ {metrics['total_vendas']:,.2f}\n"
        text += f"- **Total de Comissão:** R$ {metrics['total_comissao']:,.2f}\n"
        text += f"- **Total de Cashback:** R$ {metrics['total_cashback']:,.2f}\n"
        text += f"- **Lucro Meliuz (comissão - cashback):** R$ {metrics['lucro_meliuz']:,.2f}\n"
        
        # Expõe eficiência para a decisão não depender apenas de volume bruto.
        if metrics['total_vendas'] > 0:
            taxa_cashback = (metrics['total_cashback'] / metrics['total_vendas']) * 100
            roi = (metrics['lucro_meliuz'] / metrics['total_vendas']) * 100
            text += f"- **Taxa de Cashback:** {taxa_cashback:.2f}% das vendas\n"
            text += f"- **ROI Meliuz:** {roi:.2f}% das vendas\n"
        
        text += "\n"
    
    return text


# Executa a análise principal quando a chave do Gemini está disponível.
def call_gemini_api(data: Dict[str, Dict[str, Any]]) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise MissingLLMConfigurationError(
            "GEMINI_API_KEY não encontrada nas variáveis de ambiente. "
            "Configure em .env"
        )
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)
    
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
    
    except Exception as error:
        raise RuntimeError(f"Erro ao chamar API Gemini: {error}") from error


# Mantém uma segunda rota de LLM para contingência operacional.
def call_openai_api(data: Dict[str, Dict[str, Any]]) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise MissingLLMConfigurationError(
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
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=2048,
            top_p=0.95
        )
        
        return response.choices[0].message.content
    
    except Exception as error:
        raise RuntimeError(f"Erro ao chamar API OpenAI: {error}") from error


# Escolhe a melhor integração disponível sem exigir troca no restante do pipeline.
def analyze_with_llm(data: Dict[str, Dict[str, Any]]) -> str:
    if not isinstance(data, dict) or not data:
        raise ValueError("Dados inválidos ou vazios para análise")

    if HAS_GEMINI:
        try:
            return call_gemini_api(data)
        except MissingLLMConfigurationError:
            pass
        except Exception as error:
            print(f"Gemini falhou: {error}. Tentando OpenAI.")

    if HAS_OPENAI:
        try:
            return call_openai_api(data)
        except MissingLLMConfigurationError:
            pass
        except Exception as error:
            print(f"OpenAI falhou: {error}")

    raise RuntimeError(
        "Nenhuma API de LLM disponível. Configure GEMINI_API_KEY ou OPENAI_API_KEY em .env"
    )


if __name__ == "__main__":
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
        print("Análise gerada com sucesso:")
        print(verdict)
    except Exception as error:
        print(f"Erro: {error}")
