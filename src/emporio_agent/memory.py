"""Responsabilidade: persistir conversas, mensagens e tool calls no SQLite do agente."""

from __future__ import annotations

from .db import conn_escrita


def registrar_mensagem(*, conversa_id: str, role: str, content: str, provider: str | None = None) -> str:
    """Registra uma mensagem do usuário ou do assistente no histórico da conversa."""
    raise NotImplementedError("A persistência de memória será implementada em um passo posterior.")
