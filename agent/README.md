# agent/

Placeholder upstream do `ArrhythmiaMonitor` reservado pra "agente inteligente".

No projeto `blua-cardio` integrado, o agente (chatbot LangGraph) **não vive
nesta pasta** — vive na raiz, distribuído em:

- **`src/`** — código do chatbot:
  - `src/agents/` — 9 agents LangGraph (checkup, escalada_humana, pre_safety,
    prescricao, router, safety, suporte, supervisor, triagem)
  - `src/tools/` — tools chamadas pelos agents (criar_perfil, telemetria,
    ritmo, agendamento, classificador_risco, etc.)
  - `src/rag/` — retrieval-augmented generation (ChromaDB)
  - `src/llm/` — clients DashScope (Qwen) + Ollama (fallback)
  - `src/graph.py` — grafo principal LangGraph
  - `src/audit_log.py` — auditoria de turnos

- **`prompts/`** — system prompts dos agents (.md)

- **`knowledge_base/`** — fontes RAG (.md médicos)

- **`tests/`** — pytest do chatbot (67+ testes)

- **`tools/tools_spec.json`** — especificação das tools

- **`shared/`** — bridge layer (paths, patient_registry)

## Página Dash do chatbot

A UI Dash do chatbot vive como página em **`dashboard/pages/chat.py`** (rota
`/chat`). Não fica nesta pasta porque o projeto usa Dash `use_pages=True`
e todas as páginas Dash precisam estar juntas no `dashboard/pages/`.

## Por que essa estrutura?

A organização em raiz (vs tudo dentro de `agent/`) facilita:

1. **Imports estáveis.** Padrão `from src.tools.ritmo import ...` continua
   funcionando, sem refator de imports em ~60 arquivos.

2. **67 testes pytest verdes.** Mover `src/` pra dentro de `agent/`
   exigiria reconfiguração de `pytest.ini` + `pyproject.toml`.

3. **Separação clara entre Dashboard (UI) e Chatbot (lógica).** Dashboard
   vive em `dashboard/`. Chatbot vive em `src/` + `prompts/` + etc.
   `agent/` é só placeholder do padrão upstream.

## Histórico

A decisão de manter chatbot fora de `agent/` foi tomada durante a fase
de integração com `ArrhythmiaMonitor` (maio/2026). Ver `docs/historico/`
pros docs de planejamento e `docs/arquitetura/` pro plano formal.
