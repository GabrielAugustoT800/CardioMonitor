"""Cliente Ollama — wrapper fino sobre QwenClient com backend fixo em "ollama".

Não funciona dentro do Colab gratuito (depende de um servidor Ollama em
localhost). Está aqui porque a Configuração B (on-prem) é parte da
arquitetura prevista para clientes Care Plus com isolamento total.
"""

from __future__ import annotations

from typing import Any

from src.llm.qwen_client import QwenClient


class OllamaClient(QwenClient):
    """QwenClient com backend Ollama fixado.

    Deixar isso explícito no código consumidor facilita auditoria — basta
    grep por `OllamaClient` para achar todo lugar que usa on-prem.
    """

    def __init__(self) -> None:
        super().__init__(backend="ollama")

    def chat(self, **kwargs: Any) -> dict[str, Any]:
        kwargs["backend"] = "ollama"
        return super().chat(**kwargs)
