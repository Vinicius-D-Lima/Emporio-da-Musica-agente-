"""Responsabilidade: recriar o banco de dados da loja a partir dos CSVs do desafio, mantendo idempotência e integridade referencial."""

from __future__ import annotations


def build_database() -> None:
    """Cria ou recria o banco SQLite da loja com as tabelas da loja apenas, preservando idempotência e a FK de `conversations` ao recriar `customers`."""
    raise NotImplementedError("O build do banco será implementado em um passo posterior.")


if __name__ == "__main__":
    build_database()
