"""Tool: gerar_relatorio_telemetria — sumário agregado do dataset global.

Feature 2 do README upstream do ArrhythmiaMonitor. Complementar a
consultar_telemetria_dashboard (que filtra por paciente). Esta tool
retorna visão geral do sistema lendo dataset completo via load_blob
do dashboard/utils/storage.py (com fallback local pro cardiac_data.csv
implementado em J.3).
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path
from typing import Any

# Adiciona dashboard/ ao sys.path pra resolver `from utils.storage import load_blob`
# que assume dashboard/ como base (convenção upstream).
_DASHBOARD_DIR = Path(__file__).resolve().parents[2] / "dashboard"
if str(_DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD_DIR))

from utils.storage import load_blob  # noqa: E402


def gerar_relatorio_telemetria(n_registros: int = 50) -> dict[str, Any]:
    """
    Gera relatório resumido dos últimos N registros do dataset global.

    Args:
        n_registros: quantos batimentos analisar (default 50, max 500).

    Returns:
        dict com sumário formatado pt-BR pro chatbot incorporar.
    """
    n = max(1, min(500, n_registros))

    try:
        df = load_blob(tail=n)
    except Exception as e:  # pragma: no cover — defesa contra blob upstream
        return {
            "erro": f"Falha ao carregar telemetria: {e}",
            "relatorio": None,
        }

    if df.empty:
        return {
            "erro": "Dataset vazio ou indisponível.",
            "relatorio": None,
        }

    n_real = len(df)
    bpms = df["bpm"].tolist()
    statuses = df["status"].tolist()
    bat_anormais = (df["bat_anormais"].tolist()
                    if "bat_anormais" in df.columns else [])

    bpm_medio = statistics.mean(bpms)
    bpm_min = min(bpms)
    bpm_max = max(bpms)
    n_irregular = sum(1 for s in statuses if s == "irregular")
    pct_irregular = (n_irregular / n_real * 100) if n_real else 0
    total_anomalos = sum(bat_anormais) if bat_anormais else 0

    # Classificação semântica
    if pct_irregular < 5:
        avaliacao = "padrão estável — predominância de ritmo regular"
    elif pct_irregular < 20:
        avaliacao = "padrão misto — episódios isolados de irregularidade"
    else:
        avaliacao = ("padrão de instabilidade — alta proporção de batimentos "
                     "irregulares")

    relatorio = (
        f"Análise dos últimos {n_real} registros do CardioMonitor:\n"
        f"- BPM médio: {bpm_medio:.1f}\n"
        f"- BPM mínimo / máximo: {bpm_min:.1f} / {bpm_max:.1f}\n"
        f"- Batimentos irregulares: {n_irregular} de {n_real} "
        f"({pct_irregular:.1f}%)\n"
        f"- Total de batimentos anômalos detectados: {total_anomalos}\n"
        f"- Avaliação: {avaliacao}."
    )

    return {
        "n_registros_analisados": n_real,
        "bpm_medio": round(bpm_medio, 1),
        "bpm_min": round(bpm_min, 1),
        "bpm_max": round(bpm_max, 1),
        "pct_irregular": round(pct_irregular, 1),
        "total_anomalos": total_anomalos,
        "avaliacao": avaliacao,
        "relatorio": relatorio,
    }
