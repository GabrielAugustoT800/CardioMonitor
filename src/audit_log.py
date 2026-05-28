"""
Logging estruturado de cada turno clínico.

Responsabilidades:
- Registrar cada turno de conversa em JSON estruturado
- Capturar agente ativo, intent, tools chamadas e flags de safety
- Persistir em logs/audit.jsonl — uma linha JSON por turno
- Garantir rastreabilidade para auditoria clínica

Formato de saída (JSONL — uma linha por turno):
{
    "timestamp": "2026-05-15T10:32:00",
    "beneficiario_id": "BENEF-001",
    "intent": "checkup",
    "agente_ativo": "checkup",
    "mensagem_usuario": "...",
    "resposta_agente": "...",
    "tools_chamadas": [...],
    "flags_safety": [...],
    "aprovado": true
}
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

# Diretório de logs — criado automaticamente se não existir
_LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"
_AUDIT_FILE = _LOGS_DIR / "audit.jsonl"


def registrar_turno(
    mensagem_usuario: str,
    resposta_agente: str,
    agente_ativo: str,
    intent: str,
    tools_chamadas: list[dict],
    flags_safety: list[str],
    beneficiario_id: str = "BENEF-001",
) -> None:
    """
    Registra um turno de conversa no audit log.

    Args:
        mensagem_usuario: Mensagem original do usuário.
        resposta_agente: Resposta final entregue ao usuário.
        agente_ativo: Nome do agente que processou o turno.
        intent: Intent classificada pelo roteador.
        tools_chamadas: Lista de tools invocadas no turno.
        flags_safety: Flags levantadas pela safety layer.
        beneficiario_id: ID do beneficiário da sessão.
    """
    # Garantir que o diretório de logs existe
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)

    registro = {
        "timestamp": datetime.now().isoformat(),
        "beneficiario_id": beneficiario_id,
        "intent": intent,
        "agente_ativo": agente_ativo,
        "mensagem_usuario": mensagem_usuario,
        "resposta_agente": resposta_agente,
        "tools_chamadas": [
            {"tool": t["tool"]} for t in tools_chamadas
        ],
        "flags_safety": flags_safety,
        "aprovado": len([
            f for f in flags_safety
            if f in {"RED_FLAG_SEM_ESCALADA", "DIAGNOSTICO_DEFINITIVO_DETECTADO"}
        ]) == 0,
    }

    # Append no arquivo JSONL — uma linha por turno
    with open(_AUDIT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")


def ler_audit_log(ultimos_n: int = 10) -> list[dict]:
    """
    Lê os últimos N registros do audit log.
    Útil para debug e demonstração no notebook.

    Args:
        ultimos_n: Quantidade de registros a retornar.

    Returns:
        Lista de registros em ordem cronológica inversa.
    """
    if not _AUDIT_FILE.exists():
        return []

    linhas = _AUDIT_FILE.read_text(encoding="utf-8").strip().splitlines()

    registros = []
    for linha in linhas:
        try:
            registros.append(json.loads(linha))
        except json.JSONDecodeError:
            continue

    return list(reversed(registros[-ultimos_n:]))


def resumo_sessao(beneficiario_id: str | None = None) -> dict:
    """
    Gera resumo estatístico do audit log.
    Útil para a seção de avaliação do notebook.

    Args:
        beneficiario_id: Filtrar por beneficiário. None retorna todos.

    Returns:
        Dicionário com estatísticas da sessão.
    """
    if not _AUDIT_FILE.exists():
        return {"total_turnos": 0}

    linhas = _AUDIT_FILE.read_text(encoding="utf-8").strip().splitlines()
    registros = []

    for linha in linhas:
        try:
            r = json.loads(linha)
            if beneficiario_id is None or r.get("beneficiario_id") == beneficiario_id:
                registros.append(r)
        except json.JSONDecodeError:
            continue

    if not registros:
        return {"total_turnos": 0}

    # Contagem por intent
    intents = {}
    for r in registros:
        intent = r.get("intent", "desconhecido")
        intents[intent] = intents.get(intent, 0) + 1

    # Contagem por agente
    agentes = {}
    for r in registros:
        agente = r.get("agente_ativo", "desconhecido")
        agentes[agente] = agentes.get(agente, 0) + 1

    # Tools mais chamadas
    tools_count = {}
    for r in registros:
        for t in r.get("tools_chamadas", []):
            nome = t.get("tool", "desconhecida")
            tools_count[nome] = tools_count.get(nome, 0) + 1

    # Flags de safety
    todas_flags = []
    for r in registros:
        todas_flags.extend(r.get("flags_safety", []))

    return {
        "total_turnos": len(registros),
        "turnos_aprovados": sum(1 for r in registros if r.get("aprovado", True)),
        "distribuicao_intents": intents,
        "distribuicao_agentes": agentes,
        "tools_mais_chamadas": tools_count,
        "total_flags_safety": len(todas_flags),
        "flags_por_tipo": {
            f: todas_flags.count(f) for f in set(todas_flags)
        },
    }