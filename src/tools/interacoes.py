"""
Tool: verificar_interacoes_medicamentosas
Verifica interações entre medicamentos cardiovasculares.
"""

import json
from pathlib import Path

_MOCK_PATH = Path(__file__).resolve().parents[2] / "data" / "mocks" / "interacoes_medicamentosas.json"


def verificar_interacoes_medicamentosas(medicamentos: list[str]) -> dict:
    """
    Verifica interações medicamentosas entre os medicamentos informados.

    Args:
        medicamentos: Lista com nomes dos medicamentos. Mínimo 2.

    Returns:
        Dicionário com interações encontradas e severidade máxima.
    """
    if len(medicamentos) < 2:
        return {"erro": "Informe pelo menos 2 medicamentos para verificação."}

    with open(_MOCK_PATH, "r", encoding="utf-8") as f:
        dados = json.load(f)

    # Normalizar nomes para comparação
    nomes_normalizados = [m.strip().lower() for m in medicamentos]

    interacoes_encontradas = []

    for interacao in dados["interacoes"]:
        par = [p.lower() for p in interacao["par"]]

        # Verificar se ambos os medicamentos do par estão na lista
        if all(any(p in nome for nome in nomes_normalizados) for p in par):
            interacoes_encontradas.append(interacao)

    # Determinar severidade máxima
    hierarquia = {"nenhuma": 0, "leve": 1, "moderada": 2, "grave": 3}
    severidade_max = "nenhuma"

    for interacao in interacoes_encontradas:
        sev = interacao.get("severidade", "nenhuma")
        if hierarquia.get(sev, 0) > hierarquia.get(severidade_max, 0):
            severidade_max = sev

    if not interacoes_encontradas:
        return {
            "medicamentos_verificados": medicamentos,
            "interacoes": [],
            "severidade_maxima": "nenhuma",
            "mensagem": "Nenhuma interação clinicamente significativa identificada.",
            "recomendacao": "Uso concomitante considerado seguro. Manter monitoramento de rotina."
        }

    return {
        "medicamentos_verificados": medicamentos,
        "interacoes": interacoes_encontradas,
        "severidade_maxima": severidade_max,
        "mensagem": f"Interação {severidade_max} identificada.",
        "nota": "[RASCUNHO_AGUARDANDO_REVISAO_MEDICA] — Não alterar medicação sem orientação médica."
    }