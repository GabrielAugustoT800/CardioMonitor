"""Render de prontuário compartilhado paciente/médico (fase 2A.2).

Lê do JSON enriquecido (perfis_clinicos.json) + CSV de telemetria. Parametrizado
por papel: 'paciente' (azul, PRIMARY_BLUE) ou 'medico' (verde, SUCCESS, com
blocos extras de anotações + aprovação de rascunho).

Princípio: data-driven puro. Sem hardcode clínico. Função pura — callbacks da
fase 4 (anotações editáveis, aprovação de rascunho) conectam depois.

Reusa o vocabulário visual: hud_panel, telemetry_tile, status_chip, plotly_layout,
style_axes (de utils.theme).
"""

from __future__ import annotations

from urllib.parse import quote

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, dash_table

# Convenção do projeto: dashboard/ no sys.path -> "from utils.X" resolve
# pra dashboard/utils/X.py. Mesma convenção usada por gabriel.py / meu_perfil.py.
from utils.analysis import (
    bpm_zone, bpm_zone_color, status_label_pt,
)
from utils.storage import load_csv
from utils.theme import (
    hud_panel, telemetry_tile, status_chip,
    plotly_layout, style_axes,
    PRIMARY_BLUE, ACCENT_CYAN, SUCCESS, WARNING, DANGER,
    TEXT_DARK, TEXT_MUTED, BORDER,
)

from shared.patient_registry import get_patient
from shared.telemetry_store import _FALLBACK_CSV_BY_ID


# =============================================================================
# Helpers
# =============================================================================

# Mapeamento CID3 -> "grave" (CIDs cardiovasculares de alta gravidade).
# I48 FA, I21 IAM agudo, I50 IC, I20 angina, I25 doença isquêmica crônica.
_CIDS_GRAVES = {"I48", "I21", "I50", "I20", "I25"}


def _csv_do_paciente(paciente_id: str):
    """Resolve o CSV de telemetria do paciente via _FALLBACK_CSV_BY_ID."""
    return _FALLBACK_CSV_BY_ID.get(paciente_id)


def _iniciais(nome: str) -> str:
    """Primeiras letras das 2 primeiras palavras. 'João Silva' -> 'JS'."""
    partes = (nome or "").split()
    if not partes:
        return "??"
    return (partes[0][0] + (partes[1][0] if len(partes) > 1 else "")).upper()


def _calcular_semaforo(paciente: dict, df: pd.DataFrame | None) -> tuple[str, str]:
    """Lógica v2 validada: telemetria define piso + condição modificador.

    Regras:
    1. Piso pela telemetria (% irregular das últimas 50 leituras):
       >=25% -> vermelho (2), 10-25% -> amarelo (1), <10% -> verde (0).
    2. Condição grave ATIVA/em recuperação: sobe pra vermelho se tele >=10%,
       senão amarelo.
    3. Condição grave CONTROLADA: piso amarelo.
    4. EM ACOMPANHAMENTO: piso amarelo.
    5. CHA2DS2-VA: informativo, NÃO soma nível.

    Returns:
        (cor: 'verde'|'amarelo'|'vermelho', justificativa: str)
    """
    # 1) piso pela telemetria
    if df is None or df.empty or "status" not in df.columns:
        nivel = 1
        base = "sem dados de telemetria"
    else:
        ult = df.tail(50)
        n = len(ult)
        irreg = int((ult["status"] == "irregular").sum())
        pct = (irreg / n * 100) if n else 0.0
        if pct >= 25:
            nivel, base = 2, f"telemetria alta ({pct:.0f}% irregular)"
        elif pct >= 10:
            nivel, base = 1, f"telemetria moderada ({pct:.0f}% irregular)"
        else:
            nivel, base = 0, f"telemetria estável ({pct:.0f}% irregular)"
        pct_atual = pct
    pct_atual = locals().get("pct_atual", 0.0)

    # 2-4) condições
    grave_ativa = grave_controlada = acompanhamento = False
    for c in paciente.get("condicoes_ativas", []):
        cid3 = (c.get("cid") or "")[:3]
        status_c = (c.get("status") or "").lower()
        eh_grave = cid3 in _CIDS_GRAVES
        if eh_grave and status_c in ("ativa", "em recuperação", "em recuperacao"):
            grave_ativa = True
        elif eh_grave and status_c == "controlada":
            grave_controlada = True
        if "acompanhamento" in status_c:
            acompanhamento = True

    notas = []
    if grave_ativa:
        if pct_atual >= 10:
            nivel = max(nivel, 2)
        else:
            nivel = max(nivel, 1)
        notas.append("condição grave ativa")
    if grave_controlada:
        nivel = max(nivel, 1)
        notas.append("condição grave controlada")
    if acompanhamento:
        nivel = max(nivel, 1)
        notas.append("em acompanhamento")

    cor = {0: "verde", 1: "amarelo", 2: "vermelho"}[min(nivel, 2)]
    justif = base + (" | " + " + ".join(notas) if notas else "")
    return cor, justif


def _semaforo_chip(cor: str, justificativa: str = "") -> html.Span:
    """Chip visual do semáforo. Reusa .hud-chip do CSS."""
    mapa = {
        "verde": ("hud-chip--ok", "🟢 Risco baixo"),
        "amarelo": ("hud-chip--warn", "🟡 Atenção"),
        "vermelho": ("hud-chip--bad", "🔴 Risco alto"),
    }
    css_cls, label = mapa.get(cor, ("hud-chip--ok", cor))
    return html.Span(
        className=f"hud-chip {css_cls}",
        title=justificativa,
        children=[
            html.Span(className="hud-chip__led"),
            html.Span(label, className="hud-chip__label"),
        ],
    )


def _kv_line(label: str, value, accent: str = PRIMARY_BLUE) -> html.Div:
    """Linha LABEL: valor com tipografia HUD (label mono uppercase)."""
    return html.Div(style={"marginBottom": "6px"}, children=[
        html.Span(f"{label}: ", style={
            "fontSize": "0.68rem", "fontWeight": "700",
            "color": accent, "textTransform": "uppercase",
            "letterSpacing": "0.07em",
            "fontFamily": "JetBrains Mono, Consolas, monospace",
        }),
        html.Span(str(value), style={"fontSize": "0.8rem", "color": "#2C3E50"}),
    ])


def _badge(text: str, color: str) -> html.Span:
    return html.Span(text, style={
        "display": "inline-block",
        "padding": "2px 10px",
        "border": f"1px solid {color}",
        "color": color,
        "fontSize": "0.7rem", "fontWeight": "700",
        "letterSpacing": "0.07em",
        "fontFamily": "JetBrains Mono, Consolas, monospace",
        "textTransform": "uppercase",
    })


# =============================================================================
# Blocos
# =============================================================================

def _bloco_hero(paciente: dict, papel: str, accent: str) -> html.Section:
    if papel == "medico":
        mod_tag = "MOD // 11  PRONTUÁRIO MÉDICO"
        subt = "Visão clínica — Dr. Robert Chase"
    else:
        mod_tag = "MOD // 03  PRONTUÁRIO"
        subt = "Registro Médico Eletrônico — CardioMonitor"
    return html.Section(className="hud-hero", children=[
        html.Span(mod_tag, className="hud-hero__tag"),
        html.H1([
            f"Prontuário — {paciente.get('nome', '?')} ",
            html.Span("❤", className="hud-heart"),
        ]),
        html.P(subt),
    ])


def _bloco_identidade_e_medico(paciente: dict, accent: str,
                                semaforo: tuple[str, str] | None) -> html.Div:
    """Grid 1fr/1fr: identidade (esq) + médico responsável (dir)."""
    nome = paciente.get("nome", "?")
    medico = paciente.get("medico_responsavel") or {}

    chip_status = None
    if semaforo:
        chip_status = _semaforo_chip(*semaforo)

    return html.Div(style={
        "display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px",
        "marginBottom": "20px",
    }, children=[
        # ── Identidade ──────────────────────────────────────────────────────
        hud_panel(
            title="Identificação do Paciente",
            status="DADOS CLÍNICOS", accent=accent,
            children=html.Div([
                html.Div(style={"display": "flex", "alignItems": "center",
                                "gap": "16px", "marginBottom": "14px"}, children=[
                    html.Div(_iniciais(nome), style={
                        "width": "54px", "height": "54px", "borderRadius": "50%",
                        "backgroundColor": accent, "color": "#FFFFFF",
                        "display": "flex", "alignItems": "center",
                        "justifyContent": "center",
                        "fontSize": "1.4rem", "fontWeight": "700",
                        "fontFamily": "JetBrains Mono, Consolas, monospace",
                        "flexShrink": "0",
                    }),
                    html.Div([
                        html.Div(nome, style={
                            "fontSize": "1rem", "fontWeight": "700",
                            "color": accent,
                            "fontFamily": "JetBrains Mono, Consolas, monospace",
                        }),
                        html.Div(
                            f"{paciente.get('nascimento', '?')}  //  "
                            f"{paciente.get('idade', '?')} anos  //  "
                            f"{paciente.get('sexo', '?').capitalize() if paciente.get('sexo') else '?'}",
                            style={"fontSize": "0.75rem", "color": "#6B7D8F",
                                   "fontFamily": "JetBrains Mono, Consolas, monospace"},
                        ),
                        html.Div(paciente.get("plano", ""), style={
                            "fontSize": "0.72rem", "color": "#6B7D8F",
                        }),
                    ]),
                    chip_status if chip_status else html.Span(),
                ]),
                _kv_line("CHA₂DS₂-VA",
                         f"{paciente.get('cha2ds2_va', '?')}  (informativo)",
                         accent=accent),
                _kv_line("Score Risco Cardiovascular",
                         paciente.get("score_risco_cardiovascular", "—"),
                         accent=accent),
                _kv_line("ID", paciente.get("id", "?"), accent=accent),
            ])
        ),
        # ── Médico responsável ──────────────────────────────────────────────
        hud_panel(
            title="Médico Responsável",
            status=(medico.get("especialidade") or "").upper(),
            accent=ACCENT_CYAN,
            children=html.Div([
                html.Div(style={"display": "flex", "alignItems": "center",
                                "gap": "16px", "marginBottom": "12px"}, children=[
                    html.Div(_iniciais(medico.get("nome", "Dr Chase")), style={
                        "width": "54px", "height": "54px", "borderRadius": "50%",
                        "backgroundColor": ACCENT_CYAN, "color": "#FFFFFF",
                        "display": "flex", "alignItems": "center",
                        "justifyContent": "center",
                        "fontSize": "1.2rem", "fontWeight": "700",
                        "fontFamily": "JetBrains Mono, Consolas, monospace",
                        "flexShrink": "0",
                    }),
                    html.Div([
                        html.Div(medico.get("nome", "—"), style={
                            "fontSize": "1rem", "fontWeight": "700",
                            "color": "var(--hud-blue-dark)",
                            "fontFamily": "JetBrains Mono, Consolas, monospace",
                        }),
                        html.Div(medico.get("especialidade", ""), style={
                            "fontSize": "0.78rem", "color": ACCENT_CYAN,
                            "fontWeight": "600",
                        }),
                        html.Div(medico.get("crm", ""), style={
                            "fontSize": "0.72rem", "color": "#6B7D8F",
                            "fontFamily": "JetBrains Mono, Consolas, monospace",
                        }),
                    ]),
                ]),
            ])
        ),
    ])


def _bloco_resumo_clinico(paciente: dict, accent: str) -> html.Div | None:
    texto = paciente.get("resumo_clinico")
    if not texto:
        return None
    return hud_panel(
        title="Resumo Clínico", status="NARRATIVA MÉDICA", accent=accent,
        children=html.P(texto, style={
            "margin": 0, "fontSize": "0.86rem",
            "lineHeight": "1.6", "color": "#2C3E50",
        })
    )


def _bloco_condicoes(paciente: dict, accent: str) -> html.Div:
    condicoes = paciente.get("condicoes_ativas", [])
    if not condicoes:
        body = html.P("Sem condições registradas.",
                      style={"margin": 0, "color": TEXT_MUTED,
                             "fontStyle": "italic"})
    else:
        items = []
        for c in condicoes:
            status_c = (c.get("status") or "").lower()
            if "ativa" in status_c or "recupera" in status_c:
                chip_cls, chip_label = "hud-chip--bad", c.get("status", "ativa")
            elif "controlada" in status_c:
                chip_cls, chip_label = "hud-chip--warn", c.get("status", "controlada")
            else:
                chip_cls, chip_label = "hud-chip--ok", c.get("status", "—")
            items.append(html.Div(style={
                "padding": "10px 14px", "marginBottom": "8px",
                "borderLeft": f"3px solid {accent}",
                "backgroundColor": "rgba(7,62,130,0.04)",
                "display": "flex", "alignItems": "center",
                "justifyContent": "space-between", "gap": "12px",
            }, children=[
                html.Div([
                    html.Span(c.get("cid", "?"), style={
                        "fontSize": "0.72rem", "fontWeight": "700",
                        "color": accent, "letterSpacing": "0.08em",
                        "fontFamily": "JetBrains Mono, Consolas, monospace",
                        "marginRight": "10px",
                    }),
                    html.Span(c.get("nome", "?"), style={
                        "fontSize": "0.88rem", "fontWeight": "600",
                        "color": "#2C3E50",
                    }),
                    html.Span(f"  desde {c.get('desde', '?')}", style={
                        "fontSize": "0.72rem", "color": "#6B7D8F",
                        "marginLeft": "8px",
                        "fontFamily": "JetBrains Mono, Consolas, monospace",
                    }),
                ]),
                html.Span(className=f"hud-chip {chip_cls}", children=[
                    html.Span(className="hud-chip__led"),
                    html.Span(chip_label, className="hud-chip__label"),
                ]),
            ]))
        body = html.Div(items)
    return hud_panel(
        title="Condições Ativas",
        status=f"{len(condicoes)} REGISTRO" if len(condicoes) == 1
               else f"{len(condicoes)} REGISTROS",
        accent=accent, children=body,
    )


def _prescricao_card(p: dict, accent: str) -> html.Div:
    """Card de um medicamento. Lê campos enriquecidos (classe/posologia/
    meta_terapeutica/observacao), todos opcionais."""
    children = [
        # Linha 1 (destaque): nome + dose + frequência
        html.Div(style={"display": "flex", "alignItems": "baseline",
                        "gap": "10px", "marginBottom": "6px",
                        "flexWrap": "wrap"}, children=[
            html.Span(p.get("nome", "?"), style={
                "fontSize": "0.96rem", "fontWeight": "700",
                "color": accent,
                "fontFamily": "JetBrains Mono, Consolas, monospace",
            }),
            html.Span(p.get("dose", ""), style={
                "fontSize": "0.82rem", "fontWeight": "600",
                "color": "#2C3E50",
            }),
            html.Span(f" · {p.get('frequencia', '')}", style={
                "fontSize": "0.78rem", "color": "#6B7D8F",
            }) if p.get("frequencia") else None,
        ]),
    ]
    # Linha 2: classe + indicação
    classe = p.get("classe")
    indic = p.get("indicacao")
    if classe or indic:
        partes = []
        if classe:
            partes.append(html.Span(classe, style={
                "color": ACCENT_CYAN, "fontWeight": "600",
            }))
        if indic:
            if partes:
                partes.append(html.Span("  //  ", style={"color": "#6B7D8F"}))
            partes.append(html.Span(indic, style={"color": "#2C3E50"}))
        children.append(html.Div(partes, style={
            "fontSize": "0.78rem", "marginBottom": "6px",
        }))
    # Linha 3: posologia
    if p.get("posologia"):
        children.append(html.Div([
            html.Span("Posologia: ", style={
                "fontSize": "0.7rem", "fontWeight": "700",
                "color": accent, "letterSpacing": "0.06em",
                "fontFamily": "JetBrains Mono, Consolas, monospace",
            }),
            html.Span(p["posologia"], style={
                "fontSize": "0.8rem", "color": "#2C3E50",
            }),
        ], style={"marginBottom": "4px"}))
    # Linha 4: meta terapêutica
    if p.get("meta_terapeutica"):
        children.append(html.Div([
            html.Span("Meta: ", style={
                "fontSize": "0.7rem", "fontWeight": "700",
                "color": SUCCESS, "letterSpacing": "0.06em",
                "fontFamily": "JetBrains Mono, Consolas, monospace",
            }),
            html.Span(p["meta_terapeutica"], style={
                "fontSize": "0.8rem", "color": "#2C3E50",
            }),
        ], style={"marginBottom": "4px"}))
    # Linha 5: observação (warning)
    if p.get("observacao"):
        children.append(html.Div(p["observacao"], style={
            "marginTop": "8px", "padding": "6px 10px",
            "backgroundColor": "rgba(242,183,5,0.10)",
            "borderLeft": f"3px solid {WARNING}",
            "fontSize": "0.76rem", "color": "#7A5B00",
            "lineHeight": "1.5",
        }))
    # Rodapé: desde
    if p.get("inicio"):
        children.append(html.Div(f"desde {p['inicio']}", style={
            "marginTop": "8px", "fontSize": "0.7rem",
            "color": "#6B7D8F",
            "fontFamily": "JetBrains Mono, Consolas, monospace",
        }))
    return html.Div(style={
        "padding": "14px 16px", "marginBottom": "12px",
        "border": f"1px solid {BORDER}",
        "borderLeft": f"3px solid {accent}",
        "backgroundColor": "rgba(7,62,130,0.03)",
    }, children=children)


def _bloco_prescricao(paciente: dict, accent: str) -> html.Div:
    meds = paciente.get("medicacoes_ativas", [])
    if not meds:
        body = html.P("Sem medicações ativas.",
                      style={"margin": 0, "color": TEXT_MUTED,
                             "fontStyle": "italic"})
        status = "0 ITENS"
    else:
        body = html.Div([_prescricao_card(m, accent) for m in meds])
        status = f"{len(meds)} ITEM" if len(meds) == 1 else f"{len(meds)} ITENS"
    return hud_panel(
        title="Prescrição Médica Vigente",
        status=status, accent=accent, children=body,
    )


def _bloco_alergias(paciente: dict, accent: str) -> html.Div:
    alergias = paciente.get("alergias", [])
    if not alergias:
        body = html.P("Sem alergias registradas.",
                      style={"margin": 0, "color": TEXT_MUTED,
                             "fontStyle": "italic"})
    else:
        items = []
        for a in alergias:
            grav = (a.get("gravidade") or "").lower()
            if "grave" in grav or "severa" in grav:
                chip_cls = "hud-chip--bad"
            elif "moderada" in grav:
                chip_cls = "hud-chip--warn"
            else:
                chip_cls = "hud-chip--ok"
            items.append(html.Div(style={
                "padding": "8px 12px", "marginBottom": "6px",
                "borderLeft": f"3px solid {DANGER}",
                "backgroundColor": "rgba(229,62,62,0.04)",
                "display": "flex", "alignItems": "center",
                "justifyContent": "space-between", "gap": "12px",
            }, children=[
                html.Div([
                    html.Span(a.get("substancia", "?"), style={
                        "fontSize": "0.88rem", "fontWeight": "700",
                        "color": DANGER,
                        "fontFamily": "JetBrains Mono, Consolas, monospace",
                    }),
                    html.Span(f"  // reação: {a.get('reacao', '?')}", style={
                        "fontSize": "0.78rem", "color": "#2C3E50",
                        "marginLeft": "8px",
                    }),
                ]),
                html.Span(className=f"hud-chip {chip_cls}", children=[
                    html.Span(className="hud-chip__led"),
                    html.Span(a.get("gravidade", "—"),
                              className="hud-chip__label"),
                ]),
            ]))
        body = html.Div(items)
    return hud_panel(
        title="Alergias",
        status=f"{len(alergias)} REGISTRO" if len(alergias) == 1
               else f"{len(alergias)} REGISTROS",
        accent=DANGER if alergias else accent, children=body,
    )


def _consulta_card(c: dict, accent: str) -> html.Div:
    status_c = (c.get("status") or "").lower()
    is_agendada = "agend" in status_c
    cor = ACCENT_CYAN if is_agendada else accent
    badge_text = "AGENDADA" if is_agendada else "REALIZADA"
    badge_color = ACCENT_CYAN if is_agendada else SUCCESS
    return html.Div(style={
        "borderLeft": f"3px solid {cor}",
        "padding": "12px 16px", "marginBottom": "10px",
        "backgroundColor": "rgba(7,62,130,0.04)",
    }, children=[
        html.Div(style={"display": "flex",
                        "justifyContent": "space-between",
                        "alignItems": "center", "marginBottom": "4px",
                        "flexWrap": "wrap", "gap": "8px"}, children=[
            html.Span(f"{c.get('data', '?')}  //  {c.get('tipo', '?')}", style={
                "fontFamily": "JetBrains Mono, Consolas, monospace",
                "fontSize": "0.8rem", "fontWeight": "700",
                "color": "var(--hud-blue-dark)",
            }),
            _badge(badge_text, badge_color),
        ]),
        html.P(c.get("resumo", c.get("observacoes", "")), style={
            "fontSize": "0.82rem", "color": "#2C3E50",
            "margin": "0 0 4px 0", "lineHeight": "1.5",
        }),
        html.Span(c.get("medico", ""), style={
            "fontSize": "0.72rem", "color": "#6B7D8F",
            "fontFamily": "JetBrains Mono, Consolas, monospace",
        }),
    ])


def _bloco_consultas(paciente: dict, accent: str) -> html.Div:
    consultas = paciente.get("consultas") or {}
    ultima = consultas.get("ultima")
    proxima = consultas.get("proxima")
    historico = consultas.get("historico", [])

    return hud_panel(
        title="Consultas",
        status=f"{len(historico)} NO HISTÓRICO",
        accent=accent,
        children=html.Div([
            # Última + Próxima lado a lado
            html.Div(className="grid grid-2", style={"marginBottom": "12px"},
                     children=[
                # Última
                html.Div([
                    html.Div("ÚLTIMA CONSULTA", style={
                        "fontSize": "0.7rem", "fontWeight": "700",
                        "color": accent, "letterSpacing": "0.1em",
                        "fontFamily": "JetBrains Mono, Consolas, monospace",
                        "marginBottom": "6px",
                    }),
                    _consulta_card({**(ultima or {}),
                                    "tipo": (ultima or {}).get("especialidade",
                                                              "Consulta"),
                                    "status": "realizada",
                                    "resumo": (ultima or {}).get("observacoes",
                                                                 "Sem observações.")},
                                   accent) if ultima
                    else html.P("Sem registro de última consulta.",
                                style={"color": TEXT_MUTED,
                                       "fontStyle": "italic", "margin": 0}),
                ]),
                # Próxima
                html.Div([
                    html.Div("PRÓXIMA CONSULTA", style={
                        "fontSize": "0.7rem", "fontWeight": "700",
                        "color": ACCENT_CYAN, "letterSpacing": "0.1em",
                        "fontFamily": "JetBrains Mono, Consolas, monospace",
                        "marginBottom": "6px",
                    }),
                    _consulta_card({**(proxima or {}),
                                    "tipo": (proxima or {}).get("especialidade",
                                                                "Consulta"),
                                    "status": "agendada",
                                    "resumo": "Aguardando atendimento.",
                                    "medico": (proxima or {}).get("medico", "—")},
                                   accent) if proxima
                    else html.P("Sem consulta agendada.",
                                style={"color": TEXT_MUTED,
                                       "fontStyle": "italic", "margin": 0}),
                ]),
            ]),
            # Histórico
            html.Div([
                html.Div("HISTÓRICO", style={
                    "fontSize": "0.7rem", "fontWeight": "700",
                    "color": accent, "letterSpacing": "0.1em",
                    "fontFamily": "JetBrains Mono, Consolas, monospace",
                    "marginTop": "8px", "marginBottom": "6px",
                }),
                html.Div([_consulta_card(c, accent) for c in historico])
                if historico
                else html.P("Sem histórico de consultas.",
                            style={"color": TEXT_MUTED,
                                   "fontStyle": "italic", "margin": 0}),
            ]),
        ]),
    )


def _bloco_exames(paciente: dict, accent: str) -> html.Div:
    exames = paciente.get("exames_recentes", [])
    if not exames:
        body = html.P("Sem exames recentes.",
                      style={"margin": 0, "color": TEXT_MUTED,
                             "fontStyle": "italic"})
    else:
        items = []
        for e in exames:
            items.append(html.Div(style={
                "padding": "10px 14px", "marginBottom": "8px",
                "borderLeft": f"3px solid {ACCENT_CYAN}",
                "backgroundColor": "rgba(0,169,224,0.04)",
            }, children=[
                html.Div(style={"display": "flex",
                                "justifyContent": "space-between",
                                "flexWrap": "wrap", "gap": "8px"}, children=[
                    html.Span(f"{e.get('data', '?')}  //  {e.get('tipo', '?')}",
                              style={
                                "fontFamily": "JetBrains Mono, Consolas, monospace",
                                "fontSize": "0.8rem", "fontWeight": "700",
                                "color": "var(--hud-blue-dark)",
                              }),
                    _badge(e.get("resultado", "—"),
                           SUCCESS if (e.get("resultado") or "").lower() == "normal"
                           else WARNING),
                ]),
                html.P(e.get("laudo", ""), style={
                    "fontSize": "0.8rem", "color": "#2C3E50",
                    "margin": "6px 0 0 0", "lineHeight": "1.5",
                }),
            ]))
        body = html.Div(items)
    return hud_panel(
        title="Exames Recentes",
        status=f"{len(exames)} REGISTRO" if len(exames) == 1
               else f"{len(exames)} REGISTROS",
        accent=ACCENT_CYAN, children=body,
    )


def _blocos_telemetria(df: pd.DataFrame, accent: str) -> list:
    """Telemetria PPG: KPIs + 5 figuras + tabela. Cópia fiel do gabriel.py,
    parametrizada por accent (azul/verde). Função pura de df."""
    reg = int((df["status"] == "regular").sum())
    irr = int((df["status"] == "irregular").sum())
    duration_s = float(df["timestamp_s"].max() - df["timestamp_s"].min())
    bpm_mean = float(df["bpm"].mean())

    # KPIs ────────────────────────────────────────────────────────────────────
    kpis = html.Div(className="grid grid-5", children=[
        telemetry_tile("BPM médio", f"{bpm_mean:.1f}", unit="bpm",
                       sub=bpm_zone(bpm_mean), accent=bpm_zone_color(bpm_mean)),
        telemetry_tile("BPM mín / máx",
                       f"{df['bpm'].min():.0f} / {df['bpm'].max():.0f}",
                       sub="amplitude total", accent=PRIMARY_BLUE),
        telemetry_tile("IBI médio",
                       f"{df['ibi_ms'].mean():.0f}", unit="ms",
                       sub=f"sd {df['ibi_ms'].std():.0f} ms",
                       accent=ACCENT_CYAN),
        telemetry_tile("Episódios irregulares", str(irr),
                       sub=f"{irr/len(df)*100:.1f}% dos batimentos",
                       accent=DANGER if irr else SUCCESS),
        telemetry_tile("Batimentos anormais",
                       str(int(df["bat_anormais"].sum())),
                       sub="somatório da janela deslizante",
                       accent=WARNING),
    ])

    # BPM timeline ────────────────────────────────────────────────────────────
    bpm_fig = go.Figure(layout=plotly_layout(340))
    style_axes(bpm_fig, "Tempo (s)", "BPM")
    bpm_fig.add_hrect(y0=60, y1=100, fillcolor=SUCCESS, opacity=0.06,
                      line_width=0)
    bpm_fig.add_trace(go.Scatter(
        x=df["timestamp_s"], y=df["bpm"], mode="lines",
        line=dict(color=accent, width=1.6), name="BPM",
        hovertemplate="t=%{x:.1f}s<br>BPM=%{y:.1f}<extra></extra>",
    ))
    for s, color in [("regular", SUCCESS), ("atencao", WARNING),
                     ("irregular", DANGER)]:
        sub = df[df["status"] == s]
        if not sub.empty:
            bpm_fig.add_trace(go.Scatter(
                x=sub["timestamp_s"], y=sub["bpm"], mode="markers",
                marker=dict(color=color, size=6,
                            line=dict(color="#FFFFFF", width=1)),
                name=status_label_pt(s),
            ))

    # IBI ─────────────────────────────────────────────────────────────────────
    ibi_fig = go.Figure(layout=plotly_layout(320))
    style_axes(ibi_fig, "Tempo (s)", "ms")
    ibi_fig.add_trace(go.Scatter(
        x=df["timestamp_s"], y=df["ibi_ms"], mode="lines",
        line=dict(color=ACCENT_CYAN, width=1.6), name="IBI"))
    ibi_fig.add_trace(go.Scatter(
        x=df["timestamp_s"], y=df["media_ibi"], mode="lines",
        line=dict(color=accent, width=1.4, dash="dot"),
        name="Média (janela 5)"))

    # Desvio + anormais ───────────────────────────────────────────────────────
    stab_fig = go.Figure(layout=plotly_layout(320))
    style_axes(stab_fig, "Tempo (s)", "Desvio (ms)", y2_title="Anormais")
    stab_fig.add_trace(go.Scatter(
        x=df["timestamp_s"], y=df["desvio_medio"], mode="lines",
        line=dict(color=DANGER, width=1.6), name="Desvio médio"))
    stab_fig.add_trace(go.Bar(
        x=df["timestamp_s"], y=df["bat_anormais"], name="Anormais",
        marker_color=ACCENT_CYAN, opacity=0.35, yaxis="y2"))
    stab_fig.add_hline(y=100, line_color=WARNING, line_dash="dash")
    stab_fig.add_hline(y=120, line_color=DANGER, line_dash="dash")

    # Histograma ──────────────────────────────────────────────────────────────
    hist = px.histogram(df, x="bpm", nbins=30, color="status",
                        color_discrete_map={
                            "regular": SUCCESS, "atencao": WARNING,
                            "irregular": DANGER})
    hist.update_layout(**plotly_layout(300))
    style_axes(hist, "BPM", "Contagem")

    # Box plot ────────────────────────────────────────────────────────────────
    box = go.Figure(layout=plotly_layout(300))
    style_axes(box, "", "ms")
    box.add_trace(go.Box(y=df["ibi_ms"], name="IBI (ms)",
                         marker_color=accent, line_color=accent))
    box.add_trace(go.Box(y=df["desvio_medio"], name="Desvio médio",
                         marker_color=DANGER, line_color=DANGER))

    # Tabela ──────────────────────────────────────────────────────────────────
    view = df.copy()
    view["status"] = view["status"].map(status_label_pt)
    if "datetime" in view.columns and pd.api.types.is_datetime64_any_dtype(view["datetime"]):
        view["datetime"] = view["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
    view = view.rename(columns={
        "datetime": "Data/hora", "patient": "Paciente",
        "timestamp_s": "t (s)", "ibi_ms": "IBI (ms)", "bpm": "BPM",
        "media_ibi": "Média IBI", "desvio_medio": "Desvio médio",
        "bat_anormais": "Bat. anormais", "status": "Status",
    })
    table = dash_table.DataTable(
        data=view.to_dict("records"),
        columns=[{"name": c, "id": c} for c in view.columns],
        page_size=15, style_as_list_view=True,
        style_table={"overflowX": "auto"},
        style_cell={
            "fontFamily": "JetBrains Mono, Consolas, monospace",
            "fontSize": "0.78rem", "padding": "6px 10px",
            "border": "1px solid #E3ECF5", "color": "#0B1E34",
        },
        style_header={
            "backgroundColor": "#F3F7FB", "fontWeight": "700",
            "textTransform": "uppercase", "letterSpacing": "0.08em",
            "fontSize": "0.7rem", "color": "#073E82",
            "borderBottom": "2px solid #073E82",
        },
        style_data_conditional=[
            {"if": {"filter_query": '{Status} eq "Regular"'}, "color": SUCCESS},
            {"if": {"filter_query": '{Status} eq "Atenção"'}, "color": "#9A7300"},
            {"if": {"filter_query": '{Status} eq "Irregular"'},
             "color": DANGER, "fontWeight": "700"},
        ],
    )
    csv_href = "data:text/csv;charset=utf-8," + quote(df.to_csv(index=False))

    return [
        hud_panel(title="Monitoramento PPG — Sessão de Referência",
                  status=f"{len(df)} BATIMENTOS  //  {duration_s:.0f}s",
                  accent=ACCENT_CYAN, children=kpis),
        hud_panel(title="Frequência cardíaca ao longo da aquisição",
                  status="TIMELINE", accent=ACCENT_CYAN,
                  children=dcc.Graph(figure=bpm_fig,
                                     config={"displayModeBar": False})),
        html.Div(className="grid grid-2", children=[
            hud_panel(title="Intervalo entre batimentos (IBI)",
                      status="ms",
                      children=dcc.Graph(figure=ibi_fig,
                                         config={"displayModeBar": False})),
            hud_panel(title="Desvio médio e batimentos anormais",
                      status="DESVIO", accent=DANGER,
                      children=dcc.Graph(figure=stab_fig,
                                         config={"displayModeBar": False})),
        ]),
        hud_panel(title="Distribuições", status="HIST + BOX",
                  children=html.Div(className="grid grid-2", children=[
                      dcc.Graph(figure=hist, config={"displayModeBar": False}),
                      dcc.Graph(figure=box, config={"displayModeBar": False}),
                  ])),
        hud_panel(title="Registros PPG", status=f"{len(df)} linhas",
                  children=[
                      table,
                      html.Div(style={"marginTop": "14px"}, children=[
                          html.A("BAIXAR CSV", href=csv_href,
                                 className="hud-btn hud-btn--ghost",
                                 download="telemetria.csv"),
                      ]),
                  ]),
    ]


# ── Blocos exclusivos do médico ──────────────────────────────────────────────

def _bloco_anotacoes(paciente: dict) -> html.Div:
    """Anotações clínicas — só médico. Fase 2A.2: render read-only (mostra as
    anotações existentes). Edição/persistência vem na Fase 4."""
    anotacoes = paciente.get("anotacoes_medicas", [])
    if anotacoes:
        items = [
            html.Div(style={
                "padding": "10px 14px", "marginBottom": "8px",
                "borderLeft": f"3px solid {SUCCESS}",
                "backgroundColor": "rgba(31,174,111,0.05)",
            }, children=[
                html.Div([
                    html.Span(a.get("data", "?"), style={
                        "fontSize": "0.75rem", "fontWeight": "700",
                        "color": SUCCESS, "letterSpacing": "0.06em",
                        "fontFamily": "JetBrains Mono, Consolas, monospace",
                    }),
                    html.Span(f"  ·  {a.get('medico', '?')}", style={
                        "fontSize": "0.72rem", "color": "#6B7D8F",
                        "fontFamily": "JetBrains Mono, Consolas, monospace",
                    }),
                ], style={"marginBottom": "4px"}),
                html.P(a.get("texto", ""), style={
                    "margin": 0, "fontSize": "0.82rem",
                    "color": "#2C3E50", "lineHeight": "1.5",
                }),
            ]) for a in anotacoes
        ]
        body = html.Div(items)
    else:
        body = html.P("Sem anotações registradas.",
                      style={"margin": 0, "color": TEXT_MUTED,
                             "fontStyle": "italic"})
    return hud_panel(
        title="Anotações Clínicas",
        status="VISÍVEL SÓ AO MÉDICO",
        accent=SUCCESS,
        children=html.Div([
            body,
            html.Div(
                "Edição e persistência: implementação na Fase 4 do app médico.",
                style={
                    "marginTop": "10px",
                    "padding": "8px 12px",
                    "fontSize": "0.74rem", "color": TEXT_MUTED,
                    "fontStyle": "italic",
                    "borderTop": f"1px dashed {BORDER}",
                },
            ),
        ]),
    )


def _bloco_aprovacao_rascunho(paciente: dict) -> html.Div:
    """Aprovação de rascunho — só médico. Fase 2A.2: aviso 'em construção'.
    Geração de rascunho (tool) + aprovar/rejeitar/editar: Fase 4."""
    return hud_panel(
        title="Aprovação de Rascunho de Prescrição",
        status="AGUARDANDO IMPLEMENTAÇÃO",
        accent=WARNING,
        children=html.Div([
            html.Div([
                html.Strong("Princípio-guia: ",
                            style={"color": WARNING}),
                "a IA propõe rascunho, o médico decide. Aprovar/rejeitar/editar.",
            ], style={
                "padding": "10px 14px", "marginBottom": "10px",
                "backgroundColor": "rgba(242,183,5,0.10)",
                "borderLeft": f"3px solid {WARNING}",
                "fontSize": "0.8rem", "color": "#7A5B00",
            }),
            html.P(
                "Em construção — implementação na Fase 4 do app médico. "
                "Vai integrar com a tool sugerir_rascunho_prescricao (já existe) "
                "e persistir aprovações via update_patient.",
                style={"margin": 0, "color": TEXT_MUTED,
                       "fontStyle": "italic", "fontSize": "0.82rem"},
            ),
        ]),
    )


# =============================================================================
# Função principal
# =============================================================================

def render_prontuario(paciente_id: str, papel: str = "paciente") -> html.Div:
    """Renderiza o prontuário completo de um paciente.

    Args:
        paciente_id: ID do paciente (GABRIEL, LUCAS, MARIA, HELENA, PEDRO).
        papel: 'paciente' (azul, sem anotações/rascunhos) ou
               'medico' (verde, com anotações + aprovação de rascunho + semáforo).

    Returns:
        html.Div pronto pra ser retornado por layout() de uma rota.
    """
    paciente = get_patient(paciente_id)
    if not paciente:
        return html.Div(className="hud-page", children=[
            html.Section(className="hud-hero", children=[
                html.Span("MOD // 03  PRONTUÁRIO", className="hud-hero__tag"),
                html.H1(f"Paciente '{paciente_id}' não encontrado"),
                html.P("Verifique o ID ou o registro de pacientes."),
            ]),
            html.Div(className="hud-alert", children=[
                html.Strong("[ ERRO ]"),
                html.Span(f"  paciente_id='{paciente_id}' não está em "
                          f"perfis_clinicos.json."),
            ]),
        ])

    csv_path = _csv_do_paciente(paciente_id)
    df = None
    if csv_path is not None and csv_path.exists():
        try:
            df = load_csv(csv_path)
        except Exception:
            df = None

    accent = SUCCESS if papel == "medico" else PRIMARY_BLUE
    semaforo = _calcular_semaforo(paciente, df) if papel == "medico" else None

    blocos = [
        _bloco_hero(paciente, papel, accent),
        _bloco_identidade_e_medico(paciente, accent, semaforo),
    ]
    resumo = _bloco_resumo_clinico(paciente, accent)
    if resumo is not None:
        blocos.append(resumo)
    blocos.extend([
        _bloco_condicoes(paciente, accent),
        _bloco_prescricao(paciente, accent),
        _bloco_alergias(paciente, accent),
        _bloco_consultas(paciente, accent),
        _bloco_exames(paciente, accent),
    ])
    if df is not None and not df.empty:
        blocos.extend(_blocos_telemetria(df, accent))
    else:
        blocos.append(hud_panel(
            title="Telemetria PPG",
            status="SEM DADOS",
            children=html.P(
                "Sem CSV de telemetria disponível pra este paciente.",
                style={"margin": 0, "color": TEXT_MUTED,
                       "fontStyle": "italic"},
            ),
        ))

    if papel == "medico":
        blocos.append(_bloco_anotacoes(paciente))
        blocos.append(_bloco_aprovacao_rascunho(paciente))

    return html.Div(blocos, className="hud-page")
