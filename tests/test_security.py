"""Responsabilidade: validar regras de segurança e vazamento de dados no Passo 2 e Passo 6 do projeto."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from emporio_agent import db, memory


@pytest.fixture
def banco_teste(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "emporio.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)

    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE customers (
                customer_id INTEGER PRIMARY KEY,
                email TEXT NOT NULL,
                phone TEXT NOT NULL
            );
            CREATE TABLE products (
                product_id INTEGER PRIMARY KEY,
                description_raw TEXT
            );
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            );
            INSERT INTO customers (customer_id, email, phone)
            VALUES (1, 'cliente@exemplo.com', '67999999999');
            INSERT INTO products (product_id, description_raw)
            VALUES (1, 'Descrição interna');
            """
        )

    return db_path


@pytest.mark.parametrize(
    ("operacao", "sql"),
    [
        (
            "INSERT",
            "INSERT INTO customers (customer_id, email, phone) "
            "VALUES (2, 'novo@exemplo.com', '67988888888')",
        ),
        ("UPDATE", "UPDATE customers SET email = 'alterado@exemplo.com' WHERE customer_id = 1"),
        ("DELETE", "DELETE FROM customers WHERE customer_id = 1"),
    ],
)
def test_conn_leitura_bloqueia_escrita(
    banco_teste: Path, operacao: str, sql: str
) -> None:
    with closing(db.conn_leitura()) as conn:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute(sql)

    print(f"\n[TESTE] Conexão somente leitura: {operacao} bloqueado como esperado")


def test_authorizer_bloqueia_description_raw_e_permite_email(
    banco_teste: Path,
) -> None:
    with closing(db.conn_leitura()) as conn:
        with pytest.raises(sqlite3.DatabaseError, match="not authorized|prohibited"):
            conn.execute("SELECT description_raw FROM products").fetchone()

        email = conn.execute("SELECT email FROM customers").fetchone()["email"]

        with pytest.raises(sqlite3.DatabaseError, match="not authorized|prohibited"):
            conn.execute("SELECT phone FROM customers").fetchone()

    assert email == "cliente@exemplo.com"
    print("\n[TESTE] Authorizer: description_raw bloqueado; customers.email permitido")


def test_conexoes_habilitam_chaves_estrangeiras(banco_teste: Path) -> None:
    with closing(db.conn_leitura()) as conn:
        foreign_keys_leitura = conn.execute("PRAGMA foreign_keys").fetchone()[0]

    with closing(memory.conn_escrita()) as conn:
        foreign_keys_escrita = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
            conn.execute("INSERT INTO orders (order_id, customer_id) VALUES (1, 999)")

    assert foreign_keys_leitura == 1
    assert foreign_keys_escrita == 1
    print(
        "\n[TESTE] Chaves estrangeiras: leitura="
        f"{foreign_keys_leitura}, escrita={foreign_keys_escrita}; referência inválida bloqueada"
    )


@pytest.mark.skip(reason="Passo 6")
def test_tools_nao_expoem_telefone_email_ou_description_raw():
    """Critério do Passo 6: nenhuma tool expõe telefone, e-mail ou `description_raw` e o código não usa `SELECT *` nem `date.today()` fora do módulo de configuração."""
    pass
