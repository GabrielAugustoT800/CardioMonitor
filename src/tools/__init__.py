"""
Exporta todas as tools para uso nos agentes.

Atualizado Sprint 2: adiciona sugerir_rascunho_prescricao (tool nova)
"""

from .historico import consultar_historico_paciente
from .interacoes import verificar_interacoes_medicamentosas
from .agendamento import agendar_teleconsulta
from .ritmo import analisar_ritmo_cardiaco
from .wearable import consultar_sinais_vitais_wearable
from .estratificador_cardiovascular import estratificar_dor_toracica
from .prescricao import sugerir_rascunho_prescricao

__all__ = [
    "consultar_historico_paciente",
    "verificar_interacoes_medicamentosas",
    "agendar_teleconsulta",
    "analisar_ritmo_cardiaco",
    "consultar_sinais_vitais_wearable",
    "estratificar_dor_toracica",
    "sugerir_rascunho_prescricao",
]
