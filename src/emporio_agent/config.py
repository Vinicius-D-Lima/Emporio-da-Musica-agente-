"""Responsabilidade: carregar configurações e centralizar data, hora e expediente da loja."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

FUSO_LOJA = ZoneInfo("America/Campo_Grande")
PROVEDORES = frozenset({"gemini", "groq"})

load_dotenv()


@dataclass(frozen=True)
class Configuracao:
    """Configurações de provedores e referência temporal lidas do ambiente."""

    llm_provider: str
    llm_fallback: str | None
    gemini_api_key: str | None
    groq_api_key: str | None
    reference_datetime: datetime | None


def _referencia_do_ambiente() -> datetime | None:
    valor = os.getenv("REFERENCE_DATETIME", "").strip()
    if not valor:
        return None

    try:
        referencia = datetime.fromisoformat(valor)
    except ValueError as exc:
        raise ValueError(
            "REFERENCE_DATETIME inválida: use o formato ISO "
            "YYYY-MM-DDTHH:MM:SS, por exemplo 2026-03-23T10:00:00."
        ) from exc

    if referencia.tzinfo is None:
        return referencia.replace(tzinfo=FUSO_LOJA)
    return referencia.astimezone(FUSO_LOJA)


def _chave_do_provedor(
    provedor: str, gemini_api_key: str | None, groq_api_key: str | None
) -> str | None:
    return gemini_api_key if provedor == "gemini" else groq_api_key


def carregar_configuracao() -> Configuracao:
    """Carrega e valida provedores, chaves e data/hora de referência."""
    provedor = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
    fallback = os.getenv("LLM_FALLBACK", "groq").strip().lower() or None

    if provedor not in PROVEDORES:
        raise ValueError(
            f"LLM_PROVIDER inválido: {provedor!r}. Use 'gemini' ou 'groq'."
        )
    if fallback is not None and fallback not in PROVEDORES:
        raise ValueError(
            f"LLM_FALLBACK inválido: {fallback!r}. Use 'gemini', 'groq' ou deixe vazio."
        )

    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip() or None
    groq_api_key = os.getenv("GROQ_API_KEY", "").strip() or None

    for nome, selecionado in (("LLM_PROVIDER", provedor), ("LLM_FALLBACK", fallback)):
        if selecionado is None:
            continue
        chave = _chave_do_provedor(selecionado, gemini_api_key, groq_api_key)
        if not chave or chave.startswith("[PREENCHER"):
            nome_chave = "GEMINI_API_KEY" if selecionado == "gemini" else "GROQ_API_KEY"
            raise ValueError(
                f"{nome_chave} ausente ou não configurada para {nome}={selecionado!r}."
            )

    return Configuracao(
        llm_provider=provedor,
        llm_fallback=fallback,
        gemini_api_key=gemini_api_key,
        groq_api_key=groq_api_key,
        reference_datetime=_referencia_do_ambiente(),
    )


def agora() -> datetime:
    """Retorna a referência configurada ou o horário atual no fuso da loja."""
    referencia = _referencia_do_ambiente()
    if referencia is not None:
        return referencia
    return datetime.now(FUSO_LOJA)


def hoje() -> date:
    """Retorna a data de `agora()` no fuso da loja."""
    return agora().date()


def loja_aberta(instante: datetime) -> bool:
    """Informa se a loja está aberta no instante dado; feriados não são modelados."""
    if instante.tzinfo is None:
        local = instante.replace(tzinfo=FUSO_LOJA)
    else:
        local = instante.astimezone(FUSO_LOJA)

    horario = local.timetz().replace(tzinfo=None)
    if local.weekday() < 5:
        return time(9) <= horario < time(18)
    if local.weekday() == 5:
        return time(9) <= horario < time(13)
    return False
