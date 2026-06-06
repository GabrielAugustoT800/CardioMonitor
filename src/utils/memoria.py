"""
Utilitário de truncagem de memória conversacional.

Sessões longas no Dash podem acumular dezenas de turnos. Como o
EstadoBlua usa Annotated[list[dict], operator.add] para histórico,
o acúmulo é inevitável e pode estourar a janela de contexto do LLM
(qwen-plus tem 128k tokens, mas chamadas repetidas com histórico
gigante elevam custo proporcionalmente).

Estratégia: summarize-and-replace.
- Mantém os últimos N_TURNOS_RECENTES turnos completos
- Resume os turnos mais antigos em uma única mensagem system
- Reduz tokens em ~70-80% sem perder contexto clínico crítico

Quando a função é chamada:
- No nó 'saida' do grafo, após cada turno completo
- Antes de persistir o histórico via MemorySaver do LangGraph
"""

from __future__ import annotations

import json
from typing import Any

# Configurações de truncagem
_N_TURNOS_RECENTES = 6      # 6 turnos × 2 mensagens (user+assistant) = 12 mensagens
_MAX_TOKENS_RESUMO = 300    # tamanho máximo do resumo gerado
_THRESHOLD_TURNOS = 8       # só ativa truncagem se > 8 turnos no histórico


def truncar_historico_se_necessario(
    historico: list[dict],
    chat_func: Any,
    n_turnos_recentes: int = _N_TURNOS_RECENTES,
    threshold: int = _THRESHOLD_TURNOS,
) -> tuple[list[dict], bool]:
    """
    Trunca o histórico via summarize-and-replace se ele excedeu o threshold.

    Args:
        historico: Lista de mensagens no formato padrão chat completion
                   [{"role": "user"|"assistant"|"system"|"tool", "content": ...}, ...]
        chat_func: Função chat() do qwen_client para gerar o resumo.
                   Injeção de dependência para evitar import circular.
        n_turnos_recentes: Quantos turnos completos preservar como mensagens originais.
        threshold: Só ativa truncagem se total de turnos exceder este valor.

    Returns:
        Tupla (historico_truncado, foi_truncado):
        - historico_truncado: nova lista de mensagens
        - foi_truncado: True se houve truncagem, False se passou intacto
    """
    # Contagem aproximada de turnos — cada turno tem 2 mensagens (user + assistant),
    # mas tool calls podem adicionar mais. Vamos contar conservadoramente.
    n_user_msgs = sum(1 for m in historico if m.get("role") == "user")

    if n_user_msgs <= threshold:
        return historico, False

    # Separar mensagens system pré-existentes (ex: prompt + RAG injetado)
    # — manter como estão.
    pre_system = [m for m in historico if m.get("role") == "system"]
    nao_system = [m for m in historico if m.get("role") != "system"]

    # Identificar índice de corte: queremos os últimos n_turnos_recentes turnos completos
    # Andamos de trás para frente contando mensagens user até atingir n
    indices_user = [i for i, m in enumerate(nao_system) if m.get("role") == "user"]

    if len(indices_user) <= n_turnos_recentes:
        return historico, False  # não havia tantos turnos quanto pensávamos

    indice_corte = indices_user[-n_turnos_recentes]

    msgs_antigas = nao_system[:indice_corte]
    msgs_recentes = nao_system[indice_corte:]

    if not msgs_antigas:
        return historico, False

    # Gerar resumo das mensagens antigas
    try:
        resumo = _gerar_resumo(msgs_antigas, chat_func)
    except Exception as exc:
        print(f"[memoria] Erro ao gerar resumo: {exc}. Mantendo histórico original.")
        return historico, False

    # Montar novo histórico: prompts originais + resumo + mensagens recentes
    novo_historico = pre_system + [
        {
            "role": "system",
            "content": f"[RESUMO DOS TURNOS ANTERIORES DA SESSÃO]\n\n{resumo}"
        }
    ] + msgs_recentes

    return novo_historico, True


def _gerar_resumo(msgs_antigas: list[dict], chat_func: Any) -> str:
    """
    Chama LLM (modelo leve, temperatura baixa) para resumir mensagens antigas.

    O resumo preserva informação clinicamente relevante:
    - Sintomas relatados
    - Medicações mencionadas
    - Sinais vitais informados
    - Decisões/recomendações dadas
    - Tools chamadas e seus resultados-chave
    """
    # Serializar mensagens para passar ao LLM
    conteudo = []
    for m in msgs_antigas:
        role = m.get("role", "?")
        content = m.get("content", "")
        if isinstance(content, str):
            conteudo.append(f"[{role}]: {content[:500]}")     # corte por segurança
        elif content is None and "tool_calls" in m:
            tc_nomes = [t.get("function", {}).get("name", "?")
                        for t in m.get("tool_calls", [])]
            conteudo.append(f"[{role}]: <tool calls: {', '.join(tc_nomes)}>")

    texto = "\n".join(conteudo)

    system_prompt = (
        "Você resume conversas clínicas cardiovasculares preservando "
        "informação relevante para continuidade do atendimento.\n\n"
        "Preserve obrigatoriamente:\n"
        "- Sintomas relatados pelo paciente\n"
        "- Medicações mencionadas (nome e dose)\n"
        "- Sinais vitais informados (PA, FC, SpO2, etc.)\n"
        "- Decisões clínicas ou orientações dadas\n"
        "- Resultados de tools (histórico, interações, etc.)\n\n"
        "Formato: prosa concisa em até 200 palavras. "
        "Não invente informação que não esteja na conversa."
    )

    resposta = chat_func(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": texto},
        ],
        enable_thinking=False,
        temperature=0.1,
        max_tokens=_MAX_TOKENS_RESUMO,
    )

    return resposta.get("content", "[resumo indisponível]").strip()
