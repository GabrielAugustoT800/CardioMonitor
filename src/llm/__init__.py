"""Camada LLM — clientes para DashScope (cloud) e Ollama (on-prem)."""

from src.llm.qwen_client import QwenClient, chat
from src.llm.ollama_client import OllamaClient

__all__ = ["QwenClient", "OllamaClient", "chat"]
