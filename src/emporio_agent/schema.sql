-- Responsabilidade: definir o schema completo do SQLite usado pelo Empório da Música, incluindo tabelas da loja e do agente.

CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY,
    name TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS products (
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

CREATE TABLE IF NOT EXISTS promotions (
    promotion_id INTEGER PRIMARY KEY,
    product_id INTEGER,
    discount_percent REAL CHECK(discount_percent >= 1 AND discount_percent <= 100),
    label TEXT,
    is_active INTEGER CHECK(is_active IN (0, 1)),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    name TEXT,
    phone TEXT,
    email TEXT,
    city TEXT
);

CREATE TABLE IF NOT EXISTS orders (
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

CREATE TABLE IF NOT EXISTS order_items (
    order_id INTEGER,
    product_id INTEGER,
    quantity INTEGER CHECK(quantity > 0),
    PRIMARY KEY (order_id, product_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

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
