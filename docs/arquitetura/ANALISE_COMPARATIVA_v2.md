# ANÁLISE COMPARATIVA v2 — blua-cardio × ArrhythmiaMonitor

**Filosofia adotada:** Cenário 3 — começar do zero. `ArrhythmiaMonitor` é a base canônica. Chatbot do `blua-cardio` é reaplicado por cima. Branch novo no repositório `blua-cardio`. Decisões C1-C13 já fechadas em sessão anterior.

**Objetivo deste documento:** consolidar o que vem de onde, classificar os 39 commits atuais do `blua-cardio` em categorias [A]/[B]/[C]/[D], e listar os arquivos finais do repo integrado com origem clara.

**Próximo documento:** `PLANO_INTEGRACAO_ARRHYTHMIAMONITOR.md` estilo `PLANO_MERGE.md` (sub-passos numerados, validações, rollback).

---

## 1. Varredura dos 39 commits do blua-cardio

Cada commit classificado em:

- **[A] BUGFIX REAL** — preservar. Sistema quebra sem isso.
- **[B] REFACTOR DO PASSO 8** — descartar. Estrutura final vem do upstream.
- **[C] PATCH DE HARMONIA PRÉ-INTEGRAÇÃO** — re-avaliar; alguns podem virar irrelevantes.
- **[D] DOCS** — neutro; podem ser preservados como referência histórica em `docs/historico/`.
- **[F] FEATURE DO CHATBOT** — preservar. Categoria nova que percebi durante varredura: muitos commits são features puras do chatbot (sem conflito com upstream).

### Tabela completa (ordem cronológica)

| # | Hash | Categoria | Título | Justificativa |
|---|------|-----------|--------|---------------|
| 1 | `cf3866c` | [B+F] | scaffolding inicial do blua-cardio | Base do merge anterior. Conteúdo de chatbot ([F]) e de dashboard_legacy ([B]) misturados. Preservar `src/`, `prompts/`, `knowledge_base/`, `tests/`, `data/mocks/` por serem [F]. Descartar `app/dash_app.py`, `app/streamlit_app.py`, `dashboard_legacy/`, `blua_merge_files/` por serem [B] do merge antigo. |
| 2 | `7fa42ff` | [F] | bridge layer chatbot↔dashboard (shared/) | Cria `shared/paths.py`, `shared/patient_registry.py`, `shared/telemetry_store.py`. `telemetry_store.py` será descontinuado (C1). `paths.py` + `patient_registry.py` preservados. |
| 3 | `03b57b4` | [F] | rename BENEF-MARIA → GABRIEL | Decisão de naming. Preservar — afeta `data/mocks/perfis_clinicos.json`, prompts e tests. |
| 4 | `a3d7f6e` | [F] | live mode em `analisar_ritmo_cardiaco` | Feature do chatbot. Tool aceita `paciente_id` opcional além dos parâmetros legados. Preservar. |
| 5 | `8a34f98` | [F] | tools `criar_perfil_paciente` + `consultar_telemetria_dashboard` | Features do chatbot. Preservar inteiras. |
| 6 | `84992c9` | [F] | registra novas tools nos agents + spec | Atualização de `prompts/agente_checkup.md`, `prompts/agente_triagem.md`, `tools/tools_spec.json`. Preservar. |
| 7 | `af3977f` | [D] | docs PATCH_5.5 + PASSO_8_UNIFICACAO_DASH | Docs. Mover para `docs/historico/` (PATCH_5.5 ainda válido como referência; PASSO_8 fica como histórico). |
| 8 | `d59eb91` | [A] | disclaimer PPG em classificações não-regulares | **Bugfix de segurança real.** Sistema sem disclaimer pode ser interpretado como diagnóstico médico. Preservar `src/tools/ritmo.py`. |
| 9 | `40e88dd` | [A] | renomeia "diagnóstico curto" → "observação" | Higiene de escopo (PATCH_5.5). Preservar. |
| 10 | `e77ae90` | [A] | marca medicações/alergias como auto-declaradas | Bugfix de escopo (PATCH_5.5). Preservar `src/tools/criar_perfil.py`. |
| 11 | `f5c33a4` | [A] | system prompt checkup — 3 regras invioláveis | Bugfix de escopo (PATCH_5.5). Preservar `prompts/agente_checkup.md`. |
| 12 | `846899b` | [A] | testes de regressão de escopo | Preservar `tests/test_escopo_cardiovascular.py`. |
| 13 | `819a0b9` | [D] | docs PATCH_5.6 | Docs. Mover para `docs/historico/`. |
| 14 | `e24d65d` | [A] | checkup few-shot anti-invenção (PATCH 5.6) | Bugfix de escopo. Preservar. |
| 15 | `96116ac` | [A] | placeholders nos prompts + anti-invenção | Bugfix. Preservar. |
| 16 | `32c8e65` | [A] | supervisor retry + Pydantic + 14 testes | **Bugfix arquitetural grande.** Preservar `src/agents/router.py` + `tests/test_supervisor_robusto.py`. |
| 17 | `f55eb47` | [A] | guardas contra invenção e fora de escopo | Bugfix. Preservar. |
| 18 | `c71fe2b` | [D] | docs PLANO_FASES_2_A_5 + PROMPT_FASES_1_A_5 | Docs históricos. Mover para `docs/historico/`. |
| 19 | `d952079` | [D] | resultados smoke E2E Passo 7 | Docs históricos. Mover para `docs/historico/`. |
| 20 | `c9c6cad` | [A] | corrige 3 bugs arquiteturais (smoke 7) | **Bugfix crítico.** Bugs do BluaDiagnostics Sprint 2 expostos no smoke. Preservar. |
| 21 | `170e409` | [D] | PLANO_MERGE.md — Passo 7 concluído | Doc. Mover histórico. |
| 22 | `024cde5` | [D] | ISSUES.md com 2 bugs pré-existentes | Doc. Mover histórico (referenciar issues que viraram bugfixes). |
| 23 | `06407b0` | [D] | resolve TODO do PLANO_MERGE.md | Doc. Mover histórico. |
| 24 | `ecd5805` | [D] | docs MINI_PATCHES_HARMONIA_ARRHYTHMIAMONITOR | Docs. Mover histórico (R1-R4 abaixo). |
| 25 | `e8a6da5` | [D] | docs INTEGRACAO_ARRHYTHMIAMONITOR.md | Docs (este é o histórico do plano de integração que estamos refazendo agora). Mover histórico. |
| 26 | `6df5f63` | [C/D] | env var override em paths de telemetria (R2) | C1 descontinua `shared/telemetry_store.py` → R2 perde propósito. **Descartar R2.** Mas a generalização em `shared/paths.py` (BLUA_ROOT) pode ser preservada. |
| 27 | `7ccfaab` | [F] | persistir consultas localmente (R3) | Feature do chatbot. Cria `data/consultas/` + modifica `src/tools/agendamento.py`. Preservar — coexiste com feature pendente "agendamento via Blob" do README do `ArrhythmiaMonitor` (fora do escopo desta integração). |
| 28 | `cc171e5` | [C] | alinha GABRIEL com prontuário do ArrhythmiaMonitor (R1) | R1 alinhou `data/mocks/perfis_clinicos.json` com o que `pages/gabriel.py` upstream tem hardcoded. Preservar — Gabriel canônico do JSON precisa bater com o do `gabriel.py` upstream. |
| 29 | `2d815c4` | [B] | remove `app/streamlit_app.py` legado | Cleanup do Passo 8. Irrelevante — Cenário 3 já não traz `streamlit_app.py`. |
| 30 | `f69182c` | [B] | adota `pages/` na raiz + move utils | Refactor do Passo 8 que ficará irrelevante porque a estrutura final virá do upstream com `dashboard/pages/` + `dashboard/utils/`. **Descartar.** |
| 31 | `05eb50a` | [B] | converte dash_app.py em pages/chat.py com use_pages | Refactor do Passo 8 — **mas o resultado (`pages/chat.py` como página Dash) é o que vai ser reaplicado** em Cenário 3. **Conteúdo de `pages/chat.py` (609 linhas) é preservado**; o refactor formal em si é descartado. |
| 32 | `3e2073c` | [D] | revisão de INTEGRACAO_ARRHYTHMIAMONITOR.md | Doc. Histórico. |
| 33 | `d583634` | [D] | docs decisão adiar seletor global | Doc. Histórico. |
| 34 | `1bfa33e` | [F] | adiciona `pages/pacientes.py` (lista registry) | Feature pequena. Preservar mas será adaptada — em Cenário 3, `/pacientes` vira página de gestão de perfil (Gabriel + Meu Perfil). |
| 35 | `9731eec` | [B] | unified_app.py como entrypoint único | Refactor do Passo 8. Descartar — entrypoint vai ser substituído por `dashboard/app.py` upstream + 3 fixes Windows 8.5. |
| 36 | `af5ad61` | [A] | smoke A-E verde + fixes S1-S5 do 8.9 | **Os fixes S1-S5 são bugfixes CSS reais.** Preservar como patch aplicado sobre `style.css` upstream. Os smoke results em si são docs (histórico). |
| 37 | `8efb998` | [B] | remove `dashboard_legacy/` órfão | Cleanup. Irrelevante — Cenário 3 já não traz dashboard_legacy. |
| 38 | `e774d2a` | [B] | merge final Passo 8 — Dash unificado | Merge final do Passo 8. **Descartar como estrutura**, mas o estado pós-merge contém arquivos que serão preservados separadamente (chat.py, mocks, src/). |
| 39 | `281aa17` | [D] | reescreve README | Doc. README final será reescrito pelo usuário pós-integração (C12). Descartar. |

### Resumo da varredura

| Categoria | Quantidade | Ação |
|-----------|------------|------|
| [A] BUGFIX REAL | 11 commits | Preservar mudanças, reaplicar em conteúdo upstream |
| [B] REFACTOR DO PASSO 8 | 7 commits | Descartar (estrutura final vem do upstream) |
| [C] PATCH DE HARMONIA | 2 commits (R1, R2) | Re-avaliar: R1 preservar, R2 descartar |
| [D] DOCS | 12 commits | Mover para `docs/historico/` |
| [F] FEATURE DO CHATBOT | 7 commits | Preservar inteiras (são código do chatbot independente) |

**Total preservado em essência:** 11 bugfix + 7 feature + 1 R1 + 12 docs (como referência) = 31 commits têm valor.
**Descartados:** 7 refactor do Passo 8 + 1 R2 = 8 commits que ficam obsoletos com Cenário 3.

---

## 2. Mapeamento arquivo-por-arquivo do repo integrado final

Estrutura final espelha o upstream `ArrhythmiaMonitor` com chatbot adicionado em `agent/page.py` (placeholder já existe upstream) e estruturas auxiliares do chatbot na raiz.

### 2.1 Raiz do repositório

| Arquivo | Origem | Notas |
|---------|--------|-------|
| `README.md` | Upstream literal | C12 — o usuário atualizará depois |
| `requirements.txt` | **MESCLADO** | Union de upstream + chatbot. Versões mais restritivas em conflito. C9. |
| `api.py` | Upstream literal | API ML FastAPI. C8. |
| `predicao.py` | Upstream literal | Random Forest classifier. C8. |
| `modelo_predicao.pkl` | Upstream literal | Modelo treinado. C8. |
| `treino.py` | Upstream literal | Script de treino. C8. |
| `config.py` | Upstream literal | Config da API. C8. |
| `dataset_ppg.csv` | Upstream literal | Dataset de treino. C8. |
| `dataset_ppg_300.xlsx` | Upstream literal | C8. |
| `monitor_csv.py` | Upstream literal | C8. |
| `startup.sh` | Upstream literal | Bootstrap Azure App Service. C8. |
| `.env.example` | **MESCLADO** | Var do upstream (Azure, SMTP) + chatbot (DASHSCOPE_API_KEY, LANGSMITH). |
| `.gitignore` | **MESCLADO** | Union. |
| `pyproject.toml` | Do `blua-cardio` | Necessário pro pytest do chatbot. |
| `pytest.ini` | Do `blua-cardio` | Configuração de testes. |
| `main.py` | Do `blua-cardio` | Entry CLI do chatbot (opcional, usado em testes/desenvolvimento). |
| `colab_setup.py` | Do `blua-cardio` | Bootstrap LangSmith. |

### 2.2 `dashboard/` — UI Dash

Espelho do upstream com adições documentadas.

| Arquivo | Origem | Notas |
|---------|--------|-------|
| `dashboard/app.py` | Upstream + **3 fixes 8.5** | C4. Reaplica: `redirect_from`, `pages_folder` absoluto, encoding ASCII no print. Também adiciona `dcc.Store(id="session-data")` no layout global + link "CHAT" no topbar. |
| `dashboard/pages/home.py` | Upstream literal | Página `/`. |
| `dashboard/pages/monitor.py` | Upstream literal | Página `/monitor`. C1 implementado: já usa `utils/storage.py` upstream. |
| `dashboard/pages/analysis.py` | Upstream literal | Página `/analise`. |
| `dashboard/pages/gabriel.py` | Upstream literal | Página `/gabriel`. **628 linhas com prontuário hardcoded** — fica intacto. C2. |
| `dashboard/pages/meu_perfil.py` | **NOVO (criado nesta integração)** | Layout simplificado pra Meu Perfil. C2. Lê do `data/mocks/perfis_clinicos.json` filtrado por `MEU_PERFIL`. |
| `dashboard/pages/pacientes.py` | **NOVO** | Gestão de perfis (Gabriel + Meu Perfil). Inspirado em `pages/pacientes.py` do `blua-cardio` mas adaptado. C13. |
| `dashboard/pages/chat.py` | Do `blua-cardio` literal (609 linhas) | Página `/chat`. C3. Conteúdo de `pages/chat.py` atual. Pode receber QoL adjustments pra harmonia visual mas estrutura fica. |
| `dashboard/utils/storage.py` | Upstream literal | 165 linhas (vs 93 local). Suporta Azure Blob + local. C1: substitui `shared/telemetry_store.py`. |
| `dashboard/utils/analysis.py` | Upstream literal | |
| `dashboard/utils/theme.py` | Upstream literal | |
| `dashboard/utils/serial_reader.py` | Upstream literal | |
| `dashboard/utils/email_alert.py` | Upstream + **flag desabilitada** | C6. Wrapper checa `BLUA_EMAIL_ALERTS=enabled` antes de tentar SMTP. |
| `dashboard/assets/style.css` | Upstream + **fixes S1-S5 8.9** | C5. Reaplica: `min-width: 0` em `.hud-patient`, `overflow-wrap: anywhere` em `.blua-bubble`/`.hud-panel__body`/`.hud-patient__name`/`.hud-patient__meta`, `html { overflow-y: scroll }`. |
| `dashboard/assets/alert.wav` | Upstream literal | (md5-idêntico ao local). |
| `dashboard/assets/blua_custom.css` | Do `blua-cardio` | Estilos extras do chatbot — preservar se ainda usados pela `pages/chat.py`. |

### 2.3 `src/` — chatbot LangGraph (raiz, preservado intacto)

Toda essa árvore vem do `blua-cardio` atual, **sem alterações**. Contém todos os bugfixes [A] aplicados sobre a base.

| Caminho | Origem | Notas |
|---------|--------|-------|
| `src/agents/*.py` | `blua-cardio` literal | 9 agents (checkup, escalada_humana, pre_safety, prescricao, router, safety, suporte, triagem) + bugfixes [A]. |
| `src/tools/*.py` | `blua-cardio` literal | Tools (criar_perfil, telemetria, ritmo, agendamento, classificador_risco, estratificador_cardiovascular, historico, interacoes, prescricao, wearable) + bugfixes. |
| `src/rag/*.py` | `blua-cardio` literal | retriever, reranker, indexer. |
| `src/llm/*.py` | `blua-cardio` literal | qwen_client, ollama_client. |
| `src/audit_log.py` | `blua-cardio` literal | |
| `src/graph.py` | `blua-cardio` literal | LangGraph principal. |
| `src/prompts.py` | `blua-cardio` literal | |
| `src/utils/*.py` | `blua-cardio` literal | memoria.py. |

**Adaptação necessária (não criação):** `src/tools/ritmo.py` e `src/tools/telemetria.py` importam `shared.telemetry_store`. Com C1, esses imports mudam para `dashboard.utils.storage`. Já incluído na fase E do plano. ~5 linhas de mudança.

### 2.4 `prompts/`, `knowledge_base/`, `tests/`, `tools/`

| Caminho | Origem | Notas |
|---------|--------|-------|
| `prompts/*.md` | `blua-cardio` literal | System prompts + bugfixes PATCH_5.5/5.6/anti-invenção. |
| `knowledge_base/*.md` | `blua-cardio` literal | RAG sources. 11 arquivos médicos. |
| `tests/*.py` | `blua-cardio` literal | 67 pytests (incluindo `test_escopo_cardiovascular.py` e `test_supervisor_robusto.py`). |
| `tools/tools_spec.json` | `blua-cardio` literal | Spec de todas as tools. |

### 2.5 `shared/` — bridge layer (parcialmente preservado)

| Arquivo | Origem | Notas |
|---------|--------|-------|
| `shared/__init__.py` | **MODIFICADO** | Remove import de `telemetry_store` (C1). Mantém `paths`, `patient_registry`. |
| `shared/paths.py` | `blua-cardio` literal | Constants. Preservar — `PROFILES_JSON`, `BLUA_ROOT` env var override (R2 parcial). |
| `shared/patient_registry.py` | `blua-cardio` literal | Atomic write + LRU cache invalidation. Preservar 100%. |
| ~~`shared/telemetry_store.py`~~ | **DESCARTADO** | C1. Funções migradas para `dashboard/utils/storage.py` upstream. |

### 2.6 `data/`

| Caminho | Origem | Notas |
|---------|--------|-------|
| `data/cardiac_data.csv` | Upstream literal | CSV genérico — **Meu Perfil usa este**. C2/2.4. |
| `data/gabriel_data.csv` | Upstream literal | CSV específico — **Gabriel usa este**. C2/2.4. |
| `data/mocks/perfis_clinicos.json` | `blua-cardio` + **MEU_PERFIL adicionado** | Tem Gabriel (R1-alinhado com `gabriel.py` upstream) + MEU_PERFIL placeholder a ser preenchido pelo usuário via chatbot ou diretamente. C2. |
| `data/mocks/wearable.json` | `blua-cardio` literal | Mock pra tool `wearable`. |
| `data/mocks/agendamentos.json` | `blua-cardio` literal | |
| `data/mocks/interacoes_medicamentosas.json` | `blua-cardio` literal | |
| `data/consultas/.gitkeep` | `blua-cardio` literal | R3 — agendamentos locais. |

### 2.7 `firmware/` — placeholder upstream

| Caminho | Origem | Notas |
|---------|--------|-------|
| `firmware/esp32_max30100.ino` | `blua-cardio` literal | (era `dashboard_legacy/esp32/`, movido em commit 8efb998). |

### 2.8 `simulador/` — simulador ESP32 C++ (opt-in)

| Caminho | Origem | Notas |
|---------|--------|-------|
| `simulador/simulador_esp32.cpp` | Upstream literal | C7. |
| `simulador/simulador_esp32.exe` | Upstream literal | C7 — binário pre-compilado. |
| `simulador/gerador_ibi.py` | Upstream literal | C7. |
| `simulador/README.md` | **NOVO** | Setup MSYS2 + OpenSSL + g++ pra recompilar. C7. |

### 2.9 `agent/` — placeholder upstream + ponteiro

| Caminho | Origem | Notas |
|---------|--------|-------|
| `agent/README.md` | **NOVO** | Aponta para `src/` (chatbot LangGraph) + `prompts/` + `knowledge_base/` + `tests/`. Dá utilidade ao placeholder upstream sem mover código. C10b ajustado. |

### 2.10 `docs/`

| Caminho | Origem | Notas |
|---------|--------|-------|
| `docs/historico/PLANO_MERGE.md` | `blua-cardio` literal | Referência do merge anterior. |
| `docs/historico/PASSO_8_UNIFICACAO_DASH.md` | `blua-cardio` literal | |
| `docs/historico/PATCH_5.5_DISCIPLINA_ESCOPO.md` | `blua-cardio` literal | |
| `docs/historico/PATCH_5.6_REFORCO_REGRA_1.md` | `blua-cardio` literal | |
| `docs/historico/MINI_PATCHES_HARMONIA_ARRHYTHMIAMONITOR.md` | `blua-cardio` literal | R1-R4. |
| `docs/historico/INTEGRACAO_ARRHYTHMIAMONITOR.md` | `blua-cardio` literal | Histórico. |
| `docs/historico/ISSUES.md` | `blua-cardio` literal | |
| `docs/historico/SMOKE_PASSO_7_RESULTADOS.md` | `blua-cardio` literal | |
| `docs/historico/PLANO_FASES_2_A_5.md` | `blua-cardio` literal | |
| `docs/historico/PROMPT_FASES_1_A_5.md` | `blua-cardio` literal | |
| `docs/historico/PROMPT_INICIAL.md` | `blua-cardio` literal | |
| `docs/historico/README_blua_original.md` | `blua-cardio` literal | |
| `docs/PLANO_INTEGRACAO_ARRHYTHMIAMONITOR.md` | **NOVO** | Plano formal desta integração. A ser escrito a seguir. |

### 2.11 Descartados

| Caminho | Razão |
|---------|-------|
| `app/dash_app.py` | Sucessor é `dashboard/pages/chat.py`. |
| `app/streamlit_app.py` | Já removido em commit 2d815c4. |
| `app/unified_app.py` | Sucessor é `dashboard/app.py` upstream + 3 fixes 8.5. |
| `app/assets/*` | Movido para `dashboard/assets/`. |
| `blua_merge_files/` | Artefato do merge antigo. |
| `dashboard_legacy/` | Já removido em commit 8efb998. |
| `pages/` (raiz) | Movido para `dashboard/pages/`. |
| `utils/` (raiz) | Movido para `dashboard/utils/`. |

---

## 3. Conflitos resolvidos (referência)

Já decididos em sessão anterior, listados aqui para fechamento.

| ID | Decisão |
|----|---------|
| C1 | Descontinuar `shared/telemetry_store.py`. Usar `dashboard/utils/storage.py` upstream. |
| C2 | Gabriel canônico fixo (gabriel.py upstream intacto, 628 linhas) + Meu Perfil em `perfis_clinicos.json` + layout próprio `meu_perfil.py` simplificado. |
| C3 | Chatbot em `/chat`, não `/`. Raiz `/` vira `home.py` upstream. |
| C4 | `dashboard/app.py` upstream + reaplicar 3 fixes Windows 8.5 + `dcc.Store(session-data)` + link CHAT topbar. |
| C5 | `style.css` upstream + reaplicar 5 fixes 8.9 (S1-S5). |
| C6 | Email alerts trazidos, flag `BLUA_EMAIL_ALERTS=disabled` por default. |
| C7 | Simulador ESP32 opt-in. Binário pre-compilado commitado. README MSYS2 separado em `simulador/`. |
| C8 | API ML completa trazida como referência (`api.py`, `predicao.py`, modelo, dataset, treino, config). |
| C9 | `requirements.txt` mesclado por união. |
| C10 | Estrutura upstream max. `agent/` mantido como placeholder vazio (sub-opção b). Chatbot vive em `src/`, `prompts/`, `knowledge_base/`, `tests/` na raiz. |
| C11 | Branch novo no `blua-cardio` repo. |
| C12 | README upstream literal por enquanto. |
| C13 | Dropdown global Gabriel+Meu Perfil incluído no plano atual (não adiado). |

---

## 4. Features pendentes do README do ArrhythmiaMonitor (fora do escopo)

O README upstream lista 3 features de chatbot a implementar. Conforme decisão da sessão anterior, **ficam fora deste plano** — serão tratadas em sessão separada após esta integração estar rodando.

1. **Agendamento de consultas no Blob.** Hoje o chatbot grava localmente (R3, `data/consultas/`). Especificação upstream é gravar em Blob Storage. Fica como roadmap.
2. **Relatório de registros recentes via load_blob.** Agent que chama `load_blob(tail=50)` e sumariza. Requer Blob Storage rodando localmente ou pull da Azure.
3. **Dúvidas sobre Warfarina/Atenolol/Losartana.** Refinamento do RAG existente — knowledge base já tem os 7 .md necessários.

---

## 5. Próximo passo

Escrever `PLANO_INTEGRACAO_ARRHYTHMIAMONITOR.md` estilo `PLANO_MERGE.md` com:

- Fase A: Setup do branch novo + bootstrap upstream.
- Fase B: Trazer conteúdo do chatbot (src/, prompts/, knowledge_base/, tests/, data/mocks/).
- Fase C: Trazer assets adicionais (simulador, firmware, docs históricos).
- Fase D: Adaptar `dashboard/app.py` (fixes 8.5 + chat + dcc.Store).
- Fase E: Adaptar `style.css` (fixes 8.9 S1-S5).
- Fase F: Resolver C1 — migrar imports de `telemetry_store` → `utils/storage`.
- Fase G: Mesclar `requirements.txt`.
- Fase H: Implementar C2 + C13 — Meu Perfil + dropdown global + página `/pacientes` reformulada.
- Fase I: Smoke E2E + pytest verde.

Estimativa: 10-14h totais distribuídas em 4-5 sessões.

---

**Fim da análise comparativa v2.**
