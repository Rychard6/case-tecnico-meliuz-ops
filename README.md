# Sistema de Análise A/B para Cashback (Meliuz)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📋 Descrição do Projeto

Sistema automatizado que analisa testes A/B de cashback usando **Python**, **Pandas** e **IA (Gemini/GPT)** para responder:

> **"Qual variante de cashback devemos escalar para 100% do tráfego?"**

### Fluxo do Pipeline

```
CSV bruto
    ↓
[1] Processamento de Dados (Pandas)
    - Limpeza de strings financeiras (R$, formatação brasileira)
    - Cálculo de métricas por grupo
    ↓
[2] Análise com IA (LLM)
    - System prompt focado em rentabilidade
    - Análise comparativa entre variantes
    ↓
[3] Salvamento de Resultado
    - Google Sheets (primário)
    - Arquivo CSV local (fallback)
    ↓
[4] Relatório Final
    - Exibição em console (Markdown)
    - Veredito para decisão executiva
```

---

## 🚀 Quick Start

### 1. Clonar e Configurar

```bash
# Clone ou navegue até o projeto
cd automacao

# Crie um ambiente virtual
python -m venv venv

# Ative o ambiente
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Instale as dependências
pip install -r requirements.txt
```

### 2. Configurar Credenciais (`.env`)

```bash
# Copie o template
cp .env.example .env

# Edite o arquivo .env com suas credenciais
# (instruções detalhadas abaixo)
```

### 3. Executar Análise

```bash
# Análise simples (com salvamento no Sheets)
python src/main.py --file data/parceiro_A.csv

# Sem salvar no Sheets (apenas console)
python src/main.py --file data/parceiro_B.csv --output local

# Modo silencioso (sem logs verbosos)
python src/main.py --file data/parceiro_C.csv --quiet
```

---

## ⚙️ Configuração Detalhada

### Pré-requisitos

- **Python 3.10+** instalado
- Uma API de LLM (Google Gemini OU OpenAI)
- (Opcional) Acesso a Google Sheets via Service Account

### 1️⃣ Configurar LLM (Obrigatório)

#### Opção A: Google Gemini (Recomendado - Grátis)

1. Vá para [Google AI Studio](https://ai.google.dev/)
2. Clique em "Get API Key"
3. Copie a chave
4. Em `.env`, adicione:
   ```bash
   GEMINI_API_KEY="sua-chave-aqui"
   ```

#### Opção B: OpenAI (GPT-4)

1. Vá para [OpenAI API](https://platform.openai.com/api-keys)
2. Crie uma nova chave secreta
3. Em `.env`, adicione:
   ```bash
   OPENAI_API_KEY="sk-seu-token-aqui"
   ```

### 2️⃣ Configurar Google Sheets (Opcional)

Se você quer salvar resultados automaticamente em uma planilha:

#### Passo 1: Criar Service Account

1. Vá para [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto
3. Ative a API "Google Sheets API"
4. Vá para **IAM & Admin** → **Service Accounts**
5. Crie uma nova Service Account
6. Gere uma chave JSON e baixe o arquivo

#### Passo 2: Compartilhar Planilha

1. Crie uma planilha em [Google Sheets](https://sheets.google.com)
2. Copie o ID da URL: `https://docs.google.com/spreadsheets/d/{ID_AQUI}/edit`
3. Compartilhe a planilha com o email da Service Account (encontra-se no JSON)

#### Passo 3: Configurar `.env`

```bash
# Opção A: Apontar para arquivo JSON (local)
GOOGLE_SERVICE_ACCOUNT_JSON="/caminho/para/service-account-key.json"

# Opção B: Variável com conteúdo JSON (CI/CD)
GOOGLE_SERVICE_ACCOUNT_JSON_CONTENT='{"type":"service_account",...}'

# ID da planilha
GOOGLE_SHEETS_ID="seu-sheet-id-aqui"
```

---

## 📁 Estrutura do Projeto

```
automacao/
├── data/                          # Pasta para CSVs (entrada)
│   ├── parceiro_A.csv
│   ├── parceiro_B.csv
│   └── ...
├── src/
│   ├── __init__.py
│   ├── main.py                    # Orquestrador principal + CLI
│   ├── data_processor.py          # Limpeza e processamento de dados
│   ├── llm_analyzer.py            # Integração com IA (Gemini/OpenAI)
│   └── sheets_integration.py      # Salvamento em Sheets + fallback
├── .env                           # Credenciais (NÃO commitr no git!)
├── .env.example                   # Template de .env
├── .gitignore                     # Ignora .env, credenciais, etc
├── requirements.txt               # Dependências Python
├── README.md                      # Este arquivo
└── resultados.csv                 # Fallback local (gerado automaticamente)
```

---

## 📊 Schema do CSV de Entrada

Os arquivos CSV devem conter **exatamente** estas colunas:

| Coluna | Tipo | Exemplo | Notas |
|--------|------|---------|-------|
| `Data` | String | 2024-01-15 | Data do registro |
| `Grupos de usuários` | String | "Grupo A (Controle)" | Identificador do grupo |
| `Parceiro` | String | "Meliuz" | Nome do parceiro |
| `compradores` | Integer | 1234 | Quantidade de compradores |
| `comissão` | String | "R$ 5.000,00" | **Formatação brasileira** |
| `cashback` | String | "R$ 3.000,00" | **Formatação brasileira** |
| `vendas totais` | String | "R$ 50.000,00" | **Formatação brasileira** |

### ✅ Exemplo de CSV Válido

```csv
Data,Grupos de usuários,Parceiro,compradores,comissão,cashback,vendas totais
2024-01-15,Grupo A (Controle),Meliuz,1000,R$ 5.000,00,R$ 3.000,00,R$ 50.000,00
2024-01-15,Grupo B (10% Cashback),Meliuz,1100,R$ 5.500,00,R$ 5.500,00,R$ 55.000,00
2024-01-16,Grupo A (Controle),Meliuz,950,R$ 4.750,00,R$ 2.850,00,R$ 47.500,00
2024-01-16,Grupo B (10% Cashback),Meliuz,1080,R$ 5.400,00,R$ 5.400,00,R$ 54.000,00
```

---

## 🏃 Exemplos de Uso

### Análise Simples (com Google Sheets)

```bash
python src/main.py --file data/cashback_janeiro_2024.csv
```

**Output Esperado:**

```
[1/4] Processando arquivo: cashback_janeiro_2024.csv
✓ Dados processados com sucesso
  Grupos encontrados: ['Grupo A (Controle)', 'Grupo B (10% Cashback)']

[2/4] Enviando dados para análise com IA...
✓ Análise concluída com sucesso

[3/4] Salvando resultado no Google Sheets...
✓ Resultado salvo no Google Sheets com sucesso

[4/4] Gerando relatório final...

================================================================================
RELATÓRIO DE ANÁLISE A/B - CASHBACK
================================================================================
Dataset: cashback_janeiro_2024.csv
Data da Análise: 2024-01-20T14:32:15.123456

📊 DADOS PROCESSADOS:

{
  "Grupo A (Controle)": {
    "total_compradores": 1950,
    "total_vendas": 97500.0,
    "total_comissao": 9750.0,
    "total_cashback": 5850.0,
    "lucro_meliuz": 3900.0
  },
  "Grupo B (10% Cashback)": {
    "total_compradores": 2180,
    "total_vendas": 109000.0,
    "total_comissao": 10900.0,
    "total_cashback": 10900.0,
    "lucro_meliuz": 0.0
  }
}

────────────────────────────────────────────────────────────────────────────────

🤖 VEREDITO DA IA:

## 📊 Resumo Executivo
Teste A/B realizado para otimizar cashback em janeiro/2024, com 2 grupos...

## 📈 Análise Comparativa
| Métrica | Grupo A (Controle) | Grupo B (10% Cashback) |
|---------|-------------------|----------------------|
| Compradores | 1.950 | 2.180 |
| Vendas | R$ 97.500,00 | R$ 109.000,00 |
| Lucro Meliuz | R$ 3.900,00 | R$ 0,00 |

## 🎯 Veredito Final
**ESCALAR: Grupo A (Controle)**
- Maior lucro Meliuz (R$ 3.900 vs R$ 0)
- Eficiência de cashback: 6% vs 10%
- Confiança: **Alta**

## ⚡ Próximos Passos
1. Monitore redução de churn no Grupo B
2. Teste Grupo C com 7% de cashback

================================================================================
```

### Análise sem Google Sheets

```bash
python src/main.py --file data/teste_B.csv --output local
```

(Apenas exibe o relatório, não salva em Sheets)

### Modo Silencioso

```bash
python src/main.py --file data/teste_C.csv --quiet
```

(Executa sem logs verbosos, apenas resultado final)

---

## 🔧 Tratamento de Erros

### Erro: `GEMINI_API_KEY not found`

**Solução:**
1. Verifique se `.env` existe na raiz do projeto
2. Adicione a chave: `GEMINI_API_KEY="sua-chave-aqui"`
3. Re-execute o script

### Erro: `Arquivo não encontrado`

**Solução:**
1. Verifique se o caminho está correto: `python src/main.py --file data/seu_arquivo.csv`
2. O arquivo CSV deve estar em `data/`

### Erro: `Colunas esperadas faltando`

**Solução:**
1. Verifique o schema do CSV (seção "Schema do CSV de Entrada")
2. Certifique-se de que as colunas têm **exatamente** esses nomes

### Erro ao Salvar no Google Sheets (Fallback Ativado)

Se o sistema não conseguir acessar Google Sheets, ele **automaticamente** salva em `resultados.csv` (arquivo local). Nada é perdido! ✅

---

## 📈 Saída do Sistema

O sistema gera dois tipos de saída:

### 1. Console (Markdown Formatado)

Relatório completo com:
- Resumo executivo
- Análise comparativa entre grupos
- Veredito final com recomendação
- Próximos passos

### 2. Google Sheets (ou CSV Local)

Adiciona uma linha com:
- **Data Análise**: `2024-01-20T14:32:15.123456`
- **Dataset**: `cashback_janeiro_2024`
- **Veredito IA**: Resumo da recomendação

---

## 🛠️ Desenvolvimento

### Executar Testes Unitários

```bash
python -m unittest tests/test_pipeline.py
```

### Adicionar Novo Processamento

1. Edite `src/data_processor.py`
2. Crie nova função com type hints
3. Importe em `main.py`

### Melhorar System Prompt do LLM

Edite `get_system_prompt()` em `src/llm_analyzer.py`

---

## 📝 Notas Importantes

### Segurança

- **Nunca** comite `.env` no Git
- Use `.gitignore` para ignorar arquivos sensíveis
- Rotação regular de API keys recomendada

### Performance

- Para CSVs grandes (>100MB), considere processar em chunks
- Limite de tokens do LLM: ~2000 tokens de output

### Custo

- **Gemini**: Grátis até limite mensal
- **OpenAI**: ~$0.02 por análise (dependendo do modelo)
- **Google Sheets**: Grátis (precisa apenas de conta Google)

---

## 🤝 Contribuição

Se encontrar bugs ou tiver sugestões de melhoria:

1. Reporte em GitHub Issues
2. Faça fork e crie feature branch
3. Submit pull request

---

## 📄 Licença

MIT License - Veja [LICENSE](LICENSE) para detalhes

---

## 📞 Suporte

- **Email**: seu-email@meliuz.com
- **Slack**: #automacao-cashback
- **Docs**: [Wiki do Projeto](https://wiki.meliuz.com/...)

---

**Versão**: 1.0.0  
**Última Atualização**: 2024-01-20  
**Desenvolvido por**: Engineering Team (Meliuz)
