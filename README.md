# blua-cardio

Plataforma cardiovascular integrada: chatbot multi-agente (LangGraph, pt-BR)
+ dashboard de telemetria PPG/BPM ao vivo de ESP32 + MAX30100.

Projeto novo nascido da união de duas bases anteriores:
- BluaDiagnostics (chatbot)
- cardiac_dashboard_dash (dashboard)

## Status
Em construção. Plano de integração em `PLANO_MERGE.md`.

## Stack
- Python 3.10+
- LangGraph + Qwen (via DashScope/Ollama)
- Dash (UI)
- ChromaDB (RAG)
- pandas (telemetria)

## Como rodar (após Passo 5 do PLANO_MERGE.md)
Ver `PLANO_MERGE.md` → Passo 7 (smoke tests).
