"""Responsabilidade: expor a interface em linha de comando do Empório da Música."""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from collections.abc import Sequence

from . import agent, llm, memory


def _criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Converse com o agente do Empório da Música."
    )
    parser.add_argument(
        "--conversa",
        metavar="ID",
        help="Retoma uma conversa existente pelo identificador.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Habilita logs de depuração.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    modelo: agent.ModelCallable | None = None,
) -> int:
    """Executa a conversa interativa e imprime as respostas do agente."""
    args = _criar_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )
    conversa_id = args.conversa
    if conversa_id is not None:
        try:
            memory.recuperar_historico(conversa_id=conversa_id)
        except (sqlite3.Error, ValueError) as exc:
            print(f"Não foi possível iniciar a conversa: {exc}", file=sys.stderr)
            return 1

    if modelo is None:
        try:
            modelo = llm.criar_modelo()
        except (ImportError, ValueError, llm.LLMError) as exc:
            print(f"Não foi possível configurar o provedor LLM: {exc}", file=sys.stderr)
            return 1

    if conversa_id is None:
        try:
            conversa_id = memory.criar_conversa()
        except (sqlite3.Error, ValueError) as exc:
            print(f"Não foi possível iniciar a conversa: {exc}", file=sys.stderr)
            return 1

    print(f"Conversa: {conversa_id}")
    print("Digite /sair para encerrar.")
    while True:
        try:
            mensagem = input("Você: ").strip()
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print("\nConversa encerrada.")
            return 0

        if mensagem == "/sair":
            return 0
        if not mensagem:
            continue

        try:
            resposta = agent.responder_mensagem(
                mensagem,
                conversa_id=conversa_id,
                debug=args.debug,
                modelo=modelo,
            )
        except KeyboardInterrupt:
            print("\nConversa encerrada.")
            return 0
        except (agent.ModelCallError, llm.LLMError, sqlite3.Error, ValueError) as exc:
            print(f"Não foi possível processar a mensagem: {exc}", file=sys.stderr)
            return 1

        print(f"Empório: {resposta}")


if __name__ == "__main__":
    raise SystemExit(main())
