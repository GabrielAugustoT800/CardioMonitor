"""
Grafo LangGraph do BluaDiagnostics — Sprint 2.

Evoluções vs Sprint 1:
- Nó 'roteador' renomeado para 'supervisor' (com lógica estatal)
- Nó 'pre_safety' adicionado ANTES do supervisor (regex jailbreak/OOS)
- Nó 'prescricao' (5º agente especialista) adicionado
- Nó 'escalada_humana' separado do safety
- Estado expandido: trajetoria_nos, documentos_rag, confidence,
  requer_aprovacao_humana, flags_safety_anteriores
- Memory truncation no nó 'saida'

Fluxo:
    Usuario → Pre-Safety → Supervisor → (Checkup | Triagem | Suporte | Prescricao | Escalada | ForaEscopo)
           → Safety → Saida (audit + truncagem) → Resposta
"""

from __future__ import annotations

import operator
from typing import Annotated, Optional, TypedDict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.agents import (
    supervisionar,
    agente_checkup,
    agente_triagem,
    agente_suporte_clinico,
    agente_prescricao,
    agente_safety,
)
from src.agents.pre_safety import pre_safety_check
from src.agents.escalada_humana import agente_escalada_humana
from src.audit_log import registrar_turno
from src.llm.qwen_client import chat as chat_llm
from src.utils.memoria import truncar_historico_se_necessario


# =============================================================================
# Estado do grafo — expandido para Sprint 2
# =============================================================================

class EstadoBlua(TypedDict, total=False):
    """
    Estado compartilhado entre todos os nós do grafo.
    Cada campo é atualizado pelos nós conforme o fluxo avança.

    total=False permite que nós retornem apenas os campos que atualizam.
    """
    # Entrada
    mensagem_usuario: str
    beneficiario_id: str

    # Pre-safety
    pre_safety_bloqueado: bool
    pre_safety_motivo: Optional[str]
    pre_safety_padrao_detectado: Optional[str]

    # Supervisor (ex-roteador)
    intent_classificada: str
    confianca_intent: float
    motivo_roteamento: str

    # Histórico de conversa — acumulado via operador de adição
    historico: Annotated[list[dict], operator.add]

    # Sprint 2 — trajetória de nós visitados neste turno
    trajetoria_nos: Annotated[list[str], operator.add]

    # Resposta do agente especializado
    resposta_agente: str
    agente_ativo: str
    tools_chamadas: list[dict]

    # Sprint 2 — documentos RAG recuperados (para painel técnico e evals)
    documentos_rag: list[dict]

    # Sprint 2 — flag HITL (acionada pelo agente Prescrição)
    requer_aprovacao_humana: bool

    # Safety
    resposta_validada: str
    flags_safety: list[str]
    flags_safety_anteriores: list[str]   # para lógica estatal do supervisor
    aprovado: bool

    # Sprint 2 — confidence scoring (calculado no nó saida)
    confidence_score: float
    confidence_nivel: str

    # Saída final
    resposta_final: str
    historico_truncado: bool


# =============================================================================
# Nós do grafo
# =============================================================================

def no_pre_safety(estado: EstadoBlua) -> dict:
    """
    Filtro rápido de jailbreak e fora-de-escopo via regex.
    Executa ANTES de qualquer chamada de LLM.
    """
    resultado = pre_safety_check(estado["mensagem_usuario"])

    if resultado["bloqueado"]:
        print(f"[graph] Pre-safety bloqueou: motivo={resultado['motivo']}, "
              f"padrão={resultado['padrao_detectado']!r}")

    return {
        "pre_safety_bloqueado": resultado["bloqueado"],
        "pre_safety_motivo": resultado["motivo"],
        "pre_safety_padrao_detectado": resultado["padrao_detectado"],
        # Se bloqueado, preenche resposta diretamente — pula supervisor
        "resposta_agente": resultado["resposta"] or "",
        "agente_ativo": "pre_safety" if resultado["bloqueado"] else "",
        "tools_chamadas": [],
        "documentos_rag": [],
        "trajetoria_nos": ["pre_safety"],
    }


def no_supervisor(estado: EstadoBlua) -> dict:
    """
    Classifica intenção do usuário com lógica estatal.
    Diferente de um classificador estático: considera flags do turno anterior
    para forçar triagem quando RED_FLAG persistiu.
    """
    resultado = supervisionar(
        mensagem=estado["mensagem_usuario"],
        historico=estado.get("historico", []),
        flags_safety_anteriores=estado.get("flags_safety_anteriores", []),
    )

    print(f"[graph] Supervisor: intent={resultado['intent']} "
          f"(confiança={resultado['confianca']:.2f}, motivo={resultado['motivo']})")

    return {
        "intent_classificada": resultado["intent"],
        "confianca_intent": resultado["confianca"],
        "motivo_roteamento": resultado["motivo"],
        "trajetoria_nos": ["supervisor"],
    }


def no_checkup(estado: EstadoBlua) -> dict:
    """Executa o agente de check-up cardiovascular."""
    resultado = agente_checkup(
        mensagem=estado["mensagem_usuario"],
        historico=estado.get("historico", []),
        beneficiario_id=estado.get("beneficiario_id", "BENEF-MARIA"),
    )
    return {
        "resposta_agente": resultado["resposta"],
        "agente_ativo": "checkup",
        "tools_chamadas": resultado.get("tools_chamadas", []),
        "documentos_rag": resultado.get("documentos_rag", []),
        "trajetoria_nos": ["checkup"],
    }


def no_triagem(estado: EstadoBlua) -> dict:
    """Executa o agente de triagem cardiovascular."""
    resultado = agente_triagem(
        mensagem=estado["mensagem_usuario"],
        historico=estado.get("historico", []),
        beneficiario_id=estado.get("beneficiario_id", "BENEF-MARIA"),
    )
    return {
        "resposta_agente": resultado["resposta"],
        "agente_ativo": "triagem",
        "tools_chamadas": resultado.get("tools_chamadas", []),
        "documentos_rag": resultado.get("documentos_rag", []),
        "trajetoria_nos": ["triagem"],
    }


def no_suporte(estado: EstadoBlua) -> dict:
    """Executa o agente de suporte clínico cardiovascular."""
    resultado = agente_suporte_clinico(
        mensagem=estado["mensagem_usuario"],
        historico=estado.get("historico", []),
        beneficiario_id=estado.get("beneficiario_id", "BENEF-MARIA"),
    )
    return {
        "resposta_agente": resultado["resposta"],
        "agente_ativo": "suporte_clinico",
        "tools_chamadas": resultado.get("tools_chamadas", []),
        "documentos_rag": resultado.get("documentos_rag", []),
        "trajetoria_nos": ["suporte_clinico"],
    }


def no_prescricao(estado: EstadoBlua) -> dict:
    """Executa o agente de prescrição cardiovascular (5º especialista, Sprint 2)."""
    resultado = agente_prescricao(
        mensagem=estado["mensagem_usuario"],
        historico=estado.get("historico", []),
        beneficiario_id=estado.get("beneficiario_id", "BENEF-MARIA"),
    )
    return {
        "resposta_agente": resultado["resposta"],
        "agente_ativo": "prescricao",
        "tools_chamadas": resultado.get("tools_chamadas", []),
        "documentos_rag": resultado.get("documentos_rag", []),
        "requer_aprovacao_humana": resultado.get("requer_aprovacao_humana", False),
        "trajetoria_nos": ["prescricao"],
    }


def no_escalada_humana(estado: EstadoBlua) -> dict:
    """
    Nó determinístico de escalada para SAMU 192.
    Acionado quando supervisor detecta intent='escalada_humana' (futuro)
    ou via lógica estatal de RED_FLAG persistente.
    """
    resultado = agente_escalada_humana(
        mensagem=estado["mensagem_usuario"],
        motivo_escalada=estado.get("motivo_roteamento", "sintoma_critico_cv"),
        beneficiario_id=estado.get("beneficiario_id", "BENEF-MARIA"),
    )
    return {
        "resposta_agente": resultado["resposta"],
        "agente_ativo": "escalada_humana",
        "tools_chamadas": [],
        "documentos_rag": [],
        "trajetoria_nos": ["escalada_humana"],
    }


def no_fora_escopo(estado: EstadoBlua) -> dict:
    """Responde quando o supervisor classifica como fora_de_escopo."""
    resposta = (
        "Sou especializado em saúde cardiovascular e sistema circulatório — "
        "esse tema está fora do meu escopo de atuação. "
        "Para outros assuntos de saúde, recomendo contatar o canal de clínica "
        "geral da Care Plus ou seu médico de referência. "
        "Posso te ajudar com algo relacionado ao seu coração ou pressão arterial?"
        "\n\n⚕️ *Este assistente não substitui avaliação médica. "
        "Em emergência, ligue 192 (SAMU).*"
    )
    return {
        "resposta_agente": resposta,
        "agente_ativo": "fora_escopo",
        "tools_chamadas": [],
        "documentos_rag": [],
        "trajetoria_nos": ["fora_escopo"],
    }


def no_safety(estado: EstadoBlua) -> dict:
    """
    Valida a resposta do agente antes de entregar ao usuário.

    Será refatorado para dupla camada (heurística + LLM auditor) no Lote 3.
    Por enquanto mantém a camada heurística existente, com adição da
    verificação de tag de prescrição.
    """
    # Se pre_safety já bloqueou, safety passa intacto adicionando só disclaimer
    if estado.get("pre_safety_bloqueado"):
        return {
            "resposta_validada": estado.get("resposta_agente", ""),
            "flags_safety": [f"PRE_SAFETY_BLOQUEOU_{estado.get('pre_safety_motivo', 'unknown').upper()}"],
            "aprovado": True,
            "trajetoria_nos": ["safety"],
        }

    resultado = agente_safety(
        mensagem_usuario=estado["mensagem_usuario"],
        resposta_agente=estado.get("resposta_agente", ""),
        intent=estado.get("intent_classificada", "checkup"),
    )

    if resultado["flags"]:
        print(f"[graph] Safety flags: {resultado['flags']}")

    return {
        "resposta_validada": resultado["resposta"],
        "flags_safety": resultado["flags"],
        "aprovado": resultado["aprovado"],
        "trajetoria_nos": ["safety"],
    }


def _calcular_confidence(estado: EstadoBlua) -> tuple[float, str]:
    """
    Calcula o confidence score da resposta com base em 3 sinais reais.

    Será exposto no painel técnico do Dash e nos resultados de eval.
    """
    # Sinal 1: qualidade do RAG (proxy: número e similaridade dos chunks)
    docs = estado.get("documentos_rag", [])
    if docs:
        scores = [d.get("score_similaridade", 0.5) for d in docs]
        sinal_rag = sum(scores) / len(scores)
    else:
        sinal_rag = 0.4   # baixo mas não zero — alguns turnos legitimamente não precisam RAG

    # Sinal 2: confiança do supervisor na classificação
    sinal_intent = estado.get("confianca_intent", 0.7)

    # Sinal 3: ações concretas (tool calls confirmam dados reais)
    sinal_tools = 1.0 if estado.get("tools_chamadas") else 0.6

    # Combinação ponderada
    score = 0.4 * sinal_rag + 0.3 * sinal_intent + 0.3 * sinal_tools

    if score >= 0.8:
        nivel = "alta"
    elif score >= 0.6:
        nivel = "media"
    else:
        nivel = "baixa"

    return score, nivel


def no_saida(estado: EstadoBlua) -> dict:
    """
    Finaliza o turno:
    - Atualiza histórico (com truncagem se necessário)
    - Calcula confidence
    - Registra audit log
    """
    resposta_final = estado.get("resposta_validada") or estado.get("resposta_agente", "")

    # Calcular confidence
    score, nivel = _calcular_confidence(estado)

    # Montar incremento de histórico
    novo_historico = [
        {"role": "user", "content": estado["mensagem_usuario"]},
        {"role": "assistant", "content": resposta_final},
    ]

    # Truncagem condicional (só se histórico já estava grande)
    historico_completo = estado.get("historico", []) + novo_historico
    historico_final, foi_truncado = truncar_historico_se_necessario(
        historico=historico_completo,
        chat_func=chat_llm,
    )

    # Calcular delta do histórico que precisa retornar
    # Como o operator.add cumula, precisamos retornar apenas o incremento
    # (no caso truncado, isso fica mais complexo — para simplificar,
    # truncagem real só será aplicada no histórico exposto via session,
    # não no estado interno do checkpointer)
    if foi_truncado:
        print(f"[graph] Histórico truncado: {len(historico_completo)} → {len(historico_final)} mensagens")

    # Registrar no audit log
    registrar_turno(
        mensagem_usuario=estado["mensagem_usuario"],
        resposta_agente=resposta_final,
        agente_ativo=estado.get("agente_ativo", "desconhecido"),
        intent=estado.get("intent_classificada", "desconhecido"),
        tools_chamadas=estado.get("tools_chamadas", []),
        flags_safety=estado.get("flags_safety", []),
        beneficiario_id=estado.get("beneficiario_id", "BENEF-MARIA"),
    )

    return {
        "resposta_final": resposta_final,
        "historico": novo_historico,
        "confidence_score": score,
        "confidence_nivel": nivel,
        "historico_truncado": foi_truncado,
        "trajetoria_nos": ["saida"],
    }


# =============================================================================
# Roteamento condicional
# =============================================================================

def decidir_apos_pre_safety(estado: EstadoBlua) -> str:
    """Após pre-safety, decide se segue para supervisor ou pula direto para safety."""
    if estado.get("pre_safety_bloqueado"):
        return "safety"     # bloqueado: pula direto pro safety+saida
    return "supervisor"


def decidir_agente(estado: EstadoBlua) -> str:
    """
    Decide qual agente acionar com base na intent classificada pelo supervisor.
    """
    intent = estado.get("intent_classificada", "checkup")

    mapa = {
        "checkup": "checkup",
        "triagem": "triagem",
        "suporte": "suporte",
        "prescricao": "prescricao",
        "fora_de_escopo": "fora_escopo",
    }

    # Caso especial: motivo de escalada estatal → vai direto para escalada_humana
    if estado.get("motivo_roteamento") == "escalada_persistente_red_flag":
        return "escalada_humana"

    return mapa.get(intent, "checkup")


# =============================================================================
# Construção do grafo
# =============================================================================

def construir_grafo() -> StateGraph:
    """
    Constrói e compila o StateGraph do BluaDiagnostics — Sprint 2.

    Retorna grafo compilado com MemorySaver para persistência de estado
    entre turnos (memória multi-turno).
    """
    builder = StateGraph(EstadoBlua)

    # Adicionar nós
    builder.add_node("pre_safety", no_pre_safety)
    builder.add_node("supervisor", no_supervisor)
    builder.add_node("checkup", no_checkup)
    builder.add_node("triagem", no_triagem)
    builder.add_node("suporte", no_suporte)
    builder.add_node("prescricao", no_prescricao)
    builder.add_node("escalada_humana", no_escalada_humana)
    builder.add_node("fora_escopo", no_fora_escopo)
    builder.add_node("safety", no_safety)
    builder.add_node("saida", no_saida)

    # Ponto de entrada — pre_safety roda ANTES do supervisor
    builder.set_entry_point("pre_safety")

    # Após pre_safety: bloqueado vai direto pro safety, OK segue pro supervisor
    builder.add_conditional_edges(
        "pre_safety",
        decidir_apos_pre_safety,
        {
            "safety": "safety",
            "supervisor": "supervisor",
        }
    )

    # Roteamento condicional após supervisor classificar intent
    builder.add_conditional_edges(
        "supervisor",
        decidir_agente,
        {
            "checkup": "checkup",
            "triagem": "triagem",
            "suporte": "suporte",
            "prescricao": "prescricao",
            "escalada_humana": "escalada_humana",
            "fora_escopo": "fora_escopo",
        }
    )

    # Todos os agentes vão para safety
    builder.add_edge("checkup", "safety")
    builder.add_edge("triagem", "safety")
    builder.add_edge("suporte", "safety")
    builder.add_edge("prescricao", "safety")
    builder.add_edge("escalada_humana", "safety")
    builder.add_edge("fora_escopo", "safety")

    # Safety → saída
    builder.add_edge("safety", "saida")

    # Saída encerra o grafo
    builder.add_edge("saida", END)

    # Compilar com memória para multi-turno + HITL síncrono via interrupt_after
    # B6: depois do agente_prescricao gerar o rascunho, o grafo PAUSA antes
    # de chegar em safety/saida. O frontend exibe rascunho + botão aprovar.
    # Retomada via `aprovar_rascunho_prescricao(grafo, thread_id, aprovado=True/False)`.
    memoria = MemorySaver()
    grafo = builder.compile(
        checkpointer=memoria,
        interrupt_after=["prescricao"],
    )

    print("[graph] Grafo BluaDiagnostics Sprint 2 compilado com sucesso.")
    print("[graph] 10 nós: pre_safety, supervisor, checkup, triagem, suporte, "
          "prescricao, escalada_humana, fora_escopo, safety, saida")
    print("[graph] HITL síncrono: pausa após 'prescricao' (CFM 2.314/22).")

    # Warm-up: forçar o carregamento dos modelos pesados (embeddings 2GB +
    # cross-encoder ~50MB) AGORA, durante o startup, em vez de na primeira
    # mensagem do usuario. Custa ~60s aqui, mas a UI fica fluida desde
    # o primeiro clique.
    _aquecer_modelos_rag()

    return grafo


def _aquecer_modelos_rag() -> None:
    """Carrega embeddings + cross-encoder antes do primeiro turno.

    Sem isto, a primeira mensagem do usuario espera ~60s pelo modelo de
    embeddings (multilingual-e5-large, 2GB) carregar do disco pra RAM.
    Com isto, o custo migra pro startup do servidor.
    """
    import time
    inicio = time.perf_counter()
    print("[graph] Aquecendo modelos RAG (embeddings + reranker)...")
    try:
        from src.rag.retriever import recuperar_contexto
        # Query dummy: forca _obter_colecao() a instanciar a embedding fn
        # e o ChromaDB a executar uma busca real (que carrega o modelo).
        _ = recuperar_contexto("aquecimento inicial", n_resultados=1)

        # Reranker (cross-encoder ms-marco-MiniLM) — usado em triagem.
        # Tambem pesa carregar na primeira chamada.
        from src.rag.reranker import rerank_cross_encoder
        _ = rerank_cross_encoder(
            "aquecimento",
            [{"chunk": "teste warm-up reranker", "fonte": "warmup",
              "score_similaridade": 0.5}]
        )
        dt = time.perf_counter() - inicio
        print(f"[graph] Modelos RAG aquecidos em {dt:.1f}s. "
              "Primeira mensagem agora vai fluir.")
    except Exception as exc:
        # Warm-up nunca pode quebrar o startup — se falhar, a primeira
        # mensagem so vai ser lenta como antes.
        print(f"[graph] Warm-up falhou ({type(exc).__name__}: {exc}); "
              "primeira mensagem pode ficar lenta.")


# =============================================================================
# Função de execução de turno (mantém assinatura compatível com Sprint 1)
# =============================================================================

def executar_turno(
    grafo: StateGraph,
    mensagem_usuario: str,
    thread_id: str,
    beneficiario_id: str = "BENEF-MARIA",
    historico: list[dict] | None = None,
    flags_safety_anteriores: list[str] | None = None,
) -> dict:
    """
    Executa um turno de conversa no grafo.

    Args:
        grafo: Grafo compilado pelo construir_grafo().
        mensagem_usuario: Mensagem atual do usuário.
        thread_id: ID único da sessão — preserva memória entre turnos.
        beneficiario_id: ID do beneficiário mockado (default Maria do PDF).
        historico: Histórico externo opcional (para compat com CLI).
        flags_safety_anteriores: Flags do turno N-1 — alimentam lógica estatal
                                 do supervisor (escalada persistente).

    Returns:
        Estado final do grafo após o turno.
    """
    estado_inicial: dict = {
        "mensagem_usuario": mensagem_usuario,
        "beneficiario_id": beneficiario_id,
        "historico": historico or [],
        "flags_safety_anteriores": flags_safety_anteriores or [],
        "trajetoria_nos": [],
        "tools_chamadas": [],
        "documentos_rag": [],
        "flags_safety": [],
        "aprovado": True,
        "requer_aprovacao_humana": False,
    }

    config = {"configurable": {"thread_id": thread_id}}
    estado_final = grafo.invoke(estado_inicial, config=config)

    # B6: detectar se grafo pausou no interrupt_after de prescricao.
    # LangGraph deixa `next` populado com os nós pendentes quando há interrupção.
    snapshot = grafo.get_state(config)
    if snapshot.next:
        # Pausou — rascunho gerado pelo prescricao está em resposta_agente,
        # mas safety/saida ainda não rodaram. Sinaliza pro frontend mostrar
        # botões aprovar/rejeitar.
        estado_final = dict(estado_final)  # copia mutável
        estado_final["requer_aprovacao_humana"] = True
        # Pra UX consistente, expor rascunho como resposta provisória
        if not estado_final.get("resposta_final"):
            estado_final["resposta_final"] = estado_final.get("resposta_agente", "")

    return estado_final


def aprovar_rascunho_prescricao(
    grafo: StateGraph,
    thread_id: str,
    aprovado: bool,
    observacao_medico: str | None = None,
) -> dict:
    """
    Retoma execução do grafo pausado no interrupt_after de prescricao (HITL).

    Args:
        grafo: Grafo compilado pelo construir_grafo().
        thread_id: Mesmo thread_id usado em executar_turno().
        aprovado: True = médico aprovou rascunho, False = rejeitou.
        observacao_medico: Justificativa opcional (vai pro audit log).

    Returns:
        Estado final após safety + saida rodarem.

    Comportamento:
        - aprovado=True: grafo continua normal, prescricao já está no estado.
        - aprovado=False: estado é atualizado com mensagem de recusa e flag
          RASCUNHO_REJEITADO_HUMANO antes de prosseguir.
    """
    config = {"configurable": {"thread_id": thread_id}}

    if not aprovado:
        # Sobrescrever a resposta antes de safety/saida
        msg_recusa = (
            "Rascunho não aprovado na revisão médica."
            + (f" Observação: {observacao_medico}" if observacao_medico else "")
            + " Recomenda-se nova teleconsulta ou reavaliação clínica antes "
            "de emitir prescrição."
        )
        grafo.update_state(
            config,
            {
                "resposta_agente": msg_recusa,
                "flags_safety_anteriores": ["RASCUNHO_REJEITADO_HUMANO"],
            },
        )
    else:
        # Só registra a aprovação no estado (audit log pega depois)
        grafo.update_state(
            config,
            {
                "flags_safety_anteriores": ["RASCUNHO_APROVADO_HUMANO"],
            },
        )

    # Retomar execução — `None` como input significa "continuar do checkpoint"
    estado_final = grafo.invoke(None, config=config)
    return estado_final
