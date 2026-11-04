"""Responsabilidade: encapsular as conexões SQLite e as regras de autorização para leitura e escrita do agente."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "emporio.db"


def autorizador(action, arg1, arg2, *rest):
    """Impede a leitura de descrições internas e telefones de clientes."""
    if action == sqlite3.SQLITE_READ:
        if (arg1 == "products" and arg2 == "description_raw") or (
            arg1 == "customers" and arg2 == "phone"
        ):
            return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def conn_leitura():
    """Cria uma conexão SQLite somente leitura para consultar dados de loja e pedidos."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.set_authorizer(autorizador)
    return conn


def conn_escrita():
    """Cria uma conexão SQLite com permissão de escrita para histórico e memória do agente."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
