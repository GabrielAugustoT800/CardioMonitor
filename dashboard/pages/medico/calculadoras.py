"""Página /medico/calculadoras — 4 calculadoras clínicas (fase 9).

Ferramenta autônoma com todos os inputs vazios/default. A UI (render +
adapters de cálculo) vive em utils/calculadoras_ui.py — esta página
contém só o register_page + layout + os 4 callbacks da rota (prefixo
'rota-').

Por que a separação: o bloco do prontuário também usa a mesma UI (com
prefixo 'pron-'). Se a UI ficasse aqui, o import de pages/prontuario.py
via 'from pages.medico.calculadoras' provocaria registro duplo dos
@callback (Dash dispara erro 'Duplicate callback outputs').
"""

from __future__ import annotations

import dash
from dash import html, callback, Input, Output, State, no_update

from utils.calculadoras_ui import (
    _render_calculadoras_ui,
    calcular_cha2ds2, calcular_hb, calcular_egfr, calcular_heart,
)


dash.register_page(
    __name__,
    path="/medico/calculadoras",
    name="Calculadoras",
    role="medico",
    order=30,
)


def layout(**kwargs):
    return html.Div(className="hud-page", children=[
        html.Section(className="hud-hero", children=[
            html.Span("MOD // 30  CALCULADORAS CLÍNICAS",
                      className="hud-hero__tag"),
            html.H1("Calculadoras clínicas cardiovasculares"),
            html.P("Ferramentas determinísticas baseadas em guidelines "
                   "atuais. CHA₂DS₂-VASc · HAS-BLED · eGFR · HEART score."),
        ]),
        html.Div(_render_calculadoras_ui(prefixo="rota-"),
                 style={"maxWidth": "880px", "margin": "0 auto"}),
    ])


# =============================================================================
# Callbacks da ROTA AUTÔNOMA (prefixo "rota-")
# =============================================================================

@callback(
    Output("rota-cha-resultado", "children"),
    Input("rota-cha-btn", "n_clicks"),
    State("rota-cha-idade", "value"),
    State("rota-cha-sexo", "value"),
    State("rota-cha-fatores", "value"),
    prevent_initial_call=True,
)
def _calc_cha_rota(n, idade, sexo, fatores):
    if not n:
        return no_update
    return calcular_cha2ds2(idade, sexo, fatores)


@callback(
    Output("rota-hb-resultado", "children"),
    Input("rota-hb-btn", "n_clicks"),
    State("rota-hb-fatores", "value"),
    prevent_initial_call=True,
)
def _calc_hb_rota(n, fatores):
    if not n:
        return no_update
    return calcular_hb(fatores)


@callback(
    Output("rota-egfr-resultado", "children"),
    Input("rota-egfr-btn", "n_clicks"),
    State("rota-egfr-cr", "value"),
    State("rota-egfr-idade", "value"),
    State("rota-egfr-sexo", "value"),
    prevent_initial_call=True,
)
def _calc_egfr_rota(n, cr, idade, sexo):
    if not n:
        return no_update
    return calcular_egfr(cr, idade, sexo)


@callback(
    Output("rota-heart-resultado", "children"),
    Input("rota-heart-btn", "n_clicks"),
    State("rota-heart-hist", "value"),
    State("rota-heart-ecg", "value"),
    State("rota-heart-idade", "value"),
    State("rota-heart-risco", "value"),
    State("rota-heart-trop", "value"),
    prevent_initial_call=True,
)
def _calc_heart_rota(n, h, e, i, r, t):
    if not n:
        return no_update
    return calcular_heart(h, e, i, r, t)
