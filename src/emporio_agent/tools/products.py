"""Responsabilidade: implementar as queries e valiações das tools de catálogo do Empório da Música."""

from __future__ import annotations


def buscar_produtos(*, query: str | None = None, category_id: int | None = None, limit: int = 10):
    """Busca produtos por termo ou categoria, respeitando disponibilidade e sem expor campos sensíveis."""
    raise NotImplementedError("A busca de produtos será implementada em um passo posterior.")


def detalhes_produto(*, product_id: int, include_specs: bool = False):
    """Retorna os detalhes de um produto validado, sem `description_raw`, telefone ou e-mail."""
    raise NotImplementedError("Os detalhes do produto serão implementados em um passo posterior.")
