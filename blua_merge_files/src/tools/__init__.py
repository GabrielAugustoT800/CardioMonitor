"""
Exporta todas as tools para uso nos agentes.

Atualizado pós-merge:
- analisar_ritmo_cardiaco agora aceita paciente_id (modo live via dashboard)
- criar_perfil_paciente — NOVA — chatbot cria BENEF-NEW-NNN
- consultar_telemetria_dashboard — NOVA — chatbot lê cardiac_data.csv
"""

from .historico import consultar_historico_paciente
from .interacoes import verificar_interacoes_medicamentosas
from .agendamento import agendar_teleconsulta
from .ritmo import analisar_ritmo_cardiaco
from .wearable import consultar_sinais_vitais_wearable
from .estratificador_cardiovascular import estratificar_dor_toracica
from .prescricao import sugerir_rascunho_prescricao

# --- Novas tools do merge ---
from .criar_perfil import criar_perfil_paciente
from .telemetria import consultar_telemetria_dashboard

__all__ = [
    "consultar_historico_paciente",
    "verificar_interacoes_medicamentosas",
    "agendar_teleconsulta",
    "analisar_ritmo_cardiaco",
    "consultar_sinais_vitais_wearable",
    "estratificar_dor_toracica",
    "sugerir_rascunho_prescricao",
    # novas
    "criar_perfil_paciente",
    "consultar_telemetria_dashboard",
]
