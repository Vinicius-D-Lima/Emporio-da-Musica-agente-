"""Responsabilidade: isolar o acesso ao manual de políticas do Empório da Música para o prompt do agente."""

from __future__ import annotations


def get_policy_context() -> str:
    """Retorna o conteúdo do manual de políticas em texto, sem ferramentas de recuperação por enquanto."""
    from pathlib import Path
    politica_path = Path(__file__).resolve().parents[2] / "data" / "processed" / "politicas.md"
    return politica_path.read_text(encoding="utf-8")
