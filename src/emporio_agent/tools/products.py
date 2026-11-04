"""Responsabilidade: implementar as queries e validações das tools de catálogo do Empório da Música."""

from __future__ import annotations

import json
import re
import unicodedata
from contextlib import closing

from ..db import conn_leitura
from ..schemas import BuscarProdutosArgs, DetalhesProdutoArgs

_CAMPOS_DE_SPECS = {
    "strings": "cordas",
    "electronics": "eletronica",
    "scale": "escala",
    "color": "cor",
}
_PRODUTOS_SEM_SPECS = range(135, 145)
_COLUNAS_PRODUTO = """
    p.product_id,
    p.name,
    p.category_id,
    c.name AS category,
    p.price_brl,
    p.stock_quantity,
    p.status,
    p.specs_json
"""


def _termos_normalizados(texto: str) -> tuple[list[str], str]:
    sem_acentos = unicodedata.normalize("NFKD", texto)
    sem_acentos = "".join(
        caractere
        for caractere in sem_acentos
        if not unicodedata.combining(caractere)
    )
    termos = re.findall(r"[a-z0-9]+", sem_acentos.lower())
    return termos, "".join(termos)


def corresponde_nome(query: str, nome: str) -> bool:
    termos_query, query_compacta = _termos_normalizados(query)
    termos_nome, nome_compacto = _termos_normalizados(nome)
    return query_compacta in nome_compacto or all(
        any(termo in termo_nome for termo_nome in termos_nome)
        for termo in termos_query
    )


def _mensagem_disponibilidade(status: str, estoque: int) -> str:
    if status == "coming_soon":
        return "em breve"
    if status == "discontinued":
        return "descontinuado" if estoque > 0 else "saiu do catálogo"
    if estoque <= 0:
        return "sem estoque no momento"
    return "disponível"


def _serializar_produto(
    linha, *, include_specs: bool = False
) -> dict[str, object]:
    produto: dict[str, object] = {
        "product_id": linha["product_id"],
        "name": linha["name"],
        "category_id": linha["category_id"],
        "category": linha["category"],
        "price_brl": linha["price_brl"],
        "stock_quantity": linha["stock_quantity"],
        "status": linha["status"],
        "availability_message": _mensagem_disponibilidade(
            linha["status"], linha["stock_quantity"]
        ),
    }

    product_id = linha["product_id"]
    if include_specs and product_id not in _PRODUTOS_SEM_SPECS:
        specs = json.loads(linha["specs_json"])
        produto["specs"] = {
            nome_publico: specs[chave]
            for chave, nome_publico in _CAMPOS_DE_SPECS.items()
            if chave in specs
        }

    return produto


def buscar_produtos(
    *,
    query: str | None = None,
    category_id: int | None = None,
    preco_max: float | None = None,
    limit: int = 10,
) -> dict[str, object]:
    """Busca produtos disponíveis, filtrando termo, categoria e preço máximo."""
    argumentos = BuscarProdutosArgs.model_validate(
        {
            "query": query,
            "category_id": category_id,
            "preco_max": preco_max,
            "limit": limit,
        }
    )

    sql = f"""
        SELECT {_COLUNAS_PRODUTO}
        FROM products AS p
        LEFT JOIN categories AS c ON c.category_id = p.category_id
        WHERE p.status = 'active'
          AND p.stock_quantity > 0
    """
    parametros: list[object] = []
    if argumentos.category_id is not None:
        sql += " AND p.category_id = ?"
        parametros.append(argumentos.category_id)
    if argumentos.preco_max is not None:
        sql += " AND p.price_brl <= ?"
        parametros.append(argumentos.preco_max)
    sql += " ORDER BY p.product_id"

    with closing(conn_leitura()) as conn:
        linhas = conn.execute(sql, parametros).fetchall()

    if argumentos.query is not None:
        linhas = [
            linha
            for linha in linhas
            if corresponde_nome(argumentos.query, linha["name"])
        ]

    total = len(linhas)
    produtos = [_serializar_produto(linha) for linha in linhas[: argumentos.limit]]
    if total == 0:
        return {
            "status": "no_results",
            "message": "Nenhum produto encontrado.",
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


def detalhes_produto(
    *, product_id: int, include_specs: bool = False
) -> dict[str, object]:
    """Retorna os detalhes públicos de um produto com sua disponibilidade atual."""
    argumentos = DetalhesProdutoArgs.model_validate(
        {"product_id": product_id, "include_specs": include_specs}
    )

    with closing(conn_leitura()) as conn:
        linha = conn.execute(
            f"""
            SELECT {_COLUNAS_PRODUTO}
            FROM products AS p
            LEFT JOIN categories AS c ON c.category_id = p.category_id
            WHERE p.product_id = ?
            """,
            (argumentos.product_id,),
        ).fetchone()

    if linha is None:
        return {
            "status": "not_found",
            "message": "Produto não encontrado.",
            "product_id": argumentos.product_id,
        }

    return {
        "status": "success",
        "product": _serializar_produto(linha, include_specs=argumentos.include_specs),
    }
