"""Página /prontuario — render data-driven do paciente ativo.

Layout mínimo (placeholder) + 2 callbacks:
- _renderizar_prontuario: reage a perfil-ativo/papel-ativo/anotacoes-refresh
  e chama render_prontuario(paciente_id, papel) do módulo utils/prontuario.py.
- _salvar_anotacao (fase 4A, pattern-matching): persiste no arquivo runtime,
  limpa textarea, mostra feedback, dispara re-render via anotacoes-refresh.

role implícito = paciente (default no nav filter). Visão médico (verde com
blocos extras de anotações + rascunho) acontece quando papel-ativo='medico'
— setado pelo caseload (fase 3) ou login (fase 1).
"""

from __future__ import annotations

import dash
from dash import (
    html, callback, Input, Output, State, ALL, MATCH, ctx, no_update,
)

# Convenção do projeto: dashboard/ no sys.path -> "from utils.X"
from utils.prontuario import render_prontuario
from utils.anotacoes_runtime import salvar_anotacao
from utils.rascunhos_runtime import aprovar, rejeitar


dash.register_page(
    __name__,
    path="/prontuario",
    name="Prontuário",
    order=3,
)


def layout(**kwargs):
    # Placeholder vazio — o callback abaixo preenche com o render do paciente
    # ativo. Sem isso a página apareceria em branco até a primeira mudança do
    # Store; com Input(perfil-ativo) + prevent_initial_call=False, o callback
    # dispara na montagem e popula.
    return html.Div(id="prontuario-container", className="hud-page-wrapper")


@callback(
    Output("prontuario-container", "children"),
    Input("perfil-ativo", "data"),
    Input("papel-ativo", "data"),
    # Trigger de re-render apos salvar anotacao (fase 4A). O valor numerico
    # nao e usado — so a mudanca dele dispara o callback, que chama
    # render_prontuario, que monta _bloco_anotacoes que le o arquivo runtime
    # via todas_anotacoes(). Ciclo se fecha automaticamente.
    Input("anotacoes-refresh", "data"),
    # Trigger de re-render apos decisao de rascunho (fase 4B). Mesmo padrao.
    Input("rascunhos-refresh", "data"),
    prevent_initial_call=False,
)
def _renderizar_prontuario(perfil_data, papel_data, _refresh_anot, _refresh_rasc):
    """Renderiza o prontuário do paciente ativo, parametrizado por papel.

    perfil_data tem estrutura {"id": "<PID>"} (Store global em app.py).
    papel_data tem estrutura {"role": "paciente"|"medico"} (fase 1).
    _refresh: int incrementado por _salvar_anotacao (unused aqui).
    Default GABRIEL + papel='paciente' se Stores None/vazios.

    Quando o médico clica num card do /medico/caseload (fase 3), o callback
    do caseload escreve papel-ativo={'role':'medico'} ANTES de navegar pra cá.
    O render_prontuario com papel='medico' adiciona os 2 blocos extras
    (anotações + aprovação de rascunho) e usa accent verde (SUCCESS).
    """
    if isinstance(perfil_data, dict):
        paciente_id = perfil_data.get("id") or "GABRIEL"
    elif isinstance(perfil_data, str) and perfil_data:
        # Compat defensiva: se algum dia o Store virar string pura
        paciente_id = perfil_data
    else:
        paciente_id = "GABRIEL"

    papel = "paciente"  # default seguro
    if isinstance(papel_data, dict):
        papel = papel_data.get("role") or "paciente"

    return render_prontuario(paciente_id, papel=papel)


# =============================================================================
# Fase 4A — Salvar anotação clínica (pattern-matching)
# =============================================================================
# IDs do bloco de anotações em utils/prontuario.py:_bloco_anotacoes são
# {"type": "anotacao-{input|salvar|feedback}", "pid": <PID>}.
# Cada paciente tem sua trinca, mas este único callback atende todos via
# Input/State/Output com ALL no pid.
@callback(
    Output("anotacoes-refresh", "data"),
    Output({"type": "anotacao-input", "pid": ALL}, "value"),
    Output({"type": "anotacao-feedback", "pid": ALL}, "children"),
    Input({"type": "anotacao-salvar", "pid": ALL}, "n_clicks"),
    State({"type": "anotacao-input", "pid": ALL}, "value"),
    State("anotacoes-refresh", "data"),
    prevent_initial_call=True,
)
def _salvar_anotacao(n_clicks_list, valores, refresh_atual):
    """Salva a anotação do paciente clicado no arquivo runtime + dispara
    re-render do prontuário.

    Pattern-matching: ALL captura todos os botões existentes na página
    (na prática, só um — o do paciente ativo, já que render_prontuario
    monta um único bloco). O ctx.triggered_id diz qual paciente disparou.

    Guards:
    - Lista vazia/None ou todos n_clicks zerados (carga inicial) -> no_update.
    - triggered_id None ou sem 'pid' -> no_update.
    - Texto vazio/whitespace -> feedback "vazio", sem persistir.
    """
    if not n_clicks_list or not any(n for n in n_clicks_list if n):
        return no_update, no_update, no_update

    triggered = ctx.triggered_id
    if not isinstance(triggered, dict):
        return no_update, no_update, no_update

    pid = triggered.get("pid")
    if not pid:
        return no_update, no_update, no_update

    # Achar o valor correspondente ao paciente clicado. ctx.states_list[0]
    # é a lista dos State({"type":"anotacao-input","pid":ALL},"value") — seus
    # ids casam 1:1 com a lista `valores`. Mapeamos pid -> valor.
    state_ids = []
    if ctx.states_list:
        # states_list é lista por grupo; aqui só temos 1 grupo (o ALL)
        for grupo in ctx.states_list:
            if isinstance(grupo, list):
                for item in grupo:
                    state_ids.append(item.get("id") if isinstance(item, dict) else None)
                break
            if isinstance(grupo, dict):
                state_ids.append(grupo.get("id"))

    # Achar índice do paciente clicado
    idx_clicado = -1
    for i, sid in enumerate(state_ids):
        if isinstance(sid, dict) and sid.get("pid") == pid:
            idx_clicado = i
            break

    n_targets = len(state_ids)
    if idx_clicado < 0 or n_targets == 0:
        return no_update, no_update, no_update

    valor = (valores or [None] * n_targets)[idx_clicado]

    # Texto vazio: feedback só no card clicado, sem persistir, sem refresh.
    if not valor or not str(valor).strip():
        limpar = [no_update] * n_targets
        feedback = [no_update] * n_targets
        feedback[idx_clicado] = "⚠ Anotação vazia"
        return no_update, limpar, feedback

    # Salvar no arquivo runtime
    salvar_anotacao(pid, str(valor))

    # Limpar todos os textareas (após salvar, o re-render vai rebuildar a
    # lista; o textarea volta a ser placeholder). Feedback "salvo" só no
    # card clicado.
    limpar = [""] * n_targets
    feedback = [no_update] * n_targets
    feedback[idx_clicado] = "✓ Anotação salva"

    # Incrementa o refresh trigger pra disparar _renderizar_prontuario
    novo_refresh = (refresh_atual or 0) + 1
    return novo_refresh, limpar, feedback


# =============================================================================
# Fase 4B — Aprovação de rascunho de prescrição
# =============================================================================
# IDs do bloco de aprovação em utils/prontuario.py:_card_rascunho_pendente:
#   {"type": "rascunho-aprovar",    "rid": ..., "pid": ...}  (botao)
#   {"type": "rascunho-editar",     "rid": ..., "pid": ...}  (botao toggle)
#   {"type": "rascunho-rejeitar",   "rid": ..., "pid": ...}  (botao)
#   {"type": "rascunho-edit-input", "rid": ...}              (textarea oculta)
#
# Princípio: o botão "Aprovar" é ÚNICO — se a textarea daquele rid estiver
# visível (display=block), o callback lê o valor e marca como 'editado'.
# Senão, aprova com o texto original (status='aprovado'). Isso evita ter
# 2 callbacks com Output duplicado em rascunhos-refresh.


@callback(
    Output("rascunhos-refresh", "data", allow_duplicate=True),
    Input({"type": "rascunho-aprovar", "rid": ALL, "pid": ALL}, "n_clicks"),
    State({"type": "rascunho-edit-input", "rid": ALL}, "value"),
    State({"type": "rascunho-edit-input", "rid": ALL}, "style"),
    State({"type": "rascunho-edit-input", "rid": ALL}, "id"),
    State("rascunhos-refresh", "data"),
    prevent_initial_call=True,
)
def _aprovar_rascunho(n_clicks_list, valores, estilos, ids_input, refresh_atual):
    """Aprova um rascunho. Se a textarea daquele rid estiver visível
    (display=block), aprova como 'editado' com o texto atual. Senão, aprova
    direto (status='aprovado')."""
    if not n_clicks_list or not any(n for n in n_clicks_list if n):
        return no_update

    triggered = ctx.triggered_id
    if not isinstance(triggered, dict):
        return no_update

    rid = triggered.get("rid")
    pid = triggered.get("pid")
    if not rid or not pid:
        return no_update

    # Procurar o input/textarea daquele rid. Se display=block, pegar valor.
    texto_editado = None
    for i, id_dict in enumerate(ids_input or []):
        if not isinstance(id_dict, dict) or id_dict.get("rid") != rid:
            continue
        estilo = estilos[i] if i < len(estilos) else {}
        if isinstance(estilo, dict) and estilo.get("display") == "block":
            valor = valores[i] if i < len(valores) else None
            if valor and str(valor).strip():
                texto_editado = str(valor).strip()
        break

    aprovar(pid, rid, texto_editado=texto_editado)
    return (refresh_atual or 0) + 1


@callback(
    Output("rascunhos-refresh", "data", allow_duplicate=True),
    Input({"type": "rascunho-rejeitar", "rid": ALL, "pid": ALL}, "n_clicks"),
    State("rascunhos-refresh", "data"),
    prevent_initial_call=True,
)
def _rejeitar_rascunho(n_clicks_list, refresh_atual):
    """Rejeita um rascunho. Registra decisão (médico + data)."""
    if not n_clicks_list or not any(n for n in n_clicks_list if n):
        return no_update

    triggered = ctx.triggered_id
    if not isinstance(triggered, dict):
        return no_update

    rid = triggered.get("rid")
    pid = triggered.get("pid")
    if not rid or not pid:
        return no_update

    rejeitar(pid, rid)
    return (refresh_atual or 0) + 1


@callback(
    Output({"type": "rascunho-edit-input", "rid": MATCH}, "style"),
    Input({"type": "rascunho-editar", "rid": MATCH, "pid": ALL}, "n_clicks"),
    State({"type": "rascunho-edit-input", "rid": MATCH}, "style"),
    prevent_initial_call=True,
)
def _toggle_edit_rascunho(n_clicks_list, style_atual):
    """Mostra/esconde a textarea de edição do rascunho.

    Aceita lista vazia ou todos n_clicks=0 (carga inicial) como no-op.
    Combinação MATCH(rid) + ALL(pid): MATCH faz o callback rodar por rid;
    ALL no pid casa com qualquer pid daquele rid (na prática só tem 1).
    """
    if not n_clicks_list or not any(n for n in n_clicks_list if n):
        return no_update

    novo_estilo = dict(style_atual or {})
    atual = novo_estilo.get("display")
    novo_estilo["display"] = "block" if atual == "none" else "none"
    return novo_estilo
