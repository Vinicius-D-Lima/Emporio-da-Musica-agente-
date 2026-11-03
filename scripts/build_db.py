"""Responsabilidade: recriar o banco de dados da loja a partir dos CSVs do desafio, mantendo idempotência e integridade referencial."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "data" / "emporio.db"
RAW_DIR = ROOT_DIR / "data" / "raw"


def _clean_records(frame: pd.DataFrame) -> list[dict[str, object]]:
    """Converte DataFrames pandas em registros seguros para inserção em SQLite."""
    if frame.empty:
        return []
    cleaned = frame.where(pd.notna(frame), None)
    return cleaned.to_dict(orient="records")


def _normalize_int(value: object) -> int | None:
    """Converte valores numéricos em inteiros sem deixar vazios como strings."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if str(value).strip() == "":
        return None
    return int(float(str(value).strip()))


def _normalize_float(value: object) -> float | None:
    """Converte strings numéricas em floats confiáveis."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value).strip())


def _parse_payment(raw_value: object) -> tuple[str | None, int | None]:
    """Extrai tipo de pagamento e número de parcelas quando a origem vem em formato textual."""
    if raw_value is None or raw_value == "":
        return None, None
    text = str(raw_value).strip()
    if "_" in text:
        payment_type, installments_raw = text.split("_", 1)
        installments = installments_raw.replace("x", "")
        try:
            return payment_type, int(installments)
        except ValueError:
            return payment_type, None
    return text, None


def _create_store_tables(conn: sqlite3.Connection) -> None:
    """Cria as tabelas da loja conforme o schema do projeto."""
    conn.executescript(
        """
        CREATE TABLE categories (
            category_id INTEGER PRIMARY KEY,
            name TEXT,
            description TEXT
        );

        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            name TEXT,
            category_id INTEGER,
            price_brl REAL CHECK(price_brl > 0),
            stock_quantity INTEGER CHECK(stock_quantity >= 0),
            status TEXT CHECK(status IN ('active', 'discontinued', 'coming_soon')),
            specs_json TEXT,
            description_raw TEXT,
            created_at TEXT,
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
        );

        CREATE TABLE promotions (
            promotion_id INTEGER PRIMARY KEY,
            product_id INTEGER,
            discount_percent REAL CHECK(discount_percent >= 1 AND discount_percent <= 100),
            label TEXT,
            is_active INTEGER CHECK(is_active IN (0, 1)),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );

        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT,
            phone TEXT,
            email TEXT,
            city TEXT
        );

        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            order_date TEXT,
            status TEXT CHECK(status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')),
            total_brl REAL,
            payment_type TEXT,
            installments INTEGER,
            tracking_code TEXT,
            estimated_delivery TEXT,
            notes TEXT,
            total_needs_review INTEGER DEFAULT 0,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        CREATE TABLE order_items (
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER CHECK(quantity > 0),
            PRIMARY KEY (order_id, product_id),
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
        """
    )


def build_database() -> None:
    """Cria ou recria o banco SQLite da loja com as tabelas da loja apenas, preservando idempotência e a FK de `conversations` ao recriar `customers`."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    raw_dir = RAW_DIR

    if not raw_dir.exists():
        raise FileNotFoundError(f"Diretório de CSVs não encontrado: {raw_dir}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF")

    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                started_at TEXT,
                verified_customer_id INTEGER,
                FOREIGN KEY (verified_customer_id) REFERENCES customers(customer_id)
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                provider TEXT,
                created_at TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );

            CREATE TABLE IF NOT EXISTS tool_calls (
                id TEXT PRIMARY KEY,
                message_id TEXT,
                tool_name TEXT,
                args_json TEXT,
                ok INTEGER,
                created_at TEXT,
                FOREIGN KEY (message_id) REFERENCES messages(id)
            );
            """
        )

        conn.execute("DELETE FROM tool_calls")
        conn.execute("DELETE FROM messages")
        conn.execute("DELETE FROM conversations")

        for table in [
            "order_items",
            "orders",
            "promotions",
            "products",
            "customers",
            "categories",
        ]:
            conn.execute(f"DROP TABLE IF EXISTS {table}")

        _create_store_tables(conn)

        categories = pd.read_csv(raw_dir / "desafio_tecnico_ai_eng - categories.csv")
        for row in _clean_records(categories):
            conn.execute(
                "INSERT INTO categories (category_id, name, description) VALUES (?, ?, ?)",
                (
                    _normalize_int(row["category_id"]),
                    row.get("name"),
                    row.get("description"),
                ),
            )

        products = pd.read_csv(raw_dir / "desafio_tecnico_ai_eng - products.csv")
        for row in _clean_records(products):
            conn.execute(
                """
                INSERT INTO products (
                    product_id, name, category_id, price_brl, stock_quantity, status,
                    specs_json, description_raw, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _normalize_int(row["product_id"]),
                    row.get("name"),
                    _normalize_int(row["category_id"]),
                    _normalize_float(row["price_brl"]),
                    _normalize_int(row["stock_quantity"]),
                    row.get("status"),
                    row.get("specs"),
                    row.get("description"),
                    row.get("created_at"),
                ),
            )

        promotions = pd.read_csv(raw_dir / "desafio_tecnico_ai_eng - promotions.csv")
        for row in _clean_records(promotions):
            conn.execute(
                "INSERT INTO promotions (promotion_id, product_id, discount_percent, label, is_active) VALUES (?, ?, ?, ?, ?)",
                (
                    _normalize_int(row["promotion_id"]),
                    _normalize_int(row["product_id"]),
                    _normalize_float(row["discount_percent"]),
                    row.get("description"),
                    _normalize_int(row["is_active"]),
                ),
            )

        customers = pd.read_csv(raw_dir / "desafio_tecnico_ai_eng - customers.csv")
        for row in _clean_records(customers):
            conn.execute(
                "INSERT INTO customers (customer_id, name, phone, email, city) VALUES (?, ?, ?, ?, ?)",
                (
                    _normalize_int(row["customer_id"]),
                    row.get("name"),
                    row.get("phone"),
                    row.get("email"),
                    row.get("city"),
                ),
            )

        orders = pd.read_csv(raw_dir / "desafio_tecnico_ai_eng - orders.csv")
        for row in _clean_records(orders):
            payment_type, installments = _parse_payment(row.get("payment_method"))
            conn.execute(
                """
                INSERT INTO orders (
                    order_id, customer_id, order_date, status, total_brl, payment_type,
                    installments, tracking_code, estimated_delivery, notes, total_needs_review
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _normalize_int(row["order_id"]),
                    _normalize_int(row["customer_id"]),
                    row.get("order_date"),
                    row.get("status"),
                    _normalize_float(row["total_brl"]),
                    payment_type,
                    installments,
                    row.get("tracking_code"),
                    row.get("estimated_delivery"),
                    row.get("notes"),
                    0,
                ),
            )

        order_items = pd.read_csv(raw_dir / "desafio_tecnico_ai_eng - order_items.csv")
        for row in _clean_records(order_items):
            conn.execute(
                "INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)",
                (
                    _normalize_int(row["order_id"]),
                    _normalize_int(row["product_id"]),
                    _normalize_int(row["quantity"]),
                ),
            )

        conn.execute("PRAGMA foreign_keys = ON")
        conn.commit()
    except Exception:
        conn.rollback()
        conn.execute("PRAGMA foreign_keys = ON")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    build_database()
