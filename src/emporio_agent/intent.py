"""Responsabilidade: classificar mensagens por regras e fallback opcional para ambiguidade."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Sequence

ROTULOS = (
    "dado_loja",
    "politica",
    "acessorio",
    "fora_assunto",
    "saudacao",
)

_PALAVRAS_ACESSORIOS = (
    "cabo",
    "cabos",
    "palheta",
    "palhetas",
    "case",
    "cases",
    "capa",
    "capas",
    "correia",
    "correias",
    "pedal",
    "pedais",
    "amplificador",
    "amplificadores",
    "afinador",
    "afinadores",
    "encordoamento",
    "encordoamentos",
    "baqueta",
    "baquetas",
    "suporte",
    "suportes",
    "estante",
    "estantes",
    "microfone",
    "microfones",
)
_PALAVRAS_DADO_LOJA = (
    "produto",
    "produtos",
    "catalogo",
    "instrumento",
    "instrumentos",
    "guitarra",
    "guitarras",
    "baixo",
    "baixos",
    "violao",
    "violoes",
    "bateria",
    "baterias",
    "teclado",
    "teclados",
    "piano",
    "pianos",
    "ukulele",
    "ukuleles",
    "violino",
    "violinos",
    "saxofone",
    "saxofones",
    "flauta",
    "flautas",
    "preco",
    "custa",
    "custam",
    "estoque",
    "disponivel",
    "disponibilidade",
    "promocao",
    "promocoes",
    "desconto",
    "pedido",
    "pedidos",
    "rastreio",
    "rastrear",
    "entrega do meu pedido",
    "status do pedido",
)
_PALAVRAS_DADO_EXPLICITO = (
    "produto",
    "produtos",
    "catalogo",
    "preco",
    "custa",
    "custam",
    "estoque",
    "disponivel",
    "disponibilidade",
    "promocao",
    "promocoes",
    "desconto",
    "pedido",
    "pedidos",
    "rastreio",
    "rastrear",
    "entrega do meu pedido",
    "status do pedido",
)
_PALAVRAS_POLITICA = (
    "horario",
    "funcionamento",
    "abre",
    "abrem",
    "fecha",
    "fecham",
    "pagamento",
    "pagamentos",
    "pix",
    "cartao",
    "cartoes",
    "boleto",
    "parcelamento",
    "parcelar",
    "parcelam",
    "parcelas",
    "troca",
    "trocar",
    "devolucao",
    "devolver",
    "arrependimento",
    "garantia",
    "frete",
    "prazo de entrega",
    "entrega",
    "privacidade",
    "lgpd",
    "dados pessoais",
    "reclamacao",
    "reclamacoes",
    "reembolso",
)
_PALAVRAS_FORA_ASSUNTO = (
    "receita",
    "receitas",
    "bolo",
    "cozinhar",
    "clima",
    "previsao do tempo",
    "futebol",
    "politica partidaria",
    "eleicao",
    "programar",
    "programacao",
    "codigo python",
    "me ensina",
    "aula de musica",
    "aulas de musica",
)
_SAUDACOES = (
    "oi",
    "ola",
    "bom dia",
    "boa tarde",
    "boa noite",
    "tudo bem",
)


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(
        caractere for caractere in texto if not unicodedata.combining(caractere)
    )


def _contem_termo(texto: str, termos: Sequence[str]) -> bool:
    return any(
        re.search(
            rf"(?<![a-z0-9]){re.escape(termo)}(?![a-z0-9])",
            texto,
        )
        is not None
        for termo in termos
    )


def _validar_rotulos(rotulos: Sequence[str]) -> list[str]:
    """Valida e normaliza rótulos externos conforme a taxonomia pública."""
    if isinstance(rotulos, (str, bytes)) or not isinstance(rotulos, Sequence):
        raise TypeError("O classificador LLM deve retornar uma sequência de rótulos.")
    desconhecidos = [rotulo for rotulo in rotulos if rotulo not in ROTULOS]
    if desconhecidos:
        raise ValueError(f"rótulo de intenção desconhecido: {desconhecidos[0]!r}.")
    presentes = set(rotulos)
    return [rotulo for rotulo in ROTULOS if rotulo in presentes]


def classificar_intencao(
    mensagem: str,
    *,
    classificador_llm: Callable[[str], Sequence[str]] | None = None,
) -> list[str]:
    """Classifica por regras e usa um classificador LLM injetado se não houver regra."""
    if not isinstance(mensagem, str):
        raise TypeError("A mensagem precisa ser texto.")

    texto = _normalizar(mensagem.strip())
    if not texto:
        return []

    rotulos: set[str] = set()
    tem_acessorio = _contem_termo(texto, _PALAVRAS_ACESSORIOS)
    if _contem_termo(texto, _PALAVRAS_DADO_LOJA) and (
        not tem_acessorio or _contem_termo(texto, _PALAVRAS_DADO_EXPLICITO)
    ):
        rotulos.add("dado_loja")
    if _contem_termo(texto, _PALAVRAS_POLITICA):
        rotulos.add("politica")
    if tem_acessorio:
        rotulos.update({"acessorio", "fora_assunto"})
    if _contem_termo(texto, _PALAVRAS_FORA_ASSUNTO):
        rotulos.add("fora_assunto")
    if _contem_termo(texto, _SAUDACOES):
        rotulos.add("saudacao")

    if rotulos:
        return [rotulo for rotulo in ROTULOS if rotulo in rotulos]
    if classificador_llm is None:
        return []
    return _validar_rotulos(classificador_llm(mensagem))
