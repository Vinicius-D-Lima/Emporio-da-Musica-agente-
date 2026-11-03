"""Responsabilidade: cobrir as ferramentas do catálogo, pedidos e promoções nos passos 4 e 5 do projeto."""

import pytest


@pytest.mark.skip(reason="Passo 4")
def test_buscar_produtos_e_detalhes_produto_respeitam_catalogo_e_disponibilidade():
    """Critério de aceite do Passo 4: `buscar_produtos` e `detalhes_produto` consultam o catálogo com filtros válidos e respeitam disponibilidade."""
    pass


@pytest.mark.skip(reason="Passo 5")
def test_promocoes_ativas_verificar_cliente_e_status_pedido_processam_regras_de_negocio():
    """Critério de aceite do Passo 5: promoções ativas, verificação de cliente e status do pedido obedecem as regras de negócio e retornam estrutura padronizada."""
    pass
