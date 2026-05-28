"""
Tool: sugerir_rascunho_prescricao
Gera rascunho de prescrição pós-teleconsulta para revisão médica.

REGRA INVIOLÁVEL:
Toda resposta gerada por essa tool retorna status
'RASCUNHO_AGUARDANDO_REVISAO_MEDICA'. Nunca substitui o médico —
funciona apenas como suporte ao fluxo HITL (Human-In-The-Loop).

Restrições ativas:
- Bloqueia rascunho se não há teleconsulta nos últimos 7 dias (CFM 2.314/22)
- Detecta conflitos com alergias registradas
- Lista branca de medicamentos cardiovasculares
- Status approved_by_medico=False sempre
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

_MOCK_PATH = Path(__file__).resolve().parents[2] / "data" / "mocks" / "perfis_clinicos.json"

# Lista branca de medicamentos cardiovasculares aprovados para rascunho
# Mantém o escopo cardiovascular inviolável — outros medicamentos são recusados
_MEDICAMENTOS_CARDIOVASCULARES = {
    # Anti-hipertensivos
    "losartana", "valsartana", "candesartana", "olmesartana", "telmisartana",
    "enalapril", "captopril", "ramipril", "lisinopril", "perindopril",
    "anlodipino", "nifedipino", "verapamil", "diltiazem",
    "atenolol", "metoprolol", "bisoprolol", "carvedilol", "propranolol", "nebivolol",
    "hidroclorotiazida", "clortalidona", "indapamida",
    # Antiarrítmicos
    "amiodarona", "sotalol", "propafenona", "flecainida",
    # Anticoagulantes / antiagregantes
    "varfarina", "warfarina", "apixabana", "rivaroxabana", "dabigatrana", "edoxabana",
    "aas", "clopidogrel", "ticagrelor", "prasugrel",
    # Estatinas
    "atorvastatina", "rosuvastatina", "sinvastatina", "pravastatina", "ezetimiba",
    # Diuréticos cardiovasculares
    "furosemida", "espironolactona", "eplerenona",
    # Nitratos
    "isossorbida", "mononitrato", "dinitrato", "nitroglicerina",
}

# Resolução CFM 2.314/22: telemedicina exige vínculo clínico recente
_DIAS_VALIDADE_CONSULTA = 7

# Tag inviolável que toda resposta com medicamentos DEVE conter
TAG_RASCUNHO = "RASCUNHO_AGUARDANDO_REVISAO_MEDICA"


def _carregar_perfil(paciente_id: str) -> dict | None:
    """Carrega o perfil do beneficiário no mock."""
    with open(_MOCK_PATH, "r", encoding="utf-8") as f:
        dados = json.load(f)
    return next(
        (b for b in dados["beneficiarios"] if b["id"] == paciente_id),
        None
    )


def _consulta_recente(consulta: dict, hoje: datetime | None = None) -> bool:
    """Verifica se a última consulta foi nos últimos _DIAS_VALIDADE_CONSULTA dias."""
    if not consulta or "data" not in consulta:
        return False
    try:
        data_consulta = datetime.strptime(consulta["data"], "%Y-%m-%d")
        hoje = hoje or datetime.now()
        return (hoje - data_consulta) <= timedelta(days=_DIAS_VALIDADE_CONSULTA)
    except (ValueError, KeyError):
        return False


def _verificar_escopo_cv(medicamentos: list[dict]) -> list[str]:
    """Retorna lista de medicamentos fora do escopo cardiovascular."""
    fora_escopo = []
    for med in medicamentos:
        nome_lower = med.get("nome", "").lower()
        # Match parcial — ex: "Losartana Potássica" → bate com "losartana"
        if not any(cv in nome_lower for cv in _MEDICAMENTOS_CARDIOVASCULARES):
            fora_escopo.append(med.get("nome", "(sem nome)"))
    return fora_escopo


def _verificar_alergias(medicamentos: list[dict], alergias: list[dict]) -> list[dict]:
    """Retorna conflitos entre medicamentos sugeridos e alergias registradas."""
    alergias_lower = {a["substancia"].lower(): a for a in alergias}
    conflitos = []
    for med in medicamentos:
        nome_lower = med.get("nome", "").lower()
        for alergia_nome, alergia_dados in alergias_lower.items():
            if alergia_nome in nome_lower or nome_lower in alergia_nome:
                conflitos.append({
                    "medicamento": med.get("nome"),
                    "substancia_alergia": alergia_dados["substancia"],
                    "reacao": alergia_dados.get("reacao", "não especificada"),
                    "gravidade": alergia_dados.get("gravidade", "não especificada"),
                })
    return conflitos


def sugerir_rascunho_prescricao(
    paciente_id: str,
    indicacao_clinica: str,
    medicamentos_sugeridos: list[dict],
) -> dict:
    """
    Gera rascunho de prescrição pós-teleconsulta para revisão médica humana.

    A regra fundamental: NUNCA substitui o médico. Toda resposta tem status
    RASCUNHO_AGUARDANDO_REVISAO_MEDICA, mesmo que tudo pareça correto.

    Args:
        paciente_id: ID do beneficiário. Ex: 'BENEF-MARIA'.
        indicacao_clinica: Descrição da indicação clínica.
                          Ex: 'manutenção do tratamento de hipertensão controlada'.
        medicamentos_sugeridos: Lista de medicamentos com estrutura:
            [
                {
                    "nome": "Losartana Potássica",
                    "dose": "50mg",
                    "frequencia": "1x ao dia",
                    "duracao_dias": 90
                },
                ...
            ]

    Returns:
        Dicionário com o rascunho estruturado, ou erro estruturado se
        alguma das restrições for violada.
    """
    # 1. Validar entrada
    if not medicamentos_sugeridos:
        return {
            "erro": "Lista de medicamentos vazia.",
            "status": "RECUSADO",
            "tag": TAG_RASCUNHO,
        }

    # 2. Carregar perfil do beneficiário
    perfil = _carregar_perfil(paciente_id)
    if not perfil:
        return {
            "erro": f"Beneficiário '{paciente_id}' não encontrado.",
            "status": "RECUSADO",
            "tag": TAG_RASCUNHO,
        }

    # 3. Verificar escopo cardiovascular — recusa medicamentos fora do escopo
    fora_escopo = _verificar_escopo_cv(medicamentos_sugeridos)
    if fora_escopo:
        return {
            "erro": "Medicamento fora do escopo cardiovascular do BluaDiagnostics.",
            "medicamentos_recusados": fora_escopo,
            "orientacao": (
                "Para prescrições fora do escopo cardiovascular, encaminhar ao "
                "canal de clínica geral da Care Plus."
            ),
            "status": "RECUSADO",
            "tag": TAG_RASCUNHO,
        }

    # 4. Verificar teleconsulta recente (CFM 2.314/22)
    ultima_consulta = perfil.get("consultas", {}).get("ultima", {})
    if not _consulta_recente(ultima_consulta):
        return {
            "erro": (
                f"Sem teleconsulta nos últimos {_DIAS_VALIDADE_CONSULTA} dias. "
                f"Resolução CFM 2.314/22 exige vínculo clínico recente para "
                f"emissão de prescrição via telemedicina."
            ),
            "ultima_consulta_registrada": ultima_consulta.get("data", "nenhuma"),
            "orientacao": "Agendar teleconsulta com cardiologista antes de prescrever.",
            "status": "RECUSADO",
            "tag": TAG_RASCUNHO,
        }

    # 5. Verificar conflitos com alergias
    alergias = perfil.get("alergias", [])
    conflitos = _verificar_alergias(medicamentos_sugeridos, alergias)
    if conflitos:
        return {
            "erro": "Conflito com alergias registradas do beneficiário.",
            "conflitos": conflitos,
            "orientacao": (
                "Revisar escolha terapêutica e considerar alternativas. "
                "Não emitir rascunho sem nova avaliação médica."
            ),
            "status": "RECUSADO",
            "tag": TAG_RASCUNHO,
        }

    # 6. Tudo OK — gerar rascunho com a tag inviolável
    return {
        "status": TAG_RASCUNHO,
        "tag": TAG_RASCUNHO,
        "paciente_id": paciente_id,
        "paciente_nome": perfil.get("nome"),
        "indicacao_clinica": indicacao_clinica,
        "medicamentos": medicamentos_sugeridos,
        "medico_responsavel_consulta": ultima_consulta.get("medico"),
        "data_consulta_origem": ultima_consulta.get("data"),
        "data_geracao_rascunho": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "approved_by_medico": False,
        "aviso_legal": (
            "Este rascunho é apoio à decisão clínica no fluxo de prescrição. "
            "Resolução CFM 2.314/22: aprovação e assinatura por médico habilitado "
            "são obrigatórias antes de qualquer dispensação. O BluaDiagnostics "
            "não substitui a decisão clínica humana."
        ),
        "proxima_etapa": (
            "Aguardando revisão e aprovação do médico responsável via app Blua. "
            "Após aprovação, prescrição válida será emitida com assinatura digital ICP-Brasil."
        ),
    }
