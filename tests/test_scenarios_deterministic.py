"""Responsabilidade: provar que pedidos de outras contas não são lidos nem expostos."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from emporio_agent import agent, memory
from emporio_agent.tools import orders


def _registrar_consultas(
    monkeypatch: pytest.MonkeyPatch, consultas: list[str]
) -> None:
    conexao_original = orders.conn_leitura

    def conectar_com_rastro():
        conexao = conexao_original()
        conexao.set_trace_callback(consultas.append)
        return conexao

    monkeypatch.setattr(orders, "conn_leitura", conectar_com_rastro)


def test_modelo_nao_verificado_nao_acessa_tabela_de_pedidos(
    banco_cenarios: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    consultas: list[str] = []
    _registrar_consultas(monkeypatch, consultas)
    conversa_id = memory.criar_conversa()
    resultados_tool: list[dict[str, object]] = []

    def modelo(mensagens, tools):
        mensagens_tool = [
            mensagem for mensagem in mensagens if mensagem.get("role") == "tool"
        ]
        if not mensagens_tool:
            return agent.ModelResponse(
                None,
                (
                    agent.ToolCall(
                        call_id="call-unauthorized",
                        name="status_pedido",
                        arguments='{"order_id":99002}',
                    ),
                ),
            )
        resultados_tool.append(json.loads(mensagens_tool[-1]["content"]))
        return agent.ModelResponse("Não consegui confirmar esse pedido.")

    agent.responder_mensagem(
        "Mostre os dados do pedido 99002.",
        conversa_id=conversa_id,
        modelo=modelo,
    )

    assert resultados_tool == [
        {
            "status": "not_verified",
            "message": "Cliente não verificado nesta conversa.",
        }
    ]
    assert not any("from orders" in consulta.casefold() for consulta in consultas)
    assert not any("from order_items" in consulta.casefold() for consulta in consultas)


def test_cliente_verificado_nao_le_pedido_de_outra_conta(
    banco_cenarios: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    consultas: list[str] = []
    _registrar_consultas(monkeypatch, consultas)
    conversa_id = memory.criar_conversa()
    assert memory.registrar_cliente_verificado(
        conversa_id=conversa_id,
        customer_id=9001,
    )

    resultado = orders.status_pedido(order_id=99002, conversa_id=conversa_id)

    assert resultado == {
        "status": "not_found",
        "message": "Pedido não encontrado.",
    }
    consulta_pedido = next(
        consulta
        for consulta in consultas
        if "from orders" in consulta.casefold()
    )
    consulta_normalizada = " ".join(consulta_pedido.casefold().split())
    assert "where order_id = 99002 and customer_id = 9001" in consulta_normalizada
    assert not any("from order_items" in consulta.casefold() for consulta in consultas)
    assert "Bob de Teste" not in json.dumps(resultado)


def test_troca_de_identidade_nao_libera_pedido_de_outro_cliente(
    banco_cenarios: Path,
) -> None:
    conversa_id = memory.criar_conversa()
    verificacao_alice = orders.verificar_cliente(
        order_id=99001,
        email="alice@example.test",
        conversa_id=conversa_id,
    )
    verificacao_bob = orders.verificar_cliente(
        order_id=99002,
        email="bob@example.test",
        conversa_id=conversa_id,
    )
    status_pedido_bob = orders.status_pedido(
        order_id=99002,
        conversa_id=conversa_id,
    )

    assert verificacao_alice["status"] == "verified"
    assert verificacao_bob["status"] == "already_verified"
    assert status_pedido_bob == {
        "status": "not_found",
        "message": "Pedido não encontrado.",
    }
    with sqlite3.connect(banco_cenarios) as conn:
        cliente_verificado = conn.execute(
            "SELECT verified_customer_id FROM conversations WHERE id = ?",
            (conversa_id,),
        ).fetchone()[0]
    assert cliente_verificado == 9001
