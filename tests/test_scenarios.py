"""Responsabilidade: cenários de ponta a ponta com LLM apenas no passo 15 do projeto."""

import pytest


@pytest.mark.llm
@pytest.mark.skip(reason="Passo 15")
def test_agente_responde_a_cenarios_de_catalogo_pedido_e_fora_de_escopo():
    """Critério de aceite do Passo 15: o agente atende catálogo, pedido e fora de escopo em cenário real, com a marca `llm` e sem execução por padrão."""
    pass
