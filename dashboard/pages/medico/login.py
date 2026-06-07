"""Login — seletor de papel disfarçado de login (app médico, fase 1).

Digite 'medico' ou 'paciente' (case-insensitive). Senha é visual, não valida.
Roteia: medico -> /medico/caseload | paciente -> / | inválido -> mensagem.

role="oculto" no register_page: nunca aparece no nav (filtrado em app.py).
"""

from __future__ import annotations

import dash
from dash import html, dcc, callback, Input, Output, State, no_update

dash.register_page(__name__, path="/login", name="Login", role="oculto", order=-1)


def layout(**kwargs):
    return html.Div(className="hud-page", children=[
        html.Div(className="login-wrap", children=[
            html.Div(className="hud-panel login-card", children=[
                # cantos HUD (brackets) — mesmo vocabulário visual
                html.Span(className="hud-corner hud-corner--tl"),
                html.Span(className="hud-corner hud-corner--tr"),
                html.Span(className="hud-corner hud-corner--bl"),
                html.Span(className="hud-corner hud-corner--br"),
                html.Div(className="hud-panel__body", children=[
                    # marca C+ CardioMonitor
                    html.Div(className="login-brand", children=[
                        html.Span("C+", className="login-mark"),
                        html.Div([
                            html.Div("CardioMonitor", className="login-title"),
                            html.Small("Acesso ao sistema", className="login-sub"),
                        ]),
                    ]),
                    # campo usuário
                    html.Label("USUÁRIO", className="login-label"),
                    dcc.Input(
                        id="login-user", type="text", n_submit=0,
                        placeholder="medico ou paciente",
                        className="login-input", autoComplete="off",
                    ),
                    # campo senha (visual — não valida)
                    html.Label("SENHA", className="login-label"),
                    dcc.Input(
                        id="login-pass", type="password", n_submit=0,
                        placeholder="••••••••",
                        className="login-input", autoComplete="off",
                    ),
                    # botão Entrar
                    html.Button("ENTRAR", id="login-submit",
                                className="hud-btn", n_clicks=0,
                                style={"width": "100%", "marginTop": "14px"}),
                    # mensagem (erro/instrução)
                    html.Div(id="login-msg", className="login-msg"),
                    # instrução
                    html.Div(
                        "Digite 'medico' ou 'paciente' no campo usuário. "
                        "A senha é apenas demonstrativa.",
                        className="login-hint",
                    ),
                ]),
            ]),
        ]),
    ])


@callback(
    Output("papel-ativo", "data"),
    Output("hud-url", "pathname", allow_duplicate=True),
    Output("login-msg", "children"),
    Input("login-submit", "n_clicks"),
    Input("login-user", "n_submit"),
    Input("login-pass", "n_submit"),
    State("login-user", "value"),
    prevent_initial_call=True,
)
def _login(_n_clicks, _n_user, _n_pass, usuario):
    """Seletor de papel. Senha ignorada (visual). Case-insensitive, sem sinônimos."""
    u = (usuario or "").strip().lower()
    if u == "medico":
        return {"role": "medico"}, "/medico/caseload", ""
    if u == "paciente":
        return {"role": "paciente"}, "/", ""
    return no_update, no_update, "Digite 'medico' ou 'paciente' no campo usuário."
