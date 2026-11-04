"""Responsabilidade: testar a integração dos provedores sem chamadas externas."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import httpx
import pytest
from openai import APIStatusError, APITimeoutError, BadRequestError, RateLimitError

from emporio_agent import config, llm


def _configuracao(
    *,
    principal: str = "gemini",
    fallback: str | None = "groq",
) -> config.Configuracao:
    return config.Configuracao(
        llm_provider=principal,
        llm_fallback=fallback,
        gemini_api_key="gemini-key-test",
        groq_api_key="groq-key-test",
        gemini_model="gemini-3.5-flash-lite",
        groq_model="openai/gpt-oss-120b",
        reference_datetime=None,
    )


def _resposta(
    *,
    content: str | None = "Resposta",
    tool_calls: list[object] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content, tool_calls=tool_calls or [])
            )
        ]
    )


class _FakeClient:
    def __init__(self, resultado: object | Exception) -> None:
        self.argumentos: list[dict[str, object]] = []
        self.resultado = resultado
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    def _create(self, **kwargs: object) -> object:
        self.argumentos.append(kwargs)
        if isinstance(self.resultado, Exception):
            raise self.resultado
        return self.resultado


def test_cliente_usa_base_url_modelo_e_limite_de_retentativas_por_provedor() -> None:
    criados: list[dict[str, object]] = []

    def factory(**kwargs):
        criados.append(kwargs)
        return _FakeClient(_resposta())

    gemini = llm.get_llm_client(
        "gemini",
        ajustes=_configuracao(),
        client_factory=factory,
    )
    groq = llm.get_llm_client(
        "groq",
        ajustes=_configuracao(),
        client_factory=factory,
    )

    assert isinstance(gemini, _FakeClient)
    assert isinstance(groq, _FakeClient)
    assert [item["base_url"] for item in criados] == [
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        "https://api.groq.com/openai/v1",
    ]
    assert all(item["max_retries"] == 0 for item in criados)
    assert all(item["timeout"] == 45.0 for item in criados)


def test_converte_resposta_e_chamada_de_ferramenta_openai_compatible() -> None:
    metadata = {"google": {"thought_signature": "c2lnbmF0dXJl"}}
    chamada = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name="buscar_produtos", arguments='{"query":"gd20"}'),
        extra_content=metadata,
    )
    cliente = _FakeClient(_resposta(content=None, tool_calls=[chamada]))
    modelo = llm.criar_modelo(
        ajustes=_configuracao(fallback=None),
        client_factory=lambda **kwargs: cliente,
    )

    resposta = modelo(
        [{"role": "user", "content": "Procure o GD20"}],
        [{"type": "function"}],
    )

    assert resposta.provider == "gemini"
    assert resposta.content is None
    assert resposta.tool_calls[0].call_id == "call-1"
    assert resposta.tool_calls[0].name == "buscar_produtos"
    assert resposta.tool_calls[0].arguments == '{"query":"gd20"}'
    assert resposta.tool_calls[0].provider_metadata == metadata
    assert cliente.argumentos[0]["model"] == "gemini-3.5-flash-lite"
    assert "tools" in cliente.argumentos[0]


def test_envia_metadata_da_chamada_no_proximo_request_openai_compatible() -> None:
    mensagens = [
        {"role": "user", "content": "Procure o GD20"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call-1",
                    "type": "function",
                    "function": {
                        "name": "buscar",
                        "arguments": '{"query":"gd20"}',
                    },
                    "extra_content": {
                        "google": {"thought_signature": "c2lnbmF0dXJl"}
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call-1",
            "name": "buscar",
            "content": '{"status":"success"}',
        },
    ]
    cliente = _FakeClient(_resposta(content="Encontrei o GD20"))
    modelo = llm.criar_modelo(
        ajustes=_configuracao(fallback=None),
        client_factory=lambda **kwargs: cliente,
    )

    modelo(mensagens, [])

    assert cliente.argumentos[0]["messages"] == mensagens


def test_fallback_groq_nao_recebe_metadata_especifica_do_gemini() -> None:
    erro = RateLimitError(
        "limite",
        response=httpx.Response(429, request=httpx.Request("POST", "https://test")),
        body={},
    )
    chamada = {
        "id": "call-1",
        "type": "function",
        "function": {"name": "buscar", "arguments": '{"query":"gd20"}'},
        "extra_content": {"google": {"thought_signature": "c2lnbmF0dXJl"}},
    }
    mensagens = [
        {"role": "assistant", "content": None, "tool_calls": [chamada]}
    ]
    clientes = {
        "gemini": _FakeClient(erro),
        "groq": _FakeClient(_resposta(content="Resposta da reserva")),
    }
    modelo = llm.criar_modelo(
        ajustes=_configuracao(),
        client_factory=lambda *, api_key, **kwargs: clientes[
            "gemini" if api_key.startswith("gemini") else "groq"
        ],
    )

    resposta = modelo(mensagens, [])

    mensagens_groq = clientes["groq"].argumentos[0]["messages"]
    assert resposta.provider == "groq"
    assert "extra_content" not in mensagens_groq[0]["tool_calls"][0]
    assert "extra_content" in mensagens[0]["tool_calls"][0]


def test_metadata_de_thought_signature_invalida_falha_explicitamente() -> None:
    with pytest.raises(llm.LLMError, match="thought signature inválida"):
        llm._google_thought_signature(
            {"google": {"thought_signature": "não-é-base64"}}
        )


def test_fallback_ocorre_em_429_e_registra_o_provedor_reserva(
    caplog: pytest.LogCaptureFixture,
) -> None:
    resposta_reserva = _resposta(content="Resposta da reserva")
    clientes = {
        "gemini": _FakeClient(
            RateLimitError(
                "limite",
                response=httpx.Response(429, request=httpx.Request("POST", "https://test")),
                body={},
            )
        ),
        "groq": _FakeClient(resposta_reserva),
    }

    def factory(*, api_key, **kwargs):
        return clientes["gemini" if api_key.startswith("gemini") else "groq"]

    modelo = llm.criar_modelo(ajustes=_configuracao(), client_factory=factory)
    resposta = modelo([{"role": "user", "content": "Olá"}], [])

    assert resposta.content == "Resposta da reserva"
    assert resposta.provider == "groq"
    assert "tentando groq" in caplog.text
    assert "tools" not in clientes["groq"].argumentos[0]
    assert clientes["groq"].argumentos[0]["model"] == "openai/gpt-oss-120b"


@pytest.mark.parametrize(
    "erro",
    [
        APITimeoutError(request=httpx.Request("POST", "https://test")),
        APIStatusError(
            "modelo não encontrado",
            response=httpx.Response(
                404, request=httpx.Request("POST", "https://test")
            ),
            body={},
        ),
        APIStatusError(
            "indisponível",
            response=httpx.Response(
                503, request=httpx.Request("POST", "https://test")
            ),
            body={},
        ),
    ],
)
def test_fallback_ocorre_em_timeout_404_e_erro_5xx(erro: Exception) -> None:
    clientes = {
        "gemini": _FakeClient(erro),
        "groq": _FakeClient(_resposta(content="Resposta da reserva")),
    }
    modelo = llm.criar_modelo(
        ajustes=_configuracao(),
        client_factory=lambda *, api_key, **kwargs: clientes[
            "gemini" if api_key.startswith("gemini") else "groq"
        ],
    )

    resposta = modelo([{"role": "user", "content": "Olá"}], [])

    assert resposta.provider == "groq"
    assert resposta.content == "Resposta da reserva"


def test_erro_nao_transitorio_nao_chama_provedor_reserva() -> None:
    erro = BadRequestError(
        "parâmetros inválidos",
        response=httpx.Response(400, request=httpx.Request("POST", "https://test")),
        body={},
    )
    clientes = {"gemini": _FakeClient(erro), "groq": _FakeClient(_resposta())}
    modelo = llm.criar_modelo(
        ajustes=_configuracao(),
        client_factory=lambda *, api_key, **kwargs: clientes[
            "gemini" if api_key.startswith("gemini") else "groq"
        ],
    )

    with pytest.raises(llm.LLMError, match="BadRequestError"):
        modelo([{"role": "user", "content": "Olá"}], [])

    assert clientes["groq"].argumentos == []


def test_debug_registra_detalhe_tecnico_sem_expor_dados_da_requisicao(
    caplog: pytest.LogCaptureFixture,
) -> None:
    email = "cliente@example.com"
    pergunta = f"Quero consultar o pedido de {email} número 12345678"
    corpo = {
        "error": {
            "message": f"Invalid tool schema for request: {pergunta}; gemini-key-test",
            "code": "INVALID_ARGUMENT",
            "type": "invalid_request",
            "details": "corpo interno não deve ser registrado",
        }
    }
    erro = BadRequestError(
        "Bad request",
        response=httpx.Response(
            400,
            json=corpo,
            request=httpx.Request("POST", "https://test"),
        ),
        body=corpo,
    )
    clientes = {"gemini": _FakeClient(erro), "groq": _FakeClient(_resposta())}
    modelo = llm.criar_modelo(
        ajustes=_configuracao(),
        client_factory=lambda *, api_key, **kwargs: clientes[
            "gemini" if api_key.startswith("gemini") else "groq"
        ],
    )

    with caplog.at_level(logging.DEBUG, logger="emporio_agent.llm"):
        with pytest.raises(llm.LLMError, match="BadRequestError"):
            modelo([{"role": "user", "content": pergunta}], [])

    assert "INVALID_ARGUMENT" in caplog.text
    assert "Invalid tool schema" in caplog.text
    assert pergunta not in caplog.text
    assert email not in caplog.text
    assert "12345678" not in caplog.text
    assert "gemini-key-test" not in caplog.text
    assert "corpo interno não deve ser registrado" not in caplog.text
    assert clientes["groq"].argumentos == []


def test_debug_extrai_detalhes_whitelisted_do_corpo_http(
    caplog: pytest.LogCaptureFixture,
) -> None:
    corpo_http = {
        "error": {
            "code": 400,
            "status": "INVALID_ARGUMENT",
            "message": "Error code: 400",
            "details": [
                {
                    "fieldViolations": [
                        {
                            "field": "tools[0].function.parameters",
                            "description": "Unsupported JSON Schema keyword: anyOf",
                            "requestBody": "não deve aparecer",
                        }
                    ]
                }
            ],
        },
        "requestBody": "não deve aparecer",
    }
    resposta_http = httpx.Response(
        400,
        json=corpo_http,
        request=httpx.Request("POST", "https://test"),
    )
    erro = BadRequestError(
        "Error code: 400",
        response=resposta_http,
        body={"error": {"message": "Error code: 400"}},
    )
    clientes = {"gemini": _FakeClient(erro), "groq": _FakeClient(_resposta())}
    modelo = llm.criar_modelo(
        ajustes=_configuracao(),
        client_factory=lambda *, api_key, **kwargs: clientes[
            "gemini" if api_key.startswith("gemini") else "groq"
        ],
    )

    with caplog.at_level(logging.DEBUG, logger="emporio_agent.llm"):
        with pytest.raises(llm.LLMError):
            modelo([{"role": "user", "content": "Procure uma guitarra"}], [])

    assert "INVALID_ARGUMENT" in caplog.text
    assert "Unsupported JSON Schema keyword: anyOf" in caplog.text
    assert "requestBody" not in caplog.text
    assert "não deve aparecer" not in caplog.text


def test_fallback_nao_ocorre_em_erro_de_autenticacao() -> None:
    erro = APIStatusError(
        "não autorizado",
        response=httpx.Response(401, request=httpx.Request("POST", "https://test")),
        body={},
    )
    clientes = {"gemini": _FakeClient(erro), "groq": _FakeClient(_resposta())}
    modelo = llm.criar_modelo(
        ajustes=_configuracao(),
        client_factory=lambda *, api_key, **kwargs: clientes[
            "gemini" if api_key.startswith("gemini") else "groq"
        ],
    )

    with pytest.raises(llm.LLMError, match="status 401"):
        modelo([{"role": "user", "content": "Olá"}], [])

    assert clientes["groq"].argumentos == []


def test_gemini_migra_para_sdk_nativo_so_em_incompatibilidade_de_tools() -> None:
    erro = BadRequestError(
        "Function calling is not supported",
        response=httpx.Response(400, request=httpx.Request("POST", "https://test")),
        body={},
    )
    cliente_openai = _FakeClient(erro)
    chamada_nativa: list[dict[str, object]] = []

    def genai_factory(api_key):
        def generate_content(**kwargs):
            chamada_nativa.append(kwargs)
            return SimpleNamespace(
                candidates=[
                    SimpleNamespace(
                        content=SimpleNamespace(
                            parts=[
                                SimpleNamespace(
                                    text="Encontrei o instrumento.",
                                    function_call=SimpleNamespace(
                                        name="buscar",
                                        args={"query": "gd20"},
                                    ),
                                    thought_signature=b"signature",
                                )
                            ]
                        )
                    )
                ]
            )

        return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))

    modelo = llm.criar_modelo(
        ajustes=_configuracao(fallback=None),
        client_factory=lambda **kwargs: cliente_openai,
        genai_client_factory=genai_factory,
    )

    resposta = modelo(
        [
            {"role": "system", "content": "Instruções"},
            {"role": "user", "content": "Olá"},
        ],
        [
            {
                "type": "function",
                "function": {
                    "name": "buscar",
                    "description": "Busca",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                    },
                },
            }
        ],
    )

    assert resposta.content == "Encontrei o instrumento."
    assert resposta.provider == "gemini"
    assert resposta.tool_calls[0].name == "buscar"
    assert resposta.tool_calls[0].arguments == '{"query": "gd20"}'
    assert resposta.tool_calls[0].provider_metadata == {
        "google": {"thought_signature": "c2lnbmF0dXJl"}
    }
    assert chamada_nativa[0]["model"] == "gemini-3.5-flash-lite"


def test_adaptador_nativo_preserva_chamada_e_resultado_de_tool_no_historico() -> None:
    system, contents = llm._mensagens_genai(
        [
            {"role": "system", "content": "Regras"},
            {"role": "user", "content": "Procure o GD20"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {
                            "name": "buscar",
                            "arguments": '{"query":"gd20"}',
                        },
                        "extra_content": {
                            "google": {"thought_signature": "c2lnbmF0dXJl"}
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call-1",
                "name": "buscar",
                "content": '{"status":"success"}',
            },
        ]
    )

    assert system == "Regras"
    assert contents[1].role == "model"
    assert contents[1].parts[0].function_call.name == "buscar"
    assert contents[1].parts[0].thought_signature == b"signature"
    assert contents[2].parts[0].function_response.name == "buscar"
    assert contents[2].parts[0].function_response.response == {
        "result": {"status": "success"}
    }


def test_falha_de_autenticacao_nao_tenta_reserva() -> None:
    erro = BadRequestError(
        "invalid api key",
        response=httpx.Response(401, request=httpx.Request("POST", "https://test")),
        body={},
    )
    clientes = {"gemini": _FakeClient(erro), "groq": _FakeClient(_resposta())}
    modelo = llm.criar_modelo(
        ajustes=_configuracao(),
        client_factory=lambda *, api_key, **kwargs: clientes[
            "gemini" if api_key.startswith("gemini") else "groq"
        ],
    )

    with pytest.raises(llm.LLMError, match="BadRequestError"):
        modelo([{"role": "user", "content": "Olá"}], [])

    assert clientes["groq"].argumentos == []
