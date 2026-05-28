"""Home page - overview + KPIs + navigation."""

from __future__ import annotations

import dash
from dash import html, dcc

from utils.storage import DEFAULT_CSV, GABRIEL_CSV, ensure_csv, load_csv
from utils.theme import (
    telemetry_tile, hud_panel,
    PRIMARY_BLUE, ACCENT_CYAN, SUCCESS, DANGER,
)

dash.register_page(__name__, path="/", name="Home", order=0)


def _snapshot_tiles():
    ensure_csv(DEFAULT_CSV)
    live_df = load_csv(DEFAULT_CSV)
    gabriel_df = load_csv(GABRIEL_CSV) if GABRIEL_CSV.exists() else None

    live_count = len(live_df)
    last_bpm = f"{live_df['bpm'].iloc[-1]:.1f}" if not live_df.empty else "--"
    irreg = int((live_df["status"] == "irregular").sum()) if not live_df.empty else 0
    gcount = len(gabriel_df) if gabriel_df is not None else 0

    return html.Div(className="grid grid-4", children=[
        telemetry_tile("Registros ao vivo",
                       f"{live_count:,}".replace(",", "."),
                       sub="CSV cardiac_data.csv", accent=PRIMARY_BLUE),
        telemetry_tile("Ultimo BPM ao vivo",
                       last_bpm, unit="bpm",
                       sub="ultima amostra", accent=ACCENT_CYAN),
        telemetry_tile("Eventos irregulares",
                       str(irreg),
                       sub="no historico ao vivo",
                       accent=DANGER if irreg else SUCCESS),
        telemetry_tile("Dataset Gabriel",
                       str(gcount),
                       sub="batimentos carregados",
                       accent=PRIMARY_BLUE),
    ])


def _nav_card(idx: str, title: str, body: str, href: str):
    return dcc.Link(
        href=href,
        className="hud-navcard",
        children=[
            html.Div(idx, className="hud-navcard__idx"),
            html.Div(title, className="hud-navcard__title"),
            html.Div(body, className="hud-navcard__text"),
            html.Div("ABRIR >>", className="hud-navcard__arrow"),
        ],
    )


def layout():
    return html.Div([
        html.Section(className="hud-hero", children=[
            html.Span("SYS // OVERVIEW", className="hud-hero__tag"),
            html.H1([
                "CardioMonitor ",
                html.Span("\u2764", className="hud-heart"),
            ]),
            html.P("Plataforma clinica de monitoramento cardiaco em tempo real "),
        ]),

        hud_panel(
            title="Briefing",
            status="READY",
            children=html.P(
                [
                    "Esta plataforma recebe dados do sensor ",
                    html.Strong("MAX30100"),
                    " via ",
                    html.Strong("ESP32"),
                    ", calcula metricas PPG (BPM, IBI, desvio medio em janela "
                    "deslizante) e classifica cada batimento como ",
                    html.Strong("Regular"), ", ",
                    html.Strong("Atencao"), " ou ",
                    html.Strong("Irregular"),
                    ". Alertas audiveis sao emitidos automaticamente em "
                    "episodios de arritmia.",
                ],
                style={"margin": 0, "color": "var(--hud-muted)",
                       "lineHeight": "1.55"},
            ),
        ),

        hud_panel(
            title="Telemetria - snapshot",
            status="LIVE",
            accent=ACCENT_CYAN,
            children=_snapshot_tiles(),
        ),

        hud_panel(
            title="Navegacao",
            status="3 MODULOS",
            children=html.Div(className="grid grid-3", children=[
                _nav_card(
                    "MOD // 01",
                    "Monitor em tempo real",
                    "BPM ao vivo via ESP32/MAX30100, classificacao de status "
                    "e alerta sonoro em batimentos irregulares. Dados gravados "
                    "automaticamente em CSV.",
                    "/monitor",
                ),
                _nav_card(
                    "MOD // 02",
                    "Analise historica",
                    "Leitura do CSV gravado: tendencias de BPM, distribuicao de "
                    "IBI, eventos irregulares, exportacao e filtro por paciente.",
                    "/analise",
                ),
                _nav_card(
                    "MOD // 03",
                    "Paciente Gabriel",
                    "Prontuario PPG do paciente Gabriel (200 batimentos do "
                    "dataset de referencia) renderizado no formato do dashboard.",
                    "/gabriel",
                ),
            ]),
        ),
    ])
