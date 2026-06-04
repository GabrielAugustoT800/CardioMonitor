"""
Tool: agendar_teleconsulta + consultar_agenda_medico
Fluxo interativo de agendamento com Dr. Gregory House.

Fluxo obrigatório:
1. Agente chama consultar_agenda_medico() → lista slots disponíveis
2. Agente apresenta os slots ao usuário e aguarda escolha
3. Usuário escolhe um slot
4. Agente chama agendar_teleconsulta(slot_id=..., motivo=...)

Persistência dual-write best-effort:
- Azure Blob (primário): container 'dataset', blob 'consultas_<paciente_id>.json'
- Disco local (backup): data/consultas/consultas_<paciente_id>.json
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

from shared.paths import DATA_DIR

log = logging.getLogger(__name__)

_MOCK_PATH = Path(__file__).resolve().parents[2] / "data" / "mocks" / "agendamentos.json"
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# ── Persistência ──────────────────────────────────────────────────────────────

def _registrar_localmente(paciente_id: str | None, consulta: dict) -> Path | None:
    try:
        consultas_dir = DATA_DIR / "consultas"
        consultas_dir.mkdir(parents=True, exist_ok=True)
        pid = paciente_id or "sem_paciente"
        arquivo = consultas_dir / f"consultas_{pid}.json"
        consultas = json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else []
        consultas.append(consulta)
        tmp = arquivo.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(consultas, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(arquivo)
        log.info("Consulta registrada em %s", arquivo)
        return arquivo
    except Exception as exc:
        log.warning("Falha ao persistir consulta no disco: %s: %s", type(exc).__name__, exc)
        return None


def _registrar_no_blob(paciente_id: str | None, consulta: dict) -> str | None:
    try:
        from dashboard.utils.storage import blob_available
        if not blob_available():
            return None
        from azure.storage.blob import BlobServiceClient
        conn = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        if not conn:
            return None
        pid = paciente_id or "sem_paciente"
        blob_name = f"consultas_{pid}.json"
        client = BlobServiceClient.from_connection_string(conn)
        blob_client = client.get_blob_client(container="dataset", blob=blob_name)
        try:
            existente = json.loads(blob_client.download_blob().readall().decode("utf-8"))
            if not isinstance(existente, list):
                existente = []
        except Exception:
            existente = []
        existente.append(consulta)
        blob_client.upload_blob(
            json.dumps(existente, ensure_ascii=False, indent=2), overwrite=True)
        log.info("Consulta registrada no Blob: dataset/%s", blob_name)
        return blob_name
    except Exception as exc:
        log.warning("Falha ao registrar consulta no Blob: %s: %s", type(exc).__name__, exc)
        return None


def _persistir(paciente_id: str | None, consulta: dict) -> dict:
    return {
        "blob": _registrar_no_blob(paciente_id, consulta),
        "local": _registrar_localmente(paciente_id, consulta),
    }


# ── Tools públicas ────────────────────────────────────────────────────────────

def consultar_agenda_medico(
    urgencia: str = "rotina",
) -> dict:
    """
    Lista os slots disponíveis do Dr. Gregory House para o nível de urgência.

    O agente deve chamar esta tool PRIMEIRO, apresentar as opções ao usuário
    e aguardar a escolha antes de chamar agendar_teleconsulta.

    Args:
        urgencia: rotina | prioritario | urgente

    Returns:
        Lista de slots disponíveis com id, data, horário e instruções.
    """
    urgencias_validas = {"rotina", "prioritario", "urgente"}
    if urgencia not in urgencias_validas:
        return {
            "erro": f"Urgência '{urgencia}' inválida.",
            "urgencias_validas": list(urgencias_validas),
        }

    with open(_MOCK_PATH, "r", encoding="utf-8") as f:
        dados = json.load(f)

    slots = dados["slots_disponiveis"].get(urgencia, [])
    if not slots:
        return {"erro": f"Nenhum slot disponível para urgência '{urgencia}'."}

    return {
        "medico": "Dr. Gregory House",
        "crm": "CRM-SP 123456",
        "especialidade": "Cardiologia",
        "urgencia": urgencia,
        "slots_disponiveis": [
            {
                "slot_id": s["id"],
                "disponibilidade": s["disponibilidade"],
                "plataforma": s["plataforma"],
            }
            for s in slots
        ],
        "instrucao_agente": (
            "Apresente os slots acima ao usuário e aguarde ele escolher um. "
            "Após a escolha, chame agendar_teleconsulta com o slot_id escolhido."
        ),
    }


def agendar_teleconsulta(
    motivo: str,
    slot_id: str,
    paciente_id: str | None = None,
    urgencia: str = "rotina",
    especialidade: str = "cardiologia",
) -> dict:
    """
    Confirma o agendamento no slot escolhido pelo usuário.

    Deve ser chamada APENAS após o usuário ter escolhido um slot
    via consultar_agenda_medico.

    Args:
        motivo: Resumo clínico do motivo da consulta.
        slot_id: ID do slot escolhido pelo usuário (ex: AGD-ROT-001).
        paciente_id: ID do paciente (ex: GABRIEL).
        urgencia: rotina | prioritario | urgente
        especialidade: Default cardiologia.

    Returns:
        Confirmação do agendamento com dados completos.
    """
    urgencias_validas = {"rotina", "prioritario", "urgente"}
    if urgencia not in urgencias_validas:
        return {
            "erro": f"Urgência '{urgencia}' inválida.",
            "urgencias_validas": list(urgencias_validas),
        }

    with open(_MOCK_PATH, "r", encoding="utf-8") as f:
        dados = json.load(f)

    slots = dados["slots_disponiveis"].get(urgencia, [])
    slot = next((s for s in slots if s["id"] == slot_id), None)

    if not slot:
        # Fallback: usa primeiro slot disponível da urgência
        if slots:
            slot = slots[0]
        else:
            return {"erro": f"Slot '{slot_id}' não encontrado."}

    codigo = f"BLU-{urgencia[:3].upper()}-{uuid.uuid4().hex[:4].upper()}"
    link = f"{slot['link_base']}-{codigo.lower()}"

    consulta = {
        "slot_id": slot_id,
        "agendado_em": datetime.now().isoformat(timespec="seconds"),
        "data": slot["disponibilidade"],
        "tipo": "Consulta agendada via agente",
        "medico": slot["medico"],
        "crm": slot.get("crm", "CRM-SP 123456"),
        "urgencia": urgencia,
        "resumo": motivo,
        "status": "agendada",
        "paciente_id": paciente_id,
        "codigo_confirmacao": codigo,
    }

    referencias = _persistir(paciente_id, consulta)

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
        "registro_blob": referencias["blob"],
        "registro_local": str(referencias["local"]) if referencias["local"] else None,
    }