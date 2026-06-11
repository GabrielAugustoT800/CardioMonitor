# Especificação Técnica — App Médico CardioMonitor

Visão do médico (Dr. Robert Chase) sobre o mesmo sistema do paciente. Construído reusando o vocabulário visual existente (helpers de `theme.py`, classes HUD), com accent **verde** distinguindo do azul do paciente.

Princípio-guia: **a IA organiza e apresenta, o médico decide.** Toda feature é assistiva, nunca substitutiva.

---

## 1. Arquitetura

### 1.1 App único, papel decide a experiência

Um só servidor Dash multi-pages. O login roteia por papel (médico/paciente). Código organizado em módulos por papel para isolamento e clareza.

```
dashboard/pages/
├── (paciente — existentes, a unificar)
│   ├── home.py            /
│   ├── monitor.py         /monitor
│   ├── analysis.py        /analise
│   ├── prontuario.py      /prontuario   ← NOVO (substitui gabriel.py + meu_perfil.py)
│   ├── chat.py            /chat
│   └── pacientes.py       /pacientes
└── medico/                ← NOVO grupo
    ├── login.py           /login
    ├── caseload.py        /medico/caseload
    ├── alertas.py         /medico/alertas
    └── prontuario_medico.py  /medico/paciente/<id>  (ou via dropdown)
```

> Nota técnica: o nav é auto-gerado de `dash.page_registry` ordenado por `order`. Páginas do médico precisam de controle de visibilidade — não devem aparecer no nav do paciente e vice-versa. Ver §6 (navegação por papel).

### 1.2 Papel ativo

Um `dcc.Store(id="papel-ativo", storage_type="session")` guarda o papel logado (`"medico"` ou `"paciente"`). Definido no login, lido pelos callbacks de navegação e visibilidade.

### 1.3 Render de prontuário compartilhado

O núcleo do prontuário (dados do paciente: identidade, telemetria, condições, medicações, alergias, consultas) é **um render data-driven reutilizável**, parametrizado por papel:

- **Paciente (azul):** prontuário sem anotações clínicas, sem aprovação de rascunhos.
- **Médico (verde):** prontuário + seção de anotações clínicas + card de aprovação de rascunhos.

Função central (em `utils/` ou módulo compartilhado):
```python
def render_prontuario(paciente_id, papel="paciente"):
    paciente = get_patient(paciente_id)
    blocos = [
        _bloco_identidade(paciente, papel),
        _bloco_telemetria(paciente_id),       # gráficos PPG (reusa analysis)
        _bloco_condicoes(paciente),
        _bloco_medicacoes(paciente),
        _bloco_alergias(paciente),
        _bloco_consultas(paciente),
    ]
    if papel == "medico":
        blocos.append(_bloco_anotacoes(paciente))         # só médico
        blocos.append(_bloco_aprovacao_rascunho(paciente)) # só médico
    return html.Div(blocos)
```

O accent muda por papel: `PRIMARY_BLUE` (paciente) vs `SUCCESS`/verde (médico).

---

## 2. Login (`/login`)

### 2.1 Visual

Cor: branca/neutra (ponto de entrada). Card centralizado com:
- Marca CardioMonitor (mesmo "C+" mark da topbar).
- Campo "Usuário".
- Campo "Senha" (visual, **não valida**).
- Botão "Entrar".
- Instrução: digite `medico` ou `paciente`.

Montado com a estética HUD (cantos quadrados, mono nos labels), mas accent neutro.

### 2.2 Lógica (seletor de papel disfarçado de login)

```python
def _processar_login(usuario, senha):
    u = (usuario or "").strip().lower()
    if u == "medico":
        # set papel-ativo = "medico", redireciona /medico/caseload
    elif u == "paciente":
        # set papel-ativo = "paciente", redireciona /
    else:
        # mensagem: "Digite 'medico' ou 'paciente'"
```

- Case-insensitive (`MEDICO`, `Medico`, `medico` funcionam).
- **Sem sinônimos** (só "medico"/"paciente").
- Senha não valida nada (pode estar vazia ou qualquer texto).
- Inválido → mensagem amigável, permanece no login.

### 2.3 Roteamento pós-login

- Médico → `/medico/caseload` (rota inicial do médico).
- Paciente → `/` (home atual).

O `papel-ativo` Store é setado, e os callbacks de navegação (§6) passam a mostrar o nav correto.

---

## 3. Telas do médico

Todas em verde (accent `SUCCESS`/verde sobre estrutura HUD), hero com tag `MOD // NN  MÉDICO`.

### 3.1 Caseload (`/medico/caseload`) — Feature 1

**Tela inicial do médico.** Lista os pacientes sob cuidado dele, com semáforo de risco, pra priorizar quem ver.

**Dados:** `medicos.json` (array de pacientes do Chase) × `perfis_clinicos.json` (dados) × telemetria (% irregular pro semáforo).

**Layout:** hero + grid de cards (um por paciente). Cada card = `hud_panel` com accent = cor do semáforo, contendo:
- Nome + idade + sexo.
- `status_chip` do semáforo (🔴/🟡/🟢).
- Condição principal.
- Métrica-chave da telemetria (ex: "18% irregular · últimas leituras").
- Botão/clique → abre prontuário do paciente.

**Ordenação:** por risco (vermelhos no topo, depois amarelos, depois verdes).

**Semáforo (lógica v2 validada):**
1. Telemetria define piso: ≥25% irregular → vermelho; 10-25% → amarelo; <10% → verde.
2. Condição grave ATIVA/recuperação (FA ativa, pós-IAM, IC) → sobe pra vermelho se telemetria ≥10%, senão amarelo.
3. Condição grave CONTROLADA → sobe no máx pra amarelo.
4. Condição leve EM ACOMPANHAMENTO → piso amarelo.
5. CHA₂DS₂-VA: exibido como info no card, **não** soma nível.

Resultado nos 5 mocks: Gabriel 🔴, Helena 🔴, Maria 🟡, Pedro 🟡, Lucas 🟢.

A função de cálculo do semáforo já foi validada (ver README_DADOS_MOCK.md). Portar pro código.

### 3.2 Fila de Alertas (`/medico/alertas`) — Feature 2

**Lista priorizada de situações acionáveis.** Diferente do caseload (todos), mostra só quem tem algo agora.

**Layout:** hero + lista vertical de `hud_panel` (ou itens com accent por severidade):
1. **Crítico** (accent vermelho): paciente com ≥25% irregular. Ex: "Helena Souza — 30% irregular nas últimas 50 leituras".
2. **Atenção** (accent amarelo): sem telemetria há > X dias.
3. **Agendamento** (accent cyan/azul): teleconsulta urgente solicitada.

Cada item: ícone de severidade + nome + descrição curta + link pro prontuário. Ordenado por severidade.

**Nota de honestidade no rodapé:** "Triagem visual para priorização — não substitui avaliação clínica."

### 3.3 Prontuário do médico (`/medico/paciente/<id>`) — Features 3+4+5

**O prontuário completo na visão do médico.** Usa o render compartilhado (§1.3) com `papel="medico"`, adicionando 3 blocos exclusivos.

**Estrutura (telas pouco densas — princípio do médico idoso):**
1. Identidade + semáforo (cabeçalho).
2. Telemetria (gráficos PPG via `plotly_layout`/`style_axes`).
3. Condições + CHA₂DS₂-VA.
4. Medicações.
5. Alergias.
6. Consultas.
7. **Comparativo temporal** (Feature 4) — seção, não tela separada.
8. **Anotações clínicas** (Feature 3) — só médico.
9. **Aprovação de rascunho** (Feature 5) — card destacado.

> Densidade: separar em seções respiráveis. Botões grandes e claros. Um foco visual por bloco. O médico pode ser idoso/pouco digital.

#### Feature 4 — Comparativo Temporal (seção no prontuário)

Tendência do paciente ao longo do tempo (melhora/piora).

**Gráficos (via Plotly compartilhado):**
- BPM ao longo do tempo (linha).
- % irregularidade por período (barras agrupando blocos de leituras).
- Indicador de tendência: "estável" / "piorando" / "melhorando" (compara primeira vs segunda metade das leituras).

**Limitação documentada:** os CSVs são 200 batimentos (janela), não meses. "Tempo" é simulado dentro do CSV. Num sistema real seria histórico de semanas/meses.

#### Feature 3 — Anotações Clínicas (só médico)

Lista de anotações + campo pra adicionar. **Paciente não vê** (evita cyberchondria; médico não compartilha anotações privadas).

Formato (campo `anotacoes_medicas` já nos perfis):
```json
{"data": "2026-05-10", "medico": "Dr. Robert Chase", "texto": "..."}
```

UI: cada anotação num bloco (data + médico + texto). Campo de input + botão "Salvar" → `update_patient` escreve no JSON.

**Aderência medicamentosa vive aqui** — como registro do relato na consulta ("paciente relatou tomar X regularmente"), não medição automática. Honesto: guarda o relato, não afirma que tomou.

#### Feature 5 — Aprovação de Rascunho de Prescrição

A encarnação do princípio-guia. IA sugere via `sugerir_rascunho_prescricao` (tool já existe); médico aprova/rejeita/edita.

**Fluxo:**
1. Médico clica "Gerar rascunho de prescrição" no prontuário.
2. Tool retorna rascunho (medicamento, dose, frequência).
3. Card destacado mostra o rascunho com tag **RASCUNHO — AGUARDANDO REVISÃO MÉDICA**.
4. Botões: **Aprovar** / **Rejeitar** / **Editar**.
5. Aprovar → vira entrada em `medicacoes_ativas` (escreve no JSON) → aparece no app do paciente.
6. Rejeitar → descartado, nada persiste.

**Card:** `hud_panel` com accent amarelo (atenção), tag em destaque, botões grandes.

**Híbrido (decisão):** aprovação acontece aqui no prontuário (contextualizada) + badge "N rascunhos pendentes" na navbar do médico que leva ao paciente com pendência.

---

## 4. Unificação do prontuário do paciente

### 4.1 O que muda

Hoje: `/gabriel` (hardcoded, 628 linhas) e `/meu-perfil` (data-driven, formulário). Ambas **removidas**, substituídas por `/prontuario` única data-driven.

- `gabriel.py` → **deletado** (hardcode não escala).
- `meu_perfil.py` → vira base do `/prontuario` (já é data-driven), renomeado/reescrito.
- `/prontuario` usa o render compartilhado (§1.3) com `papel="paciente"`.

### 4.2 Dropdown como navegação principal

O dropdown de perfil (já no topbar) vira a forma de trocar de paciente. Selecionar um paciente → `perfil-ativo` Store atualiza → `/prontuario` reflete automaticamente.

**Ferramenta de demo:** o dropdown troca livremente entre os 5 pacientes (num cenário real, o paciente veria só o próprio).

### 4.3 Limpeza da dívida MEU_PERFIL

Nesta fase, resolver as ~20 referências ao id morto MEU_PERFIL (app.py dropdown value, chat.py filtro — já parcialmente feito no lote 2, pacientes.py lista, meu_perfil.py get_patient/update_patient). Tudo junto, sem retrabalho.

---

## 5. Atalhos de navegação (demo cronometrada)

### 5.1 Atalho paciente → médico

No dropdown de pacientes, entrada especial **"Dr. Chase (visão médico)"** (separada visualmente dos pacientes por divisória). Clicar → salta pro `/medico/caseload` sem passar pelo login.

### 5.2 Atalho médico → paciente

No navbar do médico, botão **"→ visão paciente"** que volta pro app do paciente sem logout. Simetria, pra demo fluir.

---

## 6. Navegação por papel

### 6.1 Problema

O nav é auto-gerado de `page_registry`. Sem controle, as rotas do médico apareceriam no nav do paciente e vice-versa.

### 6.2 Solução

Filtrar o nav por papel. O callback que monta o nav (`_nav_links` / `_nav_active`) lê o `papel-ativo` Store e mostra só as rotas do papel:

- **Paciente:** Home, Monitor, Análise, Prontuário, Chat, Pacientes.
- **Médico:** Caseload, Alertas (+ badge rascunhos), atalho "→ visão paciente".

Rotas do médico marcadas (ex: `register_page(..., name="...", order=N)` + um marcador tipo prefixo `/medico/` ou metadata) pra o filtro distinguir.

### 6.3 Cores por papel

- Login: branco/neutro.
- Paciente: azul (`PRIMARY_BLUE` accent — atual).
- Médico: verde (`SUCCESS` accent sobre estrutura HUD).

O accent dos `hud_panel`, ticks, bordas de destaque e `hud-hero` muda conforme o papel. A estrutura HUD (brackets, mono, layout) é a mesma — é o mesmo sistema, identidade de cor distinta.

---

## 7. Fases de construção

A spec é o mapa completo; a construção é fatiada em fases que viram prompts. Cada fase: investigação (se tocar código existente) → aplicação → pytest → commit limpo (sem Claude).

**Fase 1 — Login + roteamento por papel.**
- Criar `/login` (tela neutra + lógica medico/paciente).
- `papel-ativo` Store.
- Roteamento pós-login.
- Nav filtrado por papel (§6).
- Validar: login roteia, nav muda por papel.

**Fase 2 — Render de prontuário compartilhado + unificação paciente.**
- Extrair `render_prontuario(paciente_id, papel)` data-driven.
- Criar `/prontuario` (paciente, azul) usando o render.
- Deletar `gabriel.py`; reescrever `meu_perfil.py` → base do prontuário.
- Dropdown como navegação principal.
- Limpar dívida MEU_PERFIL.
- Validar: `/prontuario` mostra qualquer paciente via dropdown; `/gabriel` some.

**Fase 3 — Caseload (Feature 1).**
- `/medico/caseload` em verde.
- Portar função do semáforo (já validada).
- Cards ordenados por risco, clique abre prontuário.
- Validar: 5 pacientes com semáforos corretos.

**Fase 4 — Prontuário do médico (Features 3+4+5).**
- `/medico/paciente/<id>` usando render compartilhado com `papel="medico"`.
- Bloco anotações (só médico) + persistência via `update_patient`.
- Bloco comparativo temporal.
- Bloco aprovação de rascunho (tool + aprovar/rejeitar/editar).
- Validar: anotações salvam, rascunho aprovado vira medicação.

**Fase 5 — Fila de alertas (Feature 2).**
- `/medico/alertas` priorizada.
- Badge "N rascunhos pendentes" na navbar médico.
- Validar: alertas ordenados por severidade.

**Fase 6 — Atalhos de navegação.**
- Atalho dropdown paciente → médico.
- Atalho navbar médico → paciente.
- Validar: troca de visão sem login.

**Fase 7 (fim) — Chat do paciente + responsividade.**
- Bug do chat (investigação no browser ao vivo, não testes isolados).
- Responsividade de todas as telas (paciente + médico) de uma vez.

---

## 8. Reuso do vocabulário visual (zero CSS novo pra layout padrão)

Importar de `utils.theme`: `hud_panel`, `telemetry_tile`, `status_chip`, `plotly_layout`, `style_axes` + constantes de cor.

- Páginas: `layout()` → `html.Div([hero, hud_panel(...), grid de hud_panels, ...])`.
- Hero: `className="hud-hero"` + tag `MOD // NN  MÉDICO`.
- Gráficos: `dcc.Graph(figure=fig, config={"displayModeBar": False})` dentro de `hud_panel`, figs via `plotly_layout()`/`style_axes()`.
- Semáforo: `status_chip` (regular→verde, atencao→amarelo, irregular→vermelho).
- Grid: `.grid .grid-N`, `.span-N`.
- Botões: `.hud-btn`, `--ghost`, `--danger`.
- Cards de paciente: padrão `hud_panel` com avatar circular + linhas LABEL: valor.

Accent verde no médico = passar `accent=SUCCESS` (ou constante verde) aos `hud_panel` e ao hero. Estrutura idêntica à do paciente.
