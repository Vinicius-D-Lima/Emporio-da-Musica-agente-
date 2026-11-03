"""Responsabilidade: isolar o acesso ao manual de políticas do Empório da Música para o prompt do agente."""

from __future__ import annotations

from pathlib import Path

POLITICA_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "processed" / "politicas.md"
)


def get_policy_context() -> str:
    """Retorna o manual limpo; este é o único ponto de leitura das políticas."""
    return POLITICA_PATH.read_text(encoding="utf-8")
