"""
Testes da tool sugerir_rascunho_prescricao.

Foco principal: a tag [RASCUNHO_AGUARDANDO_REVISAO_MEDICA] precisa estar
em TODOS os caminhos da função, mesmo nos erros — defesa em profundidade.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.tools.prescricao import (
    sugerir_rascunho_prescricao,
    TAG_RASCUNHO,
    _verificar_escopo_cv,
    _verificar_alergias,
)


# =============================================================================
# Tag inviolável (defesa em profundidade)
# =============================================================================

class TestTagInviolavel:
    """A tag DEVE estar em todos os caminhos — sucesso, erro, recusa."""

    def test_tag_em_sucesso(self):
        """Sucesso normal deve emitir tag no status."""
        with patch("src.tools.prescricao._consulta_recente", return_value=True):
            r = sugerir_rascunho_prescricao(
                paciente_id="GABRIEL",
                indicacao_clinica="HAS",
                medicamentos_sugeridos=[
                    {"nome": "Losartana Potássica", "dose": "50mg",
                     "frequencia": "1x ao dia", "duracao_dias": 90}
                ],
            )
        assert r.get("status") == TAG_RASCUNHO or r.get("tag") == TAG_RASCUNHO

    def test_tag_em_alergia(self):
        """Recusa por alergia também leva a tag."""
        r = sugerir_rascunho_prescricao(
            paciente_id="GABRIEL",
            indicacao_clinica="HAS",
            medicamentos_sugeridos=[
                {"nome": "Dipirona", "dose": "500mg", "frequencia": "8/8h"}
            ],
        )
        # Pode falhar por escopo CV (dipirona não é CV) OU por alergia
        # Em qualquer dos dois, tag deve aparecer
        assert r.get("tag") == TAG_RASCUNHO or r.get("status") == TAG_RASCUNHO

    def test_tag_em_consulta_expirada(self):
        """Sem consulta recente — recusa com tag."""
        with patch("src.tools.prescricao._consulta_recente", return_value=False):
            r = sugerir_rascunho_prescricao(
                paciente_id="GABRIEL",
                indicacao_clinica="HAS",
                medicamentos_sugeridos=[
                    {"nome": "Losartana Potássica", "dose": "50mg",
                     "frequencia": "1x ao dia"}
                ],
            )
        assert r.get("status") == "RECUSADO"
        assert r.get("tag") == TAG_RASCUNHO

    def test_tag_em_fora_escopo_cv(self):
        """Medicamento fora do escopo CV — recusa com tag."""
        r = sugerir_rascunho_prescricao(
            paciente_id="GABRIEL",
            indicacao_clinica="infecção urinária",
            medicamentos_sugeridos=[
                {"nome": "Amoxicilina", "dose": "500mg", "frequencia": "8/8h"}
            ],
        )
        assert r.get("status") == "RECUSADO"
        assert r.get("tag") == TAG_RASCUNHO

    def test_tag_em_lista_vazia(self):
        """Lista vazia — recusa com tag."""
        r = sugerir_rascunho_prescricao(
            paciente_id="GABRIEL",
            indicacao_clinica="HAS",
            medicamentos_sugeridos=[],
        )
        assert r.get("status") == "RECUSADO"
        assert r.get("tag") == TAG_RASCUNHO

    def test_tag_em_paciente_inexistente(self):
        """Paciente não encontrado — recusa com tag."""
        r = sugerir_rascunho_prescricao(
            paciente_id="BENEF-INEXISTENTE",
            indicacao_clinica="HAS",
            medicamentos_sugeridos=[
                {"nome": "Losartana Potássica", "dose": "50mg",
                 "frequencia": "1x ao dia"}
            ],
        )
        assert r.get("status") == "RECUSADO"
        assert r.get("tag") == TAG_RASCUNHO


# =============================================================================
# Verificação de escopo cardiovascular (lista branca)
# =============================================================================

class TestEscopoCardiovascular:
    """Apenas medicamentos cardiovasculares passam."""

    def test_losartana_aprovada(self):
        fora = _verificar_escopo_cv([
            {"nome": "Losartana Potássica", "dose": "50mg", "frequencia": "1x"}
        ])
        assert fora == []

    def test_atorvastatina_aprovada(self):
        fora = _verificar_escopo_cv([
            {"nome": "Atorvastatina", "dose": "20mg", "frequencia": "1x"}
        ])
        assert fora == []

    def test_amoxicilina_recusada(self):
        fora = _verificar_escopo_cv([
            {"nome": "Amoxicilina", "dose": "500mg", "frequencia": "8/8h"}
        ])
        assert "Amoxicilina" in fora

    def test_omeprazol_recusado(self):
        fora = _verificar_escopo_cv([
            {"nome": "Omeprazol", "dose": "20mg", "frequencia": "1x"}
        ])
        assert "Omeprazol" in fora

    def test_mix_aprovado_e_recusado(self):
        """Mix retorna apenas os fora de escopo."""
        fora = _verificar_escopo_cv([
            {"nome": "Losartana Potássica", "dose": "50mg", "frequencia": "1x"},
            {"nome": "Paracetamol", "dose": "750mg", "frequencia": "6/6h"},
        ])
        assert "Paracetamol" in fora
        assert "Losartana Potássica" not in fora


# =============================================================================
# Verificação de alergias
# =============================================================================

class TestAlergias:
    def test_alergia_detectada_match_exato(self):
        conflitos = _verificar_alergias(
            medicamentos=[{"nome": "Dipirona", "dose": "500mg", "frequencia": "8/8h"}],
            alergias=[{"substancia": "Dipirona", "reacao": "urticária", "gravidade": "leve"}],
        )
        assert len(conflitos) == 1
        assert conflitos[0]["medicamento"] == "Dipirona"

    def test_alergia_match_parcial(self):
        """'Losartana Potássica' deve casar com 'Losartana'."""
        conflitos = _verificar_alergias(
            medicamentos=[{"nome": "Losartana Potássica", "dose": "50mg",
                            "frequencia": "1x"}],
            alergias=[{"substancia": "Losartana", "reacao": "angioedema",
                        "gravidade": "alta"}],
        )
        assert len(conflitos) == 1

    def test_sem_alergias_sem_conflito(self):
        conflitos = _verificar_alergias(
            medicamentos=[{"nome": "Losartana", "dose": "50mg", "frequencia": "1x"}],
            alergias=[],
        )
        assert conflitos == []


# =============================================================================
# Fluxo completo
# =============================================================================

class TestFluxoCompleto:
    """Cenários end-to-end mais realistas."""

    def test_renovacao_losartana_gabriel(self):
        """Gabriel pós-consulta recente: deve aprovar."""
        # Mock para garantir que consulta de Gabriel (2026-03-12) é considerada recente
        with patch("src.tools.prescricao._consulta_recente", return_value=True):
            r = sugerir_rascunho_prescricao(
                paciente_id="GABRIEL",
                indicacao_clinica="manutenção do tratamento de hipertensão arterial controlada",
                medicamentos_sugeridos=[
                    {"nome": "Losartana Potássica", "dose": "50mg",
                     "frequencia": "1x ao dia", "duracao_dias": 90}
                ],
            )

        assert r.get("status") == TAG_RASCUNHO
        assert r.get("approved_by_medico") is False
        assert "Resolução CFM 2.314/22" in r.get("aviso_legal", "")

    def test_paracetamol_pra_gabriel_recusado_por_escopo(self):
        """Mesmo com consulta recente, paracetamol é fora do escopo CV."""
        r = sugerir_rascunho_prescricao(
            paciente_id="GABRIEL",
            indicacao_clinica="dor de cabeça",
            medicamentos_sugeridos=[
                {"nome": "Paracetamol", "dose": "750mg", "frequencia": "6/6h"}
            ],
        )
        assert r["status"] == "RECUSADO"
        assert "Paracetamol" in r.get("medicamentos_recusados", [])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
