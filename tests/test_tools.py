"""Responsabilidade: cobrir as ferramentas do catálogo, pedidos e promoções nos passos 4 e 5 do projeto."""

from __future__ import annotations

import contextlib
import importlib
import io
import sqlite3
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from emporio_agent import db, policies, prompts
from emporio_agent.schemas import BuscarProdutosArgs, PromocoesAtivasArgs
from emporio_agent.tools import products, promotions
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


@pytest.mark.parametrize(
    ("product_id", "preco_original", "desconto", "preco_final"),
    [
        (127, 359.0, 10.0, 323.10),
        (121, 549.0, 20.0, 439.20),
        (90, 2399.0, 18.0, 1967.18),
        (94, 5999.0, 8.0, 5519.08),
    ],
)
def test_promocoes_ativas_calculam_precos_finais(
    banco_catalogo: Path,
    product_id: int,
    preco_original: float,
    desconto: float,
    preco_final: float,
) -> None:
    resultado = promotions.promocoes_ativas(product_id=product_id)

    assert resultado["status"] == "success"
    assert resultado["total"] == 1
    promocao = resultado["products"][0]
    assert promocao["product_id"] == product_id
    assert promocao["original_price_brl"] == preco_original
    assert promocao["discount_percent"] == desconto
    assert promocao["final_price_brl"] == preco_final
    assert promocao["pix_price_brl"] == preco_final
    assert promocao["pix_discount_applied"] is False
    assert promocao["promotion"]["is_active"] is True
    assert "description_raw" not in promocao

    print(
        f"\n[TESTE] Promoção do produto {product_id}: "
        f"R$ {preco_original:.2f} - {desconto:g}% = R$ {preco_final:.2f}; "
        "PIX sem desconto adicional"
    )


def test_lista_apenas_promocoes_ativas_de_produtos_existentes(
    banco_catalogo: Path,
) -> None:
    resultado = promotions.promocoes_ativas(limit=10)

    assert resultado["status"] == "success"
    assert resultado["total"] == 4
    assert [produto["product_id"] for produto in resultado["products"]] == [
        90,
        94,
        121,
        127,
    ]
    assert all(
        produto["promotion"]["is_active"] is True
        and produto["product_id"] is not None
        for produto in resultado["products"]
    )
    assert all(produto["product_id"] != 96 for produto in resultado["products"])


def test_produto_sem_promocao_retorna_preco_de_tabela_e_pix(
    banco_catalogo: Path,
) -> None:
    resultado = promotions.promocoes_ativas(product_id=95)

    assert resultado["status"] == "success"
    assert resultado["total"] == 1
    produto = resultado["products"][0]
    assert produto["product_id"] == 95
    assert produto["original_price_brl"] == 2199.0
    assert produto["promotion"] is None
    assert produto["final_price_brl"] == 2199.0
    assert produto["pix_price_brl"] == 2089.05
    assert produto["pix_discount_applied"] is True


@pytest.mark.parametrize("query", ["gd20", "GD-20", "takamine gd20"])
def test_promocoes_ativas_encontra_preco_por_nome_ou_modelo(
    banco_catalogo: Path, query: str
) -> None:
    resultado = promotions.promocoes_ativas(query=query)

    assert resultado["status"] == "success"
    assert resultado["total"] == 1
    produto = resultado["products"][0]
    assert produto["product_id"] == 95
    assert produto["name"] == "Takamine GD20 Dreadnought Natural"
    assert produto["original_price_brl"] == 2199.0
    assert produto["promotion"] is None


def test_promocoes_ativas_pede_desambiguacao_sem_expor_precos(
    banco_catalogo: Path,
) -> None:
    resultado = promotions.promocoes_ativas(query="Takamine")

    assert resultado["status"] == "ambiguous"
    assert resultado["total"] > 1
    assert resultado["candidates"]
    assert all(
        set(candidato) == {"product_id", "name"}
        for candidato in resultado["candidates"]
    )
    assert "products" not in resultado


def test_promocoes_ativas_por_nome_inexistente_retorna_not_found(
    banco_catalogo: Path,
) -> None:
    resultado = promotions.promocoes_ativas(query="Modelo inexistente XYZ-987654")

    assert resultado["status"] == "not_found"
    assert resultado["query"] == "Modelo inexistente XYZ-987654"


def test_promocoes_inativas_nao_aparecem_nem_no_filtro_por_produto(
    banco_catalogo: Path,
) -> None:
    resultado_lista = promotions.promocoes_ativas()
    resultado_produto = promotions.promocoes_ativas(product_id=96)

    assert 96 not in [produto["product_id"] for produto in resultado_lista["products"]]
    assert resultado_produto["status"] == "success"
    produto = resultado_produto["products"][0]
    assert produto["promotion"] is None
    assert produto["original_price_brl"] == 799.9
    assert produto["pix_price_brl"] == round(799.9 * 0.95, 2)


def test_promocoes_respeitam_limite_e_informam_total_real(
    banco_catalogo: Path,
) -> None:
    resultado = promotions.promocoes_ativas(limit=2)

    assert len(resultado["products"]) == 2
    assert resultado["total"] == 4
    assert resultado["limit"] == 2


def test_produto_inexistente_nao_tem_promocao(
    banco_catalogo: Path,
) -> None:
    resultado = promotions.promocoes_ativas(product_id=999)

    assert resultado == {
        "status": "not_found",
        "message": "Produto não encontrado.",
        "product_id": 999,
    }


@pytest.mark.parametrize(
    "argumentos",
    [
        {"product_id": 0},
        {"product_id": -1},
        {"query": ""},
        {"product_id": 95, "query": "GD20"},
        {"limit": 0},
        {"limit": 51},
    ],
)
def test_promocoes_validam_argumentos_com_pydantic(
    argumentos: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        promotions.promocoes_ativas(**argumentos)


def test_schema_promocoes_rejeita_argumentos_nao_declarados() -> None:
    with pytest.raises(ValidationError):
        PromocoesAtivasArgs.model_validate({"unexpected": True})


def test_duas_promocoes_ativas_usam_maior_desconto_sem_acumular(
    banco_catalogo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    db_path = tmp_path / "promocoes-duplicadas.db"
    with sqlite3.connect(banco_catalogo) as origem, sqlite3.connect(db_path) as copia:
        origem.backup(copia)

    monkeypatch.setattr(db, "DB_PATH", db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO promotions
                (promotion_id, product_id, discount_percent, label, is_active)
            VALUES (1000, 127, 25, 'Promoção sintética', 1)
            """
        )
        conn.commit()
        build_db._report_anomalies(conn)
        relatorio = capsys.readouterr().out

    resultado = promotions.promocoes_ativas(product_id=127)
    promocao = resultado["products"][0]
    assert promocao["discount_percent"] == 25
    assert promocao["final_price_brl"] == 269.25
    assert promocao["final_price_brl"] != round(359 * 0.9 * 0.75, 2)
    assert "Produto 127: 2 promoções ativas" in relatorio
    print("\n[TESTE] Promoções duplicadas: maior desconto (25%) aplicado sem acumular")


@pytest.mark.skip(reason="Passo 6")
def test_verificar_cliente_e_status_pedido_processam_regras_de_negocio():
    """Critério do Passo 6: verificação de cliente e status do pedido obedecem as regras de negócio."""
    pass


def _simular_parcelamento(**argumentos):
    payments = importlib.import_module("emporio_agent.tools.payments")
    return payments.simular_parcelamento(**argumentos)


@pytest.mark.parametrize(
    ("valor", "max_parcelas"),
    [(359.0, 4), (159.9, 3), (120.0, 2), (49.0, 1)],
)
def test_simular_parcelamento_aplica_limites_do_manual(
    valor: float, max_parcelas: int
) -> None:
    resultado = _simular_parcelamento(valor=valor)

    assert resultado["status"] == "success"
    assert resultado["total_brl"] == valor
    assert resultado["max_installments"] == max_parcelas
    assert len(resultado["installments"]) == 12
    assert resultado["installments"][0] == {
        "count": 1,
        "amount_brl": round(valor, 2),
        "minimum_installment_brl": 0,
        "allowed": True,
    }
    assert all(
        linha["allowed"] is (linha["count"] <= max_parcelas)
        for linha in resultado["installments"]
    )


def test_tabela_de_parcelas_de_359_respeita_minimos_por_faixa() -> None:
    resultado = _simular_parcelamento(valor=359.0)
    parcelas = {linha["count"]: linha for linha in resultado["installments"]}

    assert parcelas[3]["amount_brl"] == 119.67
    assert parcelas[3]["minimum_installment_brl"] == 50
    assert parcelas[3]["allowed"] is True
    assert parcelas[4]["amount_brl"] == 89.75
    assert parcelas[4]["minimum_installment_brl"] == 80
    assert parcelas[4]["allowed"] is True
    assert parcelas[5]["amount_brl"] == 71.8
    assert parcelas[5]["allowed"] is False
    assert parcelas[6]["amount_brl"] == 59.83
    assert parcelas[6]["allowed"] is False
    assert parcelas[7]["amount_brl"] == 51.29
    assert parcelas[7]["minimum_installment_brl"] == 100
    assert parcelas[7]["allowed"] is False


def test_produto_usa_preco_promocional_sem_desconto_pix(
    banco_catalogo: Path,
) -> None:
    resultado = _simular_parcelamento(product_id=127)

    assert resultado["status"] == "success"
    assert resultado["product_id"] == 127
    assert resultado["quantity"] == 1
    assert resultado["unit_price_brl"] == 323.1
    assert resultado["total_brl"] == 323.1
    assert resultado["price_source"] == "active_promotion"


def test_produto_multiplica_preco_promocional_pela_quantidade(
    banco_catalogo: Path,
) -> None:
    resultado = _simular_parcelamento(product_id=127, quantidade=2)

    assert resultado["unit_price_brl"] == 323.1
    assert resultado["quantity"] == 2
    assert resultado["total_brl"] == 646.2


def test_produto_sem_promocao_usa_preco_de_tabela_sem_desconto_pix(
    banco_catalogo: Path,
) -> None:
    resultado = _simular_parcelamento(product_id=95)

    assert resultado["unit_price_brl"] == 2199.0
    assert resultado["total_brl"] == 2199.0
    assert resultado["price_source"] == "catalog"
    assert resultado["installments"][0]["amount_brl"] == 2199.0


@pytest.mark.parametrize(
    ("product_id", "availability"),
    [
        (96, "sem estoque no momento"),
        (113, "saiu do catálogo"),
        (130, "em breve"),
        (136, "descontinuado"),
    ],
)
def test_parcelamento_recusa_produto_indisponivel(
    banco_catalogo: Path, product_id: int, availability: str
) -> None:
    resultado = _simular_parcelamento(product_id=product_id)

    assert resultado == {
        "status": "not_available",
        "message": f"Produto {availability}; não é possível simular o parcelamento.",
        "product_id": product_id,
    }


@pytest.mark.parametrize(
    "argumentos",
    [
        {},
        {"valor": 100, "product_id": 95},
        {"valor": 0},
        {"valor": -1},
        {"valor": float("inf")},
        {"product_id": 0},
        {"product_id": 95, "quantidade": 0},
    ],
)
def test_parcelamento_valida_argumentos(argumentos: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _simular_parcelamento(**argumentos)


def test_manual_tem_dez_secoes_sem_placeholders() -> None:
    manual = policies.get_policy_context()

    for secao in range(1, 11):
        assert re.search(rf"(?m)^## §{secao}(?:\.|\s)", manual), f"Seção §{secao} ausente"
    assert "[PREENCHER" not in manual
    assert "Uma compra online pode ser devolvida em até sete dias corridos após o recebimento." in manual
    assert "Reclamações são encaminhadas ao responsável, com retorno em até 24 horas úteis." in manual
    assert "parcelas de duas ou três vezes devem ser de pelo menos R$ 50,00" in manual


def test_manual_e_acessado_apenas_por_policies() -> None:
    src = Path(__file__).resolve().parents[1] / "src"
    acessos = [
        caminho.relative_to(src)
        for caminho in src.rglob("*.py")
        if caminho.name != "policies.py" and "politicas.md" in caminho.read_text()
    ]

    assert acessos == []


def test_montagem_de_mensagens_preserva_ordem_de_tools_manual_historico_e_nova_mensagem() -> None:
    tools = [{"type": "function", "function": {"name": "simular_parcelamento"}}]
    historico = [{"role": "assistant", "content": "Olá!"}]

    requisicao = prompts.montar_mensagens(
        tools=tools,
        historico=historico,
        mensagem="Pode parcelar?",
    )

    assert list(requisicao) == ["tools", "messages"]
    assert requisicao["tools"] == tools
    mensagens = requisicao["messages"]
    assert mensagens[0]["role"] == "system"
    assert "persona" in mensagens[0]["content"].lower()
    assert policies.get_policy_context() in mensagens[0]["content"]
    assert mensagens[1:] == [
        historico[0],
        {"role": "user", "content": "Pode parcelar?"},
    ]


def test_template_de_prompt_define_persona_regras_e_uso_obrigatorio_da_tool() -> None:
    template = prompts.get_prompt_template()

    assert "Persona:" in template
    assert "Regras de negócio:" in template
    assert "Fora de escopo:" in template
    assert "Formato esperado:" in template
    assert "Só informe valores monetários" in template
    assert "repita exatamente o valor confirmado anteriormente" in template
    assert "`promocoes_ativas`" in template
    assert "mais de um produto correspondente" in template
    assert "Amazon Brasil" in template
    assert "Não repita a verificação" in template
    assert "chame `simular_parcelamento`" in template
    assert "Nunca calcule parcelas mentalmente" in template
    assert "Nunca revele ou confirme dados de outro cliente" in template
    assert "Parafraseie o manual" in template
    assert policies.get_policy_context() in template


def test_montagem_de_mensagens_insere_resumo_antes_do_historico_e_da_nova_mensagem() -> None:
    tools = [{"type": "function", "function": {"name": "simular_parcelamento"}}]
    historico = [
        {"role": "user", "content": "Procuro uma guitarra."},
        {"role": "assistant", "content": "Vou consultar as opções."},
    ]

    requisicao = prompts.montar_mensagens(
        tools=tools,
        historico=historico,
        resumo="A pessoa está procurando uma guitarra.",
        mensagem="Pode parcelar?",
    )

    assert requisicao["tools"] == tools
    mensagens = requisicao["messages"]
    assert [mensagem["role"] for mensagem in mensagens] == [
        "system",
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert policies.get_policy_context() in mensagens[0]["content"]
    assert "Resumo contextual da conversa anterior" in mensagens[1]["content"]
    assert "A pessoa está procurando uma guitarra." in mensagens[1]["content"]
    assert mensagens[2:4] == historico
    assert mensagens[-1] == {"role": "user", "content": "Pode parcelar?"}
