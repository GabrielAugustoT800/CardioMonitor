"""Caseload do médico — lista os 5 pacientes ordenados por risco (fase 3).

Cada card é um clickable wrapper com: nome + idade + sexo, chip do semáforo +
justificativa (tooltip), condição principal, métrica-chave (% irregular das
últimas 50 — mesma janela do cálculo de risco). Clique abre o /prontuario em
visão médico daquele paciente.

Ordem: 🔴 vermelho → 🟡 amarelo → 🟢 verde (desempate alfabético por nome).
Distribuição validada nos mocks: Gabriel/Helena vermelho, Maria/Pedro amarelo,
Lucas verde.

role='medico' no register_page: só aparece no nav quando papel-ativo = medico.
"""

from __future__ import annotations

import dash
from dash import html, callback, Input, Output, ALL, ctx, no_update

from shared.patient_registry import list_patients
from utils.storage import load_csv
from utils.theme import (
    hud_panel, SUCCESS, WARNING, DANGER, TEXT_DARK, TEXT_MUTED,
)
from utils.semaforo import calcular_semaforo, semaforo_chip
from utils.prontuario import csv_do_paciente


dash.register_page(
    __name__,
    path="/medico/caseload",
    name="Caseload",
    role="medico",
    order=10,
)


# Ordem: vermelho primeiro (maior prioridade clínica).
_ORDEM_RISCO = {"vermelho": 0, "amarelo": 1, "verde": 2}
_ACCENT_POR_COR = {"vermelho": DANGER, "amarelo": WARNING, "verde": SUCCESS}


def _condicao_principal(paciente: dict) -> str:
    """Primeira condição ativa do paciente, ou aviso de ausência."""
    cond = paciente.get("condicoes_ativas", [])
    if not cond:
        return "Sem condições registradas"
    primeira = cond[0]
    nome = primeira.get("nome", "—")
    status = primeira.get("status", "")
    return f"{nome} ({status})" if status else nome


def _metrica_chave(df) -> str:
    """% irregular das últimas 50 leituras — mesma janela do semáforo."""
    if df is None or df.empty or "status" not in df.columns:
        return "Sem telemetria"
    ult = df.tail(50)
    n = len(ult)
    if n == 0:
        return "Sem dados"
    irreg = int((ult["status"] == "irregular").sum())
    pct = (irreg / n * 100)
    return f"{pct:.0f}% irregular nas últimas {n} leituras"


def _card_paciente(paciente: dict, df, cor: str, justif: str) -> html.Div:
    """Card de paciente: wrapper clicável (pattern-matching id) envolvendo
    hud_panel com accent da cor do semáforo."""
    pid = paciente["id"]
    accent = _ACCENT_POR_COR[cor]
    nome = paciente.get("nome", pid)
    idade = paciente.get("idade", "?")
    sexo = (paciente.get("sexo") or "").capitalize() or "—"

    return html.Div(
        # Pattern-matching id: o callback _abrir_paciente captura via ALL
        id={"type": "caseload-card", "pid": pid},
        n_clicks=0,
        style={"cursor": "pointer", "marginBottom": "14px"},
        children=hud_panel(
            title=nome,
            status=f"{idade}a · {sexo}",
            accent=accent,
            children=html.Div([
                # Linha 1: chip do semáforo + justificativa
                html.Div([
                    semaforo_chip(cor, justif),
                    html.Span(justif, style={
                        "color": TEXT_MUTED,
                        "marginLeft": "10px",
                        "fontSize": "0.82rem",
                        "fontFamily": "JetBrains Mono, Consolas, monospace",
                    }),
                ], style={"marginBottom": "10px",
                          "display": "flex", "alignItems": "center",
                          "flexWrap": "wrap", "gap": "4px"}),
                # Linha 2: condição principal
                html.Div([
                    html.Span("Condição: ", style={
                        "color": TEXT_MUTED, "fontSize": "0.78rem",
                        "fontWeight": "700", "letterSpacing": "0.06em",
                        "textTransform": "uppercase",
                        "fontFamily": "JetBrains Mono, Consolas, monospace",
                    }),
                    html.Span(_condicao_principal(paciente), style={
                        "color": TEXT_DARK, "fontWeight": "600",
                        "fontSize": "0.86rem",
                    }),
                ], style={"marginBottom": "6px"}),
                # Linha 3: métrica-chave (telemetria)
                html.Div([
                    html.Span("Telemetria: ", style={
                        "color": TEXT_MUTED, "fontSize": "0.78rem",
                        "fontWeight": "700", "letterSpacing": "0.06em",
                        "textTransform": "uppercase",
                        "fontFamily": "JetBrains Mono, Consolas, monospace",
                    }),
                    html.Span(_metrica_chave(df), style={
                        "color": TEXT_DARK, "fontWeight": "600",
                        "fontSize": "0.86rem",
                        "fontFamily": "JetBrains Mono, Consolas, monospace",
                    }),
                ], style={"marginBottom": "8px"}),
                # Linha 4: dica visual de ação
                html.Div("ABRIR PRONTUÁRIO →", style={
                    "color": accent, "fontSize": "0.74rem",
                    "fontWeight": "700", "letterSpacing": "0.12em",
                    "fontFamily": "JetBrains Mono, Consolas, monospace",
                    "textAlign": "right",
                    "marginTop": "4px",
                }),
            ])
        ),
    )


def layout(**kwargs):
    """Monta o caseload do médico: lista vertical de cards ordenados por risco.

    O cálculo do semáforo é feito por paciente (carrega CSV de telemetria +
    condicoes_ativas do JSON). Resultado:
      🔴 Gabriel, Helena | 🟡 Maria, Pedro | 🟢 Lucas
    """
    pacientes = list_patients()

    # Calcula semáforo de cada paciente e empacota tudo (evita recalcular no card)
    enriquecidos = []
    for p in pacientes:
        pid = p["id"]
        csv_path = csv_do_paciente(pid)
        df = load_csv(csv_path) if csv_path and csv_path.exists() else None
        cor, justif = calcular_semaforo(p, df)
        enriquecidos.append((p, df, cor, justif))

    # Ordena por risco (vermelho->amarelo->verde) com desempate alfabético
    enriquecidos.sort(key=lambda t: (
        _ORDEM_RISCO.get(t[2], 99),
        t[0].get("nome", "")
    ))

    # Contagem pra header
    n_vermelho = sum(1 for _, _, c, _ in enriquecidos if c == "vermelho")
    n_amarelo = sum(1 for _, _, c, _ in enriquecidos if c == "amarelo")
    n_verde = sum(1 for _, _, c, _ in enriquecidos if c == "verde")

    return html.Div(className="hud-page", children=[
        html.Section(className="hud-hero", children=[
            html.Span("MOD // 10  CASELOAD MÉDICO", className="hud-hero__tag"),
            html.H1("Painel de pacientes"),
            html.P(
                f"{len(enriquecidos)} pacientes sob cuidado · "
                f"🔴 {n_vermelho}  🟡 {n_amarelo}  🟢 {n_verde}  ·  "
                "Ordenados por risco. Clique no card para abrir o prontuário."
            ),
        ]),
        html.Div(
            [_card_paciente(p, df, cor, justif)
             for p, df, cor, justif in enriquecidos],
            style={"maxWidth": "880px", "margin": "0 auto"},
        ),
    ])


@callback(
    # Trinca de Outputs com allow_duplicate (os 3 ja sao escritos noutros
    # callbacks: perfil-ativo em app.py + chat.py, hud-url em app.py + login,
    # papel-ativo em login). Dash registra cada um com hash de sufixo.
    Output("perfil-ativo", "data", allow_duplicate=True),
    Output("papel-ativo", "data", allow_duplicate=True),
    Output("hud-url", "pathname", allow_duplicate=True),
    Input({"type": "caseload-card", "pid": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def _abrir_paciente(n_clicks_list):
    """Pattern-matching: clicar num card escreve os 3 Stores + navega.

    Guard duplo:
    1. n_clicks_list pode vir todo None/0 no carregamento -> ignorar.
    2. ctx.triggered_id pode ser None se nenhum disparo real.
    """
    if not n_clicks_list or not any(n for n in n_clicks_list if n):
        return no_update, no_update, no_update

    triggered = ctx.triggered_id
    if not isinstance(triggered, dict):
        return no_update, no_update, no_update

    pid = triggered.get("pid")
    if not pid:
        return no_update, no_update, no_update

    # Escreve perfil-ativo + força papel=medico + navega.
    return {"id": pid}, {"role": "medico"}, "/prontuario"
