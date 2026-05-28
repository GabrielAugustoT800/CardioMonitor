"""
CLI para execução fora do notebook.


Uso:
    python main.py --smoke
    python main.py --once "Quero fazer meu check-up"
    python main.py --beneficiario BENEF-002 --once "Minhas medicações"
    python main.py --interativo
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path

# Garantir que src/ está no path antes de qualquer import do projeto
_RAIZ = Path(__file__).resolve().parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

try:
    from colab_setup import preparar_ambiente
    preparar_ambiente(exigir_chave=False)
except Exception as exc:
    print(f"[main] Aviso de bootstrap: {exc}")


# ----------------------------------------------------------------
# Modos de execução
# ----------------------------------------------------------------

def modo_smoke() -> int:
    """
    Valida conectividade e credenciais com uma chamada simples ao LLM.
    Retorna 0 se bem-sucedido, 1 se falhou.
    """
    from src.llm.qwen_client import smoke_test

    print("[smoke] Testando conexão com DashScope...")
    sucesso = smoke_test()
    return 0 if sucesso else 1


def modo_unico(mensagem: str, beneficiario_id: str) -> int:
    """
    Executa um único turno e imprime a resposta.
    Útil para testes rápidos via linha de comando.
    """
    from src.graph import construir_grafo, executar_turno

    grafo = construir_grafo()
    estado = executar_turno(
        grafo=grafo,
        mensagem_usuario=mensagem,
        thread_id=str(uuid.uuid4()),
        beneficiario_id=beneficiario_id,
    )

    print(f"\n[{estado.get('agente_ativo')} | {estado.get('intent_classificada')}]")
    print(estado.get("resposta_final", "(sem resposta)"))
    return 0


def modo_interativo(beneficiario_id: str) -> int:
    """
    Modo conversacional multi-turno no terminal.
    Mantém memória de sessão via thread_id fixo.
    """
    from src.graph import construir_grafo, executar_turno

    print("BluaDiagnostics — Modo interativo")
    print(f"Beneficiário: {beneficiario_id}")
    print("Digite 'sair' para encerrar.\n")

    grafo = construir_grafo()
    thread_id = str(uuid.uuid4())

    while True:
        try:
            entrada = input("Você > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando.")
            return 0

        if not entrada:
            continue

        if entrada.lower() in {"sair", "exit", "quit"}:
            return 0

        try:
            estado = executar_turno(
                grafo=grafo,
                mensagem_usuario=entrada,
                thread_id=thread_id,
                beneficiario_id=beneficiario_id,
            )

            agente = estado.get("agente_ativo", "?")
            intent = estado.get("intent_classificada", "?")
            resposta = estado.get("resposta_final", "(sem resposta)")

            print(f"\nBlua [{agente} | {intent}]\n{resposta}\n")

        except Exception as exc:
            print(f"[erro] {type(exc).__name__}: {exc}")
            return 1


# ----------------------------------------------------------------
# CLI
# ----------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="BluaDiagnostics CLI — Care Plus / Plataforma Blua"
    )

    parser.add_argument(
        "--beneficiario",
        default="BENEF-001",
        choices=[
            "BENEF-001", "BENEF-002", "BENEF-003",
            "BENEF-CV-001", "BENEF-CV-002", "BENEF-CV-003",
            "BENEF-MARIA",
        ],
        help="ID do beneficiário mockado (default: BENEF-001)",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Testa conectividade e credenciais com o DashScope",
    )
    parser.add_argument(
        "--once",
        default=None,
        metavar="MENSAGEM",
        help="Executa um único turno com a mensagem informada e encerra",
    )
    parser.add_argument(
        "--interativo",
        action="store_true",
        help="Inicia modo conversacional multi-turno no terminal",
    )

    args = parser.parse_args()

    # Validar que pelo menos um modo foi informado
    if not any([args.smoke, args.once, args.interativo]):
        parser.print_help()
        return 0

    if args.smoke:
        return modo_smoke()

    if args.once:
        return modo_unico(args.once, args.beneficiario)

    if args.interativo:
        return modo_interativo(args.beneficiario)

    return 0


if __name__ == "__main__":
    sys.exit(main())