"""Responsabilidade: simular deterministicamente as parcelas permitidas para compras no cartão."""

from __future__ import annotations

from ..schemas import SimularParcelamentoArgs
from .products import detalhes_produto
from .promotions import promocoes_ativas


def _parcela_minima(parcelas: int) -> int:
    if parcelas <= 1:
        return 0
    if parcelas <= 3:
        return 50
    if parcelas <= 6:
        return 80
    return 100


def _tabela_parcelas(total: float) -> tuple[list[dict[str, object]], int]:
    tabela: list[dict[str, object]] = []
    for quantidade in range(1, 13):
        minimo = _parcela_minima(quantidade)
        valor_parcela = round(total / quantidade, 2)
        tabela.append(
            {
                "count": quantidade,
                "amount_brl": valor_parcela,
                "minimum_installment_brl": minimo,
                "allowed": quantidade == 1 or valor_parcela >= minimo,
            }
        )

    max_parcelas = max(
        int(linha["count"]) for linha in tabela if linha["allowed"] is True
    )
    return tabela, max_parcelas


def _preco_do_produto(product_id: int) -> dict[str, object]:
    detalhes = detalhes_produto(product_id=product_id)
    if detalhes["status"] == "not_found":
        return {
            "status": "not_found",
            "message": "Produto não encontrado.",
            "product_id": product_id,
        }

    produto = detalhes["product"]
    if not isinstance(produto, dict):
        raise TypeError("Formato inesperado no resultado de detalhes_produto.")
    disponibilidade = produto["availability_message"]
    if disponibilidade != "disponível":
        return {
            "status": "not_available",
            "message": (
                f"Produto {disponibilidade}; não é possível simular o parcelamento."
            ),
            "product_id": product_id,
        }

    resultado_preco = promocoes_ativas(product_id=product_id)
    if resultado_preco["status"] != "success":
        return {
            "status": "not_found",
            "message": "Produto não encontrado.",
            "product_id": product_id,
        }

    produtos = resultado_preco["products"]
    if (
        not isinstance(produtos, list)
        or not produtos
        or not isinstance(produtos[0], dict)
    ):
        raise TypeError("Formato inesperado no resultado de promocoes_ativas.")
    preco = produtos[0]
    return {
        "status": "success",
        "unit_price_brl": preco["final_price_brl"],
        "price_source": "active_promotion"
        if preco["promotion"] is not None
        else "catalog",
    }


def simular_parcelamento(
    *,
    product_id: int | None = None,
    quantidade: int = 1,
    valor: float | None = None,
) -> dict[str, object]:
    """Calcula parcelas sem juros pelo §3.1; produtos indisponíveis são recusados."""
    argumentos = SimularParcelamentoArgs.model_validate(
        {
            "product_id": product_id,
            "quantidade": quantidade,
            "valor": valor,
        }
    )

    if argumentos.product_id is not None:
        resultado_preco = _preco_do_produto(argumentos.product_id)
        if resultado_preco["status"] != "success":
            return resultado_preco
        unit_price = resultado_preco["unit_price_brl"]
        if not isinstance(unit_price, (int, float)):
            raise TypeError("O preço retornado para o produto não é numérico.")
        total = round(unit_price * argumentos.quantidade, 2)
        price_source = resultado_preco["price_source"]
    else:
        if argumentos.valor is None:
            raise ValueError("O valor precisa estar definido após a validação.")
        unit_price = argumentos.valor
        total = round(unit_price, 2)
        price_source = "provided_value"

    tabela, max_parcelas = _tabela_parcelas(total)
    resultado: dict[str, object] = {
        "status": "success",
        "unit_price_brl": unit_price,
        "quantity": argumentos.quantidade,
        "total_brl": total,
        "price_source": price_source,
        "installments": tabela,
        "max_installments": max_parcelas,
    }
    if argumentos.product_id is not None:
        resultado["product_id"] = argumentos.product_id
    return resultado
