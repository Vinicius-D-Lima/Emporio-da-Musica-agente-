"""Responsabilidade: carregar as configurações do ambiente e centralizar a leitura da data de referência do projeto."""

from __future__ import annotations

import os
from datetime import date

from dotenv import load_dotenv

load_dotenv()


def hoje() -> date:
    """Retorna a data de referência configurada em `.env` ou a data atual do sistema."""
    referencia = os.getenv("REFERENCE_DATE", "").strip()
    if referencia:
        return date.fromisoformat(referencia)
    return date.today()
