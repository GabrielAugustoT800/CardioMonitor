"""Persistência runtime de rascunhos de prescrição (fase 4B).

Mesmo padrão de anotacoes_runtime.py (fase 4A): lê/escreve em
data/runtime/rascunhos_demo.json (gitignored). Aprovar/editar/rejeitar
muta o arquivo runtime — JSON canônico dos mocks fica intacto.

Schema do arquivo (dict por paciente_id -> lista de rascunhos):
{
  "GABRIEL": [
    {
      "id": "rasc_g01", "paciente_id": "GABRIEL",
      "data_geracao": "2026-06-05T09:15",
      "medicamento": "Metoprolol",
      "alteracao": "Aumentar dose...",
      "justificativa_ia": "Telemetria...",
      "tag_inviolavel": "[RASCUNHO_AGUARDANDO_REVISAO_MEDICA]",
      "status": "pendente" | "aprovado" | "editado" | "rejeitado",
      "decisao": null | {"medico": "...", "data": "...", "observacao": "..."},
      "texto_aprovado": null | "<texto editado pelo medico, se editado>"
    },
    ...
  ],
  ...
}

API:
    listar_rascunhos(pid) -> list   # todos
    listar_pendentes(pid) -> list   # so status='pendente'
    listar_decididos(pid) -> list   # status != 'pendente'
    aprovar(pid, rid, medico='Dr. Robert Chase', texto_editado=None) -> dict|None
    rejeitar(pid, rid, medico='Dr. Robert Chase') -> dict|None
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


_ROOT = Path(__file__).resolve().parents[2]
ARQ_RASCUNHOS = _ROOT / "data" / "runtime" / "rascunhos_demo.json"

# Status canônicos. 'editado' = aprovado com texto modificado pelo médico.
STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_REJEITADO = "rejeitado"
STATUS_EDITADO = "editado"


def _carregar_todos() -> dict[str, list[dict[str, Any]]]:
    """Lê o JSON inteiro. Retorna {} em qualquer falha (degrada gracioso)."""
    if not ARQ_RASCUNHOS.exists():
        return {}
    try:
        return json.loads(ARQ_RASCUNHOS.read_text(encoding="utf-8")) or {}
    except (json.JSONDecodeError, OSError):
        return {}


def _salvar_todos(dados: dict[str, list[dict[str, Any]]]) -> None:
    """Persiste o dict completo. Cria pasta se preciso."""
    ARQ_RASCUNHOS.parent.mkdir(parents=True, exist_ok=True)
    ARQ_RASCUNHOS.write_text(
        json.dumps(dados, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def listar_rascunhos(paciente_id: str) -> list[dict[str, Any]]:
    """Todos os rascunhos do paciente (pendentes + decididos)."""
    return _carregar_todos().get(paciente_id, [])


def listar_pendentes(paciente_id: str) -> list[dict[str, Any]]:
    """Só os com status='pendente' — em ordem original do arquivo."""
    return [r for r in listar_rascunhos(paciente_id)
            if r.get("status") == STATUS_PENDENTE]


def listar_decididos(paciente_id: str) -> list[dict[str, Any]]:
    """Aprovados, editados e rejeitados (status != pendente)."""
    return [r for r in listar_rascunhos(paciente_id)
            if r.get("status") != STATUS_PENDENTE]


def _atualizar(
    paciente_id: str,
    rascunho_id: str,
    mudancas: dict[str, Any],
) -> dict[str, Any] | None:
    """Aplica mudancas no rascunho identificado por (pid, rid). Retorna o
    dict atualizado ou None se não encontrar."""
    dados = _carregar_todos()
    lista = dados.get(paciente_id, [])
    for r in lista:
        if r.get("id") == rascunho_id:
            r.update(mudancas)
            _salvar_todos(dados)
            return r
    return None


def aprovar(
    paciente_id: str,
    rascunho_id: str,
    medico: str = "Dr. Robert Chase",
    texto_editado: str | None = None,
) -> dict[str, Any] | None:
    """Aprova um rascunho. Se texto_editado for fornecido (não-vazio),
    marca status='editado' e guarda em texto_aprovado.

    Em qualquer dos casos, decisao registra o médico e a data.
    """
    if texto_editado is not None and not str(texto_editado).strip():
        # Tratamento defensivo: texto vazio = aprovação direta (não editada)
        texto_editado = None
    status = STATUS_EDITADO if texto_editado else STATUS_APROVADO
    return _atualizar(paciente_id, rascunho_id, {
        "status": status,
        "decisao": {
            "medico": medico,
            "data": datetime.now().isoformat(timespec="minutes"),
            "observacao": None,
        },
        "texto_aprovado": (str(texto_editado).strip()
                           if texto_editado else None),
    })


def rejeitar(
    paciente_id: str,
    rascunho_id: str,
    medico: str = "Dr. Robert Chase",
) -> dict[str, Any] | None:
    """Rejeita um rascunho. Registra decisao (médico + data)."""
    return _atualizar(paciente_id, rascunho_id, {
        "status": STATUS_REJEITADO,
        "decisao": {
            "medico": medico,
            "data": datetime.now().isoformat(timespec="minutes"),
            "observacao": None,
        },
        "texto_aprovado": None,
    })
