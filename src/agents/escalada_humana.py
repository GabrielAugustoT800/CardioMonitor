"""
Nó de Escalada Humana
Responde imediatamente a casos clínicos críticos detectados pela Triagem,
forçando saída pelo canal de emergência (SAMU 192) sem passar por demais
fluxos do agente.

Este nó é acionado em duas situações:
1. Triagem retornou risco='alto' via estratificador_cardiovascular
2. Supervisor detectou intent 'escalada_humana' por lógica estatal
   (RED_FLAG_SEM_ESCALADA persistiu do turno anterior)

A resposta é construída deterministicamente — sem chamar LLM — para
garantir consistência e latência mínima em emergências.
"""

from __future__ import annotations


# ---- templates determinísticos ------------------------------------------
# Respostas hard-coded em vez de chamada LLM: garante consistência clínica
# e latência mínima (~0ms) em emergências reais.

_RESPOSTA_SAMU = (
    "🚨 **Os sintomas que você descreveu podem indicar uma situação clínica crítica.**\n\n"
    "**Ligue IMEDIATAMENTE para o SAMU — 192**\n\n"
    "Enquanto aguarda atendimento:\n\n"
    "• Mantenha-se em repouso absoluto, sentado ou deitado\n"
    "• Não tente dirigir até o pronto-socorro — espere o SAMU\n"
    "• Se estiver acompanhado, peça para alguém ficar com você\n"
    "• Se você tem AAS em casa e **não é alérgico**, mastigue um comprimido de 100mg\n"
    "• Se a dor passar nos próximos minutos, **mesmo assim ligue 192** — alguns "
    "sintomas cardiovasculares graves podem ter melhora transitória enganosa\n\n"
    "Em paralelo, estou notificando a central Care Plus para preparar o atendimento "
    "de continuidade. Você não está sozinho.\n\n"
    "⚕️ *Em emergência cardiovascular, cada minuto importa. Ligue 192 agora.*"
)

_RESPOSTA_AVC = (
    "🚨 **Os sintomas que você descreveu podem indicar um AVC (Acidente Vascular Cerebral).**\n\n"
    "**Ligue IMEDIATAMENTE para o SAMU — 192**\n\n"
    "Lembre do **FAST** — sinais que confirmam AVC:\n\n"
    "• **F**ace (rosto): peça para sorrir — um lado fica caído?\n"
    "• **A**rms (braços): levante os dois — um cai sozinho?\n"
    "• **S**peech (fala): tente dizer uma frase — sai embolada?\n"
    "• **T**ime (tempo): se SIM em qualquer dos 3, é EMERGÊNCIA. **Anote a hora**.\n\n"
    "Janela de tratamento é de até 4h30 do início dos sintomas. **Não espere.**\n\n"
    "⚕️ *Em suspeita de AVC, cada minuto custa neurônios. Ligue 192 agora.*"
)


# ---- nó de escalada ------------------------------------------------------

def agente_escalada_humana(
    mensagem: str,
    motivo_escalada: str = "sintoma_critico_cv",
    beneficiario_id: str = "BENEF-001",
) -> dict:
    """
    Gera resposta determinística de escalada para SAMU 192.

    Args:
        mensagem: Mensagem original do usuário (usada para escolher template).
        motivo_escalada: Origem da escalada — informativo para audit log.
            Valores esperados: 'sintoma_critico_cv', 'red_flag_persistente',
            'suspeita_avc', 'suspeita_iam', 'suspeita_disseccao_aortica'.
        beneficiario_id: ID do beneficiário (para audit).

    Returns:
        Dicionário compatível com formato dos demais agentes.
    """
    msg_lower = mensagem.lower()

    # Sinais textuais de AVC → template específico FAST
    sinais_avc = [
        "face caída", "rosto caído", "boca torta", "fala embolada",
        "perdi a fala", "não consigo falar", "fraqueza no braço",
        "dormência no braço", "perdi o movimento", "perdi a visão",
        "tontura intensa", "vertigem", "avc", "derrame",
    ]

    if any(s in msg_lower for s in sinais_avc):
        resposta = _RESPOSTA_AVC
        motivo_efetivo = "suspeita_avc"
    else:
        resposta = _RESPOSTA_SAMU
        motivo_efetivo = motivo_escalada

    return {
        "resposta": resposta,
        "agente": "escalada_humana",
        "tools_chamadas": [],     # nó determinístico, não chama tools
        "thinking": None,
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
        "motivo_escalada": motivo_efetivo,
    }
