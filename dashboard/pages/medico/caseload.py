"""Caseload do médico — painel de pacientes (app médico).

PLACEHOLDER (fase 1): só pro roteamento pós-login ter destino. O conteúdo
real (cards de pacientes + semáforo de risco) vem na Fase 3.

role="medico": só aparece no nav quando papel-ativo = medico.
"""

from __future__ import annotations

import dash
from dash import html

dash.register_page(__name__, path="/medico/caseload", name="Caseload",
                   role="medico", order=10)


def layout(**kwargs):
    return html.Div(className="hud-page", children=[
        html.Section(className="hud-hero", children=[
            html.Span("MOD // 10  CASELOAD MÉDICO", className="hud-hero__tag"),
            html.H1("Painel de pacientes"),
            html.P("Visão do Dr. Robert Chase — em construção (Fase 3)."),
        ]),
    ])
