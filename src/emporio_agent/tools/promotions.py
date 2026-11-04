"""Responsabilidade: consultar promoções vigentes e calcular preços finais do catálogo."""

from __future__ import annotations

from contextlib import closing

from ..db import conn_leitura
from ..schemas import PromocoesAtivasArgs
from .products import corresponde_nome

_PIX_DISCOUNT = 0.05


def _preco_do_produto(linha) -> dict[str, object]:
    preco_original = linha["price_brl"]
    promocao = None

    if linha["promotion_id"] is not None:
        desconto = linha["discount_percent"]
        preco_final = round(preco_original * (1 - desconto / 100), 2)
        promocao = {
            "promotion_id": linha["promotion_id"],
            "label": linha["label"],
            "discount_percent": desconto,
            "is_active": True,
        }
        pix_price = preco_final
        pix_discount_applied = False
    else:
        preco_final = preco_original
        pix_price = round(preco_original * (1 - _PIX_DISCOUNT), 2)
        pix_discount_applied = True

    return {
        "product_id": linha["product_id"],
        "name": linha["name"],
        "original_price_brl": preco_original,
        "promotion": promocao,
        "discount_percent": promocao["discount_percent"] if promocao else 0,
        "final_price_brl": preco_final,
        "pix_price_brl": pix_price,
        "pix_discount_applied": pix_discount_applied,
    }


def promocoes_ativas(
    *,
    product_id: int | None = None,
    query: str | None = None,
    limit: int = 10,
) -> dict[str, object]:
    """Lista promoções ou consulta preços por ID, nome ou modelo do produto."""
    argumentos = PromocoesAtivasArgs.model_validate(
        {"product_id": product_id, "query": query, "limit": limit}
    )

    sql = """
        SELECT
            p.product_id,
            p.name,
            p.price_brl,
            pr.promotion_id,
            pr.discount_percent,
            pr.label
        FROM products AS p
        LEFT JOIN promotions AS pr
            ON pr.product_id = p.product_id
           AND pr.is_active = 1
    """
    parametros: tuple[int, ...] = ()
    if argumentos.product_id is not None:
        sql += " WHERE p.product_id = ?"
        parametros = (argumentos.product_id,)
    elif argumentos.query is None:
        sql += " WHERE pr.promotion_id IS NOT NULL"
    sql += " ORDER BY p.product_id, pr.discount_percent DESC, pr.promotion_id"

    with closing(conn_leitura()) as conn:
        linhas = conn.execute(sql, parametros).fetchall()

    if argumentos.query is not None:
        linhas = [
            linha
            for linha in linhas
            if corresponde_nome(argumentos.query, linha["name"])
        ]

    if argumentos.product_id is not None and not linhas:
        return {
            "status": "not_found",
            "message": "Produto não encontrado.",
            "product_id": argumentos.product_id,
        }

    por_produto = {}
    for linha in linhas:
        por_produto.setdefault(linha["product_id"], linha)

    produtos = list(por_produto.values())
    if argumentos.query is not None and not produtos:
        return {
            "status": "not_found",
            "message": "Nenhum produto corresponde ao nome ou modelo informado.",
            "query": argumentos.query,
        }
    if argumentos.query is not None and len(produtos) > 1:
        return {
            "status": "ambiguous",
            "message": (
                "O nome ou modelo corresponde a mais de um produto. "
                "Peça à pessoa para especificar qual deseja consultar."
            ),
            "candidates": [
                {"product_id": produto["product_id"], "name": produto["name"]}
                for produto in produtos[: argumentos.limit]
            ],
            "total": len(produtos),
            "limit": argumentos.limit,
        }

    total = len(produtos)
    produtos = [
        _preco_do_produto(linha)
        for linha in produtos[: argumentos.limit]
    ]

    if total == 0:
        return {
            "status": "no_results",
            "message": "Nenhuma promoção ativa encontrada.",
            "products": [],
            "total": 0,
            "limit": argumentos.limit,
        }

    return {
        "status": "success",
        "products": produtos,
        "total": total,
        "limit": argumentos.limit,
    }
