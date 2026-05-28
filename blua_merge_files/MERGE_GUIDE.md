# Blua Merge Guide — chatbot ✕ dashboard

Guia passo-a-passo para fundir **BluaDiagnostics** (chatbot LangGraph) com
**cardiac_dashboard_dash** (CardioMonitor PPG) em um único app coeso.

A integração é mais simples do que parece porque o chatbot já tem uma tool
projetada para receber exatamente o output do dashboard — o README do Blua
inclusive declara isso como roadmap.

---

## Layout final

```
unified_blua/
├── app/
│   ├── unified_app.py        # NOVO  ← entrada única (porta 8050)
│   ├── pages/                # NOVO  ← Dash use_pages
│   │   ├── chat.py           # converter app/dash_app.py para isso
│   │   ├── home.py           # vem do dashboard
│   │   ├── monitor.py        # vem do dashboard
│   │   ├── analysis.py       # vem do dashboard
│   │   └── gabriel.py        # vem do dashboard
│   └── assets/               # mesclar os dois /assets (css + alert.wav)
├── src/                      # chatbot original — quase intacto
│   ├── agents/
│   ├── tools/
│   │   ├── ritmo.py          # SUBSTITUIR pela versão pós-merge
│   │   ├── criar_perfil.py   # NOVO
│   │   ├── telemetria.py     # NOVO
│   │   ├── __init__.py       # ATUALIZAR (exporta as 2 novas)
│   │   └── ... (resto intacto)
│   ├── graph.py
│   └── ...
├── shared/                   # NOVO ← ponte
│   ├── __init__.py
│   ├── paths.py
│   ├── patient_registry.py
│   └── telemetry_store.py
├── utils/                    # vem do dashboard (theme, storage, serial_reader, analysis)
├── data/
│   ├── cardiac_data.csv      # do dashboard
│   ├── gabriel_data.csv      # do dashboard
│   └── mocks/
│       ├── perfis_clinicos.json   # do chatbot (extensível agora)
│       └── ...
├── prompts/                  # do chatbot
├── knowledge_base/           # do chatbot
├── chroma_db/                # do chatbot (regenerado por scripts/index_kb.sh)
└── requirements.txt          # mesclado (ver seção 8)
```

---

## Passo 1 — Criar a raiz unificada

```bash
mkdir unified_blua && cd unified_blua

# Copiar o chatbot inteiro como base
cp -r /caminho/BluaDiagnostics_Sprint-main/. .

# Adicionar os módulos do dashboard que ainda não existem
cp -r /caminho/cardiac_dashboard_dash/utils ./utils
cp /caminho/cardiac_dashboard_dash/data/gabriel_data.csv ./data/
cp /caminho/cardiac_dashboard_dash/data/cardiac_data.csv ./data/

# Manter o esp32/ separado caso queira gravar firmware
cp -r /caminho/cardiac_dashboard_dash/esp32 ./esp32
```

> O chatbot vira a base porque ele é maior e tem mais infraestrutura
> (langgraph, RAG, agentes, testes). O dashboard contribui com `utils/`
> e os dois CSVs.

## Passo 2 — Instalar a ponte `shared/`

Copiar a pasta `shared/` deste pacote para a raiz do projeto:

```
unified_blua/shared/
├── __init__.py
├── paths.py
├── patient_registry.py
└── telemetry_store.py
```

Validar:

```bash
python -c "from shared import list_patients, latest_beat; \
print(len(list_patients()), 'pacientes'); \
print(latest_beat('BENEF-MARIA'))"
```

Deve imprimir o número de pacientes e o último batimento do Gabriel
(o dashboard usa esse CSV como dataset de referência para BENEF-MARIA
através do alias mapeado em `telemetry_store.py`).

## Passo 3 — Substituir as 3 tools

```bash
cp src/tools/ritmo.py src/tools/ritmo.py.sprint2_backup
cp <pacote>/src/tools/ritmo.py        src/tools/ritmo.py
cp <pacote>/src/tools/criar_perfil.py src/tools/criar_perfil.py
cp <pacote>/src/tools/telemetria.py   src/tools/telemetria.py
cp <pacote>/src/tools/__init__.py     src/tools/__init__.py
```

Rodar os testes existentes — devem continuar passando (49 verdes):

```bash
pytest tests/ -v
```

A nova `ritmo.py` é totalmente retrocompatível: a assinatura legada
(`timestamp_s, IBI_ms, BPM, media_IBI, desvio_medio, batimentos_anormais`)
continua funcionando exatamente como na Sprint 1. O argumento novo
`paciente_id` é opcional.

## Passo 4 — Registrar a página do chatbot

Converter `app/dash_app.py` em `app/pages/chat.py`. A conversão é mecânica:

```python
# topo do app/pages/chat.py
import dash
dash.register_page(__name__, path="/", name="Chat", order=1)

# Tudo de dash_app.py de "app.layout = ..." em diante vira:
layout = html.Div([...mesmo conteúdo de antes do app.layout...])

# Importante: os @callback continuam funcionando — dash detecta a sintaxe
# decorada e registra global. NÃO use @app.callback (com `app` específico
# da página) — use @callback de dash.
```

> Os callbacks já usam `from dash import callback` (não `@app.callback`),
> então a conversão é literalmente: comentar a linha `app = Dash(...)` e
> a `app.layout = ...`, trocar para `layout = ...`, adicionar o
> `register_page` no topo. 5 minutos de trabalho.

Repetir para as páginas do dashboard — elas já usam `dash.register_page`
porque o `cardiac_dashboard_dash/app.py` original usa `use_pages=True`. É
só **copiar** `pages/` do dashboard para `app/pages/` do projeto unificado.

## Passo 5 — Trocar o entrypoint

Substituir `app/dash_app.py` por `app/unified_app.py` (fornecido neste
pacote). Roda na mesma porta 8050:

```bash
python app/unified_app.py
```

Saída esperada:

```
[unified_app] Iniciando em http://localhost:8050
[unified_app] Backend: dashscope · Modelo: qwen-plus
[unified_app] Páginas registradas:
  /                    → app.pages.chat
  /home                → app.pages.home
  /monitor             → app.pages.monitor
  /analise             → app.pages.analysis
  /gabriel             → app.pages.gabriel
```

## Passo 6 — Atualizar o prompt do agente de checkup

`prompts/agente_checkup.md` precisa saber das duas novas tools. Adicionar
ao final do prompt existente:

```markdown
## Ferramentas adicionais pós-merge

### criar_perfil_paciente
Use quando um usuário **novo** (sem BENEF-XXX no histórico) quer começar
o acompanhamento. Coleta nome, idade, sexo, condições e medicações em
linguagem natural — depois CHAMA esta tool em duas etapas:

1. Sem `confirmacao=True` → recebe um preview, mostre ao usuário e PEÇA
   confirmação verbal explícita.
2. Após o usuário confirmar → chame de novo com `confirmacao=True`.

Nunca chame com `confirmacao=True` na primeira vez. O 2-step protege
contra criação acidental de perfis baseada em hallucination.

### consultar_telemetria_dashboard
Use ANTES de qualquer análise de ritmo quando o paciente já tem perfil.
Devolve um sumário da janela recente (BPM médio, % regular/irregular)
SEM emitir veredito. Use isto para "me dá os números" e em seguida
chame `analisar_ritmo_cardiaco(paciente_id=...)` para o veredito clínico.

### analisar_ritmo_cardiaco — modo live
Sempre que houver `paciente_id` conhecido, chame com `paciente_id="BENEF-XXX"`
em vez de passar IBI/BPM manualmente. A tool agora puxa a leitura real do
sensor PPG do CardioMonitor e contextualiza a observação com o histórico
do paciente.
```

## Passo 7 — Atualizar o dashboard para usar o registro compartilhado

No dashboard original o dropdown de pacientes em `pages/monitor.py` lê de
uma lista hard-coded. Trocar por:

```python
# em pages/monitor.py
from shared.patient_registry import list_patients

def _opcoes_pacientes():
    return [{"label": f"{p['nome']} ({p['id']})", "value": p["id"]}
            for p in list_patients()]

# Usar _opcoes_pacientes() no dcc.Dropdown options.
# Como o callback recria opções ao trocar de página, novos pacientes
# criados pelo chatbot aparecem automaticamente sem reload.
```

## Passo 8 — Mesclar requirements

```txt
# Combinado — sem duplicatas
openai>=1.50.0
langgraph>=0.2.50
langchain-text-splitters>=0.3.0
chromadb>=0.5.0
sentence-transformers>=3.0.0
numpy>=1.26.0
pydantic>=2.8.0
typing-extensions>=4.12.0
structlog>=24.4.0
python-dotenv>=1.0.1
tenacity>=9.0.0
regex>=2024.0.0
dash>=2.18.0
dash-bootstrap-components>=1.6.0
streamlit>=1.35.0          # fallback opcional
langsmith>=0.1.0
matplotlib>=3.8.0
pytest>=8.0.0
# do dashboard:
plotly>=5.18               # já vem com dash mas pin explícito
pandas>=2.0
pyserial>=3.5              # ESP32 serial reader
```

## Passo 9 — Smoke test do sistema unificado

```bash
# 1. Bridge funciona com dados reais
python -c "from shared import latest_beat, list_patients; \
print(len(list_patients()), 'pacientes'); \
print('último BPM:', latest_beat('BENEF-MARIA')['BPM'])"

# 2. Pytest do chatbot continua verde
pytest tests/ -v

# 3. Tool nova funciona standalone
python -c "from src.tools.criar_perfil import criar_perfil_paciente; \
print(criar_perfil_paciente('Teste', 30, 'masculino'))"

# 4. App sobe e serve as 5 páginas
python app/unified_app.py &
sleep 5
curl -s http://localhost:8050/ | grep -q 'Blua' && echo OK
curl -s http://localhost:8050/monitor | grep -q -i 'monitor' && echo OK
kill %1
```

---

## Demo flow ponta a ponta

Cenário que exercita TODA a integração:

1. **Usuário acessa http://localhost:8050/**
   Página /chat carrega. Chatbot pergunta nome.
2. **Usuário:** "Sou o Filipe, 30 anos, masculino, tenho hipertensão e tomo
   Losartana 50mg."
3. **Chatbot** chama `criar_perfil_paciente(...)` — sem confirmação. Tool
   devolve preview. Chatbot pergunta "Confirma esses dados?"
4. **Usuário:** "Sim, pode criar."
5. **Chatbot** chama de novo com `confirmacao=True`. Tool grava em
   `perfis_clinicos.json`, gera `BENEF-NEW-001`. Chatbot informa o ID e
   sugere "vamos medir seu ritmo cardíaco agora."
6. **Usuário** clica em `MONITOR` no topbar.
7. **Página /monitor** carrega. Dropdown agora inclui "Filipe Teste
   (BENEF-NEW-001)" automaticamente (registro compartilhado). Usuário
   seleciona e clica em `INICIAR SIMULAÇÃO`.
8. Durante a sessão, beats são gravados em `cardiac_data.csv` com
   `patient=BENEF-NEW-001`.
9. Usuário volta para /chat e digita "como tá meu ritmo?"
10. **Chatbot** roteado para o agente de check-up, chama
    `analisar_ritmo_cardiaco(paciente_id="BENEF-NEW-001")`. Tool puxa
    último batimento + janela de 5min do `cardiac_data.csv`, e
    contextualiza a observação com a condição HAS do passo 2.
11. **Resposta:** *"Ritmo dentro do esperado. BPM médio 75 na janela de
    5min. Paciente 30a — Hipertensão arterial sistêmica. Continue o
    monitoramento."*

Ponta a ponta. Zero CSV mockado no LLM, zero perfil hardcoded.

---

## Ideias para harmonia perfeita (pós-MVP)

Tudo abaixo é incremental sobre o que já está montado:

1. **Cross-link bidirecional na UI.** Cada bolha do chat que cita
   batimentos vira clicável → leva a `/monitor?patient=BENEF-XXX&t=...`.
   No /monitor um botão `EXPLICAR COM CHATBOT` envia o sumário corrente
   como mensagem pré-preenchida em `/chat`.

2. **Push de eventos do dashboard → chatbot.** Quando o `/monitor` detecta
   3 segundos seguidos de status `irregular`, dispara um `dcc.Store`
   evento que o chat consome no próximo turno como "contexto sticky" —
   o agente pode proativamente alertar.

3. **Pre-safety enriquecido com telemetria.** O `pre_safety_check`
   atualmente é só de texto. Para perguntas como "estou bem agora?",
   inspecionar `latest_beat(paciente_id)` ANTES do supervisor — se vier
   irregular + sintomas, vai direto para `escalada_humana` sem passar
   pelo LLM.

4. **Cache de janela na sessão.** Cada `processar_mensagem` no
   `unified_app.py` pode pré-carregar `window_summary(beneficiario)` no
   `session-data` `dcc.Store`. As tools `ritmo`/`telemetria` então usam
   o cache em vez de reler o CSV — ganho de ~30ms por turno.

5. **Eval set ampliado.** Os 35 casos atuais não exercitam a tool
   `criar_perfil_paciente` nem o caminho live de `ritmo`. Adicionar
   ao menos 5 casos:
   - "Quero começar acompanhamento, sou novo"
   - "Como estão meus batimentos agora?" (depende de live mode)
   - "Cadastra meu pai" (alguém criando perfil para terceiro — recusar
     ou pedir consentimento?)
   - "Apaga meu perfil" (não implementado de propósito — testar recusa)
   - "Mostra a tela do monitor" (cross-app — orientar via prompt)

6. **Patient-aware RAG.** O retriever atual usa MMR + filtros por
   categoria. Para perguntas com paciente conhecido, pode boostear
   chunks cuja categoria casa com `condicoes_ativas` do perfil.
   Exemplo: paciente com FA → chunks de `cardiologia_estratificacao_risco`
   sobem no rank.

7. **LangSmith traces com paciente_id como tag.** No
   `executar_turno`, passar `tags=[f"patient:{beneficiario_id}"]` e
   `metadata={"latest_bpm": ..., "irreg_pct": ...}` para que a aba
   de monitoramento da LangSmith permita filtrar por paciente e por
   estado de telemetria.

8. **ESP32 → MQTT bridge (opcional).** Hoje o ESP32 fala JSON via serial.
   Para deployment real (vários sensores), trocar serial por MQTT e ter
   o `unified_app` se subscrever — escalável.

---

## Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Race entre chatbot escrevendo `perfis_clinicos.json` e dashboard lendo | Write-then-rename atômico já implementado em `patient_registry.py` |
| LRU cache do `consultar_historico_paciente` ficando stale após `create_patient` | Invalidado automaticamente — `patient_registry.create_patient` chama `cache_clear` |
| Concorrência multi-worker (gunicorn `-w N`) | `threading.RLock` cobre 1 worker. Para N > 1, usar `fcntl.flock` no arquivo (roadmap) ou migrar para SQLite |
| ESP32 grava com `patient="live"` mas chatbot pergunta por BENEF-NEW-001 | Mapa `_ALIAS` em `telemetry_store.py` resolve, ou modificar /monitor para gravar com o ID do dropdown |
| Tool `criar_perfil_paciente` chamada com hallucinated data | 2-step `confirmacao=True` força confirmação verbal antes de gravar |
