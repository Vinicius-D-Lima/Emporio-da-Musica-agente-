"""Responsabilidade: cobrir as ferramentas do catálogo, pedidos e promoções nos passos 4 e 5 do projeto."""

from __future__ import annotations

import contextlib
import io
import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from emporio_agent import db
from emporio_agent.schemas import BuscarProdutosArgs
from emporio_agent.tools import products
from scripts import build_db


@pytest.fixture(scope="module")
def banco_catalogo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    db_path = tmp_path_factory.mktemp("catalogo") / "emporio.db"
    db_anterior = db.DB_PATH
    build_anterior = build_db.DB_PATH
    db.DB_PATH = db_path
    build_db.DB_PATH = db_path

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            build_db.build_database()
        yield db_path
    finally:
        db.DB_PATH = db_anterior
        build_db.DB_PATH = build_anterior


def test_busca_violoes_por_categoria_preco_e_disponibilidade(
    banco_catalogo: Path,
) -> None:
    resultado = products.buscar_produtos(category_id=5, preco_max=1000, limit=50)

    ids_esperados = [81, 82, 83, 84, 85, 86, 87, 88, 89, 91, 107, 112]
    ids_reais = [produto["product_id"] for produto in resultado["products"]]

    assert resultado["status"] == "success"
    assert resultado["total"] == 12
    assert ids_reais == ids_esperados
    assert 96 not in ids_reais
    assert 113 not in ids_reais
    assert all(
        produto["status"] == "active" and produto["stock_quantity"] > 0
        for produto in resultado["products"]
    )
    assert all("description_raw" not in produto for produto in resultado["products"])

    print("\n[TESTE] Busca de violões: category_id=5, preco_max=1000, limit=50")
    print(f"  Produtos esperados: {ids_esperados}")
    print(f"  IDs retornados: {ids_reais}; total={resultado['total']}")
    print("  Produtos 96 e 113 excluídos; nenhum description_raw exposto")


@pytest.mark.parametrize("query", ["gd20", "GD-20", "takamine gd20"])
def test_busca_por_nome_ignora_caixa_acento_e_hifen(
    banco_catalogo: Path, query: str
) -> None:
    resultado = products.buscar_produtos(query=query)

    assert resultado["status"] == "success"
    assert resultado["total"] == 1
    assert resultado["products"][0]["product_id"] == 95
    print(f"\n[TESTE] Busca pelo nome {query!r}: encontrou produto 95")


@pytest.mark.parametrize(
    ("product_id", "mensagem"),
    [
        (96, "sem estoque no momento"),
        (113, "saiu do catálogo"),
        (130, "em breve"),
        (136, "descontinuado"),
    ],
)
def test_detalhes_informam_disponibilidade_sem_confiar_so_no_estoque(
    banco_catalogo: Path, product_id: int, mensagem: str
) -> None:
    resultado = products.detalhes_produto(product_id=product_id)

    assert resultado["status"] == "success"
    assert resultado["product"]["product_id"] == product_id
    assert resultado["product"]["availability_message"] == mensagem
    assert "description_raw" not in resultado["product"]
    if product_id == 136:
        assert resultado["product"]["stock_quantity"] > 0
        assert resultado["product"]["status"] == "discontinued"

    print(f"\n[TESTE] Detalhes do produto {product_id}: {mensagem}")


def test_detalhes_expoem_apenas_specs_permitidas(
    banco_catalogo: Path,
) -> None:
    resultado = products.detalhes_produto(product_id=95, include_specs=True)

    specs = resultado["product"]["specs"]
    assert specs == {
        "cordas": "steel",
        "eletronica": "no",
        "escala": "650mm",
        "cor": "Natural",
    }

    print(f"\n[TESTE] Specs permitidas do produto 95: {specs}")


@pytest.mark.parametrize("product_id", [135, 136, 137, 138, 139, 140, 141, 142, 143, 144])
def test_detalhes_nao_expoem_specs_dos_produtos_inconsistentes(
    banco_catalogo: Path, product_id: int
) -> None:
    resultado = products.detalhes_produto(product_id=product_id, include_specs=True)

    assert "specs" not in resultado["product"]
    print(f"\n[TESTE] Produto {product_id}: specs omitidas conforme regra de segurança")


def test_busca_sem_resultado_retorna_estrutura_vazia(
    banco_catalogo: Path,
) -> None:
    resultado = products.buscar_produtos(category_id=6)

    assert resultado == {
        "status": "no_results",
        "message": "Nenhum produto encontrado.",
        "products": [],
        "total": 0,
        "limit": 10,
    }
    print("\n[TESTE] Categoria sem produtos: resposta estruturada no_results")


def test_busca_aplica_limite_mas_preserva_total_real(
    banco_catalogo: Path,
) -> None:
    resultado = products.buscar_produtos(category_id=5, preco_max=1000, limit=3)

    assert len(resultado["products"]) == 3
    assert resultado["total"] == 12
    assert resultado["limit"] == 3
    print(
        "\n[TESTE] Paginação: "
        f"limit={resultado['limit']}, retornados={len(resultado['products'])}, "
        f"total real={resultado['total']}"
    )


@pytest.mark.parametrize(
    "argumentos",
    [
        {"preco_max": 0},
        {"preco_max": -10},
        {"preco_max": float("inf")},
        {"preco_max": float("nan")},
        {"category_id": 0},
        {"limit": 0},
        {"limit": 51},
        {"query": "   "},
    ],
)
def test_busca_valida_argumentos_com_pydantic(argumentos: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        products.buscar_produtos(**argumentos)


def test_schema_de_busca_rejeita_argumentos_nao_declarados() -> None:
    with pytest.raises(ValidationError):
        BuscarProdutosArgs.model_validate({"unexpected": True})


@pytest.mark.parametrize("product_id", [0, -1])
def test_detalhes_valida_id_com_pydantic(product_id: int) -> None:
    with pytest.raises(ValidationError):
        products.detalhes_produto(product_id=product_id)


def test_detalhes_produto_inexistente_retorna_nao_encontrado(
    banco_catalogo: Path,
) -> None:
    resultado = products.detalhes_produto(product_id=999)

    assert resultado == {
        "status": "not_found",
        "message": "Produto não encontrado.",
        "product_id": 999,
    }


@pytest.mark.skip(reason="Passo 5")
def test_promocoes_ativas_verificar_cliente_e_status_pedido_processam_regras_de_negocio():
    """Critério de aceite do Passo 5: promoções ativas, verificação de cliente e status do pedido obedecem as regras de negócio e retornam estrutura padronizada."""
    pass
