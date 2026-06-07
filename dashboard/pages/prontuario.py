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
    prevent_initial_call=False,
)
def _renderizar_prontuario(perfil_data):
    """Renderiza o prontuário do paciente ativo.

    perfil_data tem estrutura {"id": "<PID>"} (definida no Store global
    em app.py). Default GABRIEL se Store None/vazio.
    """
    if isinstance(perfil_data, dict):
        paciente_id = perfil_data.get("id") or "GABRIEL"
    elif isinstance(perfil_data, str) and perfil_data:
        # Compat defensiva: se algum dia o Store virar string pura
        paciente_id = perfil_data
    else:
        paciente_id = "GABRIEL"

    return render_prontuario(paciente_id, papel="paciente")
