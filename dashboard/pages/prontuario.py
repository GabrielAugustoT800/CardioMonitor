"""Página /prontuario — render data-driven do paciente ativo (fase 2B).

Layout mínimo (placeholder) + callback que lê o Store perfil-ativo e chama
render_prontuario(paciente_id, papel='paciente') do módulo utils/prontuario.py.

role implícito = paciente (default no nav filter). Coexiste com /gabriel e
/meu-perfil até a Fase 2C (que deleta gabriel.py e refatora meu_perfil.py).
"""

from __future__ import annotations

import dash
from dash import html, callback, Input, Output

# Convenção do projeto: dashboard/ no sys.path -> "from utils.X"
from utils.prontuario import render_prontuario


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
    prevent_initial_call=False,
)
def _renderizar_prontuario(perfil_data, papel_data):
    """Renderiza o prontuário do paciente ativo, parametrizado por papel.

    perfil_data tem estrutura {"id": "<PID>"} (Store global em app.py).
    papel_data tem estrutura {"role": "paciente"|"medico"} (fase 1).
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
