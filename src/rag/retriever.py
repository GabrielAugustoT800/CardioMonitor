"""
Retriever do RAG cardiovascular — Sprint 2.

Evoluções vs Sprint 1:
- MMR (Max Marginal Relevance) para diversidade contextual
- Auto-RAG: reformulação clínica da query antes da busca
- Saída estruturada com score de similaridade para o painel técnico
- Filtro por categoria de metadado (red_flag, bula, protocolo, etc.)
- Integração com reranker (cross-encoder) ativável
- B19: cache LRU em recuperar_contexto (queries repetidas em eval set)

Funções principais:
- recuperar_contexto(query, ...) → string formatada (compat Sprint 1)
- recuperar_contexto_detalhado(query, ...) → tupla (string, list[dict])
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import numpy as np
from chromadb import PersistentClient
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from .indexer import CHROMA_DIR, COLECAO_NOME, MODELO_EMBEDDINGS

# Configurações
# B19: n_resultados reduzido de 4 -> 3 (RAG context ~25% menor, mantém qualidade
# clínica em CV onde os top-3 chunks já cobrem a maioria das queries vistas no eval)
N_RESULTADOS_PADRAO = 3
N_CANDIDATOS_MMR = 8  # busca 8 (era 10), MMR seleciona N_RESULTADOS_PADRAO finais
DISTANCIA_MAXIMA = 1.2
LAMBDA_MMR = 0.7  # 1=só relevância, 0=só diversidade

# Cliente global (singleton para evitar recarregar embeddings)
_CLIENTE = None
_COLECAO = None


def _obter_colecao():
    """Singleton da coleção ChromaDB."""
    global _CLIENTE, _COLECAO
    if _COLECAO is not None:
        return _COLECAO

    _CLIENTE = PersistentClient(path=str(CHROMA_DIR))
    colecoes = [c.name for c in _CLIENTE.list_collections()]
    if COLECAO_NOME not in colecoes:
        return None

    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name=MODELO_EMBEDDINGS
    )
    _COLECAO = _CLIENTE.get_collection(
        name=COLECAO_NOME,
        embedding_function=embedding_fn,
    )
    return _COLECAO


_TERMOS_CLINICOS_COMUNS = frozenset({
    "hipertensao", "hipertensão", "pressao", "pressão", "infarto",
    "angina", "isquemia", "arritmia", "taquicardia", "bradicardia",
    "dispneia", "dispneia", "edema", "sincope", "síncope", "palpitacao",
    "palpitação", "anticoagulante", "betabloqueador", "estatina",
    "losartana", "enalapril", "atenolol", "captopril", "varfarina",
    "fibrilacao", "fibrilação", "insuficiencia", "insuficiência",
    "cardiovascular", "coronariano", "miocardio", "miocárdio",
    "trombose", "embolia", "aterosclerose", "marcapasso", "stent",
})


def _query_ja_clinica(mensagem: str) -> bool:
    """Heuristica: ja contem termos clinicos suficientes? Pula reformulacao.

    Reformular custa ~2-3s por turno (chamada LLM). Se a query do usuario
    ja vem com vocabulario clinico ou e muito curta (3 palavras ou menos),
    o ganho da reformulacao e marginal e nao vale o custo.
    """
    msg_lower = mensagem.lower()
    palavras = msg_lower.split()

    # Query muito curta: reformular pode ate degradar (ex: "renovar receita"
    # vira "prescricao medicamentosa renovacao" — quase identico).
    if len(palavras) <= 3:
        return True

    # Contem >= 2 termos clinicos: ja esta boa pra RAG.
    hits = sum(1 for termo in _TERMOS_CLINICOS_COMUNS if termo in msg_lower)
    return hits >= 2


def reformular_query_clinica(mensagem_usuario: str) -> str:
    """
    Auto-RAG: reformula a mensagem do usuário em linguagem clínica antes da busca.

    Exemplo:
        "minha pressão tá lá em cima" → "hipertensão arterial sistêmica
                                         crise hipertensiva PA elevada manejo"

    Returns:
        Query reformulada. Se erro, retorna a original.
    """
    # Skip reformulacao se a query ja tem vocabulario clinico ou e curta
    # — economiza 1 chamada LLM (~2-3s) sem perda perceptivel de recall.
    if _query_ja_clinica(mensagem_usuario):
        return mensagem_usuario

    # Import local para evitar circular import
    from src.llm.qwen_client import chat

    try:
        resposta = chat(
            messages=[
                {"role": "system", "content":
                 "Você reformula mensagens de pacientes em termos clínicos cardiovasculares "
                 "para busca em base de conhecimento médica. Responda APENAS com a query "
                 "reformulada, sem texto adicional. Máximo 15 palavras. "
                 "Use terminologia técnica: hipertensão, taquicardia, dispneia, etc."},
                {"role": "user", "content": mensagem_usuario}
            ],
            enable_thinking=False,
            temperature=0.1,
            max_tokens=60,
        )
        reformulada = resposta.get("content", "").strip()
        # Limpeza defensiva
        if not reformulada or len(reformulada) > 200:
            return mensagem_usuario
        return reformulada
    except Exception as exc:
        print(f"[retriever] Reformulação falhou ({type(exc).__name__}); usando query original")
        return mensagem_usuario


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Similaridade coseno entre dois vetores."""
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom < 1e-10:
        return 0.0
    return float(np.dot(a, b) / denom)


def _aplicar_mmr(
    candidatos: list[dict],
    n_final: int,
    lambda_mult: float = LAMBDA_MMR,
) -> list[dict]:
    """
    Aplica Max Marginal Relevance para balancear relevância e diversidade.

    Args:
        candidatos: lista de dicts com 'embedding', 'distancia' e demais campos.
        n_final: quantos chunks selecionar.
        lambda_mult: 1.0 = só relevância, 0.0 = só diversidade.

    Returns:
        Lista de n_final chunks selecionados.
    """
    if not candidatos or n_final <= 0:
        return []

    if len(candidatos) <= n_final:
        return candidatos

    selecionados = []
    restantes = list(candidatos)

    # Primeiro: o mais relevante (menor distância)
    primeiro = min(restantes, key=lambda c: c["distancia"])
    selecionados.append(primeiro)
    restantes.remove(primeiro)

    # Iterativamente: MMR score = λ·relevância - (1-λ)·max_sim_com_selecionados
    while len(selecionados) < n_final and restantes:
        def mmr_score(c):
            rel = 1.0 - c["distancia"]  # transforma dist → similaridade
            emb_c = np.array(c["embedding"])
            sims = [_cosine_similarity(emb_c, np.array(s["embedding"]))
                    for s in selecionados]
            max_sim = max(sims) if sims else 0.0
            return lambda_mult * rel - (1.0 - lambda_mult) * max_sim

        proximo = max(restantes, key=mmr_score)
        selecionados.append(proximo)
        restantes.remove(proximo)

    return selecionados


def recuperar_contexto_detalhado(
    query: str,
    n_resultados: int = N_RESULTADOS_PADRAO,
    filtro_categoria: str | list[str] | None = None,
    usar_mmr: bool = True,
    usar_auto_rag: bool = True,
    usar_reranker: bool = False,
) -> tuple[str, list[dict]]:
    """
    Recupera contexto cardiovascular relevante com saída estruturada.

    Args:
        query: pergunta original do usuário.
        n_resultados: quantos chunks retornar.
        filtro_categoria: categoria(s) específica(s) a buscar. Ex: 'red_flag'
                          ou ['bula', 'protocolo'].
        usar_mmr: aplicar Max Marginal Relevance para diversidade.
        usar_auto_rag: reformular query em linguagem clínica antes de buscar.
        usar_reranker: aplicar cross-encoder reranker nos resultados.

    Returns:
        Tupla (contexto_formatado, documentos_estruturados):
        - contexto_formatado: string pronta para injetar no system prompt
        - documentos_estruturados: lista de dicts com fonte, chunk, scores
          (consumido pelo painel técnico do Dash e pelo eval Sprint 2)
    """
    colecao = _obter_colecao()
    if colecao is None:
        print("[retriever] Knowledge base não indexada. Execute indexar_knowledge_base().")
        return "", []

    # Auto-RAG: reformula query clinicamente
    query_efetiva = reformular_query_clinica(query) if usar_auto_rag else query

    # Filtro por categoria via where do ChromaDB
    where_clause = None
    if filtro_categoria:
        if isinstance(filtro_categoria, str):
            where_clause = {"categoria": filtro_categoria}
        elif isinstance(filtro_categoria, list):
            where_clause = {"categoria": {"$in": filtro_categoria}}

    # Busca semântica — pega top N_CANDIDATOS_MMR para depois aplicar MMR
    n_candidatos = N_CANDIDATOS_MMR if usar_mmr else n_resultados

    try:
        # include embeddings só se for usar MMR (evita custo desnecessário)
        include_fields = ["documents", "metadatas", "distances"]
        if usar_mmr:
            include_fields.append("embeddings")

        resultados = colecao.query(
            query_texts=[query_efetiva],
            n_results=n_candidatos,
            where=where_clause,
            include=include_fields,
        )
    except Exception as exc:
        print(f"[retriever] Erro na busca: {type(exc).__name__}: {exc}")
        return "", []

    # Estruturar candidatos
    candidatos = []
    docs = resultados["documents"][0]
    metas = resultados["metadatas"][0]
    dists = resultados["distances"][0]
    embs = resultados.get("embeddings", [[]])[0] if usar_mmr else [None] * len(docs)

    for doc, meta, dist, emb in zip(docs, metas, dists, embs):
        if dist > DISTANCIA_MAXIMA:
            continue
        candidatos.append({
            "fonte": meta.get("fonte", "?"),
            "titulo": meta.get("titulo", "?"),
            "categoria": meta.get("categoria", "geral"),
            "chunk": doc,
            "distancia": float(dist),
            "score_similaridade": round(1.0 - float(dist) / 2.0, 4),
            "embedding": emb,
        })

    if not candidatos:
        return "", []

    # MMR para diversidade
    if usar_mmr:
        candidatos = _aplicar_mmr(candidatos, n_final=n_resultados)
    else:
        candidatos = candidatos[:n_resultados]

    # Reranker opcional
    if usar_reranker:
        candidatos = _aplicar_reranker(query_efetiva, candidatos)

    # Limpar embeddings antes de retornar (não precisa expor ao Dash)
    documentos_estruturados = []
    for i, c in enumerate(candidatos):
        documentos_estruturados.append({
            "rank": i + 1,
            "fonte": c["fonte"],
            "titulo": c["titulo"],
            "categoria": c["categoria"],
            "chunk": c["chunk"],
            "score_similaridade": c["score_similaridade"],
            "score_rerank": c.get("score_rerank"),
            "distancia": c["distancia"],
        })

    # Contexto formatado para o prompt
    blocos = []
    for d in documentos_estruturados:
        blocos.append(f"[Fonte: {d['titulo']} | Categoria: {d['categoria']}]\n{d['chunk']}")

    contexto_formatado = "CONTEXTO CLÍNICO RELEVANTE:\n\n" + "\n\n---\n\n".join(blocos)
    contexto_formatado += f"\n\n[QUERY ORIGINAL: {query}]"
    if usar_auto_rag and query_efetiva != query:
        contexto_formatado += f"\n[QUERY REFORMULADA: {query_efetiva}]"

    return contexto_formatado, documentos_estruturados


def _aplicar_reranker(query: str, candidatos: list[dict]) -> list[dict]:
    """Reranker via cross-encoder. Import local para não onerar quando desabilitado."""
    try:
        from .reranker import rerank_cross_encoder
        return rerank_cross_encoder(query, candidatos)
    except Exception as exc:
        print(f"[retriever] Reranker falhou ({exc}); mantendo ordem MMR")
        return candidatos


# Compatibilidade com Sprint 1 — retorna apenas a string
# B19: cache LRU acelera queries repetidas (eval set tem várias perguntas
# idênticas / muito parecidas). Chave do cache é (query, n_resultados, filtro).
# maxsize=128 cobre 1 sessão de eval inteira (32-35 casos) com folga.


def _filtro_cacheavel(filtro):
    """Normaliza filtro_categoria pra ser hashable (lists -> tuples)."""
    if isinstance(filtro, list):
        return tuple(filtro)
    return filtro


@lru_cache(maxsize=128)
def _recuperar_contexto_cached(
    query: str,
    n_resultados: int,
    filtro_categoria_hashable,
) -> str:
    """Versão cacheada — argumentos garantidamente hashables."""
    # Normaliza o filtro de volta pra list se foi serializado como tuple
    filtro = (
        list(filtro_categoria_hashable)
        if isinstance(filtro_categoria_hashable, tuple)
        else filtro_categoria_hashable
    )
    contexto, _ = recuperar_contexto_detalhado(
        query=query,
        n_resultados=n_resultados,
        filtro_categoria=filtro,
        usar_mmr=True,
        usar_auto_rag=True,
        usar_reranker=False,
    )
    return contexto


def recuperar_contexto(
    query: str,
    n_resultados: int = N_RESULTADOS_PADRAO,
    filtro_categoria: str | list[str] | None = None,
) -> str:
    """
    Wrapper compatível com a assinatura da Sprint 1.

    Para os agentes que querem o documentos_estruturados (Sprint 2),
    use recuperar_contexto_detalhado diretamente.
    """
    return _recuperar_contexto_cached(
        query,
        n_resultados,
        _filtro_cacheavel(filtro_categoria),
    )


def limpar_cache_recuperacao() -> None:
    """Limpa o cache LRU (útil em testes ou após reindexação)."""
    _recuperar_contexto_cached.cache_clear()
