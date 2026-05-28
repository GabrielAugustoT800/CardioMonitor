"""
Pacote RAG do BluaDiagnostics — Sprint 2.

Exporta:
- indexar_knowledge_base: popula ChromaDB com categorias
- recuperar_contexto: compat Sprint 1 (string)
- recuperar_contexto_detalhado: Sprint 2 (tupla string + estruturado)
- reformular_query_clinica: Auto-RAG
"""

from .indexer import indexar_knowledge_base, CHROMA_DIR, COLECAO_NOME
from .retriever import (
    recuperar_contexto,
    recuperar_contexto_detalhado,
    reformular_query_clinica,
)
from .reranker import rerank_cross_encoder, RerankerConfig

__all__ = [
    "indexar_knowledge_base",
    "recuperar_contexto",
    "recuperar_contexto_detalhado",
    "reformular_query_clinica",
    "rerank_cross_encoder",
    "RerankerConfig",
    "CHROMA_DIR",
    "COLECAO_NOME",
]
