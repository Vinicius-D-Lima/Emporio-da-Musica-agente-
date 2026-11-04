"""Responsabilidade: chamar os provedores de LLM e aplicar fallback controlado."""

from __future__ import annotations

import base64
import binascii
import json
import logging
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Protocol
from uuid import uuid4

import httpx
from google.genai.errors import APIError as GenAIAPIError
from openai import (
    APIStatusError,
    APITimeoutError,
    BadRequestError,
    OpenAI,
    RateLimitError,
)

from . import config
from .agent import ModelCallable, ModelMessage, ModelResponse, ToolCall

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_NUMERO_LONGO_RE = re.compile(r"(?<!\d)\+?\d[\d\s().-]{7,}\d(?!\d)")
_MAX_DIAGNOSTICO_CHARS = 500
_CAMPOS_ERRO_PROVEDOR = {
    "error",
    "message",
    "code",
    "status",
    "type",
    "param",
    "reason",
    "details",
    "errors",
    "fieldViolations",
    "field",
    "description",
    "@type",
    "violations",
}
_CAMPOS_ERRO_ANINHADOS = {
    "error",
    "details",
    "errors",
    "fieldViolations",
    "violations",
}

_BASE_URLS = {
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "groq": "https://api.groq.com/openai/v1",
}


class LLMError(RuntimeError):
    """Falha explícita na configuração ou na resposta de um provedor."""


class _ChatCompletionEndpoint(Protocol):
    def create(self, **kwargs: object) -> object: ...


class _Chat(Protocol):
    completions: _ChatCompletionEndpoint


class _OpenAIClient(Protocol):
    chat: _Chat


class _GenAIModels(Protocol):
    def generate_content(self, **kwargs: object) -> object: ...


class _GenAIClient(Protocol):
    models: _GenAIModels


ClientFactory = Callable[..., _OpenAIClient]
GenAIClientFactory = Callable[[str], _GenAIClient]

_SEM_EXTRA_CONTENT = object()


def _extra_content(valor: object) -> Mapping[str, object] | None:
    extra = getattr(valor, "extra_content", _SEM_EXTRA_CONTENT)
    if extra is _SEM_EXTRA_CONTENT:
        model_extra = getattr(valor, "model_extra", None)
        if isinstance(model_extra, Mapping):
            extra = model_extra.get("extra_content", _SEM_EXTRA_CONTENT)
    if extra is _SEM_EXTRA_CONTENT or extra is None:
        return None
    if not isinstance(extra, Mapping):
        raise LLMError("O provedor retornou metadata de chamada inválida.")
    return dict(extra)


def _google_thought_signature(extra: object) -> bytes | None:
    if not isinstance(extra, Mapping):
        return None
    if "google" not in extra:
        return None
    google_extra = extra.get("google")
    if not isinstance(google_extra, Mapping):
        raise LLMError("O Gemini retornou metadata de chamada inválida.")
    if "thought_signature" not in google_extra:
        return None
    signature = google_extra["thought_signature"]
    if not isinstance(signature, str) or not signature:
        raise LLMError("O Gemini retornou uma thought signature inválida.")
    try:
        return base64.b64decode(signature, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise LLMError("O Gemini retornou uma thought signature inválida.") from exc


def _mensagens_para_provedor(
    mensagens: Sequence[ModelMessage], provedor: str
) -> list[ModelMessage]:
    if provedor == "gemini":
        return list(mensagens)

    resultado: list[ModelMessage] = []
    for mensagem in mensagens:
        chamadas = mensagem.get("tool_calls")
        if (
            mensagem.get("role") != "assistant"
            or not isinstance(chamadas, Sequence)
            or isinstance(chamadas, (str, bytes))
        ):
            resultado.append(mensagem)
            continue
        mensagem_sem_metadata = dict(mensagem)
        chamadas_sem_metadata: list[object] = []
        for chamada in chamadas:
            if isinstance(chamada, Mapping):
                chamada_sem_metadata = dict(chamada)
                chamada_sem_metadata.pop("extra_content", None)
                chamadas_sem_metadata.append(chamada_sem_metadata)
            else:
                chamadas_sem_metadata.append(chamada)
        mensagem_sem_metadata["tool_calls"] = chamadas_sem_metadata
        resultado.append(mensagem_sem_metadata)
    return resultado


def _api_key(ajustes: config.Configuracao, provedor: str) -> str:
    chave = (
        ajustes.gemini_api_key if provedor == "gemini" else ajustes.groq_api_key
    )
    if not chave:
        raise LLMError(f"A chave de API para o provedor {provedor!r} não está configurada.")
    return chave


def _modelo(ajustes: config.Configuracao, provedor: str) -> str:
    return ajustes.gemini_model if provedor == "gemini" else ajustes.groq_model


def _criar_cliente_openai(
    provedor: str,
    ajustes: config.Configuracao,
    fabrica: ClientFactory,
) -> _OpenAIClient:
    return fabrica(
        api_key=_api_key(ajustes, provedor),
        base_url=_BASE_URLS[provedor],
        max_retries=0,
        timeout=45.0,
    )


def get_llm_client(
    provedor: str | None = None,
    *,
    ajustes: config.Configuracao | None = None,
    client_factory: ClientFactory = OpenAI,
) -> _OpenAIClient:
    """Cria um cliente OpenAI-compatible para o provedor selecionado."""
    configuracao = ajustes or config.carregar_configuracao()
    nome = provedor or configuracao.llm_provider
    if nome not in _BASE_URLS:
        raise ValueError(f"Provedor LLM desconhecido: {nome!r}.")
    return _criar_cliente_openai(nome, configuracao, client_factory)


def _converter_resposta_openai(resposta: object, provedor: str) -> ModelResponse:
    choices = getattr(resposta, "choices", None)
    if not choices:
        raise LLMError("O provedor retornou uma resposta sem escolhas.")
    mensagem = getattr(choices[0], "message", None)
    if mensagem is None:
        raise LLMError("O provedor retornou uma escolha sem mensagem.")

    conteudo = getattr(mensagem, "content", None)
    if conteudo is not None and not isinstance(conteudo, str):
        raise LLMError("O provedor retornou conteúdo em formato inesperado.")
    chamadas: list[ToolCall] = []
    for chamada in getattr(mensagem, "tool_calls", None) or ():
        funcao = getattr(chamada, "function", None)
        call_id = getattr(chamada, "id", None)
        nome = getattr(funcao, "name", None)
        argumentos = getattr(funcao, "arguments", None)
        if not all(isinstance(valor, str) and valor for valor in (call_id, nome)):
            raise LLMError("O provedor retornou uma chamada de ferramenta inválida.")
        if not isinstance(argumentos, str):
            raise LLMError("O provedor retornou argumentos de ferramenta inválidos.")
        chamadas.append(
            ToolCall(
                call_id,
                nome,
                argumentos,
                provider_metadata=_extra_content(chamada),
            )
        )
    return ModelResponse(
        conteudo,
        tuple(chamadas),
        provider=provedor,
    )


def _is_gemini_tool_incompatibility(exc: BadRequestError) -> bool:
    mensagem = str(exc).casefold()
    menciona_tool = "tool" in mensagem or "function" in mensagem
    indica_incompatibilidade = any(
        termo in mensagem
        for termo in ("not supported", "unsupported", "does not support", "not available")
    )
    return menciona_tool and indica_incompatibilidade


def _criar_cliente_genai(api_key: str) -> _GenAIClient:
    from google import genai

    return genai.Client(api_key=api_key)


def _mensagens_genai(
    mensagens: Sequence[ModelMessage],
) -> tuple[str, list[object]]:
    from google.genai import types

    instrucoes: list[str] = []
    conteudos: list[object] = []
    for mensagem in mensagens:
        role = mensagem.get("role")
        conteudo = mensagem.get("content")
        if role == "system":
            if isinstance(conteudo, str) and conteudo:
                instrucoes.append(conteudo)
        elif role == "user":
            if not isinstance(conteudo, str):
                raise LLMError("Mensagem de usuário inválida para o provedor Gemini.")
            conteudos.append(types.Content(role="user", parts=[types.Part(text=conteudo)]))
        elif role == "assistant":
            partes: list[object] = []
            if isinstance(conteudo, str) and conteudo:
                partes.append(types.Part(text=conteudo))
            for chamada in mensagem.get("tool_calls", []):
                funcao = chamada["function"]
                argumentos = json.loads(funcao["arguments"])
                if not isinstance(argumentos, dict):
                    raise LLMError("Argumentos de ferramenta inválidos no histórico.")
                thought_signature = _google_thought_signature(
                    chamada.get("extra_content")
                )
                if thought_signature is None:
                    partes.append(
                        types.Part.from_function_call(
                            name=funcao["name"],
                            args=argumentos,
                        )
                    )
                else:
                    partes.append(
                        types.Part(
                            function_call=types.FunctionCall(
                                name=funcao["name"],
                                args=argumentos,
                            ),
                            thought_signature=thought_signature,
                        )
                    )
            if partes:
                conteudos.append(types.Content(role="model", parts=partes))
        elif role == "tool":
            nome = mensagem.get("name")
            if not isinstance(nome, str):
                raise LLMError("Resultado de ferramenta sem nome no histórico.")
            if not isinstance(conteudo, str):
                raise LLMError("Resultado de ferramenta inválido no histórico.")
            try:
                resultado = json.loads(conteudo)
            except json.JSONDecodeError as exc:
                raise LLMError("Resultado de ferramenta não está em JSON válido.") from exc
            conteudos.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_function_response(
                            name=nome,
                            response={"result": resultado},
                        )
                    ],
                )
            )
        else:
            raise LLMError(f"Papel de mensagem não suportado pelo Gemini: {role!r}.")
    return "\n\n".join(instrucoes), conteudos


def _chamar_gemini_nativo(
    cliente: _GenAIClient,
    ajustes: config.Configuracao,
    mensagens: Sequence[ModelMessage],
    tools: Sequence[dict[str, object]],
) -> ModelResponse:
    from google.genai import types

    system_instruction, contents = _mensagens_genai(mensagens)
    declarations = []
    for tool in tools:
        function = tool["function"]
        declarations.append(
            types.FunctionDeclaration(
                name=function["name"],
                description=function["description"],
                parameters_json_schema=function["parameters"],
            )
        )
    tool_config = (
        [types.Tool(function_declarations=declarations)] if declarations else None
    )
    resposta = cliente.models.generate_content(
        model=ajustes.gemini_model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction or None,
            tools=tool_config,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        ),
    )

    conteudo = getattr(resposta, "candidates", None)
    if not conteudo or not getattr(conteudo[0], "content", None):
        raise LLMError("O Gemini não retornou conteúdo.")
    partes = getattr(conteudo[0].content, "parts", None) or ()
    textos: list[str] = []
    chamadas: list[ToolCall] = []
    for parte in partes:
        texto = getattr(parte, "text", None)
        if isinstance(texto, str):
            textos.append(texto)
        chamada = getattr(parte, "function_call", None)
        if chamada is not None:
            nome = getattr(chamada, "name", None)
            argumentos = getattr(chamada, "args", None)
            if not isinstance(nome, str) or not isinstance(argumentos, Mapping):
                raise LLMError("O Gemini retornou uma chamada de ferramenta inválida.")
            thought_signature = getattr(parte, "thought_signature", None)
            metadata = None
            if thought_signature is not None:
                if not isinstance(thought_signature, bytes):
                    raise LLMError("O Gemini retornou uma thought signature inválida.")
                metadata = {
                    "google": {
                        "thought_signature": base64.b64encode(
                            thought_signature
                        ).decode("ascii")
                    }
                }
            chamadas.append(
                ToolCall(
                    call_id=f"gemini-{uuid4().hex}",
                    name=nome,
                    arguments=json.dumps(argumentos, ensure_ascii=False),
                    provider_metadata=metadata,
                )
            )
    texto_resposta = "\n".join(textos) or None
    return ModelResponse(texto_resposta, tuple(chamadas), provider="gemini")


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, (RateLimitError, APITimeoutError, httpx.TimeoutException)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code in {404, 429} or exc.status_code >= 500
    if isinstance(exc, GenAIAPIError):
        status = getattr(exc, "code", None)
        return status in {404, 429} or (isinstance(status, int) and status >= 500)
    return False


def _redigir_diagnostico(
    detalhe: str,
    mensagens: Sequence[ModelMessage],
    chaves_api: Sequence[str],
) -> str:
    valores_sensiveis: list[str] = list(chaves_api)
    for mensagem in mensagens:
        conteudo = mensagem.get("content")
        if isinstance(conteudo, str):
            valores_sensiveis.append(conteudo)
        chamadas = mensagem.get("tool_calls", [])
        if not isinstance(chamadas, Sequence) or isinstance(chamadas, (str, bytes)):
            continue
        for chamada in chamadas:
            if not isinstance(chamada, Mapping):
                continue
            funcao = chamada.get("function")
            if isinstance(funcao, Mapping):
                argumentos = funcao.get("arguments")
                if isinstance(argumentos, str):
                    valores_sensiveis.append(argumentos)

    for valor in sorted(set(valores_sensiveis), key=len, reverse=True):
        if len(valor) >= 4:
            detalhe = re.sub(
                re.escape(valor),
                "[conteúdo omitido]",
                detalhe,
                flags=re.IGNORECASE,
            )
    detalhe = _EMAIL_RE.sub("[e-mail omitido]", detalhe)
    detalhe = _NUMERO_LONGO_RE.sub("[número omitido]", detalhe)
    return detalhe[:_MAX_DIAGNOSTICO_CHARS]


def _filtrar_campos_erro(valor: object, profundidade: int = 0) -> object:
    if profundidade >= 8:
        return "[limite de detalhes]"
    if isinstance(valor, Mapping):
        campos_filtrados: dict[str, object] = {}
        for chave, conteudo in valor.items():
            if chave not in _CAMPOS_ERRO_PROVEDOR:
                continue
            if chave in _CAMPOS_ERRO_ANINHADOS and not isinstance(
                conteudo, (Mapping, list)
            ):
                continue
            filtrado = _filtrar_campos_erro(conteudo, profundidade + 1)
            if filtrado is not None:
                campos_filtrados[str(chave)] = filtrado
        return campos_filtrados
    if isinstance(valor, list):
        return [
            _filtrar_campos_erro(item, profundidade + 1) for item in valor[:5]
        ]
    if isinstance(valor, (str, int, float, bool)) or valor is None:
        return valor
    return None


def _detalhe_tecnico(exc: Exception) -> str | None:
    resposta = getattr(exc, "response", None)
    texto_resposta = getattr(resposta, "text", None)
    filtrado: object = None
    if isinstance(texto_resposta, str) and texto_resposta:
        try:
            corpo_resposta = json.loads(texto_resposta[:16_000])
        except json.JSONDecodeError:
            filtrado = {"response": texto_resposta[:_MAX_DIAGNOSTICO_CHARS]}
        else:
            filtrado = _filtrar_campos_erro(corpo_resposta)

    if not filtrado:
        corpo = getattr(exc, "body", None)
        if isinstance(corpo, (str, bytes)):
            texto_corpo = (
                corpo.decode("utf-8", errors="replace")
                if isinstance(corpo, bytes)
                else corpo
            )
            try:
                corpo = json.loads(texto_corpo[:16_000])
            except json.JSONDecodeError:
                corpo = None
        filtrado = _filtrar_campos_erro(corpo)

    if not filtrado:
        campos: dict[str, object] = {}
        codigo = getattr(exc, "code", None)
        tipo = getattr(exc, "type", None)
        mensagem = getattr(exc, "message", None)
        if isinstance(codigo, (str, int)):
            campos["code"] = codigo
        if isinstance(tipo, str):
            campos["type"] = tipo
        if isinstance(mensagem, str):
            campos["message"] = mensagem
        filtrado = campos
    if not filtrado:
        return None
    return json.dumps(filtrado, ensure_ascii=False, separators=(",", ":"))


def _registrar_falha(
    provedor: str,
    exc: Exception,
    *,
    mensagens: Sequence[ModelMessage],
    chaves_api: Sequence[str],
) -> LLMError:
    logger.error(
        "Falha no provedor LLM %s (%s).",
        provedor,
        type(exc).__name__,
    )
    status = getattr(exc, "status_code", getattr(exc, "code", None))
    detalhe_status = f", status {status}" if status is not None else ""
    detalhe = _detalhe_tecnico(exc)
    if detalhe is not None:
        detalhe_redigido = _redigir_diagnostico(
            detalhe,
            mensagens,
            chaves_api,
        )
        logger.debug(
            "Detalhe técnico do provedor %s (status %s): %s",
            provedor,
            status,
            detalhe_redigido,
        )
    return LLMError(
        f"Falha ao chamar o provedor LLM {provedor!r} "
        f"({type(exc).__name__}{detalhe_status})."
    )


def criar_modelo(
    *,
    ajustes: config.Configuracao | None = None,
    client_factory: ClientFactory = OpenAI,
    genai_client_factory: GenAIClientFactory = _criar_cliente_genai,
) -> ModelCallable:
    """Constrói o modelo com fallback em indisponibilidade, limite e timeout."""
    configuracao = ajustes or config.carregar_configuracao()
    clientes = {
        nome: _criar_cliente_openai(nome, configuracao, client_factory)
        for nome in {configuracao.llm_provider, configuracao.llm_fallback}
        if nome is not None
    }

    def chamar_com_provedor(
        provedor: str,
        mensagens: Sequence[ModelMessage],
        tools: Sequence[dict[str, object]],
    ) -> ModelResponse:
        cliente = clientes[provedor]
        try:
            argumentos: dict[str, object] = {
                "model": _modelo(configuracao, provedor),
                "messages": _mensagens_para_provedor(mensagens, provedor),
            }
            if tools:
                argumentos["tools"] = list(tools)
            resposta = cliente.chat.completions.create(**argumentos)
        except BadRequestError as exc:
            if (
                provedor != "gemini"
                or not tools
                or not _is_gemini_tool_incompatibility(exc)
            ):
                raise
            logger.warning(
                "Tool calling incompatível no endpoint OpenAI-compatible do Gemini; "
                "usando o SDK nativo."
            )
            cliente_nativo = genai_client_factory(_api_key(configuracao, "gemini"))
            return _chamar_gemini_nativo(
                cliente_nativo,
                configuracao,
                mensagens,
                tools,
            )
        return _converter_resposta_openai(resposta, provedor)

    def chamar(
        mensagens: Sequence[ModelMessage],
        tools: Sequence[dict[str, object]],
    ) -> ModelResponse:
        principal = configuracao.llm_provider
        try:
            resposta = chamar_com_provedor(principal, mensagens, tools)
        except (
            APIStatusError,
            APITimeoutError,
            GenAIAPIError,
            httpx.TimeoutException,
        ) as exc:
            reserva = configuracao.llm_fallback
            if not _is_retryable(exc) or reserva is None or reserva == principal:
                raise _registrar_falha(
                    principal,
                    exc,
                    mensagens=mensagens,
                    chaves_api=(
                        configuracao.gemini_api_key,
                        configuracao.groq_api_key,
                    ),
                ) from exc
            logger.warning(
                "Provedor LLM %s indisponível (%s); tentando %s.",
                principal,
                type(exc).__name__,
                reserva,
            )
            try:
                resposta = chamar_com_provedor(reserva, mensagens, tools)
            except (
                APIStatusError,
                APITimeoutError,
                GenAIAPIError,
                httpx.TimeoutException,
            ) as erro_reserva:
                raise _registrar_falha(
                    reserva,
                    erro_reserva,
                    mensagens=mensagens,
                    chaves_api=(
                        configuracao.gemini_api_key,
                        configuracao.groq_api_key,
                    ),
                ) from erro_reserva
        logger.info("Resposta recebida do provedor LLM %s.", resposta.provider)
        return resposta

    return chamar
