"""Responsabilidade: validar persistência, isolamento e resumo do histórico de conversas."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pytest

from emporio_agent import db, memory


@pytest.fixture
def banco_memoria(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "memoria.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    schema = Path(db.__file__).with_name("schema.sql").read_text(encoding="utf-8")
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema)
    return db_path


def test_criar_conversa_e_registrar_mensagens_em_ordem(
    banco_memoria: Path,
) -> None:
    conversa_id = memory.criar_conversa()
    usuario_id = memory.registrar_mensagem(
        conversa_id=conversa_id, role="user", content="Olá"
    )
    assistente_id = memory.registrar_mensagem(
        conversa_id=conversa_id,
        role="assistant",
        content="Como posso ajudar?",
        provider="gemini",
    )

    historico = memory.recuperar_historico(conversa_id=conversa_id)

    assert historico == {
        "summary": None,
        "messages": [
            {"id": usuario_id, "role": "user", "content": "Olá", "provider": None},
            {
                "id": assistente_id,
                "role": "assistant",
                "content": "Como posso ajudar?",
                "provider": "gemini",
            },
        ],
    }


def test_historico_isola_conversas_e_nao_retorna_argumentos_de_tools(
    banco_memoria: Path,
) -> None:
    conversa_a = memory.criar_conversa()
    conversa_b = memory.criar_conversa()
    mensagem_id = memory.registrar_mensagem(
        conversa_id=conversa_a, role="assistant", content="Verificando."
    )
    memory.registrar_mensagem(
        conversa_id=conversa_b, role="user", content="Outra conversa."
    )
    memory.registrar_chamada_tool(
        mensagem_id=mensagem_id,
        tool_name="verificar_cliente",
        argumentos={
            "order_id": 10,
            "email": "cliente@exemplo.com",
            "nested": {"telefone": "(67) 99999-0000"},
        },
        ok=False,
    )

    historico = memory.recuperar_historico(conversa_id=conversa_a)
    with sqlite3.connect(banco_memoria) as conn:
        args_json, ok = conn.execute(
            "SELECT args_json, ok FROM tool_calls"
        ).fetchone()

    assert [item["content"] for item in historico["messages"]] == ["Verificando."]
    assert historico["messages"][0]["id"] == mensagem_id
    assert json.loads(args_json) == {
        "email": "[REDACTED]",
        "nested": {"telefone": "[REDACTED]"},
        "order_id": 10,
    }
    assert ok == 0


def test_registrar_mensagem_valida_conversa_e_papel(banco_memoria: Path) -> None:
    with pytest.raises(ValueError, match=re.compile("conversa", re.IGNORECASE)):
        memory.registrar_mensagem(
            conversa_id="inexistente", role="user", content="Olá"
        )

    conversa_id = memory.criar_conversa()
    with pytest.raises(ValueError, match="role"):
        memory.registrar_mensagem(
            conversa_id=conversa_id, role="admin", content="Olá"
        )


def test_mensagens_redigem_email_e_telefone(banco_memoria: Path) -> None:
    conversa_id = memory.criar_conversa()
    memory.registrar_mensagem(
        conversa_id=conversa_id,
        role="user",
        content="Meu e-mail é cliente@exemplo.com e meu telefone é (67) 99999-0000.",
    )

    historico = memory.recuperar_historico(conversa_id=conversa_id)
    conteudo = historico["messages"][0]["content"]
    with sqlite3.connect(banco_memoria) as conn:
        conteudo_persistido = conn.execute(
            "SELECT content FROM messages WHERE conversation_id = ?",
            (conversa_id,),
        ).fetchone()[0]

    assert "cliente@exemplo.com" not in conteudo
    assert "(67) 99999-0000" not in conteudo
    assert conteudo.count("[REDACTED]") == 2
    assert conteudo_persistido == conteudo


def test_resumidor_recebe_conteudo_herdado_com_pii_redigida(
    banco_memoria: Path,
) -> None:
    conversa_id = memory.criar_conversa()
    with sqlite3.connect(banco_memoria) as conn:
        conn.executemany(
            """
            INSERT INTO messages (id, conversation_id, role, content, created_at)
            VALUES (?, ?, 'user', ?, ?)
            """,
            [
                (
                    f"antiga-{i}",
                    conversa_id,
                    "contato cliente@exemplo.com, telefone (67) 99999-0000"
                    if i == 0
                    else f"mensagem-{i}",
                    "2026-03-23T10:00:00",
                )
                for i in range(21)
            ],
        )

    recebido: list[str] = []
    memory.resumir_historico(
        conversa_id=conversa_id,
        resumidor=lambda resumo, mensagens: (
            recebido.extend(msg["content"] for msg in mensagens) or "Resumo."
        ),
    )

    assert "cliente@exemplo.com" not in recebido[0]
    assert "(67) 99999-0000" not in recebido[0]


def test_resumo_mantem_mensagens_recentes_e_registra_limite(
    banco_memoria: Path,
) -> None:
    conversa_id = memory.criar_conversa()
    ids = [
        memory.registrar_mensagem(
            conversa_id=conversa_id, role="user", content=f"mensagem-{i}"
        )
        for i in range(25)
    ]
    chamada: dict[str, object] = {}

    def resumidor(
        resumo_anterior: str | None, mensagens: list[dict[str, str]]
    ) -> str:
        chamada["resumo_anterior"] = resumo_anterior
        chamada["mensagens"] = mensagens
        return "Resumo das primeiras mensagens."

    atualizou = memory.resumir_historico(
        conversa_id=conversa_id, resumidor=resumidor
    )
    historico = memory.recuperar_historico(conversa_id=conversa_id)

    assert atualizou is True
    assert chamada["resumo_anterior"] is None
    assert len(chamada["mensagens"]) == 15
    assert historico["summary"] == "Resumo das primeiras mensagens."
    assert historico["messages"][0]["id"] == ids[15]
    assert len(historico["messages"]) == 10
    with sqlite3.connect(banco_memoria) as conn:
        limite = conn.execute(
            "SELECT summarized_until_message_id FROM conversations WHERE id = ?",
            (conversa_id,),
        ).fetchone()[0]
    assert limite == ids[14]


def test_resumidor_com_falha_nao_descarta_historico(
    banco_memoria: Path,
) -> None:
    conversa_id = memory.criar_conversa()
    for i in range(21):
        memory.registrar_mensagem(
            conversa_id=conversa_id, role="user", content=f"mensagem-{i}"
        )

    def resumidor(
        resumo_anterior: str | None, mensagens: list[dict[str, str]]
    ) -> str:
        raise RuntimeError("provedor indisponível")

    with pytest.raises(RuntimeError, match="provedor indisponível"):
        memory.resumir_historico(conversa_id=conversa_id, resumidor=resumidor)

    historico = memory.recuperar_historico(conversa_id=conversa_id)
    assert historico["summary"] is None
    assert len(historico["messages"]) == 21


def test_resumos_sequenciais_incorporam_resumo_anterior(
    banco_memoria: Path,
) -> None:
    conversa_id = memory.criar_conversa()
    for i in range(21):
        memory.registrar_mensagem(
            conversa_id=conversa_id, role="user", content=f"mensagem-{i}"
        )

    assert memory.resumir_historico(
        conversa_id=conversa_id,
        resumidor=lambda resumo, mensagens: "Resumo inicial.",
    )
    for i in range(21, 32):
        memory.registrar_mensagem(
            conversa_id=conversa_id, role="user", content=f"mensagem-{i}"
        )

    anteriores: list[str | None] = []
    assert memory.resumir_historico(
        conversa_id=conversa_id,
        resumidor=lambda resumo, mensagens: (
            anteriores.append(resumo) or "Resumo atualizado."
        ),
    )

    historico = memory.recuperar_historico(conversa_id=conversa_id)
    assert anteriores == ["Resumo inicial."]
    assert historico["summary"] == "Resumo atualizado."
    assert [item["content"] for item in historico["messages"]] == [
        f"mensagem-{i}" for i in range(22, 32)
    ]
