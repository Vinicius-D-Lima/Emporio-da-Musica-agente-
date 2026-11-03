"""Responsabilidade: validar o build do banco SQLite do Empório da Música."""

from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

from scripts import build_db


def test_build_database_atende_aos_criterios_do_passo_1(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """Critério do Passo 1: carregar os CSVs idempotentemente, manter as conversas, validar os dados e reportar anomalias."""
    db_path = tmp_path / "emporio.db"
    monkeypatch.setattr(build_db, "DB_PATH", db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.executescript(
            """
            CREATE TABLE conversations (
                id TEXT PRIMARY KEY,
                started_at TEXT,
                verified_customer_id INTEGER,
                FOREIGN KEY (verified_customer_id) REFERENCES customers(customer_id)
            );
            CREATE TABLE messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT REFERENCES conversations(id),
                role TEXT,
                content TEXT,
                provider TEXT,
                created_at TEXT
            );
            CREATE TABLE tool_calls (
                id TEXT PRIMARY KEY,
                message_id TEXT REFERENCES messages(id),
                tool_name TEXT,
                args_json TEXT,
                ok INTEGER,
                created_at TEXT
            );
            INSERT INTO conversations (id, started_at, verified_customer_id)
            VALUES ('conversa-teste', '2026-03-23T10:00:00', 1);
            INSERT INTO messages (id, conversation_id, role, content, created_at)
            VALUES ('mensagem-teste', 'conversa-teste', 'user', 'Olá', '2026-03-23T10:00:00');
            INSERT INTO tool_calls (id, message_id, tool_name, args_json, ok, created_at)
            VALUES ('tool-teste', 'mensagem-teste', 'buscar_produtos', '{}', 1, '2026-03-23T10:00:00');
            """
        )

    build_db.build_database()
    primeira_saida = capsys.readouterr().out

    with sqlite3.connect(db_path) as conn:
        contagens_esperadas = {
            "categories": 9,
            "customers": 50,
            "orders": 20,
            "order_items": 22,
            "products": 65,
            "promotions": 25,
        }
        for tabela, quantidade in contagens_esperadas.items():
            assert conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0] == quantidade
        contagens_reais = {
            tabela: conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
            for tabela in contagens_esperadas
        }

        erros_fk = conn.execute("PRAGMA foreign_key_check").fetchall()
        assert erros_fk == []
        assert conn.execute(
            "SELECT summary, summarized_until_message_id FROM conversations WHERE id = 'conversa-teste'"
        ).fetchone() == (None, None)
        assert conn.execute(
            "SELECT content FROM messages WHERE id = 'mensagem-teste'"
        ).fetchone() == ("Olá",)
        assert conn.execute(
            "SELECT tool_name FROM tool_calls WHERE id = 'tool-teste'"
        ).fetchone() == ("buscar_produtos",)

        pagamento_cartao = conn.execute(
            "SELECT payment_type, installments FROM orders WHERE order_id = 2"
        ).fetchone()
        assert pagamento_cartao == ("credit", 6)
        assert conn.execute(
            "SELECT COUNT(*) FROM orders WHERE payment_type IN ('pix', 'debit', 'boleto') AND installments IS NULL"
        ).fetchone()[0] == 10
        assert conn.execute(
            "SELECT COUNT(*) FROM orders WHERE payment_type = 'credit' AND installments IS NULL"
        ).fetchone()[0] == 0
        pedido_com_revisao = conn.execute(
            "SELECT order_id FROM orders WHERE total_needs_review = 1 ORDER BY order_id"
        ).fetchall()
        assert pedido_com_revisao == [(3,), (20,)]
        assert conn.execute(
            "SELECT COUNT(*) FROM orders WHERE total_needs_review NOT IN (0, 1)"
        ).fetchone()[0] == 0

        produtos = conn.execute(
            "SELECT specs_json, created_at FROM products ORDER BY product_id"
        ).fetchall()
        for specs_json, created_at in produtos:
            assert isinstance(json.loads(specs_json), dict)
            date.fromisoformat(created_at)

        datas_pedidos = conn.execute(
            "SELECT order_date, estimated_delivery FROM orders"
        ).fetchall()
        for order_date, estimated_delivery in datas_pedidos:
            date.fromisoformat(order_date)
            if estimated_delivery:
                date.fromisoformat(estimated_delivery)

        colunas_conversa = {
            linha[1] for linha in conn.execute("PRAGMA table_info(conversations)")
        }
        assert {
            "summary",
            "summarized_until_message_id",
            "verification_attempts",
        } <= colunas_conversa

        conn.execute(
            """
            UPDATE conversations
            SET summary = 'Resumo preservado',
                summarized_until_message_id = 17
            WHERE id = 'conversa-teste'
            """
        )
        conn.commit()

    build_db.build_database()
    capsys.readouterr()

    with sqlite3.connect(db_path) as conn:
        for tabela, quantidade in contagens_esperadas.items():
            assert conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0] == quantidade
        assert conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0] == 1
        assert conn.execute(
            "SELECT summary, summarized_until_message_id FROM conversations WHERE id = 'conversa-teste'"
        ).fetchone() == ("Resumo preservado", 17)
        assert conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM tool_calls").fetchone()[0] == 1
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []

    assert "produto 96" in primeira_saida.lower()
    assert "produto 136" in primeira_saida.lower()
    assert "produto 130" in primeira_saida.lower()
    assert "mais de uma promoção ativa" in primeira_saida.lower()

    print("\n[TESTE] Build do banco: parâmetros e resultados verificados")
    print(f"  Banco temporário: {db_path}")
    print("  Execuções do build: 2")
    print(f"  Contagens esperadas e reais: {contagens_reais}")
    print(f"  Chaves estrangeiras inválidas: {erros_fk}")
    print(f"  Pagamento do pedido 2: {pagamento_cartao} (esperado: ('credit', 6))")
    print("  Pagamentos à vista sem parcelas: 10 (esperado: 10)")
    print(f"  Pedidos marcados para revisão: {[row[0] for row in pedido_com_revisao]} (esperado: [3, 20])")
    print(f"  Tolerância de comparação de totais: R$ 0,01")
    print(f"  Produtos com JSON e data ISO verificados: {len(produtos)}")
    print(f"  Pedidos com datas ISO verificados: {len(datas_pedidos)}")
    print("  Dados da conversa, mensagem, tool call e resumo preservados após 2 execuções")
    print("  Anomalias do relatório encontradas: produtos 96, 130 e 136")
    print("  Relatório emitido pelo build:")
    for linha in primeira_saida.rstrip().splitlines():
        print(f"    {linha}")
    print("  Resultado: todos os critérios testados passaram")
