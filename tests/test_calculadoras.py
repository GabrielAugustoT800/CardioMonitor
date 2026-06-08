"""Testes das calculadoras clínicas (fase 9).

Casos de referência baseados em literatura + perfis dos pacientes mock.
"""

import sys
from pathlib import Path

# Garante que dashboard/ está no path (mesma convenção das outras suites)
_DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"
if str(_DASHBOARD) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD))

import pytest

from utils.calculadoras import (
    cha2ds2_vasc, has_bled, egfr_ckd_epi, heart_score,
)


# ── CHA2DS2-VASc ─────────────────────────────────────────────────────────────

def test_cha2ds2_vasc_homem_sem_fatores():
    """Homem 50 anos sem fatores -> score 0, não anticoagular."""
    score, conduta = cha2ds2_vasc(50, "M", False, False, False, False, False)
    assert score == 0
    assert "Não anticoagular" in conduta


def test_cha2ds2_vasc_gabriel_perfil():
    """Gabriel: 38a, M, HAS. Score = 1 (HAS). Considerar."""
    score, conduta = cha2ds2_vasc(38, "M", False, True, False, False, False)
    assert score == 1
    assert "Considerar" in conduta


def test_cha2ds2_vasc_idosa_complicada():
    """Mulher 78a, IC, HAS, DM, AVC prévio.
    Score: 1(IC) + 1(HAS) + 2(≥75) + 1(DM) + 2(AVC) + 1(F) = 8.
    """
    score, conduta = cha2ds2_vasc(78, "F", True, True, True, False, True)
    assert score == 8
    assert "Anticoagulação indicada" in conduta


def test_cha2ds2_vasc_mulher_baixo_risco():
    """Mulher 50a sem fatores -> score 1 (só sexo), não anticoagular."""
    score, conduta = cha2ds2_vasc(50, "F", False, False, False, False, False)
    assert score == 1
    assert "Não anticoagular" in conduta


# ── HAS-BLED ─────────────────────────────────────────────────────────────────

def test_has_bled_baixo_risco():
    """Nenhum fator -> score 0, baixo risco."""
    score, conduta = has_bled(False, False, False, False, False,
                              False, False, False)
    assert score == 0
    assert "Baixo risco" in conduta


def test_has_bled_alto_risco():
    """5 fatores -> score 5, alto risco mas não contraindica."""
    score, conduta = has_bled(True, True, False, True, True,
                              False, True, False)
    assert score == 5
    assert "Alto risco" in conduta
    assert "NÃO contraindica" in conduta


# ── eGFR CKD-EPI 2021 ────────────────────────────────────────────────────────

def test_egfr_homem_jovem_normal():
    """Homem 30a, Cr 1.0 -> faixa G1 (~98 mL/min)."""
    egfr, cls = egfr_ckd_epi(1.0, 30, "M")
    assert 90 <= egfr <= 110
    assert "G1" in cls


def test_egfr_idoso_renal_cronico():
    """Homem 70a, Cr 2.0 -> faixa G3 (~35-40)."""
    egfr, cls = egfr_ckd_epi(2.0, 70, "M")
    assert 30 <= egfr <= 45
    assert "G3" in cls


def test_egfr_creatinina_invalida():
    """Creatinina não-positiva deve dar ValueError."""
    with pytest.raises(ValueError):
        egfr_ckd_epi(0, 40, "M")


# ── HEART score ──────────────────────────────────────────────────────────────

def test_heart_score_baixo():
    score, conduta = heart_score(0, 0, 0, 0, 0)
    assert score == 0
    assert "BAIXO" in conduta


def test_heart_score_alto():
    score, conduta = heart_score(2, 2, 2, 2, 2)
    assert score == 10
    assert "ALTO" in conduta


def test_heart_score_validacao():
    """Parâmetros fora de 0/1/2 devem dar ValueError."""
    with pytest.raises(ValueError):
        heart_score(3, 0, 0, 0, 0)


def test_heart_score_moderado():
    """5 pontos -> moderado."""
    score, conduta = heart_score(1, 1, 1, 1, 1)
    assert score == 5
    assert "MODERADO" in conduta
