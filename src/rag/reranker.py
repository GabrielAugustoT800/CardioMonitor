"""
Reranker do RAG — Sprint 2.

Cross-encoder leve (cross-encoder/ms-marco-MiniLM-L-6-v2) que reordena
os chunks recuperados pela similaridade do vetor, usando atenção cruzada
para julgamento mais preciso.

Trade-off: latência. No CPU adiciona ~2-5s por query. Por isso, na
Sprint 2 só o agente Triagem ativa o reranker (precisão > velocidade
em casos clínicos críticos). Checkup e Suporte ficam sem.

Uso típico (interno ao retriever):
    from src.rag.reranker import rerank_cross_encoder
    candidatos = rerank_cross_encoder(query, candidatos)
"""

from __future__ import annotations

from dataclasses import dataclass

# Lazy load — cross-encoder é pesado (~50MB) e demora para carregar
_MODELO_RERANK = None
_NOME_MODELO = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@dataclass
class RerankerConfig:
    """Configuração da camada de reranker."""
    enabled: bool = True
    model: str = _NOME_MODELO
    top_n: int = 3


def _obter_modelo():
    """Lazy loader do CrossEncoder."""
    global _MODELO_RERANK
    if _MODELO_RERANK is not None:
        return _MODELO_RERANK

    try:
        from sentence_transformers import CrossEncoder
        print(f"[reranker] Carregando modelo {_NOME_MODELO}...")
        _MODELO_RERANK = CrossEncoder(_NOME_MODELO)
        print("[reranker] Modelo carregado.")
        return _MODELO_RERANK
    except ImportError:
        print("[reranker] sentence-transformers não disponível; reranker desativado")
        return None
    except Exception as exc:
        print(f"[reranker] Erro ao carregar modelo: {exc}; reranker desativado")
        return None


def rerank_cross_encoder(
    query: str,
    candidatos: list[dict],
    top_n: int | None = None,
) -> list[dict]:
    """
    Reordena candidatos via cross-encoder.

    Args:
        query: pergunta original (em linguagem natural ou clínica).
        candidatos: lista de dicts com pelo menos chave 'chunk'.
        top_n: quantos retornar após reordenar. None mantém tamanho original.

    Returns:
        Lista reordenada com novo campo 'score_rerank' adicionado.
        Se modelo não disponível, retorna lista original sem alteração.
    """
    if not candidatos:
        return candidatos

    modelo = _obter_modelo()
    if modelo is None:
        return candidatos

    try:
        pares = [(query, c["chunk"]) for c in candidatos]
        scores = modelo.predict(pares)

        # Atribui score e reordena descendente
        for c, s in zip(candidatos, scores):
            c["score_rerank"] = round(float(s), 4)

        candidatos.sort(key=lambda c: c["score_rerank"], reverse=True)

        if top_n is not None:
            return candidatos[:top_n]
        return candidatos

    except Exception as exc:
        print(f"[reranker] Erro durante rerank: {exc}; mantendo ordem original")
        return candidatos


# Wrapper compatível com versão Sprint 1 (no-op)
def rerank(query, chunks, config=None):
    """Compat com Sprint 1. Use rerank_cross_encoder() na Sprint 2."""
    if config is None:
        config = RerankerConfig()
    if not config.enabled:
        return chunks
    return rerank_cross_encoder(query, chunks, top_n=config.top_n)
