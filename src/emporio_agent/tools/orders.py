"""Responsabilidade: verificar a identidade do cliente e consultar pedidos com acesso restrito."""

from __future__ import annotations

from contextlib import closing
from datetime import date

from .. import memory
from ..config import hoje
from ..db import conn_leitura
from ..schemas import StatusPedidoArgs, VerificarClienteArgs

_MAX_TENTATIVAS_VERIFICACAO = 3
_RESPOSTA_VERIFICACAO_FALHOU = {
    "status": "not_verified",
    "message": "Não foi possível verificar os dados informados.",
}
_RESPOSTA_VERIFICACAO_BLOQUEADA = {
    "status": "locked",
    "message": "Limite de tentativas de verificação atingido.",
}


def _buscar_sessao(conversa_id: str) -> dict[str, int | None] | None:
    with closing(conn_leitura()) as conn:
        linha = conn.execute(
            """
            SELECT verified_customer_id, verification_attempts
            FROM conversations
            WHERE id = ?
            """,
            (conversa_id,),
        ).fetchone()
    if linha is None:
        return None
    return {
        "verified_customer_id": linha["verified_customer_id"],
        "verification_attempts": linha["verification_attempts"],
    }


def verificar_cliente(
    *, order_id: int, email: str, conversa_id: str
) -> dict[str, str]:
    """Verifica pedido e e-mail; `conversa_id` é contexto interno, não argumento do modelo."""
    argumentos = VerificarClienteArgs.model_validate(
        {"order_id": order_id, "email": email}
    )
    sessao = _buscar_sessao(conversa_id)
    if sessao is None:
        return _RESPOSTA_VERIFICACAO_FALHOU.copy()
    if sessao["verified_customer_id"] is not None:
        with closing(conn_leitura()) as conn:
            linha = conn.execute(
                """
                SELECT o.customer_id
                FROM orders AS o
                JOIN customers AS c ON c.customer_id = o.customer_id
                WHERE o.order_id = ? AND lower(trim(c.email)) = lower(trim(?))
                """,
                (argumentos.order_id, argumentos.email),
            ).fetchone()
        if linha is not None and linha["customer_id"] == sessao["verified_customer_id"]:
            return {"status": "verified", "message": "Cliente verificado."}
        return {
            "status": "already_verified",
            "message": "Esta conversa já possui uma identidade verificada.",
        }

    if sessao["verification_attempts"] >= _MAX_TENTATIVAS_VERIFICACAO:
        return _RESPOSTA_VERIFICACAO_BLOQUEADA.copy()

    with closing(conn_leitura()) as conn:
        linha = conn.execute(
            """
            SELECT o.customer_id
            FROM orders AS o
            JOIN customers AS c ON c.customer_id = o.customer_id
            WHERE o.order_id = ? AND lower(trim(c.email)) = lower(trim(?))
            """,
            (argumentos.order_id, argumentos.email),
        ).fetchone()

    if linha is not None:
        if memory.registrar_cliente_verificado(
            conversa_id=conversa_id, customer_id=linha["customer_id"]
        ):
            return {"status": "verified", "message": "Cliente verificado."}
        return {
            "status": "already_verified",
            "message": "Esta conversa já possui uma identidade verificada.",
        }

    memory.registrar_tentativa_verificacao(conversa_id=conversa_id)
    return _RESPOSTA_VERIFICACAO_FALHOU.copy()


def _mensagem_entrega(
    *, status: str, tracking_code: str | None, estimated_delivery: str | None
) -> tuple[str | None, int | None]:
    if status in {"pending", "confirmed"} and not tracking_code:
        return "Pedido ainda não despachado.", None
    if status == "shipped" and estimated_delivery:
        atraso = (hoje() - date.fromisoformat(estimated_delivery)).days
        if atraso > 0:
            return f"Entrega em atraso há {atraso} dias.", atraso
        return f"Previsão de entrega: {estimated_delivery}.", None
    return None, None


def status_pedido(*, order_id: int, conversa_id: str) -> dict[str, object]:
    """Consulta pedido do cliente verificado; `conversa_id` é contexto interno do runtime."""
    argumentos = StatusPedidoArgs.model_validate({"order_id": order_id})
    sessao = _buscar_sessao(conversa_id)
    if sessao is None or sessao["verified_customer_id"] is None:
        return {
            "status": "not_verified",
            "message": "Cliente não verificado nesta conversa.",
        }

    with closing(conn_leitura()) as conn:
        pedido = conn.execute(
            """
            SELECT
                order_id,
                order_date,
                status,
                total_brl,
                payment_type,
                installments,
                tracking_code,
                estimated_delivery,
                notes,
                total_needs_review
            FROM orders
            WHERE order_id = ? AND customer_id = ?
            """,
            (argumentos.order_id, sessao["verified_customer_id"]),
        ).fetchone()
        if pedido is None:
            return {
                "status": "not_found",
                "message": "Pedido não encontrado.",
            }

        itens = conn.execute(
            """
            SELECT p.name, oi.quantity
            FROM order_items AS oi
            JOIN products AS p ON p.product_id = oi.product_id
            WHERE oi.order_id = ?
            ORDER BY p.name
            """,
            (argumentos.order_id,),
        ).fetchall()

    delivery_message, delay_days = _mensagem_entrega(
        status=pedido["status"],
        tracking_code=pedido["tracking_code"],
        estimated_delivery=pedido["estimated_delivery"],
    )
    resultado_pedido: dict[str, object] = {
        "order_id": pedido["order_id"],
        "status": pedido["status"],
        "order_date": pedido["order_date"],
        "items": [
            {"name": item["name"], "quantity": item["quantity"]} for item in itens
        ],
        "payment_type": pedido["payment_type"],
        "installments": pedido["installments"],
        "tracking_code": pedido["tracking_code"],
        "estimated_delivery": pedido["estimated_delivery"],
    }

    if pedido["total_needs_review"]:
        resultado_pedido["total_message"] = (
            "Valor em revisão; consulte nossa equipe."
        )
    else:
        resultado_pedido["total_brl"] = pedido["total_brl"]

    if delivery_message is not None:
        resultado_pedido["delivery_message"] = delivery_message
    if delay_days is not None:
        resultado_pedido["delay_days"] = delay_days
    if pedido["status"] == "cancelled" and pedido["notes"]:
        resultado_pedido["cancellation_reason"] = pedido["notes"]

    return {"status": "success", "order": resultado_pedido}
