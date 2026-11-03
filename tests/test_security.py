"""Responsabilidade: validar regras de segurança e vazamento de dados no Passo 2 e Passo 6 do projeto."""

import pytest


@pytest.mark.skip(reason="Passo 2")
def test_authorizer_bloqueia_acesso_indevido_ao_banco():
    """Critério de aceite do Passo 2: o `set_authorizer` bloqueia operações indevidas e protege as colunas sensíveis."""
    pass


@pytest.mark.skip(reason="Passo 6")
def test_tools_nao_expoem_telefone_email_ou_description_raw():
    """Critério de aceite do Passo 6: nenhuma tool expõe telefone, e-mail ou `description_raw` e o código não usa `SELECT *` nem `date.today()` fora do módulo de configuração."""
    pass
