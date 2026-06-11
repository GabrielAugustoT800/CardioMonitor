"""Persistência runtime de anotações clínicas (fase 4A).

Separado do JSON canônico (data/mocks/perfis_clinicos.json), que guarda
anotações históricas curadas. Este módulo grava em
data/runtime/anotacoes_demo.json (gitignored) — anotações criadas pelo
médico durante a demo ficam entre reloads do app mas não poluem os mocks
do repo nem aparecem como diff sujo no git.

API:
    carregar_anotacoes(pid) -> list[dict]   # só as runtime
    salvar_anotacao(pid, texto, medico='Dr. Robert Chase') -> dict
    todas_anotacoes(pid, paciente) -> list[dict]   # canônicas + runtime
                                                    # ordenadas por data desc
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


# Caminho absoluto pro arquivo runtime. Subindo 2 níveis a partir de
# dashboard/utils/ chegamos na raiz do projeto (CardioMonitor/).
_ROOT = Path(__file__).resolve().parents[2]
ARQ_ANOTACOES = _ROOT / "data" / "runtime" / "anotacoes_demo.json"


def _garantir_arquivo() -> None:
    """Garante que a pasta e o arquivo runtime existam (criando se preciso).

    Idempotente: chamadas repetidas são no-op se já existirem.
    """
    ARQ_ANOTACOES.parent.mkdir(parents=True, exist_ok=True)
    if not ARQ_ANOTACOES.exists():
        ARQ_ANOTACOES.write_text("{}", encoding="utf-8")


def _ler_dados() -> dict[str, list[dict[str, Any]]]:
    """Lê o JSON inteiro. Retorna {} em qualquer falha (arquivo corrompido,
    permissão, etc.) — degrada gracioso pra não derrubar a página."""
    _garantir_arquivo()
    try:
        return json.loads(ARQ_ANOTACOES.read_text(encoding="utf-8")) or {}
    except (json.JSONDecodeError, OSError):
        return {}


def carregar_anotacoes(paciente_id: str) -> list[dict[str, Any]]:
    """Anotações runtime de um paciente (sem as canônicas).

    Retorna lista vazia se nada salvo ou em qualquer falha de leitura.
    """
    return _ler_dados().get(paciente_id, [])


def salvar_anotacao(
    paciente_id: str,
    texto: str,
    medico: str = "Dr. Robert Chase",
) -> dict[str, Any]:
    """Acrescenta uma anotação runtime e retorna o dict salvo.

    Data automática (ISO sem segundos: '2026-06-08T14:32'). Texto strippado.
    Não valida vazio aqui — o callback é quem decide se ignora vazio.
    """
    dados = _ler_dados()
    nova = {
        "data": datetime.now().isoformat(timespec="minutes"),
        "medico": medico,
        "texto": texto.strip(),
    }
    dados.setdefault(paciente_id, []).append(nova)
    ARQ_ANOTACOES.write_text(
        json.dumps(dados, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return nova


def todas_anotacoes(
    paciente_id: str,
    paciente: dict[str, Any],
) -> list[dict[str, Any]]:
    """Mescla canônicas (do perfis_clinicos.json) + runtime (do arquivo demo).

    Ordenadas por data desc (mais recentes primeiro). Datas em ISO ordenam
    correto como string. Anotações canônicas tipicamente têm data 'YYYY-MM-DD'
    e runtime tem 'YYYY-MM-DDTHH:MM' — ordenação string funciona pros dois.
    """
    canonicas = paciente.get("anotacoes_medicas", []) or []
    runtime = carregar_anotacoes(paciente_id)
    todas = list(canonicas) + list(runtime)
    todas.sort(key=lambda a: a.get("data", ""), reverse=True)
    return todas
