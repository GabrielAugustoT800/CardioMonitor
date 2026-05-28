"""
Indexação da knowledge base cardiovascular no ChromaDB — Sprint 2.

Evoluções vs Sprint 1:
- Adiciona metadado 'categoria' a cada chunk para filtro por tipo
  (red_flag, bula, protocolo, politica_care_plus, estratificacao,
  apresentacao_atipica, cartilha, especialidades)
- Permite que agentes especialistas filtrem chunks por categoria relevante

Uso:
    # Via import:
    from src.rag import indexar_knowledge_base
    indexar_knowledge_base()

    # Via CLI:
    python -m src.rag.indexer            # indexa apenas se vazio
    python -m src.rag.indexer --force    # recria do zero
"""

from __future__ import annotations

import os
from pathlib import Path

from chromadb import PersistentClient
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Configurações

KB_DIR = Path(__file__).resolve().parents[2] / "knowledge_base"

CHROMA_DIR = Path(
    os.getenv("CHROMA_PERSIST_DIR",
              str(Path(__file__).resolve().parents[2] / "chroma_db"))
)

COLECAO_NOME = "bluadiagnostics_cardiovascular"
MODELO_EMBEDDINGS = "intfloat/multilingual-e5-large"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# Mapeamento de nome de arquivo → categoria do chunk
# Permite filtrar buscas RAG por tipo de documento
_MAPA_CATEGORIA = {
    "red_flags_cardiovasculares.md": "red_flag",
    "protocolo_triagem_cardiovascular.md": "protocolo",
    "diretrizes_sbc_hipertensao_arritmia.md": "protocolo",
    "anti_hipertensivos_bula_resumida.md": "bula",
    "anti_coagulante_bula_resumida.md": "bula",
    "politicas_care_plus_telemedicina.md": "politica_care_plus",
    "cartilha_beneficiario_saude_cardiaca.md": "cartilha",
    "cardiologia_estratificacao_risco.md": "estratificacao",
    "cardiologia_apresentacoes_atipicas.md": "apresentacao_atipica",
    "cardiologia_gravidez_pre_eclampsia.md": "apresentacao_atipica",
    "cardiologia_jovens_atletas.md": "apresentacao_atipica",
    "mapa_especialidades.md": "especialidades",
}


def _categoria_do_arquivo(nome_arquivo: str) -> str:
    """Retorna a categoria do chunk baseado no nome do arquivo fonte."""
    return _MAPA_CATEGORIA.get(nome_arquivo, "geral")


def _carregar_documentos() -> list[dict]:
    """Carrega todos os arquivos .md da knowledge_base/."""
    documentos = []
    for arquivo in sorted(KB_DIR.glob("*.md")):
        conteudo = arquivo.read_text(encoding="utf-8")
        documentos.append({
            "conteudo": conteudo,
            "fonte": arquivo.name,
            "titulo": arquivo.stem.replace("_", " ").title(),
            "categoria": _categoria_do_arquivo(arquivo.name),
        })
        print(f"[indexer] Carregado: {arquivo.name} "
              f"({len(conteudo)} chars, categoria={_categoria_do_arquivo(arquivo.name)})")
    return documentos


def _dividir_chunks(documentos: list[dict]) -> tuple[list[str], list[dict]]:
    """Divide documentos em chunks com metadados estruturados."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "]
    )

    textos = []
    metadados = []

    for doc in documentos:
        chunks = splitter.split_text(doc["conteudo"])

        for i, chunk in enumerate(chunks):
            textos.append(chunk)
            metadados.append({
                "fonte": doc["fonte"],
                "titulo": doc["titulo"],
                "categoria": doc["categoria"],
                "chunk_index": i,
                "total_chunks": len(chunks),
            })

    return textos, metadados


def indexar_knowledge_base(forcar_reindexacao: bool = False) -> int:
    """
    Indexa a knowledge base cardiovascular no ChromaDB.
    Idempotente — verifica se já foi indexado antes de reprocessar.

    Args:
        forcar_reindexacao: Se True, recria a coleção do zero.

    Returns:
        Número total de chunks indexados.
    """
    print("[indexer] Iniciando indexação da knowledge_base cardiovascular...")

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    cliente = PersistentClient(path=str(CHROMA_DIR))

    colecoes_existentes = [c.name for c in cliente.list_collections()]

    if COLECAO_NOME in colecoes_existentes and not forcar_reindexacao:
        colecao = cliente.get_collection(COLECAO_NOME)
        total = colecao.count()
        if total > 0:
            print(f"[indexer] Coleção já indexada com {total} chunks. "
                  f"Use forcar_reindexacao=True para reindexar.")
            return total

    if COLECAO_NOME in colecoes_existentes and forcar_reindexacao:
        cliente.delete_collection(COLECAO_NOME)
        print("[indexer] Coleção anterior removida.")

    print(f"[indexer] Carregando modelo de embeddings: {MODELO_EMBEDDINGS}")
    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name=MODELO_EMBEDDINGS
    )

    colecao = cliente.create_collection(
        name=COLECAO_NOME,
        embedding_function=embedding_fn,
        metadata={"descricao": "Knowledge base cardiovascular BluaDiagnostics Sprint 2"}
    )

    print("[indexer] Carregando documentos...")
    documentos = _carregar_documentos()

    print("[indexer] Dividindo em chunks...")
    textos, metadados = _dividir_chunks(documentos)

    ids = [f"chunk_{i:04d}" for i in range(len(textos))]

    LOTE = 100
    for inicio in range(0, len(textos), LOTE):
        fim = min(inicio + LOTE, len(textos))
        colecao.add(
            documents=textos[inicio:fim],
            metadatas=metadados[inicio:fim],
            ids=ids[inicio:fim]
        )
        print(f"[indexer] Indexado lote {inicio}-{fim} de {len(textos)}")

    print(f"[indexer] Concluído — {len(textos)} chunks indexados em {CHROMA_DIR}")

    # Estatísticas por categoria
    from collections import Counter
    cats = Counter(m["categoria"] for m in metadados)
    print(f"[indexer] Distribuição por categoria: {dict(cats)}")

    return len(textos)


# Entrypoint CLI — permite `python -m src.rag.indexer [--force]`
# Nota: o pacote `src.rag.__init__` importa este módulo, então rodar via
# `-m` dispara um RuntimeWarning cosmético do runpy. Indexação ocorre
# normalmente apesar do warning.
if __name__ == "__main__":
    import sys
    forcar = "--force" in sys.argv or "-f" in sys.argv
    indexar_knowledge_base(forcar_reindexacao=forcar)
