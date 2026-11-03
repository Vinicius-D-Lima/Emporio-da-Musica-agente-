"""Responsabilidade: verificar identidade do cliente e consultar o status de pedidos sem expor dados sensíveis."""

from __future__ import annotations


def verificar_cliente(*, order_id: int, email: str):
    """Valida o pedido e o e-mail do cliente usando a sessão como origem da identidade verificada."""
    raise NotImplementedError("A verificação de cliente será implementada em um passo posterior.")


def status_pedido(*, order_id: int):
    """Retorna o status do pedido e informações públicas relacionadas ao cliente autenticado."""
    raise NotImplementedError("O status do pedido será implementado em um passo posterior.")
