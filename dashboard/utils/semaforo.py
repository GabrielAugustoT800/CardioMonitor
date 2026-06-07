"""Semáforo de risco cardiovascular — cálculo + helper visual (fase 3).

Lógica v2 validada: telemetria dominante + condição modificador.
CHA2DS2-VA é informativo (não soma nível).

Movido de utils/prontuario.py (era privado, virou público) pra ser reusado em:
- utils/prontuario.py (render do prontuário em visão médico)
- pages/medico/caseload.py (lista de cards-semáforo)
- futura Fase 5 (fila de alertas)

Convenção do projeto: 'from utils.semaforo' (dashboard/ está no sys.path).
"""

from __future__ import annotations

import pandas as pd
from dash import html


# Mapeamento CID3 -> "grave" (CIDs cardiovasculares de alta gravidade).
# I48 FA, I21 IAM agudo, I50 IC, I20 angina, I25 doença isquêmica crônica.
_CIDS_GRAVES = {"I48", "I21", "I50", "I20", "I25"}


def calcular_semaforo(paciente: dict, df: pd.DataFrame | None) -> tuple[str, str]:
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
    # Inicialização explícita — corrige a gambiarra `locals().get('pct_atual', 0.0)`
    # do original. Quando o ramo "sem dados" é tomado, pct_atual já vale 0.0.
    pct_atual = 0.0

    # 1) piso pela telemetria
    if df is None or df.empty or "status" not in df.columns:
        nivel = 1
        base = "sem dados de telemetria"
    else:
        ult = df.tail(50)
        n = len(ult)
        irreg = int((ult["status"] == "irregular").sum())
        pct_atual = (irreg / n * 100) if n else 0.0
        if pct_atual >= 25:
            nivel, base = 2, f"telemetria alta ({pct_atual:.0f}% irregular)"
        elif pct_atual >= 10:
            nivel, base = 1, f"telemetria moderada ({pct_atual:.0f}% irregular)"
        else:
            nivel, base = 0, f"telemetria estável ({pct_atual:.0f}% irregular)"

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


def semaforo_chip(cor: str, justificativa: str = "") -> html.Span:
    """Chip visual do semáforo (reusa CSS .hud-chip).

    Aceita 2 args pra compat com o caller existente em prontuario.py
    (`semaforo_chip(*semaforo)`, expandindo tupla `(cor, justif)`).
    A justificativa vira tooltip (title=) — visível no hover.
    """
    mapa = {
        "verde": ("hud-chip--ok", "🟢 ESTÁVEL"),
        "amarelo": ("hud-chip--warn", "🟡 ATENÇÃO"),
        "vermelho": ("hud-chip--bad", "🔴 CRÍTICO"),
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
