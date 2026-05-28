"""
Tool: consultar_telemetria_dashboard

Permite ao chatbot puxar dados do CardioMonitor (cardiac_data.csv) para
contextualizar respostas — separadamente da tool `analisar_ritmo_cardiaco`,
que dá um veredito.

Quando usar cada um:
- analisar_ritmo_cardiaco(paciente_id="X") → "está irregular? está regular?"
- consultar_telemetria_dashboard(paciente_id="X") → "me mostra os números"

O agente pode chamar os dois em sequência: primeiro pega a telemetria
crua, depois pede um veredito sobre ela.
"""
from __future__ import annotations

from typing import Any

from shared.telemetry_store import load_recent_beats, window_summary


def consultar_telemetria_dashboard(
    paciente_id: str,
    janela_min: int = 5,
    n_amostras: int = 10,
) -> dict[str, Any]:
    """
    Consulta telemetria PPG mais recente capturada pelo CardioMonitor.

    Args:
        paciente_id: ID do beneficiário. Ex: BENEF-MARIA, BENEF-NEW-001.
        janela_min: Tamanho da janela em minutos para o sumário (default 5).
        n_amostras: Quantos batimentos individuais devolver na lista
            de amostra (default 10, max recomendado 30).

    Returns:
        - telemetria_disponivel: True/False
        - resumo_janela: BPM médio/mín/máx, % regular/atenção/irregular
        - ultimos_batimentos: lista dos N batimentos mais recentes
    """
    if not paciente_id or not paciente_id.strip():
        return {"erro": "paciente_id é obrigatório."}

    n_amostras = max(1, min(n_amostras, 50))

    df = load_recent_beats(paciente_id, n=n_amostras)
    if df.empty:
        return {
            "paciente_id": paciente_id,
            "telemetria_disponivel": False,
            "mensagem": (
                "Nenhum dado de PPG capturado pelo CardioMonitor para este "
                "paciente. Inicie uma sessão no /monitor ou conecte o ESP32."
            ),
        }

    sumario = window_summary(paciente_id, minutes=janela_min)

    return {
        "paciente_id": paciente_id,
        "telemetria_disponivel": True,
        "resumo_janela": sumario,
        "ultimos_batimentos": df.tail(n_amostras).to_dict(orient="records"),
        "nota": (
            "Dados em tempo real do sensor PPG. Para veredito clínico, "
            "encaminhe ao tool `analisar_ritmo_cardiaco(paciente_id=...)`."
        ),
    }
