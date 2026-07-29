-- DineFlow — Postgres schema (accounts, short-term memory, ordering).
-- Applied on every startup, so every statement must be idempotent.

-- ── Migration: v0 `customers` → v1 `users` ───────────────────────────────────
-- Renaming carries the existing foreign keys across, so this is safe to run
-- against a database that was created before authentication existed.
DO $$
BEGIN
    IF to_regclass('public.customers') IS NOT NULL
       AND to_regclass('public.users') IS NULL THEN
        ALTER TABLE customers RENAME TO users;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    name        TEXT,
    phone       TEXT,
    address     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Auth columns, added separately so the rename path above picks them up too.
ALTER TABLE users ADD COLUMN IF NOT EXISTS email         TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS role          TEXT NOT NULL DEFAULT 'customer';

DO $$
BEGIN
    ALTER TABLE users ADD CONSTRAINT users_role_check
        CHECK (role IN ('customer', 'chef'));
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users (lower(email));

-- Short-term memory: one row per turn of a conversation.
CREATE TABLE IF NOT EXISTS conversation_messages (
    id          BIGSERIAL PRIMARY KEY,
    session_id  TEXT NOT NULL,
    customer_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_session
    ON conversation_messages (session_id, id DESC);

-- Menu
CREATE TABLE IF NOT EXISTS menu_items (
    id           SERIAL PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    category     TEXT NOT NULL,
    description  TEXT NOT NULL DEFAULT '',
    price        NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    tags         TEXT[] NOT NULL DEFAULT '{}',
    is_available BOOLEAN NOT NULL DEFAULT TRUE
);

-- Dish photo, served from the frontend's /public. One placeholder for every
-- item today; swap per-dish URLs in as the photography lands.
ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS image_url TEXT;

CREATE INDEX IF NOT EXISTS idx_menu_category ON menu_items (category);

-- Ordering
CREATE TABLE IF NOT EXISTS orders (
    id           TEXT PRIMARY KEY,
    session_id   TEXT NOT NULL,
    customer_id  TEXT REFERENCES users(id) ON DELETE CASCADE,
    status       TEXT NOT NULL DEFAULT 'pending',
    subtotal     NUMERIC(10, 2) NOT NULL DEFAULT 0,
    tax          NUMERIC(10, 2) NOT NULL DEFAULT 0,
    total        NUMERIC(10, 2) NOT NULL DEFAULT 0,
    address      TEXT,
    notes        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Kitchen lifecycle. The old constraint has to come off *before* the rows are
-- remapped, or the UPDATEs below fail against the vocabulary they're replacing.
ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_status_check;

UPDATE orders SET status = 'pending'     WHERE status = 'confirmed';
UPDATE orders SET status = 'baking'      WHERE status = 'preparing';
UPDATE orders SET status = 'in_delivery' WHERE status IN ('out_for_delivery', 'completed');

ALTER TABLE orders ADD CONSTRAINT orders_status_check
    CHECK (status IN ('pending', 'baking', 'baked', 'in_delivery', 'cancelled'));

CREATE INDEX IF NOT EXISTS idx_orders_session  ON orders (session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders (customer_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_status   ON orders (status, created_at DESC);

CREATE TABLE IF NOT EXISTS order_items (
    id           BIGSERIAL PRIMARY KEY,
    order_id     TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    menu_item_id INTEGER NOT NULL REFERENCES menu_items(id),
    name         TEXT NOT NULL,
    quantity     INTEGER NOT NULL CHECK (quantity > 0),
    unit_price   NUMERIC(10, 2) NOT NULL,
    notes        TEXT
);

CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items (order_id);
