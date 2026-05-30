# PLANO_INTEGRACAO_ARRHYTHMIAMONITOR.md

**Filosofia:** Cenário 3 — `ArrhythmiaMonitor` upstream é base canônica, chatbot do `blua-cardio` reaplicado por cima. Todo trabalho acontece em **branch novo** (`integracao-arrhythmiamonitor`); `main` permanece intocada.

**Pré-requisito:** Análise comparativa v2 lida e aceita. Decisões C1-C13 fechadas. Estado atual do `blua-cardio` em commit `281aa17` (pós-Passo 8), `main` clean, pytest 67/67 verde.

**Saída esperada:** branch `integracao-arrhythmiamonitor` com:
- Dashboard espelhando upstream com 3 fixes 8.5 + 5 fixes 8.9 reaplicados.
- Chatbot integrado como `dashboard/pages/chat.py`.
- API ML, simulador C++ e firmware ESP32 trazidos como referência/opt-in.
- Meu Perfil + dropdown global Gabriel/Meu Perfil funcional.
- Pytest 67+ verde (67 originais + novos testes do C13 quando aplicável).
- Smoke E2E nas 6 rotas (`/`, `/chat`, `/monitor`, `/analise`, `/gabriel`, `/pacientes`) com HTTP 200.

**Tempo estimado total:** 10-14h distribuídas em 4-5 sessões de 2-3h cada.

**Push final pro remoto do `ArrhythmiaMonitor`:** **fora do escopo desta assistência.** Decisão futura do usuário.

---

## Convenções deste documento

### Paths

```bash
REPO="C:/Users/lucas/OneDrive/Documentos/Fiap Projects/blua-cardio"
UPSTREAM="C:/Users/lucas/OneDrive/Documentos/Fiap Projects/ArrhythmiaMonitor"
```

Em PowerShell ou Git Bash. Adaptar pra outras shells conforme necessário. Aspas duplas no PowerShell pra escapar o espaço em "Fiap Projects".

### Avisos importantes ao Claude Code

- **NUNCA modificar `$UPSTREAM`.** É fonte read-only de cópia.
- **NUNCA fazer commit em `main`.** Confirmar branch atual antes de cada commit.
- **OneDrive deve estar pausado** durante a execução. Git e OneDrive em sync ativo causam conflitos de lock.
- **Pytest verde após cada gate.** Se quebrar, parar e reportar antes de seguir.
- **ROLLBACK é resposta legítima.** Se algo der ruim numa fase, reverter via `git reset --hard` é OK.

### Sintaxe dos sub-passos

Cada sub-passo tem:
- **Objetivo:** o quê e por quê.
- **Pré-condições:** estado esperado antes.
- **Comandos:** execução concreta.
- **Validação:** como confirmar que deu certo.
- **Critério de parada:** o que fazer se falhar.

---

## FASE A — Setup do branch e bootstrap upstream

**Objetivo da fase:** criar branch de trabalho, confirmar acesso ao upstream, garantir baseline pytest verde antes de qualquer mudança.

**Tempo estimado:** 30-45min.

---

### A1 — Confirmar baseline e criar branch

**Objetivo:** garantir `main` clean no commit certo e criar `integracao-arrhythmiamonitor`.

**Comandos:**

```bash
cd "$REPO"

# Confirma estado limpo
git status
# Esperado: "On branch main", "nothing to commit, working tree clean"

# Confirma commit
git log -1 --format='%h %s'
# Esperado: "281aa17 docs(readme): reescreve README com setup completo ponta-a-ponta"

# Pytest baseline
pytest --tb=short 2>&1 | tail -3
# Esperado: "67 passed"

# Cria branch
git checkout -b integracao-arrhythmiamonitor

# Confirma branch
git branch --show-current
# Esperado: "integracao-arrhythmiamonitor"
```

**Validação:** branch criado, working tree clean, pytest 67/67.

**Critério de parada:** se pytest baseline não está verde, **PARAR**. Algo está errado no estado de `main` antes mesmo de começar a integração. Reportar e diagnosticar.

---

### A2 — Confirmar disponibilidade do upstream local

**Objetivo:** garantir que `$UPSTREAM` existe e tem o conteúdo esperado.

**Comandos:**

```bash
# Estrutura raiz
ls "$UPSTREAM"
# Esperado: README.md, agent/, api.py, config.py, dashboard/, dataset_ppg.csv,
#           dataset_ppg_300.xlsx, gerador_ibi/, modelo_predicao.pkl,
#           monitor_csv.py, predicao.py, requirements.txt, simulador_esp32/,
#           startup.sh, treino.py

# Conteúdo do dashboard
ls "$UPSTREAM/dashboard/pages"
# Esperado: analysis.py, gabriel.py, home.py, monitor.py

ls "$UPSTREAM/dashboard/utils"
# Esperado: __init__.py, analysis.py, email_alert.py, serial_reader.py,
#           storage.py, theme.py

ls "$UPSTREAM/dashboard/assets"
# Esperado: alert.wav, style.css

# Confirma upstream em git
cd "$UPSTREAM" && git log -1 --format='%h %s' && cd "$REPO"
# Esperado: "2cd2fd6 ideias para o agente inteligente"
```

**Validação:** todos os diretórios e arquivos listados existem.

**Critério de parada:** se algum arquivo crítico está faltando (especialmente `dashboard/`, `api.py`, `simulador_esp32/`), **PARAR**. Tu pode ter clonado uma versão incompleta. Confirmar fetch completo do upstream.

---

### A3 — Criar estrutura de pastas alvo no branch

**Objetivo:** preparar diretórios destino antes de copiar conteúdo. Evita confusão "onde fica o quê" durante as fases B-H.

**Comandos:**

```bash
cd "$REPO"

# Criar diretórios novos que vão receber conteúdo
mkdir -p dashboard
mkdir -p simulador
mkdir -p agent
mkdir -p docs/historico
mkdir -p docs/arquitetura

# Confirma criação
ls -la dashboard simulador agent docs
```

**Validação:** 5 diretórios novos existem, vazios.

**Critério de parada:** nenhum esperado.

---

### A4 — Commit do scaffolding inicial

**Objetivo:** primeiro commit no branch — marca início da integração.

**Comandos:**

```bash
# .gitkeep nos diretórios vazios pra git tracking
touch dashboard/.gitkeep simulador/.gitkeep agent/.gitkeep docs/historico/.gitkeep docs/arquitetura/.gitkeep

git add dashboard/.gitkeep simulador/.gitkeep agent/.gitkeep docs/historico/.gitkeep docs/arquitetura/.gitkeep

git commit -m "chore(integracao): scaffolding inicial de diretórios alvo

Cria estrutura de pastas alvo da integração ArrhythmiaMonitor:
- dashboard/: receberá conteúdo upstream + adaptações
- simulador/: receberá simulador C++ opt-in
- agent/: placeholder com README apontando para src/
- docs/historico/: docs movidos do blua-cardio
- docs/arquitetura/: docs novos da integração

Branch: integracao-arrhythmiamonitor
Próxima fase: copiar conteúdo upstream"
```

**Validação:**

```bash
git log -1 --format='%h %s'
# Esperado: "<sha> chore(integracao): scaffolding inicial..."

git status
# Esperado: "nothing to commit, working tree clean"
```

---

## FASE B — Trazer conteúdo upstream fiel

**Objetivo da fase:** cópia mecânica do conteúdo upstream pra dentro do repo. Sem adaptações ainda — só cópia fiel.

**Tempo estimado:** 45min-1h.

**Princípio:** cada cópia segue de validação que confirma fidelidade byte-a-byte.

---

### B1 — Trazer `dashboard/` upstream literal

**Objetivo:** copiar `dashboard/pages/`, `dashboard/utils/`, `dashboard/assets/` upstream pra dentro do repo.

**Pré-condições:** branch `integracao-arrhythmiamonitor` ativo. `dashboard/` existe vazia (criado em A3).

**Comandos:**

```bash
cd "$REPO"

# Confirma branch
git branch --show-current
# DEVE retornar: integracao-arrhythmiamonitor
# Se não, PARAR.

# Cópia mecânica
cp -r "$UPSTREAM/dashboard/pages" dashboard/
cp -r "$UPSTREAM/dashboard/utils" dashboard/
cp -r "$UPSTREAM/dashboard/assets" dashboard/
cp "$UPSTREAM/dashboard/app.py" dashboard/

# Conferir resultado
ls dashboard/
# Esperado: __pycache__/ (talvez), app.py, assets/, pages/, utils/, .gitkeep

ls dashboard/pages/
# Esperado: analysis.py, gabriel.py, home.py, monitor.py

ls dashboard/utils/
# Esperado: __init__.py, analysis.py, email_alert.py, serial_reader.py,
#           storage.py, theme.py
```

**Validação de fidelidade:**

```bash
# Diff recursivo entre upstream e cópia
diff -r "$UPSTREAM/dashboard/pages" dashboard/pages
# Esperado: ZERO output (arquivos idênticos)

diff -r "$UPSTREAM/dashboard/utils" dashboard/utils
# Esperado: ZERO output

diff -r "$UPSTREAM/dashboard/assets" dashboard/assets
# Esperado: ZERO output

diff "$UPSTREAM/dashboard/app.py" dashboard/app.py
# Esperado: ZERO output
```

**Critério de parada:** qualquer diff não-vazio significa cópia corrompida. **PARAR**. Deletar `dashboard/pages`, `dashboard/utils`, etc. e refazer.

**Commit:**

```bash
git add dashboard/
git rm dashboard/.gitkeep
git commit -m "feat(dashboard): traz dashboard/ upstream literal do ArrhythmiaMonitor

Cópia fiel byte-a-byte de:
- dashboard/app.py (entrypoint Dash)
- dashboard/pages/ (analysis, gabriel, home, monitor)
- dashboard/utils/ (analysis, email_alert, serial_reader, storage, theme)
- dashboard/assets/ (alert.wav, style.css)

Origem: $UPSTREAM/dashboard/
Commit upstream: 2cd2fd6

Próximo passo: adicionar chat.py + meu_perfil.py + pacientes.py em pages/,
e reaplicar fixes Windows 8.5 + CSS 8.9 (fases D-E)."
```

---

### B2 — Trazer arquivos raiz da API ML (C8)

**Objetivo:** copiar `api.py`, `predicao.py`, `treino.py`, `config.py`, modelo, datasets, `monitor_csv.py`, `startup.sh`.

**Comandos:**

```bash
cd "$REPO"

# API + ML
cp "$UPSTREAM/api.py" .
cp "$UPSTREAM/predicao.py" .
cp "$UPSTREAM/treino.py" .
cp "$UPSTREAM/config.py" .
cp "$UPSTREAM/modelo_predicao.pkl" .
cp "$UPSTREAM/dataset_ppg.csv" .
cp "$UPSTREAM/dataset_ppg_300.xlsx" .
cp "$UPSTREAM/monitor_csv.py" .
cp "$UPSTREAM/startup.sh" .

# Confere
ls api.py predicao.py treino.py config.py modelo_predicao.pkl \
   dataset_ppg.csv dataset_ppg_300.xlsx monitor_csv.py startup.sh
# Esperado: todos listados
```

**Validação:**

```bash
for f in api.py predicao.py treino.py config.py modelo_predicao.pkl \
         dataset_ppg.csv dataset_ppg_300.xlsx monitor_csv.py startup.sh; do
  diff "$UPSTREAM/$f" "$f" || echo "DIFF in $f"
done
# Esperado: zero "DIFF in ..."
```

**Commit:**

```bash
git add api.py predicao.py treino.py config.py modelo_predicao.pkl \
        dataset_ppg.csv dataset_ppg_300.xlsx monitor_csv.py startup.sh
git commit -m "feat(api): traz arquivos da API ML e bootstrap upstream

API FastAPI Random Forest deployed em Azure (C8):
- api.py: endpoint FastAPI
- predicao.py: lógica de classificação
- treino.py: script de treinamento
- config.py: configuração
- modelo_predicao.pkl: modelo treinado
- dataset_ppg.csv: dataset de treino (500 batimentos labeled)
- dataset_ppg_300.xlsx: dataset auxiliar
- monitor_csv.py: utilitário CSV
- startup.sh: bootstrap Azure App Service

Arquivos não rodam localmente (API deployed em Azure). Trazidos como
código de referência + versionamento."
```

---

### B3 — Trazer simulador C++ (C7)

**Objetivo:** copiar `simulador_esp32/` + `gerador_ibi/` upstream pra `simulador/` no repo.

**Comandos:**

```bash
cd "$REPO"

# Simulador C++ (cpp + binário .exe pre-compilado)
cp "$UPSTREAM/simulador_esp32/simulador_esp32.cpp" simulador/
cp "$UPSTREAM/simulador_esp32/simulador_esp32.exe" simulador/

# Gerador IBI Python
cp "$UPSTREAM/gerador_ibi/gerador_ibi.py" simulador/

# Confere
ls simulador/
# Esperado: simulador_esp32.cpp, simulador_esp32.exe, gerador_ibi.py, .gitkeep
```

**Validação:**

```bash
diff "$UPSTREAM/simulador_esp32/simulador_esp32.cpp" simulador/simulador_esp32.cpp
# Esperado: ZERO output

diff "$UPSTREAM/simulador_esp32/simulador_esp32.exe" simulador/simulador_esp32.exe
# Esperado: ZERO output (binário idêntico)

diff "$UPSTREAM/gerador_ibi/gerador_ibi.py" simulador/gerador_ibi.py
# Esperado: ZERO output
```

**Commit:**

```bash
git add simulador/
git rm simulador/.gitkeep
git commit -m "feat(simulador): traz simulador ESP32 C++ como opt-in (C7)

Simulador de batimentos PPG pra rodar sem hardware ESP32 real:
- simulador_esp32.cpp: código fonte C++ (requer MSYS2 + OpenSSL + g++)
- simulador_esp32.exe: binário pre-compilado Windows
- gerador_ibi.py: gerador Python de IBI (Inter-Beat Interval)

Setup MSYS2 documentado em simulador/README.md (próximo commit).

Workflow: gerador_ibi.py → simulador_esp32.exe → API Azure → ML → Blob → Dashboard"
```

---

### B4 — README do simulador (C7)

**Objetivo:** criar `simulador/README.md` com setup MSYS2 + OpenSSL + g++ pra quem quiser recompilar.

**Comandos:**

```bash
cd "$REPO"

cat > simulador/README.md << 'EOF'
# Simulador ESP32 PPG

Simulador de batimentos cardíacos via PPG (PhotoPlethysmoGraphy) pra rodar
o sistema sem hardware ESP32 + MAX30100 real.

## Conteúdo

- `simulador_esp32.cpp` — código fonte C++ que simula leitura de sensor
  e envia POST para a API ML.
- `simulador_esp32.exe` — **binário pre-compilado para Windows x64**. Pronto
  pra executar sem setup adicional.
- `gerador_ibi.py` — gerador Python de IBI (Inter-Beat Interval) usado
  como entrada do simulador.

## Uso rápido (sem recompilar)

```bash
# Em um terminal: gera IBIs
python simulador/gerador_ibi.py

# Em outro terminal: executa simulador
simulador/simulador_esp32.exe
```

Resultado: simulador envia batimentos para a API Azure (ou local), que
classifica via Random Forest e grava no Blob Storage. Dashboard lê o Blob
e exibe em tempo real em `/monitor`.

## Recompilar (se precisar modificar o .cpp)

Requer **Windows + MSYS2 + OpenSSL + g++**. Setup completo:

### 1. Instalar MSYS2

Baixar de https://www.msys2.org/ e seguir instalação padrão.

### 2. Instalar dependências no terminal MSYS2 UCRT64

```bash
pacman -Syu
pacman -S mingw-w64-ucrt-x86_64-gcc
pacman -S mingw-w64-ucrt-x86_64-openssl
pacman -S mingw-w64-ucrt-x86_64-curl
```

### 3. Compilar

```bash
cd simulador/
g++ -o simulador_esp32.exe simulador_esp32.cpp \
    -lssl -lcrypto -lcurl -lws2_32
```

### 4. Conferir

```bash
./simulador_esp32.exe --version
```

## Variáveis de ambiente

O simulador lê:
- `API_URL` — URL da API ML (Azure ou local).
- `API_KEY` — autenticação opcional.

Ver `.env.example` na raiz do projeto.

## Notas

- O `.exe` foi compilado em ambiente MSYS2 UCRT64 com OpenSSL 3.x.
- Em outras versões de OpenSSL, recompilar pode ser necessário.
- Linux/macOS: adaptar compilação (substituir `-lws2_32` por equivalente).
EOF

# Confere
cat simulador/README.md | head -20
```

**Commit:**

```bash
git add simulador/README.md
git commit -m "docs(simulador): adiciona README com setup MSYS2 pra recompilar

Documenta setup completo pra quem precisar modificar o simulador_esp32.cpp:
- Instalação MSYS2
- Dependências (gcc, openssl, curl)
- Comando de compilação
- Variáveis de ambiente

Quem só quer rodar pode usar o .exe pre-compilado direto, sem setup."
```

---

### B5 — Trazer firmware ESP32 (presente no blua-cardio atual)

**Objetivo:** `firmware/esp32_max30100.ino` já existe no `blua-cardio` (commit `8efb998` moveu de `dashboard_legacy/esp32/` para `firmware/`). Confirmar que está lá.

**Comandos:**

```bash
cd "$REPO"

ls firmware/
# Esperado: esp32_max30100.ino

# Comparar com upstream pra confirmar é o mesmo arquivo
# Upstream NÃO tem firmware/ — está em outra estrutura ou foi removido
# Verificar:
find "$UPSTREAM" -name "*.ino" 2>/dev/null
# Se upstream tem .ino em outro lugar, conferir igualdade.
# Se upstream não tem, preservar o local.
```

**Validação:** `firmware/esp32_max30100.ino` existe.

**Critério:** se upstream tem versão diferente (improvável), aceitar upstream (filosofia fiel). Se upstream não tem, manter local.

**Commit:** não há mudança a commitar (arquivo já está no branch via cherry-pick implícito do `main`).

---

## FASE C — Trazer conteúdo do chatbot do `blua-cardio`

**Objetivo da fase:** copiar diretórios do chatbot (`src/`, `prompts/`, `knowledge_base/`, `tests/`, `tools/`, `shared/`) que **já estão no branch** via merge de `main`. Esses arquivos sobreviveram ao Cenário 3 — todos os bugfixes [A] e features [F] estão neles.

**Tempo estimado:** 15-30min (validação principalmente).

**Importante:** esses diretórios **já existem** no branch porque ele foi criado a partir de `main`. Esta fase é **validação** que sobreviveram corretamente + organização.

---

### C1 — Validar presença do chatbot no branch

**Objetivo:** confirmar que tudo do chatbot está intacto no branch (foram parte do `281aa17` original).

**Comandos:**

```bash
cd "$REPO"

# Estrutura do chatbot
ls src/
# Esperado: agents/, audit_log.py, graph.py, llm/, prompts.py, rag/, tools/, utils/, __init__.py

ls src/tools/
# Esperado: __init__.py, agendamento.py, classificador_risco.py,
#           criar_perfil.py, estratificador_cardiovascular.py, historico.py,
#           interacoes.py, prescricao.py, ritmo.py, telemetria.py, wearable.py

ls prompts/
# Esperado: 8 arquivos .md

ls knowledge_base/
# Esperado: 11 arquivos .md (anti_coagulante, anti_hipertensivos,
#           cardiologia_*, cartilha_*, diretrizes_*, mapa_*,
#           politicas_*, protocolo_*, red_flags_*)

ls tests/
# Esperado: test_classificador_risco.py, test_escopo_cardiovascular.py,
#           test_estratificador_cardiovascular.py, test_pre_safety.py,
#           test_prescricao_tool.py, test_supervisor_robusto.py

ls tools/
# Esperado: tools_spec.json

ls shared/
# Esperado: __init__.py, paths.py, patient_registry.py, telemetry_store.py

ls data/mocks/
# Esperado: agendamentos.json, interacoes_medicamentosas.json,
#           perfis_clinicos.json, wearable.json

# Pytest funcional
pytest --tb=short 2>&1 | tail -5
# Esperado: "67 passed"
```

**Validação:** todos os diretórios existem, todos os arquivos esperados estão lá, pytest verde.

**Critério de parada:** se algum arquivo crítico está faltando ou pytest quebrou, **PARAR**. Algo aconteceu entre A1 e C1 que não deveria. Investigar com `git status` + `git diff HEAD~5`.

---

### C2 — Mover docs antigos pra `docs/historico/`

**Objetivo:** organizar docs do `blua-cardio` em `docs/historico/` (decisão da análise comparativa v2).

**Comandos:**

```bash
cd "$REPO"

# Lista de docs a mover (estão na raiz)
DOCS_HIST=(
  "PLANO_MERGE.md"
  "PASSO_8_UNIFICACAO_DASH.md"
  "PATCH_5.5_DISCIPLINA_ESCOPO.md"
  "PATCH_5.6_REFORCO_REGRA_1.md"
  "MINI_PATCHES_HARMONIA_ARRHYTHMIAMONITOR.md"
  "ISSUES.md"
  "SMOKE_PASSO_7_RESULTADOS.md"
  "PLANO_FASES_2_A_5.md"
  "PROMPT_FASES_1_A_5.md"
  "PROMPT_INICIAL.md"
  "README_blua_original.md"
)

# Move cada um (git mv preserva história)
for doc in "${DOCS_HIST[@]}"; do
  if [ -f "$doc" ]; then
    git mv "$doc" "docs/historico/$doc"
    echo "Movido: $doc"
  else
    echo "Não existe: $doc"
  fi
done

# Move INTEGRACAO_ARRHYTHMIAMONITOR.md de docs/ pra docs/historico/
if [ -f "docs/INTEGRACAO_ARRHYTHMIAMONITOR.md" ]; then
  git mv docs/INTEGRACAO_ARRHYTHMIAMONITOR.md docs/historico/
fi

# Conferir
ls docs/historico/
# Esperado: 12 arquivos .md
```

**Validação:**

```bash
ls *.md 2>/dev/null | head
# Esperado: apenas README.md na raiz (será substituído na fase D)

ls docs/historico/*.md | wc -l
# Esperado: 12
```

**Commit:**

```bash
git add docs/historico/ docs/
git commit -m "chore(docs): move docs históricos do blua-cardio para docs/historico/

Organiza referências do trabalho anterior (merge + Passo 8 + patches)
em docs/historico/ pra liberar raiz do projeto pra estrutura upstream.

Arquivos movidos (preservam git history via git mv):
- PLANO_MERGE.md
- PASSO_8_UNIFICACAO_DASH.md
- PATCH_5.5_DISCIPLINA_ESCOPO.md
- PATCH_5.6_REFORCO_REGRA_1.md
- MINI_PATCHES_HARMONIA_ARRHYTHMIAMONITOR.md
- ISSUES.md
- SMOKE_PASSO_7_RESULTADOS.md
- PLANO_FASES_2_A_5.md
- PROMPT_FASES_1_A_5.md
- PROMPT_INICIAL.md
- README_blua_original.md
- INTEGRACAO_ARRHYTHMIAMONITOR.md (de docs/)

São referência histórica — pra contexto se alguém precisar entender
decisões do trabalho anterior. Nenhum desses docs guia código atual."
```

---

### C3 — Criar `agent/README.md` apontando para `src/`

**Objetivo:** dar utilidade ao placeholder `agent/` do upstream (decisão final: README explicativo).

**Comandos:**

```bash
cd "$REPO"

cat > agent/README.md << 'EOF'
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
pros docs de planejamento.
EOF

# Confere
cat agent/README.md | head -10
```

**Commit:**

```bash
git rm agent/.gitkeep
git add agent/README.md
git commit -m "docs(agent): adiciona README explicando estrutura do chatbot

Dá utilidade ao placeholder agent/ do upstream sem mover código.
README aponta pra onde o chatbot realmente vive:
- src/ (agents, tools, rag, llm, graph)
- prompts/ (system prompts)
- knowledge_base/ (RAG sources)
- tests/ (pytest)
- dashboard/pages/chat.py (UI Dash)

Justifica a escolha de estrutura (preserva imports, pytest verde,
separação UI/lógica clara)."
```

---

## FASE D — Adaptar `dashboard/app.py` (C4)

**Objetivo da fase:** o `dashboard/app.py` upstream (124 linhas) precisa receber 3 fixes Windows 8.5 + `dcc.Store(session-data)` global + link CHAT no topbar pra suportar o chatbot integrado.

**Tempo estimado:** 45min-1h.

**Princípio:** mudanças mínimas e documentadas. Cada uma com comentário `# FIX 8.5` ou `# CHAT INTEGRATION` pra fácil identificação futura.

---

### D1 — Verificar conteúdo do `dashboard/app.py` upstream

**Objetivo:** confirmar baseline antes de modificar.

**Comandos:**

```bash
cd "$REPO"

# Estado atual
wc -l dashboard/app.py
# Esperado: 124 (upstream)

# Confirmar é idêntico ao upstream (deve estar — copiamos em B1)
diff "$UPSTREAM/dashboard/app.py" dashboard/app.py
# Esperado: ZERO output

# Inspecionar estrutura
head -50 dashboard/app.py
```

**Validação:** arquivo idêntico ao upstream, 124 linhas.

---

### D2 — Aplicar fix Windows 8.5.1: encoding ASCII no print

**Objetivo:** trocar caracteres Unicode em strings de print por equivalentes ASCII. Erro de `UnicodeEncodeError` no Windows com encoding default `cp1252`.

**Mapeamento dos 3 fixes Windows do 8.5 (do PASSO_8_UNIFICACAO_DASH.md):**

1. `redirect_from` — necessário se quiser `/chat` também responder em `/`. Em Cenário 3, `/` é `home.py` upstream, então este fix talvez nem se aplique mais. **Verificar se ainda é necessário.**
2. `pages_folder` absoluto — pra Dash encontrar `pages/` quando rodando do diretório raiz vs `dashboard/`.
3. Encoding ASCII — substituir `→`, `·`, etc. por equivalentes ASCII em strings que vão pro `print`.

**Procedimento:**

```bash
cd "$REPO"

# Inspeção: o que precisa de fix
grep -n '[→·│┌┐└┘]' dashboard/app.py
# Lista linhas com Unicode

# Lista linhas de print
grep -n 'print' dashboard/app.py
```

**Aplicação concreta:** Claude Code deve:

1. Ler `dashboard/app.py` upstream completo.
2. Identificar prints com Unicode (especialmente `→` usado nas mensagens "[/route → page]").
3. Substituir por ASCII (`->` em vez de `→`).
4. Adicionar comentário `# FIX 8.5: ASCII pra evitar UnicodeEncodeError no Windows cp1252`.

**Validação:**

```bash
# Confirma que não tem mais Unicode em prints
grep '[→·│]' dashboard/app.py
# Esperado: zero hits ou apenas em comentários
```

**Commit:** ainda não — agrupar com D3 e D4.

---

### D3 — Aplicar fix Windows 8.5.2: `pages_folder` absoluto

**Objetivo:** se o Dash for invocado com `python dashboard/app.py` (de raiz) vs `cd dashboard && python app.py`, o `pages_folder="pages"` relativo falha. Solução: torná-lo absoluto.

**Procedimento:**

Claude Code deve:

1. Importar `Path` em `dashboard/app.py`:
   ```python
   from pathlib import Path
   ```

2. Definir caminho absoluto:
   ```python
   _PAGES_DIR = Path(__file__).resolve().parent / "pages"
   ```

3. Substituir:
   ```python
   pages_folder="pages",
   ```
   por:
   ```python
   pages_folder=str(_PAGES_DIR),  # FIX 8.5: caminho absoluto pra funcionar de qualquer cwd
   ```

**Validação:**

```bash
grep -n "_PAGES_DIR\|pages_folder" dashboard/app.py
# Esperado: definição de _PAGES_DIR + uso de str(_PAGES_DIR) em pages_folder
```

---

### D4 — Adicionar `dcc.Store(session-data)` global

**Objetivo:** o chatbot precisa de `dcc.Store(id="session-data")` no layout global pra preservar estado entre navegações de página (saiu do /chat, foi pro /monitor, voltou pro /chat — conversa preservada).

**Procedimento:**

Claude Code deve localizar o `app.layout = html.Div([...])` no `dashboard/app.py` e adicionar `dcc.Store` no início:

```python
import uuid

app.layout = html.Div([
    # CHAT INTEGRATION: estado de sessão do chatbot preservado entre páginas
    dcc.Store(id="session-data", data={
        "thread_id": str(uuid.uuid4()),
        "mensagens": [],
        "flags_safety_anteriores": [],
        "ultimo_estado": None,
    }),

    # CHAT INTEGRATION: audio element pra alerts do chatbot
    html.Audio(id="audio-alert", src="/assets/alert.wav",
               className="blua-audio-alert", autoPlay=False),

    # Topbar (upstream)
    _topbar(),

    # Container de página (upstream)
    dash.page_container,
])
```

**Validação:**

```bash
grep -n "session-data\|audio-alert" dashboard/app.py
# Esperado: 2 hits (dcc.Store + html.Audio)
```

---

### D5 — Adicionar link "CHAT" no topbar

**Objetivo:** topbar do upstream tem links pra páginas existentes (home, monitor, analise, gabriel). Adicionar link pra `/chat`.

**Procedimento:**

Claude Code inspeciona a função `_nav_links()` ou `_topbar()` no `dashboard/app.py` upstream. Como o chatbot vai estar registrado via `dash.register_page(__name__, path="/chat", name="Chat", order=5)` em `dashboard/pages/chat.py`, a iteração `dash.page_registry.values()` vai pegar automaticamente.

**Ação concreta:** garantir que `chat.py` (quando criado na Fase F) tenha `order=5` (depois de gabriel que provavelmente é 4) pra aparecer na ordem certa no topbar.

**Validação:** após Fase F, abrir o app e confirmar visualmente que topbar mostra CHAT.

---

### D6 — Commit consolidado da Fase D

**Comandos:**

```bash
cd "$REPO"

# Confere
diff dashboard/app.py "$UPSTREAM/dashboard/app.py"
# Esperado: diffs claramente identificáveis como FIX 8.5 e CHAT INTEGRATION

# Smoke test: sobe Dash e confere HTTP 200
# (em terminal separado ou background)
# python -c "from dashboard.app import app; print('OK')"
# Esperado: "OK" sem traceback

git add dashboard/app.py
git commit -m "feat(app): adapta dashboard/app.py upstream para integração chatbot

3 fixes Windows do Passo 8.5 reaplicados:
- FIX 8.5: encoding ASCII em prints (evita UnicodeEncodeError cp1252)
- FIX 8.5: pages_folder absoluto (Path resolve em vez de string relativa)
- FIX 8.5: tratamento de redirect já não necessário (Cenário 3 não usa)

Adições para integração do chatbot (CHAT INTEGRATION):
- dcc.Store(id='session-data') global pra estado entre navegações
- html.Audio(id='audio-alert') global pra alerts do chatbot
- import uuid pra thread_id

Link CHAT no topbar virá automaticamente via dash.register_page
no chat.py (Fase F).

Diff total vs upstream: ~10 linhas adicionadas, 3 modificadas.
Todas mudanças marcadas com '# FIX 8.5' ou '# CHAT INTEGRATION'."
```

---

## FASE E — Reaplicar fixes CSS 8.9 sobre `style.css` upstream (C5)

**Objetivo da fase:** o `style.css` upstream (701 linhas) recebe 5 fixes visuais descobertos no smoke do 8.9 (sintomas S1-S5).

**Tempo estimado:** 30min.

---

### E1 — Verificar baseline do style.css

**Comandos:**

```bash
cd "$REPO"

wc -l dashboard/assets/style.css
# Esperado: 701 (upstream)

diff "$UPSTREAM/dashboard/assets/style.css" dashboard/assets/style.css
# Esperado: ZERO output
```

---

### E2 — Aplicar fixes S1-S5

**Origem dos fixes:** commit `af5ad61` ("test(passo-8): smoke A-E unificado verde após Passo 8"), seção "Fixes visuais descobertos durante Cenário E (S1-S5)".

**Procedimento:**

Claude Code adiciona ao **final** do `dashboard/assets/style.css` um bloco demarcado:

```css

/* =============================================================================
   FIXES 8.9 — descobertos no smoke do Passo 8 (commit af5ad61)
   Reaplicados sobre upstream do ArrhythmiaMonitor.
   Não remover sem testar regressão das 5 rotas em modo janela (não-fullscreen).
   ============================================================================= */

/* S1 — Card PACIENTE vazando texto à direita
   Causa: .hud-patient é CSS Grid com colunas auto/1fr/auto.
   Item central com 1fr não tinha min-width: 0 — default é "auto"
   (conteúdo intrínseco), impedindo encolhimento em viewport menor. */
.hud-patient { min-width: 0; }
.hud-patient > * { min-width: 0; overflow-wrap: break-word; }

/* S2 + S3 — Mensagem do assistant e RAG · DOCUMENTOS extrapolando container
   Causa: .blua-bubble e .hud-panel__body sem overflow-wrap/word-break.
   Palavras sem espaço (URLs, RED_FLAGS_CARDIOVASCULARES.MD, RERANK=4.01)
   ficavam como "uma palavra" inteira e vazavam o container. */
.blua-bubble,
.hud-panel__body,
.hud-patient__name,
.hud-patient__meta {
  overflow-wrap: anywhere;
  word-break: break-word;
}

/* S4 — Faixa inferior da topbar não chega à borda direita em modo janela
   Causa: scrollbar vertical clássica do browser consome ~15-17px.
   F11 (fullscreen) usa scrollbar overlay e não consome largura.
   Modo janela consome, criando o "corte" na direita.
   Fix: força scrollbar sempre presente (evita layout shift). */
html { overflow-y: scroll; }
```

**Nota sobre S5:** o sintoma S5 foi "duas topbars empilhadas em /chat" — resolvido removendo função `topbar()` interna do `pages/chat.py`. **Não é fix CSS** — é fix Python que será aplicado na Fase F quando o `chat.py` for trazido.

**Validação:**

```bash
wc -l dashboard/assets/style.css
# Esperado: ~720-730 (701 upstream + ~20 do bloco FIX 8.9)

grep -n "FIXES 8.9" dashboard/assets/style.css
# Esperado: 1 hit
```

**Commit:**

```bash
git add dashboard/assets/style.css
git commit -m "fix(css): reaplica fixes visuais do Passo 8.9 sobre style.css upstream (C5)

5 sintomas descobertos no smoke E2E do Passo 8 (commit af5ad61):
- S1: .hud-patient vazando — min-width: 0 + overflow-wrap nos filhos
- S2/S3: .blua-bubble e .hud-panel__body — overflow-wrap: anywhere
- S4: topbar não chegando à borda em modo janela — html { overflow-y: scroll }
- S5: tratado na Fase F (remoção de topbar() duplicada em chat.py)

Bloco final delimitado com comentário '/* FIXES 8.9 */' pra fácil
identificação futura. Não remover sem testar regressão das 6 rotas
em modo janela (não-fullscreen)."
```

---

## FASE F — Trazer `pages/chat.py` adaptado

**Objetivo da fase:** trazer o `pages/chat.py` atual do `blua-cardio` (609 linhas) pra `dashboard/pages/chat.py` no branch, aplicando ajustes mínimos.

**Tempo estimado:** 1h.

---

### F1 — Copiar `pages/chat.py` para `dashboard/pages/chat.py`

**Comandos:**

```bash
cd "$REPO"

# Cópia
cp pages/chat.py dashboard/pages/chat.py

# Confere
wc -l dashboard/pages/chat.py
# Esperado: 609
```

---

### F2 — Ajustar imports pro novo path

**Objetivo:** `pages/chat.py` foi escrito assumindo estar em `pages/` na raiz. Agora vai estar em `dashboard/pages/`. Alguns imports relativos podem precisar ajuste.

**Procedimento:**

Claude Code lê `dashboard/pages/chat.py` e identifica imports:

```python
# Esperado encontrar:
from src.tools.ritmo import ...
from src.graph import ...
from shared.patient_registry import ...
from utils.storage import ...  # << ESTE muda — utils foi pra dashboard/utils/
```

Substituições necessárias:

- `from utils.storage import ...` → `from dashboard.utils.storage import ...`
- `from utils.analysis import ...` → `from dashboard.utils.analysis import ...`
- `from utils.theme import ...` → `from dashboard.utils.theme import ...`

**Validação:**

```bash
grep -n "^from utils\.\|^from dashboard\.utils" dashboard/pages/chat.py
# Esperado: imports começam com "from dashboard.utils."
```

---

### F3 — Confirmar registro de página Dash

**Objetivo:** o `dashboard/pages/chat.py` precisa ter `dash.register_page(__name__, path="/chat", name="Chat", order=5)` no topo.

**Procedimento:**

Claude Code confirma a primeira chamada `dash.register_page`:

```bash
head -20 dashboard/pages/chat.py | grep register_page
# Esperado: dash.register_page(__name__, path="/chat", name="Chat", order=5)
```

Se `order` não está 5 (era qualquer outro número), atualizar pra 5.

---

### F4 — Remover topbar interna duplicada (S5 do 8.9)

**Objetivo:** o `pages/chat.py` original tinha função `topbar()` interna (legado do `dash_app.py`). Foi removida no commit `af5ad61` mas tem que confirmar que está mesmo fora.

**Comandos:**

```bash
cd "$REPO"

grep -n "def topbar\|topbar()" dashboard/pages/chat.py
# Esperado: ZERO hits ou apenas referências em comentários
# Se houver função topbar() ativa, REMOVER.
```

---

### F5 — Smoke test do chatbot integrado

**Comandos:**

```bash
cd "$REPO"

# Importa o app + chat
python -c "
import sys
sys.path.insert(0, '.')
from dashboard.app import app
import dashboard.pages.chat
print('Pages registradas:')
import dash
for path, page in dash.page_registry.items():
    print(f'  {page[\"relative_path\"]:20} -> {page[\"module\"]}')"
# Esperado: 5 pages incluindo /chat -> dashboard.pages.chat
```

**Validação:** página `/chat` aparece no registry.

**Critério de parada:** se import falha, **PARAR**. Erro de import precisa ser resolvido antes de commit. Não tentar contornar com try/except.

**Commit:**

```bash
git add dashboard/pages/chat.py
git commit -m "feat(chat): adiciona dashboard/pages/chat.py adaptado do blua-cardio (C3)

Conteúdo: pages/chat.py original (609 linhas) do estado pós-Passo 8,
incluindo todos os fixes do 8.5 (S5 — remoção topbar duplicada) +
todos os bugfixes [A] aplicados sobre o agent LangGraph.

Adaptações de path:
- imports 'from utils.X' -> 'from dashboard.utils.X'
- (resto permanece intacto: src/, shared/, prompts/, knowledge_base/)

Registrada com path='/chat', name='Chat', order=5 (depois de gabriel)."
```

---

### F6 — Limpar `pages/` da raiz (obsoleto)

**Objetivo:** `pages/` na raiz era da estrutura do Passo 8. Não é mais necessário porque tudo está em `dashboard/pages/`.

**Comandos:**

```bash
cd "$REPO"

# Confirma conteúdo
ls pages/
# Esperado: analysis.py, chat.py, gabriel.py, monitor.py, pacientes.py (e __pycache__)

# Move o que ainda não foi migrado pra um lugar diferente
# pacientes.py: vai virar dashboard/pages/pacientes.py na fase H (com adaptações)
mv pages/pacientes.py docs/historico/pages_pacientes_original.py.bak

# Remove o resto (obsoleto)
rm -rf pages/__pycache__ pages/analysis.py pages/chat.py pages/gabriel.py pages/monitor.py
rmdir pages/

# Confirma
ls pages/ 2>/dev/null
# Esperado: erro (diretório não existe)

# Idem para utils/ da raiz
mv utils/ docs/historico/utils_passo8.bak/
# Ou se preferir só deletar:
# rm -rf utils/
```

**Validação:**

```bash
ls pages/ utils/ 2>/dev/null
# Esperado: erro em ambos

# Confirma que dashboard/pages/ e dashboard/utils/ existem
ls dashboard/pages/ dashboard/utils/
# Esperado: arquivos listados
```

**Commit:**

```bash
git add -A
git commit -m "chore: remove pages/ e utils/ da raiz (obsoletos pós-integração)

Estrutura do Passo 8 (pages/ + utils/ na raiz) substituída por
dashboard/pages/ + dashboard/utils/ do upstream (fases B + F).

- pages/analysis.py, gabriel.py, monitor.py — substituídos por dashboard/pages/
- pages/chat.py — copiado pra dashboard/pages/chat.py (commit anterior)
- pages/pacientes.py — preservado em docs/historico/pages_pacientes_original.py.bak
  como referência pra fase H (vai virar dashboard/pages/pacientes.py adaptado)
- utils/ — substituído por dashboard/utils/ upstream

Estado pós-commit: raiz limpa, dashboard/ completo, app.py funcional."
```

---

### F7 — Pytest + smoke HTTP

**Objetivo:** validar que tudo continua funcionando após mudanças estruturais.

**Comandos:**

```bash
cd "$REPO"

# Pytest
pytest --tb=short 2>&1 | tail -5
# Esperado: 67 passed

# Smoke import
python -c "from dashboard.app import app, server; print('Import OK')"
# Esperado: "Import OK"

# (Opcional) Smoke HTTP — em terminal separado
# python dashboard/app.py &
# sleep 5
# curl -s http://localhost:8050/ | head -5
# curl -s http://localhost:8050/chat | head -5
# kill %1
```

**Critério de parada:** pytest abaixo de 67 verdes ou import falhando → **PARAR**.

---

## FASE G — Resolver C1: migrar `telemetry_store` → `dashboard/utils/storage`

**Objetivo da fase:** descontinuar `shared/telemetry_store.py` em favor de `dashboard/utils/storage.py` upstream. Adaptar imports em 2 arquivos do chatbot.

**Tempo estimado:** 30-45min.

---

### G1 — Identificar consumidores de `shared.telemetry_store`

**Comandos:**

```bash
cd "$REPO"

grep -rn "from shared.telemetry_store\|shared\.telemetry_store\|telemetry_store import" \
  src/ shared/ 2>/dev/null | grep -v __pycache__
# Esperado encontrar 2 arquivos: src/tools/ritmo.py, src/tools/telemetria.py
# (também shared/__init__.py mas será reescrito)
```

---

### G2 — Refatorar `src/tools/ritmo.py`

**Procedimento:**

Claude Code:

1. Lê `src/tools/ritmo.py`.
2. Localiza imports de `shared.telemetry_store`.
3. Substitui:
   ```python
   from shared.telemetry_store import latest_beat, window_summary, load_recent_beats
   ```
   por:
   ```python
   from dashboard.utils.storage import load_recent_beats  # C1: era shared.telemetry_store
   # latest_beat e window_summary recriados localmente abaixo (ver C1 do PLANO_INTEGRACAO)
   ```
4. Adiciona helpers locais (se as funções `latest_beat` e `window_summary` não existem no upstream):

```python
# C1: helpers que estavam em shared/telemetry_store.py, migrados pra cá
# (dashboard/utils/storage.py upstream tem load_recent_beats com filtro por paciente)

def latest_beat(paciente_id: str):
    """Retorna último batimento do paciente. Usa load_recent_beats do upstream."""
    df = load_recent_beats(patient=paciente_id, n=1)
    return df.to_dict("records")[0] if not df.empty else None


def window_summary(paciente_id: str, n: int = 50):
    """Sumário de janela de N batimentos. Usa load_recent_beats do upstream."""
    df = load_recent_beats(patient=paciente_id, n=n)
    if df.empty:
        return None
    return {
        "BPM_medio": df["bpm"].mean(),
        "irreg_pct": (df["status"] == "irregular").sum() / len(df) * 100,
        "n_batimentos": len(df),
    }
```

**Nota:** o `load_recent_beats` do upstream `dashboard/utils/storage.py` precisa ser inspecionado pra confirmar assinatura. Adaptar acima conforme.

---

### G3 — Refatorar `src/tools/telemetria.py`

Mesmo procedimento de G2 aplicado a `src/tools/telemetria.py`.

---

### G4 — Atualizar `shared/__init__.py`

**Comandos:**

```bash
cd "$REPO"

# Backup
cp shared/__init__.py docs/historico/shared_init_pre_C1.py.bak

# Edição: remover qualquer export de telemetry_store
# Claude Code edita shared/__init__.py removendo a linha:
# from .telemetry_store import latest_beat, window_summary, load_recent_beats, register_alias
```

Versão final esperada de `shared/__init__.py`:

```python
"""Bridge layer entre chatbot e dashboard.

Pós-integração ArrhythmiaMonitor (maio/2026):
- telemetry_store foi descontinuado em favor de dashboard.utils.storage (C1)
- paths.py e patient_registry.py preservados
"""
from .paths import PROFILES_JSON, DATA_DIR, PROJECT_ROOT
from .patient_registry import (
    list_patients,
    get_patient,
    patient_exists,
    create_patient,
    invalidate_caches,
)

__all__ = [
    "PROFILES_JSON",
    "DATA_DIR",
    "PROJECT_ROOT",
    "list_patients",
    "get_patient",
    "patient_exists",
    "create_patient",
    "invalidate_caches",
]
```

---

### G5 — Deletar `shared/telemetry_store.py`

**Comandos:**

```bash
cd "$REPO"

# Move pra histórico em vez de deletar (pode ser útil consultar)
git mv shared/telemetry_store.py docs/historico/shared_telemetry_store_pre_C1.py.bak

# Confirma
ls shared/
# Esperado: __init__.py, paths.py, patient_registry.py
```

---

### G6 — Pytest verde + smoke

**Comandos:**

```bash
cd "$REPO"

pytest --tb=short 2>&1 | tail -5
# Esperado: 67 passed

# Smoke import
python -c "
from src.tools.ritmo import analisar_ritmo_cardiaco
from src.tools.telemetria import consultar_telemetria_dashboard
from dashboard.utils.storage import load_recent_beats
from shared.patient_registry import list_patients
print('Imports OK pós-C1')"
# Esperado: "Imports OK pós-C1"
```

**Critério de parada:** se pytest cair, **PARAR**. Reverter via `git reset --hard HEAD~1` e diagnosticar. Algum teste depende de `shared.telemetry_store` com assinatura que não bate com `load_recent_beats` upstream.

**Commit:**

```bash
git add -A
git commit -m "refactor(C1): descontinua shared/telemetry_store em favor de dashboard.utils.storage

Resolve C1 das decisões da integração ArrhythmiaMonitor.

Mudanças:
- src/tools/ritmo.py: imports de shared.telemetry_store → dashboard.utils.storage
- src/tools/telemetria.py: idem
- shared/__init__.py: remove exports de telemetry_store
- shared/telemetry_store.py: movido pra docs/historico/ como backup

Helpers latest_beat() e window_summary() recriados em src/tools/ritmo.py
usando load_recent_beats do upstream como base (5 linhas cada).

Pytest 67/67 verde após refactor."
```

---

## FASE H — Implementar C2 + C13: Meu Perfil + dropdown global

**Objetivo da fase:** criar Meu Perfil em `perfis_clinicos.json`, criar `dashboard/pages/meu_perfil.py`, criar `dashboard/pages/pacientes.py` adaptado, implementar dropdown global Gabriel/Meu Perfil no topbar.

**Tempo estimado:** 2-3h.

---

### H1 — Adicionar Meu Perfil em `perfis_clinicos.json`

**Procedimento:**

Claude Code abre `data/mocks/perfis_clinicos.json` e adiciona uma entrada nova:

```json
{
  "id": "MEU_PERFIL",
  "nome": null,
  "idade": null,
  "sexo": null,
  "plano": "Care Plus",
  "condicoes_ativas": [],
  "medicacoes_ativas": [],
  "alergias": [],
  "score_risco_cardiovascular": "a_avaliar",
  "consultas": {
    "ultima": null,
    "proxima": null
  },
  "exames_recentes": [],
  "sinais_vitais_ultimo_registro": {},
  "criado_em": "2026-05-30T00:00:00",
  "origem": "perfil_proprio",
  "_meta": {
    "descricao": "Perfil do usuário do sistema. Editável via /pacientes ou via chatbot.",
    "csv_telemetria": "data/cardiac_data.csv"
  }
}
```

**Nota:** O usuário pode preencher idade/sexo/etc. depois via chatbot (`criar_perfil_paciente`) ou editando o JSON direto.

**Validação:**

```bash
cd "$REPO"

python -c "
import json
with open('data/mocks/perfis_clinicos.json') as f:
    data = json.load(f)
ids = [b['id'] for b in data['beneficiarios']]
print('IDs:', ids)
assert 'MEU_PERFIL' in ids, 'MEU_PERFIL não encontrado'
print('OK')"
# Esperado: MEU_PERFIL listado + "OK"

pytest --tb=short 2>&1 | tail -3
# Esperado: 67 passed (perfil novo não deve quebrar nada)
```

---

### H2 — Criar `dashboard/pages/meu_perfil.py`

**Procedimento:**

Claude Code cria página Dash simplificada baseada no template do `gabriel.py` (mas com layout reduzido — só dados essenciais). Estrutura:

```python
"""Página /meu-perfil — prontuário simplificado do usuário."""
from __future__ import annotations

import dash
from dash import html, dcc, callback, Input, Output
from shared.patient_registry import get_patient

dash.register_page(__name__, path="/meu-perfil", name="Meu Perfil", order=4)


def _render_perfil(perfil: dict) -> html.Div:
    if not perfil:
        return html.Div("Perfil não encontrado.", className="hud-info")

    return html.Div([
        html.H1(perfil.get("nome") or "Sem nome", className="hud-hero__title"),
        html.Div([
            html.Span("ID: "), html.Strong(perfil["id"]),
            html.Span(" · "),
            html.Span("Idade: "), html.Strong(str(perfil.get("idade") or "—")),
            html.Span(" · "),
            html.Span("Sexo: "), html.Strong(perfil.get("sexo") or "—"),
        ], className="hud-patient__meta"),
        html.H2("Condições"),
        html.Ul([html.Li(c.get("nome", c) if isinstance(c, dict) else c)
                 for c in perfil.get("condicoes_ativas", [])])
                if perfil.get("condicoes_ativas") else html.Div("Nenhuma registrada."),
        html.H2("Medicações"),
        html.Ul([html.Li(m.get("nome", m) if isinstance(m, dict) else m)
                 for m in perfil.get("medicacoes_ativas", [])])
                if perfil.get("medicacoes_ativas") else html.Div("Nenhuma registrada."),
        html.Div([
            html.A("Editar via chatbot", href="/chat", className="hud-btn hud-btn--ghost"),
        ], style={"marginTop": "24px"}),
    ], className="hud-page")


def layout():
    perfil = get_patient("MEU_PERFIL")
    return _render_perfil(perfil)
```

**Validação:**

```bash
python -c "from dashboard.pages.meu_perfil import layout; print(layout())" 2>&1 | head -5
# Esperado: HTML renderizado sem erro
```

---

### H3 — Criar `dashboard/pages/pacientes.py` adaptado

**Procedimento:**

Inspirado em `pages_pacientes_original.py.bak` (do backup feito em F6), mas adaptado pra:
- Listar apenas Gabriel e Meu Perfil (sem outros mocks BENEF-CV-*).
- Cards clicáveis que mudam o `dcc.Store(id="perfil-ativo")` global (H4).
- Links pra `/gabriel` (Gabriel) e `/meu-perfil` (Meu Perfil).

Estrutura:

```python
"""Página /pacientes — gestão de perfil ativo."""
from __future__ import annotations

import dash
from dash import html, dcc, callback, Input, Output, State
from shared.patient_registry import get_patient

dash.register_page(__name__, path="/pacientes", name="Pacientes", order=6)

PERFIS_DISPONIVEIS = ["GABRIEL", "MEU_PERFIL"]


def _card_perfil(perfil_id: str, ativo: bool):
    perfil = get_patient(perfil_id)
    if not perfil:
        return html.Div(f"Perfil {perfil_id} não encontrado", className="hud-warn")
    nome = perfil.get("nome", perfil_id)
    idade = perfil.get("idade", "—")
    rota = "/gabriel" if perfil_id == "GABRIEL" else "/meu-perfil"
    classe = "hud-panel pacientes-card" + (" pacientes-card--ativo" if ativo else "")
    return html.Div([
        html.H3(nome),
        html.Div(f"Idade: {idade}"),
        html.Div(f"ID: {perfil_id}", className="hud-text-muted"),
        html.A("Ver prontuário", href=rota, className="hud-btn hud-btn--ghost"),
        html.Button("Definir como ativo", id={"type": "btn-perfil", "id": perfil_id},
                    className="hud-btn"),
    ], className=classe)


def layout():
    return html.Div([
        html.H1("Gestão de Perfis"),
        html.P("Selecione um perfil ativo. A seleção é refletida no topbar e nas páginas."),
        html.Div(id="lista-cards-perfis", children=[
            _card_perfil(pid, ativo=(pid == "GABRIEL"))
            for pid in PERFIS_DISPONIVEIS
        ], className="grid grid-2col"),
    ], className="hud-page")
```

---

### H4 — Adicionar `dcc.Store(id="perfil-ativo")` global em `dashboard/app.py`

**Procedimento:**

Claude Code adiciona ao layout global do `dashboard/app.py` (logo após o `dcc.Store(id="session-data")` da Fase D):

```python
# C13: perfil ativo (Gabriel ou MEU_PERFIL) — afeta dropdown e páginas
dcc.Store(id="perfil-ativo", data={"id": "GABRIEL"}, storage_type="local"),
```

`storage_type="local"` persiste entre sessões do browser.

---

### H5 — Adicionar dropdown global no topbar

**Procedimento:**

Localiza a função `_topbar()` (ou similar) no `dashboard/app.py` upstream. Adiciona dropdown logo após os nav_links:

```python
def _topbar():
    return html.Header([
        html.Div([
            html.Span("CARDIO MONITOR | HUD", className="hud-topbar__brand"),
            html.Nav(_nav_links(), className="hud-topbar__nav"),
            # C13: dropdown perfil ativo
            html.Div([
                dcc.Dropdown(
                    id="topbar-perfil-dropdown",
                    options=[
                        {"label": "Gabriel", "value": "GABRIEL"},
                        {"label": "Meu Perfil", "value": "MEU_PERFIL"},
                    ],
                    value="GABRIEL",
                    clearable=False,
                    className="hud-topbar__dropdown",
                    style={"minWidth": "150px"},
                ),
            ], className="hud-topbar__perfil"),
        ], className="hud-topbar"),
    ], className="hud-topbar-wrapper")
```

Callback pra sincronizar dropdown com `perfil-ativo` Store:

```python
@callback(
    Output("perfil-ativo", "data"),
    Input("topbar-perfil-dropdown", "value"),
    prevent_initial_call=True,
)
def _atualizar_perfil_ativo(perfil_id):
    return {"id": perfil_id}
```

---

### H6 — Conectar telemetria por perfil (Gabriel → gabriel_data.csv, Meu Perfil → cardiac_data.csv)

**Procedimento:**

`dashboard/pages/monitor.py` e `dashboard/pages/analysis.py` upstream lêem do CSV. Precisa de adaptação leve: ler o `perfil-ativo` Store e escolher CSV correspondente.

**Implementação mínima:** ajustar callback principal de `monitor.py` (após inspeção) pra filtrar pelo `perfil-ativo`:

```python
# Adicionar State no callback principal:
State("perfil-ativo", "data"),

# No callback, escolher CSV:
def _csv_path(perfil):
    return "data/gabriel_data.csv" if perfil["id"] == "GABRIEL" else "data/cardiac_data.csv"
```

**Nota:** se mexer em `monitor.py` viola fidelidade. Alternativa: deixar `monitor.py` upstream intacto e fazer adaptação via wrapper de `load_recent_beats` que checa `perfil-ativo`. **Decisão a tomar no momento da execução** — depende do quanto o `monitor.py` upstream é parametrizável.

---

### H7 — Pytest + smoke H

**Comandos:**

```bash
cd "$REPO"

pytest --tb=short 2>&1 | tail -5
# Esperado: 67+ passed (talvez mais se adicionarmos testes pra Meu Perfil)

# Smoke import
python -c "
from dashboard.pages.meu_perfil import layout as l_meu
from dashboard.pages.pacientes import layout as l_pac
print(l_meu())
print('---')
print(l_pac())" 2>&1 | head -10
# Esperado: dois layouts renderizados sem erro
```

**Commit:**

```bash
git add -A
git commit -m "feat(perfil): implementa C2 + C13 — Meu Perfil + dropdown global

C2 — Gabriel canônico + Meu Perfil:
- data/mocks/perfis_clinicos.json: adiciona entrada MEU_PERFIL placeholder
- dashboard/pages/meu_perfil.py: layout simplificado próprio (rota /meu-perfil)
- gabriel.py upstream permanece 100% intacto (628 linhas)

C13 — Dropdown global:
- dashboard/app.py: dcc.Store(perfil-ativo) global + dropdown topbar
- dashboard/pages/pacientes.py: gestão de 2 perfis (Gabriel + Meu Perfil)
- Telemetria diferenciada:
  - Gabriel -> data/gabriel_data.csv
  - Meu Perfil -> data/cardiac_data.csv

O usuário poderá preencher dados do Meu Perfil via /chat (tool
criar_perfil_paciente) ou editando o JSON direto."
```

---

## FASE I — Smoke E2E final + pytest verde

**Objetivo da fase:** validar integração completa. 6 rotas com HTTP 200. Pytest 67+ verde. Chatbot funcionando. Dropdown trocando perfis.

**Tempo estimado:** 1h.

---

### I1 — Pytest completo

**Comandos:**

```bash
cd "$REPO"

pytest -v --tb=short 2>&1 | tail -20
# Esperado: 67+ passed
```

**Critério de parada:** abaixo de 67 verdes → diagnosticar e corrigir antes de seguir.

---

### I2 — Smoke HTTP 200 em todas as rotas

**Comandos:**

```bash
cd "$REPO"

# Sobe app
python dashboard/app.py &
APP_PID=$!
sleep 8

# Testa cada rota
for rota in "/" "/chat" "/monitor" "/analise" "/gabriel" "/meu-perfil" "/pacientes"; do
  status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8050$rota")
  echo "$rota -> $status"
done

# Mata o app
kill $APP_PID 2>/dev/null
wait $APP_PID 2>/dev/null
```

**Validação esperada:**

```
/ -> 200
/chat -> 200
/monitor -> 200
/analise -> 200
/gabriel -> 200
/meu-perfil -> 200
/pacientes -> 200
```

**Critério de parada:** qualquer 404/500 → diagnosticar antes de seguir.

---

### I3 — Smoke manual via browser (usuário)

**Objetivo:** validações que só o usuário pode fazer no browser.

**Checklist (passo a passo manual):**

1. Abrir `http://localhost:8050/` — confirma `home.py` upstream renderizado.
2. Topbar tem links: HOME, MONITOR, ANALISE, GABRIEL, MEU PERFIL, PACIENTES, CHAT.
3. Topbar tem dropdown de perfil com Gabriel selecionado.
4. Trocar dropdown pra "Meu Perfil" — confirmar que muda algo (visualmente o nome no header ou no /monitor).
5. Ir pra `/chat` — chatbot abre com input + área de conversa.
6. Enviar mensagem teste no chat ("oi") — chatbot responde.
7. Voltar pra `/monitor` — gráficos renderizam.
8. Voltar pra `/chat` — conversa preservada (dcc.Store session-data funcionando).
9. Console DevTools — sem erros vermelhos.
10. Trocar dropdown de volta pra Gabriel — confirmar reversão.

---

### I4 — Commit final da integração

**Comandos:**

```bash
cd "$REPO"

git log --oneline
# Listar todos os commits do branch

git status
# Esperado: clean

git commit --allow-empty -m "test(integracao): smoke E2E verde — integração ArrhythmiaMonitor concluída

Validações finais:
- Pytest 67+ verde
- 7 rotas HTTP 200: /, /chat, /monitor, /analise, /gabriel, /meu-perfil, /pacientes
- Chatbot funcionando em /chat com session preservada entre navegações
- Dropdown global Gabriel/Meu Perfil sincronizando perfil-ativo Store
- API ML como referência (não roda local — Azure)
- Simulador C++ opt-in disponível com binário pre-compilado
- Email alerts com flag desabilitada (sem vazamento)

Branch integracao-arrhythmiamonitor pronto.

Decisão de merge pra main ou push pra remoto do ArrhythmiaMonitor:
fora do escopo desta assistência. Decisão futura do usuário."
```

---

## Resumo de fases e commits esperados

| Fase | Sub-passos | Commits | Tempo |
|------|------------|---------|-------|
| A — Setup + branch | A1-A4 | 1 (scaffolding) | 30-45min |
| B — Upstream fiel | B1-B5 | 3 (dashboard, api, simulador + README) | 45min-1h |
| C — Chatbot + docs históricos | C1-C3 | 2 (docs histórico, agent README) | 15-30min |
| D — Adaptar app.py | D1-D6 | 1 (fixes 8.5 + chat integration) | 45min-1h |
| E — Fixes CSS 8.9 | E1-E2 | 1 (S1-S4) | 30min |
| F — Trazer chat.py | F1-F7 | 2 (chat.py + cleanup raiz) | 1h |
| G — Resolver C1 | G1-G6 | 1 (descontinuar telemetry_store) | 30-45min |
| H — Meu Perfil + dropdown | H1-H7 | 1 (C2 + C13) | 2-3h |
| I — Smoke final | I1-I4 | 1 (smoke verde) | 1h |

**Total:** ~13 commits, 7-12h de trabalho.

---

## Critérios de gate por fase

Cada fase precisa atender antes de seguir pra próxima:

| Gate | Critério |
|------|----------|
| Após A | Branch criado, pytest 67/67, working tree clean |
| Após B | Cópias diffs zero contra upstream, pytest 67/67 |
| Após C | docs/historico/ com 12 arquivos, agent/README.md criado, pytest 67/67 |
| Após D | `from dashboard.app import app` sem erro, pytest 67/67 |
| Após E | style.css com bloco FIX 8.9, pytest 67/67 |
| Após F | dashboard/pages/chat.py registrado, pages/ raiz vazio, pytest 67/67 |
| Após G | shared/telemetry_store.py descontinuado, imports atualizados, pytest 67/67 |
| Após H | Meu Perfil + dropdown funcionais, pytest 67+/67+ |
| Após I | 7 rotas HTTP 200, smoke browser OK |

---

## Pontos de rollback

A qualquer momento, se algo der ruim:

```bash
# Reverter último commit (preserva working tree)
git reset HEAD~1

# Reverter último commit (descarta mudanças)
git reset --hard HEAD~1

# Reverter pra N commits atrás
git reset --hard HEAD~N

# Voltar pro estado inicial do branch (descarta tudo desde A1)
git reset --hard $(git merge-base main integracao-arrhythmiamonitor)

# Deletar branch e começar de novo (do main)
git checkout main
git branch -D integracao-arrhythmiamonitor
git checkout -b integracao-arrhythmiamonitor
```

**Garantia:** `main` permanece intocada em qualquer cenário de rollback.

---

## Notas finais

### Variáveis de ambiente necessárias (resumo)

Pós-integração, `.env` precisa conter:

```bash
# Chatbot (do blua-cardio)
DASHSCOPE_API_KEY=...
QWEN_DASHSCOPE_MODEL=qwen-plus
LANGSMITH_API_KEY=...  # opcional

# Dashboard upstream (ArrhythmiaMonitor)
AZURE_STORAGE_CONNECTION_STRING=...  # se for usar Blob
API_URL=https://api-predicaocardiaca-cpc0bufrhmd7ade4.brazilsouth-01.azurewebsites.net

# Email alerts (C6, desabilitado por default)
BLUA_EMAIL_ALERTS=disabled  # mudar pra "enabled" pra ativar
EMAIL_REMETENTE=...
SENHA_REMETENTE=...
EMAIL_DESTINATARIO_1=...
```

### Sessões recomendadas

Se for fazer em múltiplas sessões:

- **Sessão 1 (2-3h):** Fases A + B + C.
- **Sessão 2 (2-3h):** Fases D + E + F.
- **Sessão 3 (2-3h):** Fase G + H1-H4.
- **Sessão 4 (2-3h):** Fase H5-H7 + I.

Cada sessão termina em commit verde. Próxima sessão começa do commit anterior.

### Out-of-scope explícito

Estas coisas **NÃO** estão neste plano:

- Push do branch `integracao-arrhythmiamonitor` pro remoto `ArrhythmiaMonitor` no GitHub.
- Merge do branch `integracao-arrhythmiamonitor` pra `main`.
- Features pendentes do README do ArrhythmiaMonitor (agendamento Blob, relatório registros, dúvidas medicamentos) — sessão separada futura.
- Atualização do README.md raiz (usuário faz depois — C12).
- Setup Azure Blob local (chatbot continua usando JSON local pra agendamentos via R3).

---

**Fim do plano.**

**Estado esperado ao fim:** branch `integracao-arrhythmiamonitor` no repo `blua-cardio` com integração completa, validada por pytest + smoke, pronta pra decisões futuras do usuário.
