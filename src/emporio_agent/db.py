"""Responsabilidade: encapsular as conexões SQLite e as regras de autorização para leitura e escrita do agente."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "emporio.db"


def autorizador(action, arg1, arg2, *rest):
    """Restringe acessos indevidos e impede vazamento de campos sensíveis ou consultas genéricas."""
    if action == "SELECT":
        if arg1 and "description_raw" in arg1:
            return sqlite3.SQLITE_DENY
        if arg1 and "phone" in arg1:
            return sqlite3.SQLITE_DENY
        if arg1 and "email" in arg1:
            return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def conn_leitura():
    """Cria uma conexão SQLite somente leitura para consultar dados de loja e pedidos."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.set_authorizer(autorizador)
    return conn


def conn_escrita():
    """Cria uma conexão SQLite com permissão de escrita para histórico e memória do agente."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
