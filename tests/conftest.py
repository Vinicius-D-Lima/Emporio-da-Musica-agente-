"""Responsabilidade: configurar opt-in dos testes LLM e fixtures de cenários isolados."""

from __future__ import annotations

import contextlib
import io
import sqlite3
from pathlib import Path

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-llm",
        action="store_true",
        default=False,
        help="Executa testes marcados com llm, que podem fazer chamadas externas.",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if config.getoption("--run-llm"):
        return

    pular_llm = pytest.mark.skip(
        reason="testes LLM são opt-in; use --run-llm para executá-los"
    )
    for item in items:
        if item.get_closest_marker("llm") is not None:
            item.add_marker(pular_llm)


@pytest.fixture
def banco_cenarios(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from emporio_agent import db
    from scripts import build_db

    db_path = tmp_path / "emporio-cenarios.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(build_db, "DB_PATH", db_path)
    monkeypatch.setenv("REFERENCE_DATETIME", "2026-03-23T10:00:00")

    with contextlib.redirect_stdout(io.StringIO()):
        build_db.build_database()

    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO customers (customer_id, name, phone, email, city)
            VALUES (?, ?, NULL, ?, ?)
            """,
            [
                (9001, "Alice de Teste", "alice@example.test", "Campo Grande"),
                (9002, "Bob de Teste", "bob@example.test", "Campo Grande"),
            ],
        )
        conn.executemany(
            """
            INSERT INTO orders (
                order_id, customer_id, order_date, status, total_brl,
                payment_type, installments, tracking_code, estimated_delivery,
                notes, total_needs_review
            ) VALUES (?, ?, '2026-03-20', 'delivered', ?, 'credit', 1, NULL, NULL, NULL, ?)
            """,
            [
                (99001, 9001, 199.99, 0),
                (99002, 9002, 299.99, 0),
                (99003, 9001, 12345.67, 1),
            ],
        )
        conn.executemany(
            """
            INSERT INTO order_items (order_id, product_id, quantity)
            VALUES (?, ?, 1)
            """,
            [(99001, 95), (99002, 127), (99003, 95)],
        )

    return db_path
