"""
Tool: consultar_sinais_vitais_wearable
Consulta leituras de wearable cardiovascular do beneficiário.
"""

import json
from pathlib import Path

_MOCK_PATH = Path(__file__).resolve().parents[2] / "data" / "mocks" / "wearable.json"


def consultar_sinais_vitais_wearable(
    paciente_id: str,
    dispositivo: str,
    periodo: str
) -> dict:
    """
    Consulta leituras de sinais vitais cardiovasculares de wearable.

    Args:
        paciente_id: ID do beneficiário. Ex: BENEF-001
        dispositivo: apple_health | google_fit | oura
        periodo: ultima_leitura | ultimas_24h | ultimos_7d

    Returns:
        Dicionário com leituras do wearable ou erro se não encontrado.
    """
    dispositivos_validos = {"apple_health", "google_fit", "oura"}
    periodos_validos = {"ultima_leitura", "ultimas_24h", "ultimos_7d"}

    if dispositivo not in dispositivos_validos:
        return {
            "erro": f"Dispositivo '{dispositivo}' inválido.",
            "dispositivos_validos": list(dispositivos_validos)
        }

    if periodo not in periodos_validos:
        return {
            "erro": f"Período '{periodo}' inválido.",
            "periodos_validos": list(periodos_validos)
        }

    with open(_MOCK_PATH, "r", encoding="utf-8") as f:
        dados = json.load(f)

    # Buscar leitura do beneficiário e dispositivo
    leitura = next(
        (
            l for l in dados["leituras"]
            if l["beneficiario_id"] == paciente_id
            and l["dispositivo"] == dispositivo
        ),
        None
    )

    if not leitura:
        return {
            "erro": f"Nenhuma leitura encontrada para {paciente_id} "
                    f"com dispositivo {dispositivo}."
        }

    # Para Sprint 1 todos os períodos retornam ultima_leitura
    return {
        "paciente_id": paciente_id,
        "dispositivo": dispositivo,
        "periodo": periodo,
        "timestamp": leitura["ultima_sincronizacao"],
        "dados": leitura["ultima_leitura"],
        "nota": leitura.get("nota", "")
    }