"""Testes da timeline cronológica do paciente (fase 10).

Cobre normalização de datas (3 formatos + vazia), agregação mínima,
ordenação desc, dedup ultima/histórico, e smoke do Gabriel real.
"""

import json
import sys
from pathlib import Path

_DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"
if str(_DASHBOARD) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD))

from utils.timeline import gerar_eventos_timeline, _normalizar_data


# ── Normalização de datas ────────────────────────────────────────────────────

def test_normalizar_data_completa():
    iso, exib = _normalizar_data("2026-05-10")
    assert iso == "2026-05-10"
    assert exib == "10/05/2026"


def test_normalizar_data_apenas_mes():
    iso, exib = _normalizar_data("2023-08")
    assert iso == "2023-08-01"  # dia 1 pra ordenar
    assert exib == "08/2023"


def test_normalizar_data_dd_mm_yyyy():
    iso, exib = _normalizar_data("15/03/2025")
    assert iso == "2025-03-15"
    assert exib == "15/03/2025"


def test_normalizar_data_vazia_vai_pro_fim():
    iso, exib = _normalizar_data("")
    assert iso == "9999-12-31"


# ── Agregação ────────────────────────────────────────────────────────────────

def test_gerar_eventos_paciente_minimo():
    """Paciente sem dados clínicos -> lista vazia."""
    eventos = gerar_eventos_timeline({"id": "TEST", "nome": "Teste"})
    assert eventos == []


def test_gerar_eventos_ordenacao_desc():
    """3 tipos em datas diferentes -> ordem desc (exame > med > consulta)."""
    paciente = {
        "id": "TEST",
        "consultas": {
            "historico": [
                {"data": "2025-01-15", "tipo": "Cardiologia",
                 "resumo": "antiga"},
            ],
        },
        "medicacoes_ativas": [
            {"nome": "X", "dose": "10mg", "inicio": "2026-03",
             "frequencia": "1x/dia", "indicacao": "teste"},
        ],
        "exames_recentes": [
            {"data": "2026-05-10", "tipo": "ECG", "resultado": "ok"},
        ],
    }
    eventos = gerar_eventos_timeline(paciente)
    assert len(eventos) == 3
    assert eventos[0].tipo == "EXAME"      # 2026-05-10
    assert eventos[1].tipo == "MEDICACAO"  # 2026-03-01
    assert eventos[2].tipo == "CONSULTA"   # 2025-01-15


def test_gerar_eventos_dedup_ultima_historico():
    """consultas.ultima com mesma data de historico[0] NÃO duplica."""
    paciente = {
        "id": "TEST",
        "consultas": {
            "ultima": {
                "data": "2026-05-10",
                "especialidade": "Cardiologia",
                "observacoes": "duplicada",
            },
            "historico": [
                {"data": "2026-05-10", "tipo": "Cardiologia",
                 "resumo": "histórico"},
            ],
        },
    }
    eventos = gerar_eventos_timeline(paciente)
    assert len(eventos) == 1
    assert eventos[0].descricao == "histórico"


def test_gerar_eventos_proxima_inclui_status():
    paciente = {
        "consultas": {
            "proxima": {"data": "2026-07-10", "especialidade": "Cardio",
                        "status": "agendada"},
        },
    }
    eventos = gerar_eventos_timeline(paciente)
    assert len(eventos) == 1
    assert eventos[0].tipo == "CONSULTA"
    assert "agendada" in eventos[0].descricao


# ── Smoke com dados reais ────────────────────────────────────────────────────

def test_gerar_eventos_gabriel_real():
    """Gabriel tem dados em todos os 3 tipos."""
    json_path = (Path(__file__).resolve().parents[1]
                 / "data" / "mocks" / "perfis_clinicos.json")
    d = json.loads(json_path.read_text(encoding="utf-8"))
    gabriel = next(b for b in d["beneficiarios"] if b["id"] == "GABRIEL")
    eventos = gerar_eventos_timeline(gabriel)
    assert len(eventos) > 0
    tipos = {e.tipo for e in eventos}
    assert "CONSULTA" in tipos
    assert "MEDICACAO" in tipos
    # Ordem desc
    for i in range(len(eventos) - 1):
        assert eventos[i].data >= eventos[i + 1].data
