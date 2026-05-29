"""
Tool: agendar_teleconsulta
Agenda teleconsulta com cardiologista na plataforma Blua. Fictício
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from shared.paths import DATA_DIR

log = logging.getLogger(__name__)

_MOCK_PATH = Path(__file__).resolve().parents[2] / "data" / "mocks" / "agendamentos.json"


def _registrar_consulta_localmente(
    *,
    motivo: str,
    medico: str,
    disponibilidade_slot: str,
    urgencia: str,
    paciente_id: str | None = None,
) -> Path:
    """
    Registra a consulta agendada em data/consultas/.

    Quando paciente_id é fornecido: data/consultas/consultas_<paciente_id>.json
    Quando ausente: data/consultas/consultas_sem_paciente.json (fallback)

    Formato compatível com a especificação futura de consultas_gabriel.json
    do repositório ArrhythmiaMonitor (Azure Blob).
    """
    consultas_dir = DATA_DIR / "consultas"
    consultas_dir.mkdir(parents=True, exist_ok=True)

    if paciente_id:
        arquivo = consultas_dir / f"consultas_{paciente_id}.json"
    else:
        arquivo = consultas_dir / "consultas_sem_paciente.json"

    # Carrega existentes (ou lista vazia)
    if arquivo.exists():
        with arquivo.open(encoding="utf-8") as f:
            consultas = json.load(f)
    else:
        consultas = []

    agora = datetime.now()

    # TODO Passo 8 (INTEGRACAO_ARRHYTHMIAMONITOR.md §3.2): popular
    # data_referencia com a data real do slot (parsing de
    # "Hoje"/"Amanhã"/etc) quando integrar com calendário real.
    data_referencia = agora.strftime("%d/%m/%Y")

    consultas.append({
        "disponibilidade_slot": disponibilidade_slot,
        "agendado_em": agora.isoformat(timespec="seconds"),
        "data_referencia": data_referencia,
        "tipo": "Consulta agendada via agente",
        "medico": medico,
        "urgencia": urgencia,
        "resumo": motivo,
        "status": "agendada",
        "paciente_id": paciente_id,
        "criado_por": "agendar_teleconsulta_v1",
    })

    # Atomic write (write-then-rename evita arquivo parcial em crash)
    tmp = arquivo.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(consultas, f, ensure_ascii=False, indent=2)
    tmp.replace(arquivo)

    return arquivo


def agendar_teleconsulta(
    urgencia: str,
    motivo: str,
    especialidade: str = "cardiologia",
    paciente_id: str | None = None,
) -> dict:
    """
    Agenda teleconsulta com cardiologista na plataforma Blua.

    Args:
        urgencia: rotina | prioritario | urgente
        motivo: Resumo clínico gerado pelo agente para briefing do médico.
        especialidade: Especialidade médica. Default: cardiologia.
        paciente_id: ID do paciente vinculado (BENEF-XXX). Opcional.
            Quando fornecido, o agendamento é persistido em
            data/consultas/consultas_<paciente_id>.json.
            Quando ausente, vai pra consultas_sem_paciente.json.

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

    # Persistir localmente em formato compatível com ArrhythmiaMonitor.
    # Falha de persistência NÃO bloqueia a resposta ao usuário (best-effort).
    registro_local: str | None = None
    try:
        arquivo = _registrar_consulta_localmente(
            motivo=motivo,
            medico=slot["medico"],
            disponibilidade_slot=slot["disponibilidade"],
            urgencia=urgencia,
            paciente_id=paciente_id,
        )
        registro_local = str(arquivo)
        log.info("Consulta registrada em %s", arquivo)
    except Exception as exc:
        log.warning("Falha ao persistir consulta: %s: %s", type(exc).__name__, exc)

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
        "motivo_registrado": motivo,
        "registro_local": registro_local,
    }
