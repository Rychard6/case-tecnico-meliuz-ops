# Case Técnico - Automação de Testes A/B (Méliuz)

## O Problema

A análise manual de testes A/B de cashback exige consolidação financeira, leitura de variações por grupo e interpretação do impacto em lucro. Esse processo leva horas, depende de critérios individuais e pode gerar inconsistência na decisão de qual variante escalar.

## A Solução/Arquitetura

O projeto implementa um pipeline em Python para transformar CSVs operacionais em uma recomendação executiva de negócio.

Fluxo principal:

1. `Pandas` carrega o CSV, valida o schema e limpa valores financeiros em formatos inconsistentes.
2. O pipeline calcula compradores, vendas, comissão, cashback e lucro Méliuz por grupo de teste.
3. A `Gemini API` recebe as métricas consolidadas e retorna um veredito em Markdown baseado em lucro, volume e eficiência de cashback.
4. O relatório Markdown é salvo em `relatorios/relatorio_[nome_do_csv].md` para auditoria e compartilhamento.
5. `Gspread` registra a decisão no Google Sheets; se a credencial estiver ausente ou inválida, o resultado é persistido em `resultados.csv` como fallback local.

## Como Executar

### 1. Instalar dependências

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar o `.env`

Crie um arquivo `.env` na raiz do projeto com as chaves necessárias.

```bash
GEMINI_API_KEY="sua-chave-gemini"
GEMINI_MODEL="gemini-1.5-flash"

# Opcional: rota de contingência para LLM
OPENAI_API_KEY="sua-chave-openai"
OPENAI_MODEL="gpt-4o-mini"

# Google Sheets
GOOGLE_SHEETS_ID="id-da-planilha"
GOOGLE_SERVICE_ACCOUNT_JSON="caminho/para/service-account.json"

# Alternativa para ambientes sem arquivo físico
GOOGLE_SERVICE_ACCOUNT_JSON_CONTENT='{"type":"service_account",...}'
```

Para o Google Sheets funcionar, a planilha deve estar compartilhada com o e-mail da Service Account presente no JSON.

### 3. Executar o pipeline

```bash
python src/main.py --file data/dataset_01_parceiroA.csv
```

Execução sem envio ao Google Sheets:

```bash
python src/main.py --file data/dataset_01_parceiroA.csv --output local
```

Execução com menos logs no terminal:

```bash
python src/main.py --file data/dataset_01_parceiroA.csv --quiet
```

Execução dos testes unitários:

```bash
python -m unittest tests/test_pipeline.py
```

## Entradas e Saídas

### Entrada

Os arquivos de entrada devem ficar em `data/` e seguir o schema abaixo:

| Coluna | Descrição |
| --- | --- |
| `Data` | Data da observação do teste |
| `Grupos de usuários` | Grupo ou variante do teste A/B |
| `Parceiro` | Identificação do parceiro analisado |
| `compradores` | Quantidade de compradores no período |
| `comissão` | Comissão bruta gerada pelo parceiro |
| `cashback` | Cashback concedido aos usuários |
| `vendas totais` | Volume financeiro total de vendas |

Os datasets do case devem ser versionados junto com o repositório quando forem anonimizados ou próprios para avaliação técnica. Arquivos sensíveis devem permanecer fora do Git.

### Saídas

O pipeline gera os seguintes artefatos:

| Artefato | Finalidade |
| --- | --- |
| `relatorios/relatorio_[nome_do_csv].md` | Relatório executivo em Markdown com o veredito da IA |
| `Google Sheets` | Registro centralizado da decisão para acompanhamento operacional |
| `resultados.csv` | Fallback local quando a integração com Sheets não estiver disponível |

Quando o Google Sheets não estiver configurado, o status operacional do pipeline passa a indicar uso de fallback local. Se Sheets e CSV local falharem ao mesmo tempo, a execução retorna erro.

## Conclusão dos Testes

### Parceiro A
- **Vencedor: Grupo 1 (~4,2% de cashback).** Entregou o maior lucro líquido absoluto (R$ 404.711,00) e a melhor margem sobre comissão (63,42%).
- **Risco:** Esta variante reteve o menor volume total de compradores. Requer monitoramento de *churn* para garantir que não haja perda de *market share* para concorrentes mais agressivos.

### Parceiro B
- **Vencedor: Grupo 1 (4,0% de cashback).** Apresentou o cenário ideal de eficiência: maximizou o lucro líquido (R$ 286.570,00) e simultaneamente gerou o maior volume de vendas (GMV) e compradores.
- **Observação:** Detectada elasticidade negativa severa nas variantes superiores. O Grupo 3 (9% de cashback) reduziu o lucro em mais de 80% e ainda diminuiu o volume de vendas em 35%.

### Parceiro C
- **Vencedor: Grupo 1 (5,0% de cashback).** Manteve a operação rentável gerando R$ 34.769,00 de lucro líquido, com o maior volume de vendas entre as opções.
- **Observação:** O Grupo 2 (7% de cashback) operou no zero a zero (*breakeven*), repassando 100% da comissão ao usuário. Recomenda-se escalar o Grupo 1 imediatamente e, no futuro, testar taxas menores (3% a 4%) para encontrar o piso de elasticidade.