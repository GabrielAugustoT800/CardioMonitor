"""
Tool: agendar_teleconsulta
Agenda teleconsulta com cardiologista na plataforma Blua. Fictício
"""

import json
import uuid
from pathlib import Path

_MOCK_PATH = Path(__file__).resolve().parents[2] / "data" / "mocks" / "agendamentos.json"


def agendar_teleconsulta(
    urgencia: str,
    motivo: str,
    especialidade: str = "cardiologia"
) -> dict:
    """
    Agenda teleconsulta com cardiologista na plataforma Blua.

    Args:
        urgencia: rotina | prioritario | urgente
        motivo: Resumo clínico gerado pelo agente para briefing do médico.
        especialidade: Especialidade médica. Default: cardiologia.

    Returns:
        Dicionário com confirmação e dados do agendamento.
    """
    urgencias_validas = {"rotina", "prioritario", "urgente"}

    if urgencia not in urgencias_validas:
        return {
            "erro": f"Urgência '{urgencia}' inválida.",
            "urgencias_validas": list(urgencias_validas)
        }

    with open(_MOCK_PATH, "r", encoding="utf-8") as f:
        dados = json.load(f)

    slots = dados["slots_disponiveis"].get(urgencia, [])

    if not slots:
        return {"erro": f"Nenhum slot disponível para urgência '{urgencia}'."}

    # Selecionar primeiro slot disponível
    slot = slots[0]

    # Gerar código de confirmação único
    codigo = f"BLU-{urgencia[:3].upper()}-{uuid.uuid4().hex[:4].upper()}"
    link = f"{slot['link_base']}-{codigo.lower()}"

    return {
        "agendado": True,
        "especialidade": especialidade,
        "urgencia": urgencia,
        "medico": slot["medico"],
        "disponibilidade": slot["disponibilidade"],
        "plataforma": slot["plataforma"],
        "link_acesso": link,
        "codigo_confirmacao": codigo,
        "instrucoes": slot["instrucoes"],
        "motivo_registrado": motivo
    }