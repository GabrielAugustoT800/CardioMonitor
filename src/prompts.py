"""
Loader único de system prompts a partir de arquivos .md em /prompts/.

Centraliza o carregamento para eliminar prompts hard-coded nos agentes —
requisito explícito da Sprint 2 ("prompts hard-coded em dezenas de lugares
serão penalizados").

Uso nos agentes:
    from src.prompts import carregar_prompt

    SYSTEM_PROMPT = carregar_prompt("agente_triagem")
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

# Diretório raiz dos prompts — relativo a este arquivo
_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


@lru_cache(maxsize=32)
def carregar_prompt(nome: str) -> str:
    """
    Carrega um system prompt do diretório /prompts/.

    Cache em memória — cada prompt é lido uma única vez por processo.

    Args:
        nome: Nome do arquivo sem extensão. Ex: "agente_triagem"
              carrega prompts/agente_triagem.md

    Returns:
        Conteúdo do arquivo como string.

    Raises:
        FileNotFoundError: Se o arquivo .md não existir.
    """
    caminho = _PROMPTS_DIR / f"{nome}.md"
    if not caminho.exists():
        raise FileNotFoundError(
            f"Prompt '{nome}.md' não encontrado em {_PROMPTS_DIR}. "
            f"Prompts disponíveis: {listar_prompts()}"
        )
    return caminho.read_text(encoding="utf-8")


def listar_prompts() -> list[str]:
    """
    Lista todos os prompts disponíveis em /prompts/.

    Útil para debug e para o painel técnico do Dash.
    """
    if not _PROMPTS_DIR.exists():
        return []
    return sorted(p.stem for p in _PROMPTS_DIR.glob("*.md"))


def invalidar_cache() -> None:
    """
    Limpa o cache de prompts.

    Útil em desenvolvimento: depois de editar um .md, chamar isso
    força recarga sem reiniciar o processo Python.
    """
    carregar_prompt.cache_clear()
