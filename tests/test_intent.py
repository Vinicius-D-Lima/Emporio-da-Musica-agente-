"""Responsabilidade: validar classificação multirrótulo por regras e fallback opcional."""

from __future__ import annotations

import pytest

from emporio_agent.intent import ROTULOS, classificar_intencao


@pytest.mark.parametrize(
    ("mensagem", "esperado"),
    [
        ("Oi!", ["saudacao"]),
        ("Bom dia, tudo bem?", ["saudacao"]),
        ("Oi, vocês têm guitarra?", ["dado_loja", "saudacao"]),
        ("Tem violão disponível?", ["dado_loja"]),
        ("Qual o preço do teclado?", ["dado_loja"]),
        ("Está tendo promoção de bateria?", ["dado_loja"]),
        ("Qual é o horário de funcionamento?", ["politica"]),
        ("Posso devolver uma compra feita online?", ["politica"]),
        ("Quais formas de pagamento vocês aceitam?", ["politica"]),
        ("Vocês parcelam em quantas vezes?", ["politica"]),
        (
            "Vocês têm cabo para guitarra?",
            ["acessorio", "fora_assunto"],
        ),
        (
            "Oi, tem palheta e qual horário vocês abrem?",
            ["politica", "acessorio", "fora_assunto", "saudacao"],
        ),
        ("Me ensina a fazer bolo de chocolate", ["fora_assunto"]),
        ("Quero consultar meu pedido", ["dado_loja"]),
    ],
)
def test_classifica_intencoes_conhecidas_e_multiplos_rotulos(
    mensagem: str, esperado: list[str]
) -> None:
    assert classificar_intencao(mensagem) == esperado


@pytest.mark.parametrize("mensagem", ["", "   ", "Pode me ajudar com isso?"])
def test_mensagem_sem_regra_reconhecida_retorna_lista_vazia(
    mensagem: str,
) -> None:
    assert classificar_intencao(mensagem) == []


def test_fallback_llm_so_e_chamado_quando_regras_nao_classificam() -> None:
    chamadas: list[str] = []

    def classificador_llm(mensagem: str) -> list[str]:
        chamadas.append(mensagem)
        return ["politica", "dado_loja"]

    assert classificar_intencao(
        "Como funciona esse caso?",
        classificador_llm=classificador_llm,
    ) == ["dado_loja", "politica"]
    assert chamadas == ["Como funciona esse caso?"]

    assert classificar_intencao(
        "Oi, tem violão?",
        classificador_llm=classificador_llm,
    ) == ["dado_loja", "saudacao"]
    assert chamadas == ["Como funciona esse caso?"]


def test_fallback_llm_rejeita_rotulos_desconhecidos() -> None:
    with pytest.raises(ValueError, match="rótulo"):
        classificar_intencao(
            "Ajude-me com esta situação desconhecida.",
            classificador_llm=lambda _: ["misto"],
        )


def test_fallback_llm_rejeita_retorno_que_nao_seja_sequencia_de_rotulos() -> None:
    with pytest.raises(TypeError, match="sequência"):
        classificar_intencao(
            "Ajude-me com esta situação desconhecida.",
            classificador_llm=lambda _: "politica",
        )


def test_falha_do_fallback_llm_e_propaga_sem_ser_silenciada() -> None:
    def classificador_indisponivel(_: str) -> list[str]:
        raise RuntimeError("LLM indisponível")

    with pytest.raises(RuntimeError, match="LLM indisponível"):
        classificar_intencao(
            "Ajude-me com esta situação desconhecida.",
            classificador_llm=classificador_indisponivel,
        )


def test_taxonomia_tem_apenas_os_rotulos_decididos() -> None:
    assert ROTULOS == (
        "dado_loja",
        "politica",
        "acessorio",
        "fora_assunto",
        "saudacao",
    )
