"""
Tool: criar_perfil_paciente

Permite ao chatbot cadastrar um novo beneficiário durante o check-up.
O novo registro fica disponível IMEDIATAMENTE no dropdown de pacientes
do CardioMonitor — não há reload manual nem migração de banco.

Fluxo de uso esperado (LLM-friendly, 2 etapas):

    1. Tool chamada SEM `confirmacao=True` → retorna preview dos dados
       coletados. O agente apresenta ao usuário e pede confirmação verbal.
    2. Usuário confirma → tool chamada de novo com `confirmacao=True` →
       perfil é gravado e retorna o BENEF-NEW-NNN.

Esse 2-step é defesa contra hallucination: o LLM não consegue criar um
perfil só porque "achou" o nome do usuário no meio de uma conversa.
"""
from __future__ import annotations

from typing import Any, Optional

from shared.patient_registry import create_patient


# Tipos de condições cardiovasculares mais comuns — usado só para
# normalização leve, não para validação estrita.
_CONDICOES_COMUNS = {
    "HAS": "Hipertensão arterial sistêmica",
    "FA": "Fibrilação atrial",
    "IC": "Insuficiência cardíaca",
    "DAC": "Doença arterial coronariana",
    "DM": "Diabetes mellitus",
    "TEP": "Tromboembolismo pulmonar",
    "AVE": "Acidente vascular encefálico",
}


def criar_perfil_paciente(
    nome: str,
    idade: int,
    sexo: str,
    condicoes: Optional[list[str]] = None,
    medicacoes: Optional[list[str]] = None,
    alergias: Optional[list[str]] = None,
    confirmacao: bool = False,
) -> dict[str, Any]:
    """
    Cria um novo perfil clínico cardiovascular no registro compartilhado.

    Args:
        nome: Nome completo do paciente.
        idade: 0–120.
        sexo: 'masculino' | 'feminino' | 'outro'.
        condicoes: Lista de condições conhecidas. Aceita siglas (HAS, FA, IC)
            que são expandidas, ou nomes completos. Ex: ['HAS', 'arritmia'].
        medicacoes: Lista de medicações em uso. Ex: ['Losartana 50mg', 'AAS 100mg'].
        alergias: Lista de alergias medicamentosas.
        confirmacao: Deve ser True para efetivamente gravar. Se False,
            retorna um preview para o agente confirmar com o usuário primeiro.

    Returns:
        Em preview: {'preview': True, 'dados': {...}, 'proxima_acao': '...'}
        Em sucesso: {'sucesso': True, 'paciente_id': 'BENEF-NEW-001', 'perfil': {...}}
        Em erro: {'erro': '...'}
    """
    # Validação de entrada — defesa em profundidade (registry também valida)
    if not nome or not nome.strip():
        return {"erro": "Nome é obrigatório."}
    if not isinstance(idade, int) or not (0 <= idade <= 120):
        return {"erro": f"Idade fora de [0, 120]: {idade!r}"}
    if sexo not in {"masculino", "feminino", "outro"}:
        return {
            "erro": f"Sexo inválido: {sexo!r}.",
            "valores_aceitos": ["masculino", "feminino", "outro"],
        }

    cond_norm = _normalizar_condicoes(condicoes or [])
    med_norm = _normalizar_medicacoes(medicacoes or [])

    # ---- Etapa 1: preview ----
    if not confirmacao:
        return {
            "preview": True,
            "mensagem": "Confirme os dados antes de criar o perfil:",
            "dados": {
                "nome": nome.strip(),
                "idade": idade,
                "sexo": sexo,
                "condicoes": [c["nome"] for c in cond_norm],
                "medicacoes": [m["nome"] for m in med_norm],
                "alergias": alergias or [],
            },
            "proxima_acao": (
                "Após confirmação do usuário, chame esta tool de novo com "
                "confirmacao=True (mesmos demais argumentos)."
            ),
        }

    # ---- Etapa 2: gravação ----
    try:
        novo = create_patient(
            nome=nome,
            idade=idade,
            sexo=sexo,
            condicoes=cond_norm,
            medicacoes=med_norm,
            alergias=alergias or [],
        )
    except ValueError as exc:
        return {"erro": str(exc)}

    return {
        "sucesso": True,
        "paciente_id": novo["id"],
        "mensagem": (
            f"Perfil criado para {novo['nome']} (ID {novo['id']}). "
            f"Disponível agora no CardioMonitor para iniciar sessão de PPG."
        ),
        "proximos_passos": [
            "Selecione o paciente no dropdown do /monitor",
            "Inicie sessão de simulação ou conecte o ESP32",
            "Os batimentos capturados ficarão automaticamente vinculados "
            f"ao ID {novo['id']}",
        ],
        "perfil": novo,
    }


def _normalizar_condicoes(condicoes: list[str]) -> list[dict[str, Any]]:
    """Converte ['HAS', 'arritmia'] em estrutura compatível com perfis_clinicos.json."""
    result = []
    for c in condicoes:
        if not isinstance(c, str) or not c.strip():
            continue
        nome = _CONDICOES_COMUNS.get(c.strip().upper(), c.strip())
        result.append({
            "nome": nome,
            "status": "informado_pelo_paciente",
            "origem": "chatbot_checkup",
        })
    return result


def _normalizar_medicacoes(medicacoes: list[str]) -> list[dict[str, Any]]:
    """Converte ['Losartana 50mg'] em estrutura mínima."""
    result = []
    for m in medicacoes:
        if not isinstance(m, str) or not m.strip():
            continue
        result.append({
            "nome": m.strip(),
            "status": "em_uso",
            "origem": "chatbot_checkup",
        })
    return result
