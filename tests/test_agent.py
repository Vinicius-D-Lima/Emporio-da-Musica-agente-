"""Responsabilidade: cobrir o loop do agente e o function calling sem chamadas externas."""

from __future__ import annotations

import contextlib
import io
import json
import sqlite3
from pathlib import Path

import pytest

from emporio_agent import agent, db, llm, memory
from scripts import build_db


@pytest.fixture
def banco_agente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "emporio-agente.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(build_db, "DB_PATH", db_path)
    with contextlib.redirect_stdout(io.StringIO()):
        build_db.build_database()
    return db_path


def _tool_call(
    name: str, arguments: dict[str, object], *, call_id: str = "call-1"
) -> agent.ToolCall:
    return agent.ToolCall(
        call_id=call_id,
        name=name,
        arguments=json.dumps(arguments),
    )


def test_registry_exports_all_tools_with_json_schemas() -> None:
    definitions = agent.get_tool_definitions()

    assert [item["function"]["name"] for item in definitions] == [
        "buscar_produtos",
        "detalhes_produto",
        "promocoes_ativas",
        "simular_parcelamento",
        "verificar_cliente",
        "status_pedido",
    ]
    for definition in definitions:
        function = definition["function"]
        assert function["parameters"]["type"] == "object"
        assert function["parameters"]["additionalProperties"] is False

    schema_status = definitions[-1]["function"]["parameters"]
    assert "conversa_id" not in schema_status["properties"]


def test_resposta_final_e_mensagens_ficam_persistidas(
    banco_agente: Path,
) -> None:
    conversa_id = memory.criar_conversa()
    chamadas: list[tuple[list[dict[str, object]], list[dict[str, object]]]] = []

    def modelo(mensagens, tools):
        chamadas.append((list(mensagens), list(tools)))
        return agent.ModelResponse("Olá! Como posso ajudar?", provider="gemini")

    resposta = agent.responder_mensagem(
        "Oi!", conversa_id=conversa_id, modelo=modelo
    )
    historico = memory.recuperar_historico(conversa_id=conversa_id)

    assert resposta == "Olá! Como posso ajudar?"
    assert len(chamadas) == 1
    assert len(chamadas[0][1]) == 6
    assert [item["role"] for item in historico["messages"]] == ["user", "assistant"]
    assert historico["messages"][-1]["content"] == resposta
    assert historico["messages"][-1]["provider"] == "gemini"


def test_sem_modelo_injetado_usa_o_provedor_configurado(
    banco_agente: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def modelo(mensagens, tools):
        return agent.ModelResponse("Resposta do provedor configurado.")

    monkeypatch.setattr(llm, "criar_modelo", lambda: modelo)

    resposta = agent.responder_mensagem("Olá")

    assert resposta == "Resposta do provedor configurado."


def test_function_call_executa_tool_e_devolve_resultado_ao_modelo(
    banco_agente: Path,
) -> None:
    conversa_id = memory.criar_conversa()
    requests: list[list[dict[str, object]]] = []

    def modelo(mensagens, tools):
        requests.append(list(mensagens))
        if len(requests) == 1:
            assert len(tools) == 6
            return agent.ModelResponse(
                None,
                (
                    agent.ToolCall(
                        call_id="call-1",
                        name="buscar_produtos",
                        arguments='{"query":"gd20"}',
                        provider_metadata={
                            "google": {"thought_signature": "c2lnbmF0dXJl"}
                        },
                    ),
                ),
                provider="groq",
            )
        assert tools
        assistant_message = next(
            item for item in requests[-1] if item["role"] == "assistant"
        )
        assert assistant_message["tool_calls"][0]["extra_content"] == {
            "google": {"thought_signature": "c2lnbmF0dXJl"}
        }
        tool_message = requests[-1][-1]
        assert tool_message["role"] == "tool"
        assert tool_message["tool_call_id"] == "call-1"
        resultado = json.loads(tool_message["content"])
        assert resultado["products"][0]["product_id"] == 95
        return agent.ModelResponse(
            "Encontrei o violão Takamine GD20.",
            provider="groq",
        )

    resposta = agent.responder_mensagem(
        "Vocês têm o GD20?", conversa_id=conversa_id, modelo=modelo
    )
    historico = memory.recuperar_historico(conversa_id=conversa_id)
    with sqlite3.connect(banco_agente) as conn:
        nome_tool, argumentos_json, sucesso = conn.execute(
            "SELECT tool_name, args_json, ok FROM tool_calls"
        ).fetchone()

    assert resposta == "Encontrei o violão Takamine GD20."
    assert nome_tool == "buscar_produtos"
    assert json.loads(argumentos_json) == {"query": "gd20"}
    assert sucesso == 1
    assert [item["role"] for item in historico["messages"]] == [
        "user",
        "assistant",
        "assistant",
    ]
    assert "thought_signature" not in json.dumps(historico)


def test_erro_de_validacao_e_repassado_sem_valores_informados(
    banco_agente: Path,
) -> None:
    conversa_id = memory.criar_conversa()
    requests: list[list[dict[str, object]]] = []

    def modelo(mensagens, tools):
        requests.append(list(mensagens))
        if len(requests) == 1:
            return agent.ModelResponse(
                None,
                (
                    _tool_call(
                        "verificar_cliente",
                        {
                            "order_id": 10,
                            "email": "cliente@exemplo.com",
                            "conversa_id": "sessao-de-outra-pessoa",
                        },
                    ),
                ),
            )
        resultado = json.loads(requests[-1][-1]["content"])
        assert resultado["status"] == "error"
        assert resultado["error"]["code"] == "invalid_arguments"
        assert "cliente@exemplo.com" not in json.dumps(resultado)
        assert "sessao-de-outra-pessoa" not in json.dumps(resultado)
        return agent.ModelResponse("Não consegui validar a solicitação.")

    resposta = agent.responder_mensagem(
        "Verifique meu pedido.", conversa_id=conversa_id, modelo=modelo
    )

    assert resposta == "Não consegui validar a solicitação."
    with sqlite3.connect(banco_agente) as conn:
        args_json, sucesso = conn.execute(
            "SELECT args_json, ok FROM tool_calls"
        ).fetchone()
    assert json.loads(args_json) == {
        "conversa_id": "sessao-de-outra-pessoa",
        "email": "[REDACTED]",
        "order_id": 10,
    }
    assert sucesso == 0


def test_tool_desconhecida_retorna_erro_estruturado_e_nao_interrompe_loop(
    banco_agente: Path,
) -> None:
    conversa_id = memory.criar_conversa()
    requests: list[list[dict[str, object]]] = []

    def modelo(mensagens, tools):
        requests.append(list(mensagens))
        if len(requests) == 1:
            return agent.ModelResponse(
                None,
                (agent.ToolCall("call-unknown", "buscar_cliente", "{}"),),
            )
        erro = json.loads(requests[-1][-1]["content"])
        assert erro["error"]["code"] == "unknown_tool"
        return agent.ModelResponse("Essa consulta não está disponível.")

    resposta = agent.responder_mensagem(
        "Consulte meu cliente.", conversa_id=conversa_id, modelo=modelo
    )

    assert resposta == "Essa consulta não está disponível."
    with sqlite3.connect(banco_agente) as conn:
        assert conn.execute("SELECT ok FROM tool_calls").fetchone()[0] == 0


def test_contexto_de_conversa_e_injetado_em_tools_de_pedido(
    banco_agente: Path,
) -> None:
    conversa_id = memory.criar_conversa()
    requests: list[list[dict[str, object]]] = []

    def modelo(mensagens, tools):
        requests.append(list(mensagens))
        if len(requests) == 1:
            return agent.ModelResponse(
                None,
                (
                    _tool_call(
                        "verificar_cliente",
                        {
                            "order_id": 10,
                            "email": "bruno.martins@jmail.com",
                        },
                    ),
                ),
            )
        if len(requests) == 2:
            verificacao = json.loads(requests[-1][-1]["content"])
            assert verificacao["status"] == "verified"
            return agent.ModelResponse(
                None,
                (_tool_call("status_pedido", {"order_id": 10}, call_id="call-2"),),
            )
        consulta = json.loads(requests[-1][-1]["content"])
        assert consulta["status"] == "success"
        assert consulta["order"]["order_id"] == 10
        return agent.ModelResponse("O pedido foi localizado.")

    resposta = agent.responder_mensagem(
        "Quero consultar o pedido 10.",
        conversa_id=conversa_id,
        modelo=modelo,
    )

    assert resposta == "O pedido foi localizado."
    with sqlite3.connect(banco_agente) as conn:
        chamadas = conn.execute(
            "SELECT tool_name, args_json FROM tool_calls ORDER BY rowid"
        ).fetchall()
        cliente_verificado = conn.execute(
            "SELECT verified_customer_id FROM conversations WHERE id = ?",
            (conversa_id,),
        ).fetchone()[0]
    assert [nome for nome, _ in chamadas] == ["verificar_cliente", "status_pedido"]
    assert "conversa_id" not in json.loads(chamadas[0][1])
    assert json.loads(chamadas[0][1])["email"] == "[REDACTED]"
    assert json.loads(chamadas[1][1]) == {"order_id": 10}
    assert cliente_verificado == 11


def test_json_invalido_de_tool_retorna_erro_estruturado(
    banco_agente: Path,
) -> None:
    conversa_id = memory.criar_conversa()
    requests: list[list[dict[str, object]]] = []

    def modelo(mensagens, tools):
        requests.append(list(mensagens))
        if len(requests) == 1:
            return agent.ModelResponse(
                None,
                (agent.ToolCall("call-bad-json", "buscar_produtos", "{"),),
            )
        erro = json.loads(requests[-1][-1]["content"])
        assert erro["error"]["code"] == "invalid_arguments"
        return agent.ModelResponse("Não consegui interpretar a consulta.")

    assert (
        agent.responder_mensagem(
            "Busque um produto.",
            conversa_id=conversa_id,
            modelo=modelo,
        )
        == "Não consegui interpretar a consulta."
    )
    with sqlite3.connect(banco_agente) as conn:
        argumentos, sucesso = conn.execute(
            "SELECT args_json, ok FROM tool_calls"
        ).fetchone()
    assert json.loads(argumentos) == {"_invalid_arguments": "invalid_json"}
    assert sucesso == 0


@pytest.mark.parametrize("argumentos", ['{"valor": NaN}', '{"valor": 1e999}'])
def test_argumentos_json_nao_finitos_sao_rejeitados_com_seguranca(
    banco_agente: Path, argumentos: str
) -> None:
    conversa_id = memory.criar_conversa()
    requests: list[list[dict[str, object]]] = []

    def modelo(mensagens, tools):
        requests.append(list(mensagens))
        if len(requests) == 1:
            return agent.ModelResponse(
                None,
                (
                    agent.ToolCall(
                        "call-non-finite",
                        "simular_parcelamento",
                        argumentos,
                    ),
                ),
            )
        assert json.loads(requests[-1][-1]["content"])["error"]["code"] == (
            "invalid_arguments"
        )
        return agent.ModelResponse("Não consegui interpretar o valor.")

    resposta = agent.responder_mensagem(
        "Simule o parcelamento.",
        conversa_id=conversa_id,
        modelo=modelo,
    )

    assert resposta == "Não consegui interpretar o valor."
    with sqlite3.connect(banco_agente) as conn:
        argumentos_salvos, sucesso = conn.execute(
            "SELECT args_json, ok FROM tool_calls"
        ).fetchone()
    assert json.loads(argumentos_salvos) == {"_invalid_arguments": "invalid_json"}
    assert sucesso == 0


def test_falha_de_execucao_da_tool_e_segura_para_o_modelo(
    banco_agente: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    conversa_id = memory.criar_conversa()

    def falha(**kwargs):
        raise sqlite3.OperationalError("dados internos")

    monkeypatch.setitem(
        agent._TOOLS,
        "buscar_produtos",
        agent._ToolSpec(
            function=falha,
            arguments=agent.BuscarProdutosArgs,
            description="Tool de teste",
        ),
    )
    requests: list[list[dict[str, object]]] = []

    def modelo(mensagens, tools):
        requests.append(list(mensagens))
        if len(requests) == 1:
            return agent.ModelResponse(
                None,
                (
                    _tool_call(
                        "buscar_produtos",
                        {"query": "guitarra"},
                    ),
                ),
            )
        erro = json.loads(requests[-1][-1]["content"])
        assert erro["error"]["code"] == "tool_execution_failed"
        assert "dados internos" not in json.dumps(erro)
        return agent.ModelResponse("Não consegui consultar agora.")

    assert (
        agent.responder_mensagem(
            "Tem guitarra?",
            conversa_id=conversa_id,
            modelo=modelo,
        )
        == "Não consegui consultar agora."
    )
    with sqlite3.connect(banco_agente) as conn:
        assert conn.execute("SELECT ok FROM tool_calls").fetchone()[0] == 0


def test_limite_de_rodadas_desativa_tools_na_chamada_final(
    banco_agente: Path,
) -> None:
    conversa_id = memory.criar_conversa()
    requests: list[list[dict[str, object]]] = []
    tools_por_chamada: list[int] = []

    def modelo(mensagens, tools):
        requests.append(list(mensagens))
        tools_por_chamada.append(len(tools))
        if len(requests) <= agent.MAX_RODADAS_TOOLS:
            return agent.ModelResponse(
                None,
                (agent.ToolCall(f"call-{len(requests)}", "nao_existe", "{}"),),
            )
        return agent.ModelResponse(
            None,
            (agent.ToolCall("call-final", "nao_existe", "{}"),),
        )

    resposta = agent.responder_mensagem(
        "Faça uma consulta.", conversa_id=conversa_id, modelo=modelo
    )

    assert resposta == agent.RESPOSTA_SEGURA
    assert tools_por_chamada == [6] * agent.MAX_RODADAS_TOOLS + [0]
    with sqlite3.connect(banco_agente) as conn:
        assert conn.execute("SELECT COUNT(*) FROM tool_calls").fetchone()[0] == 5


def test_sem_texto_na_chamada_final_retorna_resposta_segura(
    banco_agente: Path,
) -> None:
    conversa_id = memory.criar_conversa()

    resposta = agent.responder_mensagem(
        "Olá!",
        conversa_id=conversa_id,
        modelo=lambda mensagens, tools: agent.ModelResponse(None),
    )

    assert resposta == agent.RESPOSTA_SEGURA


def test_historico_longo_e_resumido_antes_da_mensagem_atual(
    banco_agente: Path,
) -> None:
    conversa_id = memory.criar_conversa()
    for i in range(21):
        memory.registrar_mensagem(
            conversa_id=conversa_id,
            role="user",
            content=f"mensagem antiga {i}",
        )
    requests: list[tuple[list[dict[str, object]], list[dict[str, object]]]] = []

    def modelo(mensagens, tools):
        requests.append((list(mensagens), list(tools)))
        if len(requests) == 1:
            assert tools == []
            return agent.ModelResponse("Resumo da conversa antiga.")
        return agent.ModelResponse("Resposta após resumir.")

    assert (
        agent.responder_mensagem(
            "Nova pergunta.",
            conversa_id=conversa_id,
            modelo=modelo,
        )
        == "Resposta após resumir."
    )
    mensagens, tools = requests[1]
    assert tools
    assert "Resumo da conversa antiga." in mensagens[1]["content"]
    assert mensagens[-1] == {"role": "user", "content": "Nova pergunta."}
    assert sum(item["role"] == "user" for item in mensagens) == 11
