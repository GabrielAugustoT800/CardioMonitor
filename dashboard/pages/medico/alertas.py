"""Página /medico/alertas — fila priorizada cross-paciente (fase 5).

Visão agregada do médico: em vez de abrir cada paciente, ver tudo que
precisa de atenção numa lista única. Clique no card seta o paciente
ativo + papel='medico' + navega pro /prontuario com hash da seção
(scroll automático via dcc.Location).

role='medico': só aparece no nav quando papel-ativo = medico.
"""

from __future__ import annotations

import dash
from dash import html, callback, Input, Output, ALL, ctx, no_update

from utils.alertas import listar_alertas
from utils.theme import (
    DANGER, WARNING, PRIMARY_BLUE,
    TEXT_DARK, TEXT_MUTED,
)


dash.register_page(
    __name__,
    path="/medico/alertas",
    name="Alertas",
    role="medico",
    order=20,  # depois do Caseload (order=10)
)


_COR_POR_TIPO = {
    "CRITICO": DANGER,
    "PICO": WARNING,
    "RASCUNHO": PRIMARY_BLUE,
}

_LABEL_POR_TIPO = {
    "CRITICO": "🔴 CRÍTICO",
    "PICO": "⚡ PICO RECENTE",
    "RASCUNHO": "📝 RASCUNHO PENDENTE",
}


def _card_alerta(alerta) -> html.Div:
    """Card clicável de alerta. Pattern-matching id leva pid + ancora pro
    callback _abrir_alerta."""
    accent = _COR_POR_TIPO.get(alerta.tipo, TEXT_MUTED)
    label = _LABEL_POR_TIPO.get(alerta.tipo, alerta.tipo)

    return html.Div(
        id={"type": "alerta-card",
            "pid": alerta.paciente_id,
            "ancora": alerta.ancora},
        n_clicks=0,
        style={
            "cursor": "pointer",
            "padding": "16px",
            "background": "rgba(0,0,0,0.02)",
            "border": "1px solid rgba(0,0,0,0.06)",
            "borderLeft": f"4px solid {accent}",
            "borderRadius": "6px",
            "marginBottom": "12px",
        },
        children=[
            html.Div([
                html.Span(label, style={
                    "color": accent, "fontWeight": "700",
                    "fontSize": "0.78rem", "letterSpacing": "0.05em",
                    "fontFamily": "JetBrains Mono, Consolas, monospace",
                }),
                html.Span(f"  ·  {alerta.paciente_nome}", style={
                    "color": TEXT_DARK, "fontWeight": "600",
                    "marginLeft": "4px", "fontSize": "0.84rem",
                }),
            ], style={"marginBottom": "6px"}),
            html.Div(alerta.titulo, style={
                "color": TEXT_DARK, "fontSize": "0.92rem",
                "marginBottom": "4px", "fontWeight": "600",
            }),
            html.Div(alerta.descricao, style={
                "color": TEXT_MUTED, "fontSize": "0.82rem",
            }),
            html.Div("ABRIR PRONTUÁRIO →", style={
                "color": accent, "fontSize": "0.72rem",
                "fontWeight": "700", "letterSpacing": "0.12em",
                "fontFamily": "JetBrains Mono, Consolas, monospace",
                "textAlign": "right",
                "marginTop": "6px",
            }),
        ],
    )


def layout(**kwargs):
    """Renderiza a fila. Recalcula a cada acesso (semáforo + rascunhos
    podem ter mudado desde a última visita)."""
    alertas = listar_alertas()

    if not alertas:
        conteudo = html.Div(
            html.P(
                "Nenhum alerta no momento. Todos os pacientes estão "
                "estáveis e sem rascunhos pendentes.",
                style={"color": TEXT_MUTED, "fontStyle": "italic",
                       "padding": "16px", "margin": 0},
            ),
            style={"maxWidth": "880px", "margin": "0 auto"},
        )
    else:
        n_critico = sum(1 for a in alertas if a.tipo == "CRITICO")
        n_pico = sum(1 for a in alertas if a.tipo == "PICO")
        n_rasc = sum(1 for a in alertas if a.tipo == "RASCUNHO")

        contadores = html.Div([
            html.Span(f"{n_critico} CRÍTICO(S)", style={
                "color": DANGER, "fontWeight": "700",
                "marginRight": "18px",
                "fontFamily": "JetBrains Mono, Consolas, monospace",
            }),
            html.Span(f"{n_pico} PICO(S)", style={
                "color": WARNING, "fontWeight": "700",
                "marginRight": "18px",
                "fontFamily": "JetBrains Mono, Consolas, monospace",
            }),
            html.Span(f"{n_rasc} RASCUNHO(S) PENDENTE(S)", style={
                "color": PRIMARY_BLUE, "fontWeight": "700",
                "fontFamily": "JetBrains Mono, Consolas, monospace",
            }),
        ], style={
            "padding": "12px 16px",
            "background": "rgba(0,0,0,0.03)",
            "borderRadius": "6px",
            "marginBottom": "16px",
            "fontSize": "0.84rem",
        })

        conteudo = html.Div([
            contadores,
            html.Div([_card_alerta(a) for a in alertas]),
        ], style={"maxWidth": "880px", "margin": "0 auto"})

    return html.Div(className="hud-page", children=[
        html.Section(className="hud-hero", children=[
            html.Span("MOD // 20  FILA DE ALERTAS",
                      className="hud-hero__tag"),
            html.H1("Pendências cross-paciente"),
            html.P(
                f"{len(alertas)} alerta(s) priorizado(s) "
                "· Clique para abrir o prontuário."
            ),
        ]),
        conteudo,
    ])


@callback(
    # allow_duplicate em perfil-ativo (chat.py + app.py + caseload.py),
    # papel-ativo (login.py + caseload.py), hud-url.pathname (app.py +
    # login.py + guard + caseload.py), hud-url.hash (primeiro escritor).
    Output("perfil-ativo", "data", allow_duplicate=True),
    Output("papel-ativo", "data", allow_duplicate=True),
    Output("hud-url", "pathname", allow_duplicate=True),
    Output("hud-url", "hash", allow_duplicate=True),
    Input({"type": "alerta-card", "pid": ALL, "ancora": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def _abrir_alerta(n_clicks_list):
    """Clica no card de alerta -> seta paciente + papel=medico + navega
    pro /prontuario#<ancora>. Hash dispara scroll automático nativo do
    browser pro elemento com id correspondente."""
    if not n_clicks_list or not any(n for n in n_clicks_list if n):
        return no_update, no_update, no_update, no_update

    triggered = ctx.triggered_id
    if not isinstance(triggered, dict):
        return no_update, no_update, no_update, no_update

    pid = triggered.get("pid")
    ancora = triggered.get("ancora", "") or ""
    if not pid:
        return no_update, no_update, no_update, no_update

    hash_str = f"#{ancora}" if ancora else ""
    return {"id": pid}, {"role": "medico"}, "/prontuario", hash_str
