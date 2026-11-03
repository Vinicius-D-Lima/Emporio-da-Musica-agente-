"""Responsabilidade: registrar as tools do agente Empório da Música e expor seus nomes públicos."""

from __future__ import annotations

from .orders import status_pedido, verificar_cliente
from .products import buscar_produtos, detalhes_produto
from .promotions import promocoes_ativas

__all__ = [
    "buscar_produtos",
    "detalhes_produto",
    "promocoes_ativas",
    "verificar_cliente",
    "status_pedido",
]
