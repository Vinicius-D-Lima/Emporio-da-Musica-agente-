"""Responsabilidade: validar configuração, referência temporal e expediente da loja."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from emporio_agent import config


@pytest.fixture
def ambiente_configurado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_FALLBACK", "groq")
    monkeypatch.setenv("GEMINI_API_KEY", "chave-gemini-teste")
    monkeypatch.setenv("GROQ_API_KEY", "chave-groq-teste")
    monkeypatch.setenv("REFERENCE_DATETIME", "2026-03-23T10:00:00")


def test_carrega_provedores_chaves_e_referencia(
    ambiente_configurado: None,
) -> None:
    configuracao = config.carregar_configuracao()

    assert configuracao.llm_provider == "gemini"
    assert configuracao.llm_fallback == "groq"
    assert configuracao.gemini_api_key == "chave-gemini-teste"
    assert configuracao.groq_api_key == "chave-groq-teste"
    assert configuracao.reference_datetime == datetime(
        2026, 3, 23, 10, 0, tzinfo=config.FUSO_LOJA
    )


def test_agora_e_hoje_usam_a_referencia_no_fuso_da_loja(
    ambiente_configurado: None,
) -> None:
    assert config.agora() == datetime(2026, 3, 23, 10, 0, tzinfo=config.FUSO_LOJA)
    assert config.hoje().isoformat() == "2026-03-23"
    assert config.agora().tzinfo == ZoneInfo("America/Campo_Grande")


def test_referencia_com_fuso_e_convertida_para_o_fuso_da_loja(
    ambiente_configurado: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("REFERENCE_DATETIME", "2026-03-23T14:00:00+00:00")

    assert config.agora() == datetime(2026, 3, 23, 10, 0, tzinfo=config.FUSO_LOJA)


def test_sem_referencia_usa_relogio_atual_com_fuso_da_loja(
    ambiente_configurado: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("REFERENCE_DATETIME")

    instante = config.agora()
    agora_sistema = datetime.now(config.FUSO_LOJA)

    assert instante.tzinfo == ZoneInfo("America/Campo_Grande")
    assert abs(instante - agora_sistema) < timedelta(seconds=2)
    assert config.hoje() == instante.date()


def test_referencia_invalida_falha_com_mensagem_clara(
    ambiente_configurado: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("REFERENCE_DATETIME", "23/03/2026 10:00")

    with pytest.raises(ValueError, match="REFERENCE_DATETIME inválida.*formato ISO"):
        config.agora()


def test_provedor_sem_chave_falha_com_mensagem_clara(
    ambiente_configurado: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY")

    with pytest.raises(ValueError, match="GEMINI_API_KEY ausente ou não configurada"):
        config.carregar_configuracao()


@pytest.mark.parametrize(
    ("instante", "aberta"),
    [
        (datetime(2026, 3, 23, 8, 59), False),
        (datetime(2026, 3, 23, 9, 0), True),
        (datetime(2026, 3, 23, 17, 59), True),
        (datetime(2026, 3, 23, 18, 0), False),
        (datetime(2026, 3, 28, 12, 59), True),
        (datetime(2026, 3, 28, 13, 0), False),
        (datetime(2026, 3, 29, 10, 0), False),
    ],
)
def test_loja_aberta_respeita_dias_e_limites(
    instante: datetime, aberta: bool
) -> None:
    assert config.loja_aberta(instante) is aberta


def test_loja_aberta_converte_instante_aware_para_fuso_local() -> None:
    instante_utc = datetime(2026, 3, 23, 14, 0, tzinfo=timezone.utc)

    assert config.loja_aberta(instante_utc)


def test_datetime_now_e_date_today_so_aparecem_em_config() -> None:
    raiz = Path(__file__).resolve().parents[1] / "src"
    ocorrencias = [
        f"{caminho.relative_to(raiz)}:{numero}:{linha.strip()}"
        for caminho in raiz.rglob("*.py")
        if caminho.name != "config.py"
        for numero, linha in enumerate(caminho.read_text().splitlines(), start=1)
        if "date.today" in linha or "datetime.now" in linha
    ]

    assert ocorrencias == []
