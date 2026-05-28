"""
BluaDiagnostics — Interface Streamlit (FALLBACK Sprint 2).

Interface alternativa ao Dash, mais simples. Usada como seguro caso o
avaliador prefira ferramenta listada explicitamente no PDF da Sprint 2.

Não tem todas as funcionalidades do Dash (sem cytoscape, sem HITL síncrono
nativo, sem alerta sonoro), mas cobre o requisito de "interface de interação
demonstrável" e mostra:
- Chat conversacional
- Sidebar com perfil paciente
- Painel com tools/RAG/trajetória

Execução:
    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

try:
    from colab_setup import preparar_ambiente
    preparar_ambiente(exigir_chave=False)
except Exception:
    pass

import streamlit as st
from src.graph import construir_grafo, executar_turno

st.set_page_config(
    page_title="BluaDiagnostics — Care Plus",
    page_icon="🫀",
    layout="wide",
)


@st.cache_resource
def carregar_grafo():
    return construir_grafo()


# Init session
if "grafo" not in st.session_state:
    st.session_state.grafo = carregar_grafo()
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.mensagens = []
    st.session_state.flags_anteriores = []
    st.session_state.ultimo_estado = None


# ============================================================================
# Sidebar — paciente
# ============================================================================

BENEFICIARIOS = {
    "GABRIEL": "Gabriel — 34a (referência do dashboard)",
    "BENEF-001": "João Carlos — 58a, HAS+arritmia",
    "BENEF-002": "Maria Aparecida — 67a, IC+FA",
    "BENEF-003": "Roberto Silva — 42a",
}

with st.sidebar:
    st.title("🫀 BluaDiagnostics")
    st.caption("Care Plus · Sprint 2 · FALLBACK Streamlit")

    st.subheader("Paciente")
    beneficiario_id = st.selectbox(
        "Beneficiário ativo",
        options=list(BENEFICIARIOS.keys()),
        format_func=lambda x: BENEFICIARIOS[x],
    )

    if st.button("🔄 Nova sessão", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.mensagens = []
        st.session_state.flags_anteriores = []
        st.session_state.ultimo_estado = None
        st.rerun()

    st.divider()
    st.caption("⚕️ Este sistema não substitui avaliação médica. "
               "Em emergência: SAMU 192.")


# ============================================================================
# Main: chat + technical panel
# ============================================================================

col_chat, col_telemetria = st.columns([2, 1])

with col_chat:
    st.header("Diálogo")

    # Histórico
    for msg in st.session_state.mensagens:
        with st.chat_message(msg["role"]):
            if msg.get("emergencia"):
                st.error(msg["content"])
            else:
                st.markdown(msg["content"])

    # Input
    if prompt := st.chat_input("Digite sua mensagem..."):
        st.session_state.mensagens.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("Pensando..."):
            estado = executar_turno(
                grafo=st.session_state.grafo,
                mensagem_usuario=prompt,
                thread_id=st.session_state.thread_id,
                beneficiario_id=beneficiario_id,
                flags_safety_anteriores=st.session_state.flags_anteriores,
            )

        resposta = estado.get("resposta_final", "")
        flags = estado.get("flags_safety", [])
        eh_emergencia = ("RED_FLAG" in str(flags)
                          or estado.get("agente_ativo") == "escalada_humana"
                          or "192" in resposta)

        st.session_state.mensagens.append({
            "role": "assistant", "content": resposta,
            "emergencia": eh_emergencia,
        })
        st.session_state.flags_anteriores = flags
        st.session_state.ultimo_estado = estado

        with st.chat_message("assistant"):
            if eh_emergencia:
                st.error(resposta)
            else:
                st.markdown(resposta)

with col_telemetria:
    st.header("Painel Técnico")
    estado = st.session_state.ultimo_estado

    if estado is None:
        st.info("Faça uma pergunta para ver telemetria.")
    else:
        # Métricas principais
        c1, c2 = st.columns(2)
        c1.metric("Intent", estado.get("intent_classificada", "—"))
        c2.metric("Agente", estado.get("agente_ativo", "—"))

        nivel = estado.get("confidence_nivel", "—")
        score = estado.get("confidence_score", 0)
        if nivel == "alta":
            st.success(f"Confidence: {nivel.upper()} ({score:.2f})")
        elif nivel == "media":
            st.warning(f"Confidence: {nivel.upper()} ({score:.2f})")
        elif nivel == "baixa":
            st.error(f"Confidence: {nivel.upper()} ({score:.2f})")

        # Trajetória
        with st.expander("Trajetória LangGraph", expanded=True):
            traj = estado.get("trajetoria_nos", [])
            if traj:
                st.write(" → ".join(traj))
            else:
                st.caption("Sem trajetória")

        # RAG
        with st.expander("RAG · Documentos recuperados", expanded=True):
            docs = estado.get("documentos_rag", [])
            if docs:
                for d in docs:
                    st.markdown(f"**#{d.get('rank')} {d.get('fonte')}**  ·  "
                                f"sim={d.get('score_similaridade'):.2f}")
                    st.caption(f"categoria: {d.get('categoria')}")
                    st.text(d.get("chunk", "")[:200] + "...")
                    st.divider()
            else:
                st.caption("Sem chunks recuperados")

        # Tools
        with st.expander("Tools chamadas"):
            tools = [t["tool"] for t in estado.get("tools_chamadas", [])]
            if tools:
                for t in tools:
                    st.code(t, language="python")
            else:
                st.caption("Nenhuma tool")

        # Safety
        with st.expander("Safety flags"):
            flags = estado.get("flags_safety", [])
            if flags:
                for f in flags:
                    st.warning(f)
            else:
                st.success("APROVADO — sem flags")

        # HITL hint
        if estado.get("requer_aprovacao_humana"):
            st.divider()
            st.info("🩺 Rascunho de prescrição aguardando aprovação médica.")
            c1, c2 = st.columns(2)
            c1.button("✓ Aprovar (médico)", use_container_width=True)
            c2.button("✗ Rejeitar", use_container_width=True)
