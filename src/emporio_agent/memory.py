"""Responsabilidade: persistir conversas, mensagens e tool calls no SQLite do agente."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from contextlib import closing
from typing import TypedDict
from uuid import uuid4

from .config import agora
from .db import conn_escrita

_VALID_ROLES = frozenset({"user", "assistant", "tool"})
_MAX_UNSUMMARIZED_MESSAGES = 20
_RECENT_MESSAGES = 10
_SENSITIVE_ARGUMENT_KEYS = frozenset(
    {"email", "phone", "telefone", "celular", "mobile"}
)
_EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_PHONE_PATTERN = re.compile(
    r"(?<!\w)(?:\+?55\s*)?(?:\(\d{2}\)\s*|\d{2}\s)\d{4,5}[-.\s]\d{4}(?!\w)"
    r"|(?<!\d)(?:\+?55)?\d{10,11}(?!\d)"
)


class MessageForSummary(TypedDict):
    role: str
    content: str


class HistoryMessage(TypedDict):
    id: str
    role: str
    content: str
    provider: str | None


class ConversationHistory(TypedDict):
    summary: str | None
    messages: list[HistoryMessage]


def _redigir_conteudo(texto: str) -> str:
    texto = _EMAIL_PATTERN.sub("[REDACTED]", texto)
    return _PHONE_PATTERN.sub("[REDACTED]", texto)


def criar_conversa(*, conversa_id: str | None = None) -> str:
    """Cria uma conversa persistida e retorna seu identificador."""
    identificador = uuid4().hex if conversa_id is None else conversa_id
    if not identificador.strip():
        raise ValueError("O identificador da conversa não pode ser vazio.")

    with closing(conn_escrita()) as conn, conn:
        conn.execute(
            "INSERT INTO conversations (id, started_at) VALUES (?, ?)",
            (identificador, agora().isoformat(timespec="seconds")),
        )
    return identificador


def registrar_mensagem(
    *,
    conversa_id: str,
    role: str,
    content: str,
    provider: str | None = None,
) -> str:
    """Registra uma mensagem do usuário, assistente ou resultado de tool."""
    if role not in _VALID_ROLES:
        raise ValueError(f"role inválido: {role!r}.")
    if not isinstance(content, str):
        raise TypeError("O conteúdo da mensagem precisa ser texto.")

    mensagem_id = uuid4().hex
    with closing(conn_escrita()) as conn, conn:
        conversa = conn.execute(
            "SELECT 1 FROM conversations WHERE id = ?", (conversa_id,)
        ).fetchone()
        if conversa is None:
            raise ValueError(f"Conversa não encontrada: {conversa_id!r}.")
        conn.execute(
            """
            INSERT INTO messages (id, conversation_id, role, content, provider, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                mensagem_id,
                conversa_id,
                role,
                _redigir_conteudo(content),
                provider,
                agora().isoformat(timespec="seconds"),
            ),
        )
    return mensagem_id


def _redigir_argumentos(valor: object, *, chave: str | None = None) -> object:
    if chave is not None:
        chave_normalizada = re.sub(r"[^a-z]", "", chave.casefold())
        if any(chave_normalizada.endswith(campo) for campo in _SENSITIVE_ARGUMENT_KEYS):
            return "[REDACTED]"
    if isinstance(valor, Mapping):
        return {
            str(chave_filha): _redigir_argumentos(valor_filho, chave=str(chave_filha))
            for chave_filha, valor_filho in valor.items()
        }
    if isinstance(valor, list):
        return [_redigir_argumentos(item) for item in valor]
    if isinstance(valor, tuple):
        return [_redigir_argumentos(item) for item in valor]
    if isinstance(valor, str):
        return _redigir_conteudo(valor)
    return valor


def registrar_chamada_tool(
    *,
    mensagem_id: str,
    tool_name: str,
    argumentos: Mapping[str, object],
    ok: bool,
) -> str:
    """Persiste uma chamada de tool, redigindo campos de e-mail e telefone."""
    if not tool_name.strip():
        raise ValueError("O nome da tool não pode ser vazio.")
    if not isinstance(argumentos, Mapping):
        raise TypeError("Os argumentos da tool precisam ser um objeto.")
    if not isinstance(ok, bool):
        raise TypeError("O resultado da tool precisa ser booleano.")

    chamada_id = uuid4().hex
    args_json = json.dumps(
        _redigir_argumentos(argumentos),
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
    )
    with closing(conn_escrita()) as conn, conn:
        mensagem = conn.execute(
            "SELECT role FROM messages WHERE id = ?", (mensagem_id,)
        ).fetchone()
        if mensagem is None or mensagem["role"] != "assistant":
            raise ValueError(
                "A chamada de tool precisa pertencer a uma mensagem do assistente."
            )
        conn.execute(
            """
            INSERT INTO tool_calls (id, message_id, tool_name, args_json, ok, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                chamada_id,
                mensagem_id,
                tool_name,
                args_json,
                int(ok),
                agora().isoformat(timespec="seconds"),
            ),
        )
    return chamada_id


def recuperar_historico(*, conversa_id: str) -> ConversationHistory:
    """Retorna o resumo e as mensagens ainda não incorporadas a ele."""
    with closing(conn_escrita()) as conn:
        conversa = conn.execute(
            """
            SELECT summary, summarized_until_message_id
            FROM conversations
            WHERE id = ?
            """,
            (conversa_id,),
        ).fetchone()
        if conversa is None:
            raise ValueError(f"Conversa não encontrada: {conversa_id!r}.")

        limite_id = conversa["summarized_until_message_id"]
        if limite_id is None:
            linhas = conn.execute(
                """
                SELECT id, role, content, provider
                FROM messages
                WHERE conversation_id = ?
                ORDER BY rowid
                """,
                (conversa_id,),
            ).fetchall()
        else:
            limite = conn.execute(
                "SELECT rowid FROM messages WHERE id = ? AND conversation_id = ?",
                (limite_id, conversa_id),
            ).fetchone()
            if limite is None:
                raise RuntimeError(
                    "O limite do resumo não aponta para uma mensagem existente."
                )
            linhas = conn.execute(
                """
                SELECT id, role, content, provider
                FROM messages
                WHERE conversation_id = ? AND rowid > ?
                ORDER BY rowid
                """,
                (conversa_id, limite["rowid"]),
            ).fetchall()

    return {
        "summary": (
            _redigir_conteudo(conversa["summary"])
            if conversa["summary"] is not None
            else None
        ),
        "messages": [
            {
                "id": linha["id"],
                "role": linha["role"],
                "content": _redigir_conteudo(linha["content"]),
                "provider": linha["provider"],
            }
            for linha in linhas
        ],
    }


def resumir_historico(
    *,
    conversa_id: str,
    resumidor: Callable[[str | None, list[MessageForSummary]], str],
) -> bool:
    """Resume mensagens antigas, preservando as dez mais recentes sem alterá-las."""
    with closing(conn_escrita()) as conn:
        conversa = conn.execute(
            """
            SELECT summary, summarized_until_message_id
            FROM conversations
            WHERE id = ?
            """,
            (conversa_id,),
        ).fetchone()
        if conversa is None:
            raise ValueError(f"Conversa não encontrada: {conversa_id!r}.")

        limite_id = conversa["summarized_until_message_id"]
        if limite_id is None:
            linhas = conn.execute(
                """
                SELECT id, role, content
                FROM messages
                WHERE conversation_id = ?
                ORDER BY rowid
                """,
                (conversa_id,),
            ).fetchall()
        else:
            limite = conn.execute(
                "SELECT rowid FROM messages WHERE id = ? AND conversation_id = ?",
                (limite_id, conversa_id),
            ).fetchone()
            if limite is None:
                raise RuntimeError(
                    "O limite do resumo não aponta para uma mensagem existente."
                )
            linhas = conn.execute(
                """
                SELECT id, role, content
                FROM messages
                WHERE conversation_id = ? AND rowid > ?
                ORDER BY rowid
                """,
                (conversa_id, limite["rowid"]),
            ).fetchall()

    if len(linhas) <= _MAX_UNSUMMARIZED_MESSAGES:
        return False

    quantidade_a_resumir = len(linhas) - _RECENT_MESSAGES
    mensagens_a_resumir: list[MessageForSummary] = [
        {
            "role": linha["role"],
            "content": _redigir_conteudo(linha["content"]),
        }
        for linha in linhas[:quantidade_a_resumir]
    ]
    resumo_anterior = conversa["summary"]
    if resumo_anterior is not None:
        resumo_anterior = _redigir_conteudo(resumo_anterior)
    novo_resumo = resumidor(resumo_anterior, mensagens_a_resumir)
    if not isinstance(novo_resumo, str) or not novo_resumo.strip():
        raise ValueError("O resumidor precisa retornar um resumo textual não vazio.")
    novo_resumo = _redigir_conteudo(novo_resumo.strip())

    novo_limite_id = linhas[quantidade_a_resumir - 1]["id"]
    with closing(conn_escrita()) as conn, conn:
        cursor = conn.execute(
            """
            UPDATE conversations
            SET summary = ?, summarized_until_message_id = ?
            WHERE id = ?
              AND summary IS ?
              AND summarized_until_message_id IS ?
            """,
            (
                novo_resumo.strip(),
                novo_limite_id,
                conversa_id,
                conversa["summary"],
                limite_id,
            ),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("O histórico mudou durante a geração do resumo.")
    return True


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
