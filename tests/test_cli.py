"""Responsabilidade: validar a interface de terminal sem chamadas externas."""

from __future__ import annotations

import contextlib
import io
import re
import sqlite3
from pathlib import Path

import pytest

from emporio_agent import agent, cli, db, llm, memory
from scripts import build_db


@pytest.fixture
def banco_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "emporio-cli.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(build_db, "DB_PATH", db_path)
    with contextlib.redirect_stdout(io.StringIO()):
        build_db.build_database()
    return db_path


def test_cli_interativa_cria_conversa_persistente_e_processa_varias_mensagens(
    banco_cli: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    mensagens = iter(["Olá", "Quais promoções?", "/sair"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(mensagens))
    chamadas: list[tuple[str, bool]] = []
    respostas_modelo: list[str] = []

    def modelo(mensagens, tools):
        texto = f"Resposta {len(respostas_modelo) + 1}"
        respostas_modelo.append(texto)
        return agent.ModelResponse(texto)

    responder_original = agent.responder_mensagem

    def registrar_chamada(mensagem, **kwargs):
        chamadas.append((kwargs["conversa_id"], kwargs["debug"]))
        return responder_original(mensagem, **kwargs)

    monkeypatch.setattr(cli.agent, "responder_mensagem", registrar_chamada)

    assert cli.main(["--debug"], modelo=modelo) == 0
    saida = capsys.readouterr()

    conversa_id = re.search(r"Conversa: ([0-9a-f]+)", saida.out).group(1)
    assert chamadas == [(conversa_id, True), (conversa_id, True)]
    assert "Empório: Resposta 1" in saida.out
    assert "Empório: Resposta 2" in saida.out
    assert "/sair" in saida.out
    with sqlite3.connect(banco_cli) as conn:
        roles = conn.execute(
            """
            SELECT role FROM messages
            WHERE conversation_id = ?
            ORDER BY rowid
            """,
            (conversa_id,),
        ).fetchall()
    assert [role for (role,) in roles] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]


def test_cli_reutiliza_conversa_informada(
    banco_cli: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    conversa_id = memory.criar_conversa()
    monkeypatch.setattr("builtins.input", lambda prompt: "/sair")

    assert (
        cli.main(
            ["--conversa", conversa_id],
            modelo=lambda mensagens, tools: agent.ModelResponse("Resposta"),
        )
        == 0
    )

    saida = capsys.readouterr()
    assert f"Conversa: {conversa_id}" in saida.out
    assert "Digite /sair para encerrar." in saida.out


def test_cli_rejeita_conversa_inexistente(
    banco_cli: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["--conversa", "inexistente"]) == 1

    saida = capsys.readouterr()
    assert saida.out == ""
    assert "Conversa não encontrada" in saida.err


def test_cli_ctrl_c_durante_resposta_encerra_sem_traceback(
    banco_cli: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("builtins.input", lambda prompt: "Olá")

    def modelo(mensagens, tools):
        raise KeyboardInterrupt

    assert cli.main([], modelo=modelo) == 0

    saida = capsys.readouterr()
    assert "Conversa encerrada." in saida.out
    assert saida.err == ""


def test_cli_informa_quando_provedor_llm_nao_esta_configurado(
    banco_cli: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def sem_chave():
        raise ValueError("GEMINI_API_KEY ausente")

    monkeypatch.setattr(cli.llm, "criar_modelo", sem_chave)

    assert cli.main([]) == 1

    saida = capsys.readouterr()
    assert "GEMINI_API_KEY ausente" in saida.err
    assert saida.out == ""


def test_cli_apresenta_falha_do_provedor_sem_traceback(
    banco_cli: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("builtins.input", lambda prompt: "Olá")

    def modelo(mensagens, tools):
        raise llm.LLMError("Falha ao chamar o provedor LLM 'gemini' (HTTP 503).")

    assert cli.main([], modelo=modelo) == 1

    saida = capsys.readouterr()
    assert "HTTP 503" in saida.err
    assert saida.out.startswith("Conversa: ")
    with sqlite3.connect(banco_cli) as conn:
        assert conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0] == 1
        assert conn.execute(
            "SELECT role, content FROM messages"
        ).fetchone() == ("user", "Olá")
