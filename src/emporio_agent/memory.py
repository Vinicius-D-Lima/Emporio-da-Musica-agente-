"""Responsabilidade: persistir conversas, mensagens e tool calls no SQLite do agente."""

from __future__ import annotations

from contextlib import closing

from .db import conn_escrita


def registrar_mensagem(*, conversa_id: str, role: str, content: str, provider: str | None = None) -> str:
    """Registra uma mensagem do usuário ou do assistente no histórico da conversa."""
    raise NotImplementedError("A persistência de memória será implementada em um passo posterior.")


def registrar_cliente_verificado(*, conversa_id: str, customer_id: int) -> bool:
    """Associa uma identidade verificada à conversa sem permitir substituição posterior."""
    with closing(conn_escrita()) as conn, conn:
        cursor = conn.execute(
            """
            UPDATE conversations
            SET verified_customer_id = ?, verification_attempts = 0
            WHERE id = ? AND verified_customer_id IS NULL
            """,
            (customer_id, conversa_id),
        )
        return cursor.rowcount == 1


def registrar_tentativa_verificacao(*, conversa_id: str) -> int | None:
    """Incrementa atomicamente tentativas de uma conversa não verificada."""
    with closing(conn_escrita()) as conn, conn:
        cursor = conn.execute(
            """
            UPDATE conversations
            SET verification_attempts = verification_attempts + 1
            WHERE id = ? AND verified_customer_id IS NULL
            """,
            (conversa_id,),
        )
        if cursor.rowcount != 1:
            return None

        linha = conn.execute(
            "SELECT verification_attempts FROM conversations WHERE id = ?",
            (conversa_id,),
        ).fetchone()
        return linha["verification_attempts"]
