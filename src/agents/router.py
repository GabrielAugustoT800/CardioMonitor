"""
Agente Supervisor (anteriormente "router")
Classifica a intenção do usuário e decide qual agente acionar.
thinking=OFF — prioridade em latência mínima.

REFATORADO Sprint 2:
- Renomeado conceitualmente para 'supervisor' (mantém função 'rotear' para compat)
- System prompt carregado de prompts/agente_supervisor.md
- Intent 'prescricao' adicionada para o novo agente
- Função 'supervisionar' adiciona lógica estatal (forçar triagem se RED_FLAG persistir)
"""

from __future__ import annotations

import json

from src.llm.qwen_client import chat, formatar_mensagens
from src.prompts import carregar_prompt

# ---- config -------------------------------------------------------------

# System prompt agora vem do arquivo prompts/agente_supervisor.md
SYSTEM_PROMPT_SUPERVISOR = carregar_prompt("agente_supervisor")

_INTENTS_VALIDAS = {"checkup", "triagem", "suporte", "prescricao", "fora_de_escopo"}


# ---- classificação base (sem estado) ------------------------------------

def rotear(mensagem: str, historico: list[dict] | None = None) -> dict:
    """
    Classifica a intenção do usuário (função base, sem lógica estatal).

    Args:
        mensagem: Mensagem atual do usuário.
        historico: Turnos anteriores da conversa.

    Returns:
        Dicionário com intent e confianca.
        Em caso de erro, retorna intent triagem como fallback (mais seguro
        que checkup quando há ambiguidade — ativa thinking + RAG completo).
    """
    historico = historico or []

    mensagens = formatar_mensagens(
        system_prompt=SYSTEM_PROMPT_SUPERVISOR,
        historico=historico,
        mensagem_usuario=mensagem,
    )

    try:
        resposta = chat(
            messages=mensagens,
            enable_thinking=False,
            temperature=0.1,
        )

        resultado = json.loads(resposta["content"].strip())

        intent = resultado.get("intent", "triagem")
        if intent not in _INTENTS_VALIDAS:
            intent = "triagem"

        return {
            "intent": intent,
            "confianca": resultado.get("confianca", 0.8),
            "motivo": "classificacao_llm",
        }

    except Exception as exc:
        print(f"[supervisor] Erro na classificação: {exc}. Usando fallback: triagem")
        return {
            "intent": "triagem",
            "confianca": 0.5,
            "motivo": "fallback_erro_parsing",
        }


# ---- supervisor com lógica estatal --------------------------------------

def supervisionar(
    mensagem: str,
    historico: list[dict] | None = None,
    flags_safety_anteriores: list[str] | None = None,
) -> dict:
    """
    Versão completa do supervisor com lógica estatal.

    Diferenças vs rotear():
    - Se RED_FLAG_SEM_ESCALADA persistiu do turno anterior, força triagem.
    - Pode aplicar outras regras de escalada baseadas em estado acumulado.

    Args:
        mensagem: Mensagem atual.
        historico: Turnos anteriores.
        flags_safety_anteriores: Flags da safety do turno N-1.

    Returns:
        {"intent": str, "confianca": float, "motivo": str}
    """
    flags = flags_safety_anteriores or []

    # Escalada persistente: RED_FLAG não resolvido → força triagem
    if "RED_FLAG_SEM_ESCALADA" in flags:
        return {
            "intent": "triagem",
            "confianca": 1.0,
            "motivo": "escalada_persistente_red_flag",
        }

    # Caso normal: classifica via LLM
    return rotear(mensagem, historico)
