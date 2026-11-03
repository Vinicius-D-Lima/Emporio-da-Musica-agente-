"""Responsabilidade: consultar promoções vigentes e retornar o cálculo do preço final para o cliente."""

from __future__ import annotations


def promocoes_ativas(*, product_id: int | None = None, limit: int = 10):
    """Lista promoções ativas e, quando aplicável, informa preço original, percentual e final."""
    raise NotImplementedError("As promoções ativas serão implementadas em um passo posterior.")
