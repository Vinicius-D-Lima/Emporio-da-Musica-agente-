"""Responsabilidade: coordenar o loop principal do agente entre prompt, classificador, tools e resposta final."""

from __future__ import annotations


def responder_mensagem(mensagem: str, *, conversa_id: str | None = None, debug: bool = False) -> str:
    """Recebe uma mensagem e retorna a resposta do agente, seguindo o loop definido pela arquitetura do projeto."""
    raise NotImplementedError("A lógica do loop do agente será implementada em um passo posterior.")
