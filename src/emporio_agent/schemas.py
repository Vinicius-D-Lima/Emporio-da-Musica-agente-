"""Responsabilidade: declarar os modelos Pydantic dos argumentos das tools do agente, com validação e tipos explícitos."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BuscarProdutosArgs(BaseModel):
    """Argumentos da busca de produtos por catálogo."""

    model_config = ConfigDict(extra="forbid")

    query: str | None = Field(default=None, description="Termo de busca do catálogo")
    category_id: int | None = Field(default=None, ge=1, description="Categoria do produto")
    preco_max: float | None = Field(
        default=None,
        gt=0,
        allow_inf_nan=False,
        description="Preço máximo inclusivo em reais",
    )
    limit: int = Field(default=10, ge=1, le=50)

    @field_validator("query")
    @classmethod
    def normalizar_query(cls, query: str | None) -> str | None:
        if query is None:
            return None
        query = query.strip()
        if not query:
            raise ValueError("O termo de busca não pode ser vazio.")
        return query


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

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, email: str) -> str:
        email = email.strip()
        if not email:
            raise ValueError("O e-mail não pode ser vazio.")
        return email


class StatusPedidoArgs(BaseModel):
    """Argumentos para consultar o status de um pedido."""

    model_config = ConfigDict(extra="forbid")

    order_id: int = Field(ge=1)


class SimularParcelamentoArgs(BaseModel):
    """Argumentos para simular parcelas a partir de produto ou valor informado."""

    model_config = ConfigDict(extra="forbid")

    product_id: int | None = Field(default=None, ge=1)
    quantidade: int = Field(default=1, ge=1)
    valor: float | None = Field(
        default=None, gt=0, allow_inf_nan=False, description="Valor total em reais"
    )

    @model_validator(mode="after")
    def validar_origem_do_preco(self) -> SimularParcelamentoArgs:
        if (self.product_id is None) == (self.valor is None):
            raise ValueError("Informe exatamente um entre product_id e valor.")
        if self.valor is not None and self.quantidade != 1:
            raise ValueError("quantidade só pode ser usada junto com product_id.")
        return self
