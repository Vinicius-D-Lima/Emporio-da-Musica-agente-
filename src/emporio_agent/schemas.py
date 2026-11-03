"""Responsabilidade: declarar os modelos Pydantic dos argumentos das tools do agente, com validação e tipos explícitos."""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict


class BuscarProdutosArgs(BaseModel):
    """Argumentos da busca de produtos por catálogo."""

    model_config = ConfigDict(extra="forbid")

    query: str | None = Field(default=None, description="Termo de busca do catálogo")
    category_id: int | None = Field(default=None, description="Categoria do produto")
    limit: int = Field(default=10, ge=1, le=50)


class DetalhesProdutoArgs(BaseModel):
    """Argumentos para detalhar um produto do catálogo."""

    model_config = ConfigDict(extra="forbid")

    product_id: int = Field(ge=1)
    include_specs: bool = False


class PromocoesAtivasArgs(BaseModel):
    """Argumentos para consultar promoções ativas."""

    model_config = ConfigDict(extra="forbid")

    product_id: int | None = Field(default=None, ge=1)
    limit: int = Field(default=10, ge=1, le=50)


class VerificarClienteArgs(BaseModel):
    """Argumentos para verificar identidade do cliente em uma sessão."""

    model_config = ConfigDict(extra="forbid")

    order_id: int = Field(ge=1)
    email: str = Field(min_length=1)


class StatusPedidoArgs(BaseModel):
    """Argumentos para consultar o status de um pedido."""

    model_config = ConfigDict(extra="forbid")

    order_id: int = Field(ge=1)
