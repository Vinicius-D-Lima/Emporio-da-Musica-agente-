"""Responsabilidade: recriar as tabelas da loja a partir dos CSVs, preservando o histórico do agente."""

from __future__ import annotations

import json
import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "data" / "emporio.db"
RAW_DIR = ROOT_DIR / "data" / "raw"
SCHEMA_PATH = ROOT_DIR / "src" / "emporio_agent" / "schema.sql"

CSV_FILES = {
    "categories": "desafio_tecnico_ai_eng - categories.csv",
    "products": "desafio_tecnico_ai_eng - products.csv",
    "promotions": "desafio_tecnico_ai_eng - promotions.csv",
    "customers": "desafio_tecnico_ai_eng - customers.csv",
    "orders": "desafio_tecnico_ai_eng - orders.csv",
    "order_items": "desafio_tecnico_ai_eng - order_items.csv",
}

STORE_TABLES = (
    "order_items",
    "orders",
    "promotions",
    "products",
    "customers",
    "categories",
)


def _clean_records(frame: pd.DataFrame) -> list[dict[str, object]]:
    """Converte valores vazios do DataFrame em None para inserção no SQLite."""
    cleaned = frame.astype(object).where(pd.notna(frame), None)
    return cleaned.to_dict(orient="records")


def _is_empty(value: object) -> bool:
    """Identifica valores vazios e NaN vindos dos CSVs."""
    return value is None or value == "" or bool(pd.isna(value))


def _normalize_int(value: object) -> int | None:
    """Converte um valor numérico do CSV para inteiro, preservando valores vazios."""
    if _is_empty(value):
        return None
    return int(float(str(value).strip()))


def _normalize_float(value: object) -> float | None:
    """Converte um valor numérico do CSV para float, preservando valores vazios."""
    if _is_empty(value):
        return None
    return float(str(value).strip())


def _normalize_text(value: object) -> str | None:
    """Converte um campo textual para string ou None, sem alterar seu conteúdo."""
    if _is_empty(value):
        return None
    return str(value)


def _parse_payment(raw_value: object) -> tuple[str | None, int | None]:
    """Separa meio de pagamento e parcelas do formato combinado presente no CSV."""
    payment = _normalize_text(raw_value)
    if payment is None:
        return None, None
    if "_" not in payment:
        return payment, None

    payment_type, installments_raw = payment.split("_", maxsplit=1)
    installments_text = installments_raw.removesuffix("x")
    try:
        return payment_type, int(installments_text)
    except ValueError as exc:
        raise ValueError(f"Formato de pagamento inválido no CSV: {payment!r}") from exc


def _read_sources(raw_dir: Path) -> dict[str, pd.DataFrame]:
    """Lê todos os CSVs e valida os campos estruturais antes de alterar o banco."""
    frames: dict[str, pd.DataFrame] = {}
    for table, filename in CSV_FILES.items():
        path = raw_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"CSV obrigatório não encontrado: {path}")
        frames[table] = pd.read_csv(path)
    return frames


def _validate_date(value: object, *, field: str, row_number: int) -> str | None:
    """Valida e retorna uma data ISO textual do CSV."""
    text = _normalize_text(value)
    if text is None:
        return None
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(
            f"Data inválida no campo {field}, linha {row_number}: {text!r}"
        ) from exc
    return text


def _schema_statements(schema: str) -> list[str]:
    """Divide o schema estático em comandos SQL individuais para manter a transação."""
    return [statement.strip() for statement in schema.split(";") if statement.strip()]


def _ensure_conversation_columns(conn: sqlite3.Connection) -> None:
    """Adiciona campos auxiliares a conversas preexistentes sem apagar seus dados."""
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(conversations)").fetchall()
    }
    if "summary" not in columns:
        conn.execute("ALTER TABLE conversations ADD COLUMN summary TEXT")
    if "summarized_until_message_id" not in columns:
        conn.execute(
            "ALTER TABLE conversations ADD COLUMN summarized_until_message_id TEXT"
        )
    if "verification_attempts" not in columns:
        conn.execute(
            "ALTER TABLE conversations ADD COLUMN verification_attempts INTEGER NOT NULL DEFAULT 0"
        )


def _insert_sources(
    conn: sqlite3.Connection, frames: dict[str, pd.DataFrame]
) -> None:
    """Carrega os registros das seis tabelas da loja com colunas explicitamente mapeadas."""
    for row in _clean_records(frames["categories"]):
        conn.execute(
            "INSERT INTO categories (category_id, name, description) VALUES (?, ?, ?)",
            (
                _normalize_int(row["category_id"]),
                _normalize_text(row.get("name")),
                _normalize_text(row.get("description")),
            ),
        )

    for row_number, row in enumerate(_clean_records(frames["products"]), start=2):
        specs_json = _normalize_text(row.get("specs"))
        if specs_json is not None:
            try:
                parsed_specs = json.loads(specs_json)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"JSON inválido em products.specs, linha {row_number}"
                ) from exc
            if not isinstance(parsed_specs, dict):
                raise ValueError(
                    f"products.specs deve conter um objeto JSON, linha {row_number}"
                )
        conn.execute(
            """
            INSERT INTO products (
                product_id, name, category_id, price_brl, stock_quantity, status,
                specs_json, description_raw, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _normalize_int(row["product_id"]),
                _normalize_text(row.get("name")),
                _normalize_int(row["category_id"]),
                _normalize_float(row["price_brl"]),
                _normalize_int(row["stock_quantity"]),
                _normalize_text(row.get("status")),
                specs_json,
                _normalize_text(row.get("description")),
                _validate_date(row.get("created_at"), field="products.created_at", row_number=row_number),
            ),
        )

    for row in _clean_records(frames["promotions"]):
        conn.execute(
            """
            INSERT INTO promotions (
                promotion_id, product_id, discount_percent, label, is_active
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                _normalize_int(row["promotion_id"]),
                _normalize_int(row["product_id"]),
                _normalize_float(row["discount_percent"]),
                _normalize_text(row.get("description")),
                _normalize_int(row["is_active"]),
            ),
        )

    for row in _clean_records(frames["customers"]):
        conn.execute(
            """
            INSERT INTO customers (customer_id, name, phone, email, city)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                _normalize_int(row["customer_id"]),
                _normalize_text(row.get("name")),
                _normalize_text(row.get("phone")),
                _normalize_text(row.get("email")),
                _normalize_text(row.get("city")),
            ),
        )

    for row_number, row in enumerate(_clean_records(frames["orders"]), start=2):
        payment_type, installments = _parse_payment(row.get("payment_method"))
        conn.execute(
            """
            INSERT INTO orders (
                order_id, customer_id, order_date, status, total_brl, payment_type,
                installments, tracking_code, estimated_delivery, notes,
                total_needs_review
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                _normalize_int(row["order_id"]),
                _normalize_int(row["customer_id"]),
                _validate_date(row.get("order_date"), field="orders.order_date", row_number=row_number),
                _normalize_text(row.get("status")),
                _normalize_float(row["total_brl"]),
                payment_type,
                installments,
                _normalize_text(row.get("tracking_code")),
                _validate_date(
                    row.get("estimated_delivery"),
                    field="orders.estimated_delivery",
                    row_number=row_number,
                ),
                _normalize_text(row.get("notes")),
            ),
        )

    for row in _clean_records(frames["order_items"]):
        conn.execute(
            """
            INSERT INTO order_items (order_id, product_id, quantity)
            VALUES (?, ?, ?)
            """,
            (
                _normalize_int(row["order_id"]),
                _normalize_int(row["product_id"]),
                _normalize_int(row["quantity"]),
            ),
        )


def _mark_orders_for_review(conn: sqlite3.Connection) -> None:
    """Marca pedidos cujo total diverge em mais de um centavo da soma pelos preços atuais."""
    orders = conn.execute(
        "SELECT order_id, total_brl FROM orders ORDER BY order_id"
    ).fetchall()
    for order_id, total_brl in orders:
        items = conn.execute(
            """
            SELECT p.price_brl, oi.quantity
            FROM order_items AS oi
            JOIN products AS p ON p.product_id = oi.product_id
            WHERE oi.order_id = ?
            """,
            (order_id,),
        ).fetchall()
        item_total = sum(
            (
                Decimal(str(price)) * Decimal(quantity)
                for price, quantity in items
            ),
            start=Decimal("0"),
        )
        needs_review = abs(Decimal(str(total_brl)) - item_total) > Decimal("0.01")
        conn.execute(
            "UPDATE orders SET total_needs_review = ? WHERE order_id = ?",
            (int(needs_review), order_id),
        )


def _report_anomalies(conn: sqlite3.Connection) -> None:
    """Imprime as anomalias de disponibilidade e promoções ativas previstas pelo plano."""
    anomalies = conn.execute(
        """
        SELECT product_id, status, stock_quantity
        FROM products
        WHERE (product_id = 96 AND status = 'active' AND stock_quantity = 0)
           OR (product_id = 136 AND status = 'discontinued' AND stock_quantity > 0)
           OR (product_id = 130 AND status = 'coming_soon' AND stock_quantity > 0)
        ORDER BY product_id
        """
    ).fetchall()
    duplicates = conn.execute(
        """
        SELECT product_id, COUNT(*) AS active_promotion_count
        FROM promotions
        WHERE is_active = 1
        GROUP BY product_id
        HAVING COUNT(*) > 1
        ORDER BY product_id
        """
    ).fetchall()

    print("Anomalias de disponibilidade:")
    for product_id, status, stock_quantity in anomalies:
        print(
            f"- Produto {product_id}: status={status}, estoque={stock_quantity}"
        )
    if not anomalies:
        print("- Nenhuma")

    print("Produtos com mais de uma promoção ativa:")
    for product_id, count in duplicates:
        print(f"- Produto {product_id}: {count} promoções ativas")
    if not duplicates:
        print("- Nenhum")


def build_database() -> None:
    """Recria somente as tabelas da loja, preserva conversas e valida os dados carregados."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not RAW_DIR.is_dir():
        raise FileNotFoundError(f"Diretório de CSVs não encontrado: {RAW_DIR}")

    frames = _read_sources(RAW_DIR)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("BEGIN")

        for statement in _schema_statements(schema):
            conn.execute(statement)
        _ensure_conversation_columns(conn)

        for table in STORE_TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        for statement in _schema_statements(schema):
            conn.execute(statement)

        _insert_sources(conn, frames)
        _mark_orders_for_review(conn)

        foreign_key_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_errors:
            raise sqlite3.IntegrityError(
                f"Falha de integridade referencial: {foreign_key_errors}"
            )
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")
        _report_anomalies(conn)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    build_database()
