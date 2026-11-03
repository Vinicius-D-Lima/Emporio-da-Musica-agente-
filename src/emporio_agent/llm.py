"""Responsabilidade: encapsular o cliente do provedor de LLM e o fallback ao método de reserva."""

from __future__ import annotations


def get_llm_client():
    """Retorna o cliente do provedor principal configurado em `.env` ou levanta `NotImplementedError` para a etapa atual."""
    raise NotImplementedError("Cliente de LLM ainda não implementado neste passo.")
