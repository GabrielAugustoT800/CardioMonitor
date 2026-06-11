# blua-cardio

Plataforma cardiovascular integrada num servidor Dash multi-pages único:
chatbot multi-agente (LangGraph, pt-BR) + dashboard de telemetria PPG/BPM
ao vivo de ESP32 + MAX30100.

## Stack

- **Python** 3.10 ou superior (testado em 3.10/3.11/3.12/3.14)
- **LangGraph** + **Qwen** via DashScope (cloud) ou Ollama (local)
- **Dash** + dash-bootstrap-components (UI multi-pages)
- **ChromaDB** + sentence-transformers (RAG)
- **pandas** + plotly (telemetria)
- **pytest** (67 testes)

## Pré-requisitos

- Python 3.10+
- Git
- ~500 MB de disco (chroma_db + modelos HF cached)
- Chave de API da [DashScope International](https://dashscope-intl.console.alibabacloud.com)
  (free tier $10 de boas-vindas)
- Opcional: [Ollama](https://ollama.com) instalado localmente se preferir
  modo offline
- Opcional: `AZURE_STORAGE_CONNECTION_STRING` para `/monitor` e `/analise`
  consumirem Blob real (sem esta var, fallback CSV local é automático)

## Setup

### 1. Clonar e entrar no projeto

```bash
git clone https://github.com/luke-meireles/blua-cardio.git
cd blua-cardio
```

### 2. Criar ambiente virtual + instalar dependências

```bash
# Linux/Mac
python -m venv venv
source venv/bin/activate

# Windows PowerShell
python -m venv venv
venv\Scripts\Activate.ps1

# Windows CMD/Git Bash
python -m venv venv
venv\Scripts\activate
```

Em seguida (com o venv ativo):

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> Tempo estimado: 2–5 minutos. Instala dash, langgraph, chromadb,
> sentence-transformers, plotly, pandas e demais deps.

### 3. Configurar segredos (`.env`)

```bash
# Linux/Mac
cp .env.example .env

# Windows
copy .env.example .env
```

Edite `.env` e preencha **no mínimo** `DASHSCOPE_API_KEY` com sua chave
da DashScope. As demais variáveis têm defaults sensatos.

> Se preferir rodar offline, mude `LLM_BACKEND=ollama` no `.env` e
> instale o Qwen local: `ollama pull qwen2.5:14b`.

### 4. Popular o banco vetorial RAG (uma vez)

```bash
python -m src.rag.indexer
```

Isso indexa os 12 documentos cardiovasculares de `knowledge_base/`
no ChromaDB local (`chroma_db/`). Resultado: ~132 chunks em ~30 s a 1 min.

> Na primeira execução, sentence-transformers baixa o modelo
> `all-MiniLM-L6-v2` (~80 MB, cached em `~/.cache/huggingface/`).
> Para reindexar do zero: `python -m src.rag.indexer --force`.

### 5. Rodar - Gerador de IBI

```bash
python simulador/gerador_ibi.py
```

Utilize para inicializar o fluxo de IBIs e arritmias gerado aleatoriamente pelo gerador de IBIs

### 5.1 Rodar - Iniciar o Dashboard

```bash
python dashboard/app.py
```

Acesse `http://localhost:8050` no browser. Na primeira execução, o
cross-encoder do reranker (`ms-marco-MiniLM-L-6-v2`, ~80 MB) também
é baixado.

## Rotas disponíveis

| Rota | Conteúdo |
|------|----------|
| `/` | Home (overview + KPIs agregados) |
| `/monitor` | Telemetria PPG ao vivo (ESP32 + MAX30100) |
| `/analise` | Análise histórica do CSV/Blob de telemetria |
| `/gabriel` | Prontuário do paciente Gabriel Oliveira (FA paroxística) |
| `/meu-perfil` | Formulário de criação de perfil → prontuário saudável |
| `/chat` | Chatbot LangGraph multi-agente |
| `/pacientes` | Lista do registry de beneficiários com refresh dinâmico |

## Modo produção

```bash
gunicorn -w 1 -b 0.0.0.0:8050 dashboard.app:server
```

> Use `-w 1` (um worker) porque o LangGraph `MemorySaver` é
> in-memory e não compartilhado entre workers.

## CLI alternativo (sem UI Dash)

Para testar o grafo direto no terminal:

```bash
python main.py --interativo                                # modo conversa
python main.py --once "Como está meu ritmo cardíaco?"      # 1 turno só
python main.py --beneficiario BENEF-002 --once "..."       # outro paciente
python main.py --smoke                                     # bateria de cenários
```

## Variáveis de ambiente

| Variável | Default | Uso |
|----------|---------|-----|
| `DASHSCOPE_API_KEY` | — (**obrigatória** em modo dashscope) | Chave da API DashScope/Qwen |
| `LLM_BACKEND` | `dashscope` | `dashscope` (cloud) ou `ollama` (local) |
| `QWEN_DASHSCOPE_MODEL` | `qwen-plus` | Modelo Qwen via DashScope |
| `QWEN_OLLAMA_MODEL` | `qwen2.5:14b` | Modelo Qwen via Ollama local |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endpoint Ollama |
| `AZURE_STORAGE_CONNECTION_STRING` | — (opcional) | Habilita Blob real; sem ela, fallback CSV local |
| `BLUA_TELEMETRY_CSV` | `dashboard/data/cardiac_data.csv` | Path do CSV de telemetria ao vivo |
| `BLUA_GABRIEL_CSV` | `dashboard/data/gabriel_data.csv` | Path do CSV do paciente Gabriel |
| `BLUA_MEU_PERFIL_CSV` | `dashboard/data/meu_perfil_data.csv` | Path do CSV saudável do Meu Perfil |
| `BLUA_ROOT` | pasta do projeto | Raiz do projeto pra resolução de paths |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | Diretório de persistência do ChromaDB |
| `LANGSMITH_API_KEY` | — (opcional) | Ativa observabilidade LangSmith |
| `LANGSMITH_PROJECT` | `BluaDiagnostics-Sprint2` | Nome do projeto no LangSmith |
| `API_ML_URL` | `https://api-predicaocardiaca-cpc0bufrhmd7ade4.brazilsouth-01.azurewebsites.net`| URL da API localizada em um servidor Azure |

## Testes

```bash
pytest --tb=short
```

Esperado: `67 passed`. Os testes cobrem:
- Tools (prescrição, criar perfil, telemetria, ritmo)
- Safety chain (pre_safety + safety + heurísticas)
- Supervisor robusto (retry + Pydantic + fallbacks)
- Triagem com guarda anti-medicação não-cardiovascular
- Regressões de escopo (PATCH 5.5)

## Estrutura

```
blua-cardio/
├── dashboard/                # servidor Dash multi-pages (entrypoint)
│   ├── app.py                # entrypoint (este é o main agora)
│   ├── assets/               # CSS, alert.wav
│   ├── pages/                # páginas Dash (use_pages=True)
│   │   ├── home.py           # /        — overview + KPIs
│   │   ├── chat.py           # /chat    — chatbot (LangGraph)
│   │   ├── monitor.py        # /monitor — PPG ao vivo
│   │   ├── analysis.py       # /analise — histórico
│   │   ├── gabriel.py        # /gabriel — prontuário Gabriel
│   │   ├── meu_perfil.py     # /meu-perfil — formulário + prontuário
│   │   └── pacientes.py      # /pacientes — lista registry
│   ├── utils/                # storage (Blob+CSV fallback), analysis, theme
│   └── data/                 # CSVs de telemetria
│       ├── cardiac_data.csv  # telemetria genérica
│       ├── gabriel_data.csv  # dataset Gabriel (200 batimentos)
│       └── meu_perfil_data.csv  # dataset Meu Perfil (200 batimentos, saudável)
├── src/                      # lógica do chatbot
│   ├── graph.py              # grafo LangGraph (10 nós)
│   ├── agents/               # supervisor, triagem, checkup, prescricao, ...
│   ├── tools/                # 10 tools (criar_perfil, agendar, ritmo, relatorio, ...)
│   ├── rag/                  # indexer + retriever + reranker (ChromaDB)
│   ├── llm/                  # cliente Qwen (DashScope/Ollama)
│   └── safety/               # pre_safety + safety + heurísticas
├── shared/                   # paths canônicos + patient_registry
├── api.py                    # API ML upstream (FastAPI + Random Forest)
├── predicao.py               # classificador Random Forest pré-treinado
├── simulador/                # simulador ESP32 (opcional, opt-in)
│   ├── simulador_esp32.cpp   # fonte C++
│   ├── simulador_esp32.exe   # binário pré-compilado Win x64
│   ├── gerador_ibi.py        # gerador de IBIs em Python
│   └── README.md             # setup MSYS2 pra recompilar
├── data/
│   ├── mocks/                # perfis_clinicos.json + outros JSONs
│   └── consultas/            # agendamentos persistidos (Blob + local)
├── knowledge_base/           # 12 documentos cardiovasculares (RAG source)
├── prompts/                  # system prompts dos agentes
├── chroma_db/                # banco vetorial (gerado pelo indexer)
├── tests/                    # 67 testes pytest
├── docs/
│   ├── arquitetura/          # planos da integração ArrhythmiaMonitor
│   └── historico/            # docs do projeto pré-integração
├── tools/                    # tools_spec.json (schema OpenAI)
├── colab_setup.py            # bootstrap de ambiente
├── main.py                   # CLI alternativo (sem UI Dash)
├── requirements.txt
├── pyproject.toml
└── pytest.ini
```

## Troubleshooting

### `DASHSCOPE_API_KEY não encontrada`

O `.env` não foi carregado ou a chave está vazia. Confirme:
1. Existe `.env` na raiz (não `.env.example`).
2. Linha `DASHSCOPE_API_KEY=sk-...` está preenchida (sem aspas, sem espaços).
3. Se rodou em terminal aberto antes da criação do `.env`, abra novo terminal.

### `dash.exceptions.InvalidConfig: A folder called 'pages' does not exist`

Você está rodando de um cwd errado. Use:

```bash
python dashboard/app.py
```

(rodar a partir da raiz do projeto). O `_PAGES_DIR` em `dashboard/app.py`
resolve o caminho absoluto do `dashboard/pages/`.

### `ChromaDB vazio` ou RAG sem documentos

Você esqueceu o passo 4 do setup. Rode:

```bash
python -m src.rag.indexer
```

### Modelos Hugging Face demoram muito pra baixar

Defina `HF_HUB_DOWNLOAD_TIMEOUT=120` no `.env` ou use HF Hub com token
(`HF_TOKEN=...`) para evitar rate limits.

### Pytest falha com `ModuleNotFoundError`

Confirme que está rodando da raiz do projeto e que o venv tem as deps.
O `pytest.ini` define `pythonpath = .` automaticamente.

## Documentos de referência

- `docs/arquitetura/PLANO_INTEGRACAO_ARRHYTHMIAMONITOR.md` — Plano executável da integração
- `docs/arquitetura/PENDENCIAS_POS_INTEGRACAO.md` — Status das pendências pós-integração
- `docs/historico/` — Documentos do projeto pré-integração (PLANO_MERGE, PASSO_8, etc.)
- `simulador/README.md` — Setup MSYS2 pra recompilar o simulador ESP32 (opcional)

## Licença

MIT (ver `pyproject.toml`).
