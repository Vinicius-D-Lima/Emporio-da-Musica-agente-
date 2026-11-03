"""Responsabilidade: validar regras de segurança e vazamento de dados no Passo 2 e Passo 6 do projeto."""

from __future__ import annotations

import sqlite3
import contextlib
import io
from contextlib import closing
from pathlib import Path

import pytest
from pydantic import ValidationError

from emporio_agent import db, memory
from emporio_agent.schemas import StatusPedidoArgs
from emporio_agent.tools import orders
from scripts import build_db


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


@pytest.fixture
def banco_pedidos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    db_path = tmp_path / "emporio-pedidos.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(build_db, "DB_PATH", db_path)

    with contextlib.redirect_stdout(io.StringIO()):
        build_db.build_database()

    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO conversations (id, started_at)
            VALUES (?, '2026-03-23T10:00:00')
            """,
            [("sessao-a",), ("sessao-b",), ("sessao-c",), ("sessao-d",)],
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


def test_verificar_cliente_aceita_email_ignorando_caixa_e_espacos(
    banco_pedidos: Path,
) -> None:
    resultado = orders.verificar_cliente(
        order_id=10,
        email="  BRUNO.MARTINS@JMAIL.COM  ",
        conversa_id="sessao-a",
    )

    assert resultado == {"status": "verified", "message": "Cliente verificado."}
    with sqlite3.connect(banco_pedidos) as conn:
        cliente_verificado = conn.execute(
            "SELECT verified_customer_id FROM conversations WHERE id = 'sessao-a'"
        ).fetchone()[0]
    assert cliente_verificado == 11
    print("\n[TESTE] Identidade: pedido 10 validado com e-mail normalizado; sessão associada")


def test_pedido_inexistente_e_email_incorreto_têm_resposta_idêntica(
    banco_pedidos: Path,
) -> None:
    pedido_inexistente = orders.verificar_cliente(
        order_id=999,
        email="bruno.martins@jmail.com",
        conversa_id="sessao-a",
    )
    email_incorreto = orders.verificar_cliente(
        order_id=10,
        email="outra.pessoa@exemplo.com",
        conversa_id="sessao-b",
    )

    assert pedido_inexistente == email_incorreto
    assert pedido_inexistente["status"] == "not_verified"
    print("\n[TESTE] Verificação: pedido inexistente e e-mail incorreto não são distinguíveis")


def test_verificacao_bloqueia_depois_de_tres_tentativas(
    banco_pedidos: Path,
) -> None:
    resultados = [
        orders.verificar_cliente(
            order_id=10,
            email=f"errado-{tentativa}@exemplo.com",
            conversa_id="sessao-a",
        )
        for tentativa in range(3)
    ]
    bloqueado = orders.verificar_cliente(
        order_id=10,
        email="bruno.martins@jmail.com",
        conversa_id="sessao-a",
    )

    assert all(resultado["status"] == "not_verified" for resultado in resultados)
    assert bloqueado == {
        "status": "locked",
        "message": "Limite de tentativas de verificação atingido.",
    }
    with sqlite3.connect(banco_pedidos) as conn:
        assert conn.execute(
            "SELECT verified_customer_id FROM conversations WHERE id = 'sessao-a'"
        ).fetchone()[0] is None
    print("\n[TESTE] Verificação: sessão bloqueada após 3 tentativas inválidas")


def test_tentativas_de_verificacao_sao_independentes_por_sessao(
    banco_pedidos: Path,
) -> None:
    for _ in range(3):
        orders.verificar_cliente(
            order_id=10,
            email="incorreto@exemplo.com",
            conversa_id="sessao-a",
        )

    resultado = orders.verificar_cliente(
        order_id=10,
        email="bruno.martins@jmail.com",
        conversa_id="sessao-b",
    )

    assert resultado["status"] == "verified"


def test_status_pedido_nao_aceita_customer_id_como_argumento_do_modelo() -> None:
    with pytest.raises(ValidationError):
        StatusPedidoArgs.model_validate({"order_id": 10, "customer_id": 11})


def test_cliente_verificado_so_acessa_pedidos_da_propria_identidade(
    banco_pedidos: Path,
) -> None:
    orders.verificar_cliente(
        order_id=10,
        email="bruno.martins@jmail.com",
        conversa_id="sessao-a",
    )

    pedido_proprio = orders.status_pedido(
        order_id=10,
        conversa_id="sessao-a",
    )
    pedido_de_outra_pessoa = orders.status_pedido(
        order_id=8,
        conversa_id="sessao-a",
    )

    assert pedido_proprio["status"] == "success"
    assert pedido_de_outra_pessoa == {
        "status": "not_found",
        "message": "Pedido não encontrado.",
    }


def test_sessao_verificada_nao_pode_trocar_de_cliente(
    banco_pedidos: Path,
) -> None:
    orders.verificar_cliente(
        order_id=10,
        email="bruno.martins@jmail.com",
        conversa_id="sessao-a",
    )

    resultado = orders.verificar_cliente(
        order_id=8,
        email="anacarol.ferreira@coldmail.com",
        conversa_id="sessao-a",
    )

    assert resultado["status"] == "already_verified"
    assert orders.status_pedido(
        order_id=10, conversa_id="sessao-a"
    )["status"] == "success"
    assert orders.status_pedido(
        order_id=8, conversa_id="sessao-a"
    )["status"] == "not_found"


def test_status_requer_cliente_verificado_na_sessao(
    banco_pedidos: Path,
) -> None:
    resultado = orders.status_pedido(order_id=10, conversa_id="sessao-a")

    assert resultado == {
        "status": "not_verified",
        "message": "Cliente não verificado nesta conversa.",
    }


def test_status_pedido_retorna_dados_operacionais_sem_dados_pessoais(
    banco_pedidos: Path,
) -> None:
    orders.verificar_cliente(
        order_id=10,
        email="bruno.martins@jmail.com",
        conversa_id="sessao-a",
    )

    resultado = orders.status_pedido(order_id=10, conversa_id="sessao-a")
    pedido = resultado["order"]

    assert resultado["status"] == "success"
    assert pedido["order_id"] == 10
    assert pedido["status"] == "confirmed"
    assert pedido["order_date"] == "2026-02-25"
    assert pedido["total_brl"] == 8732.0
    assert pedido["items"] == [
        {"name": "Music Man Bass 1X Electric Bass", "quantity": 1}
    ]
    assert pedido["payment_type"] == "pix"
    assert pedido["installments"] is None
    assert pedido["tracking_code"] is None
    assert pedido["estimated_delivery"] is None
    assert pedido["delivery_message"] == "Pedido ainda não despachado."
    assert "email" not in repr(resultado).lower()
    assert "phone" not in repr(resultado).lower()
    print("\n[TESTE] Status do pedido: campos operacionais presentes; dados pessoais ausentes")


@pytest.mark.parametrize("order_id", [3, 20])
def test_pedidos_em_revisao_nao_expoem_total(
    banco_pedidos: Path, order_id: int
) -> None:
    email = {
        3: "isabela.moreira@jmail.com",
        20: "thiago.barbosa@jmail.com",
    }[order_id]
    orders.verificar_cliente(
        order_id=order_id,
        email=email,
        conversa_id="sessao-a",
    )

    resultado = orders.status_pedido(order_id=order_id, conversa_id="sessao-a")
    pedido = resultado["order"]

    assert resultado["status"] == "success"
    assert pedido["status"] in {"delivered", "cancelled"}
    assert pedido["tracking_code"] is not None if order_id == 3 else True
    assert pedido["total_message"] == "Valor em revisão; consulte nossa equipe."
    assert "total_brl" not in pedido
    print(f"\n[TESTE] Pedido {order_id}: total oculto, estado e rastreio preservados")


def test_pedido_shipped_informa_atraso_calculado_com_data_de_referencia(
    banco_pedidos: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("REFERENCE_DATETIME", "2026-03-23T10:00:00")
    orders.verificar_cliente(
        order_id=8,
        email="anacarol.ferreira@coldmail.com",
        conversa_id="sessao-a",
    )

    resultado = orders.status_pedido(order_id=8, conversa_id="sessao-a")
    pedido = resultado["order"]

    assert pedido["status"] == "shipped"
    assert pedido["estimated_delivery"] == "2026-02-28"
    assert pedido["delay_days"] == 23
    assert pedido["delivery_message"] == "Entrega em atraso há 23 dias."
    print("\n[TESTE] Pedido 8: atraso de 23 dias calculado a partir da data de referência")


def test_pedido_cancelado_informa_motivo(
    banco_pedidos: Path,
) -> None:
    orders.verificar_cliente(
        order_id=17,
        email="matheus.correia@hayoo.com.br",
        conversa_id="sessao-a",
    )

    resultado = orders.status_pedido(order_id=17, conversa_id="sessao-a")

    assert resultado["order"]["status"] == "cancelled"
    assert resultado["order"]["cancellation_reason"] == (
        "Pedido cancelado pelo cliente antes do processamento"
    )


def test_pedido_pending_sem_rastreio_nao_inventa_previsao(
    banco_pedidos: Path,
) -> None:
    orders.verificar_cliente(
        order_id=13,
        email="fernanda.ribeiro@coldmail.com",
        conversa_id="sessao-a",
    )

    resultado = orders.status_pedido(order_id=13, conversa_id="sessao-a")
    pedido = resultado["order"]

    assert pedido["status"] == "pending"
    assert pedido["tracking_code"] is None
    assert pedido["estimated_delivery"] is None
    assert pedido["delivery_message"] == "Pedido ainda não despachado."


def test_verificar_cliente_valida_argumentos_com_pydantic(
    banco_pedidos: Path,
) -> None:
    with pytest.raises(ValidationError):
        orders.verificar_cliente(
            order_id=0,
            email="cliente@exemplo.com",
            conversa_id="sessao-a",
        )
    with pytest.raises(ValidationError):
        orders.verificar_cliente(
            order_id=10,
            email="   ",
            conversa_id="sessao-a",
        )


def test_conversa_inexistente_nao_pode_verificar_cliente(
    banco_pedidos: Path,
) -> None:
    resultado = orders.verificar_cliente(
        order_id=10,
        email="bruno.martins@jmail.com",
        conversa_id="sessao-inexistente",
    )

    assert resultado["status"] != "verified"
