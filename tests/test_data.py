"""Responsabilidade: testar o build do banco do Empório da Música no Passo 1."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from scripts.build_db import build_database


def test_build_database_recria_tabelas_da_loja_e_mantem_integridade():
    """Critério de aceite do Passo 1: o build do banco recria as tabelas da loja, mantém idempotência e preserva integridade referencial."""
    db_path = Path(__file__).resolve().parents[1] / "data" / "emporio.db"
    if db_path.exists():
        db_path.unlink()

    build_database()

    with sqlite3.connect(db_path) as conn:
        tables = [
            "categories",
            "products",
            "promotions",
            "customers",
            "orders",
            "order_items",
        ]
        for table in tables:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            assert count > 0, f"Tabela {table} ficou vazia após o build"

        assert conn.execute(
            "SELECT COUNT(*) FROM products p LEFT JOIN categories c ON c.category_id = p.category_id WHERE c.category_id IS NULL"
        ).fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM orders o LEFT JOIN customers c ON c.customer_id = o.customer_id WHERE c.customer_id IS NULL"
        ).fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM order_items oi LEFT JOIN products p ON p.product_id = oi.product_id WHERE p.product_id IS NULL"
        ).fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM order_items oi LEFT JOIN orders o ON o.order_id = oi.order_id WHERE o.order_id IS NULL"
        ).fetchone()[0] == 0

    build_database()

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0] > 0
        assert conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] > 0
