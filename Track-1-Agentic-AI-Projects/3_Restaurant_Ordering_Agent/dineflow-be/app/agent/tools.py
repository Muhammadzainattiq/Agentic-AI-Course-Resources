"""Tools the DineFlow agent can call: menu lookup, order placement, order status.

Every tool talks to Postgres — the agent never invents prices or order state.
Session/customer identity comes from the run context, not from the model, so the
model cannot place an order on someone else's account.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal

from agents import RunContextWrapper, function_tool

from app.config import get_settings
from app.db import postgres
from app.orders_status import CANCELLABLE, LABELS

logger = logging.getLogger(__name__)


@dataclass
class OrderContext:
    """Per-request context handed to the agent; never model-controlled."""

    session_id: str
    customer_id: str
    default_address: str | None = None


def _money(value: Decimal | float) -> float:
    return float(round(Decimal(str(value)), 2))


@function_tool
async def get_menu_categories() -> str:
    """List the menu's categories and how many dishes are in each.

    Cheap overview — call this before naming categories, rather than guessing,
    and before pulling a whole category the customer may not want.
    """
    rows = await postgres.fetch(
        """
        SELECT category, count(*) AS n, min(price) AS lo, max(price) AS hi
        FROM menu_items WHERE is_available = TRUE
        GROUP BY category ORDER BY category
        """
    )
    if not rows:
        return "The menu is empty."

    currency = get_settings().restaurant_currency
    return "\n".join(
        f"{r['category']}: {r['n']} dishes, {_money(r['lo'])}–{_money(r['hi'])} {currency}"
        for r in rows
    )


@function_tool
async def get_menu(category: str | None = None, tag: str | None = None) -> str:
    """Look up the restaurant menu.

    Args:
        category: Optional category filter, e.g. "mains", "drinks", "desserts".
        tag: Optional tag filter, e.g. "vegan", "spicy", "gluten-free".
    """
    rows = await postgres.fetch(
        """
        SELECT id, name, category, description, price, tags
        FROM menu_items
        WHERE is_available = TRUE
          AND ($1::text IS NULL OR lower(category) = lower($1))
          AND ($2::text IS NULL OR $2 = ANY (tags))
        ORDER BY category, name
        """,
        category,
        tag,
    )
    if not rows:
        return "No menu items match that filter."

    currency = get_settings().restaurant_currency
    lines = [
        f"#{r['id']} {r['name']} ({r['category']}) — {_money(r['price'])} {currency}"
        f" — {r['description']}"
        + (f" [tags: {', '.join(r['tags'])}]" if r["tags"] else "")
        for r in rows
    ]
    return "\n".join(lines)


@function_tool
async def search_menu(query: str) -> str:
    """Free-text search the menu by dish name or description.

    Args:
        query: What the customer asked for, e.g. "something with chicken".
    """
    rows = await postgres.fetch(
        """
        SELECT id, name, category, description, price
        FROM menu_items
        WHERE is_available = TRUE
          AND (name ILIKE '%' || $1 || '%' OR description ILIKE '%' || $1 || '%')
        ORDER BY name
        LIMIT 15
        """,
        query,
    )
    if not rows:
        return f"Nothing on the menu matches '{query}'."

    currency = get_settings().restaurant_currency
    return "\n".join(
        f"#{r['id']} {r['name']} ({r['category']}) — {_money(r['price'])} {currency}"
        f" — {r['description']}"
        for r in rows
    )


@function_tool
async def place_order(
    ctx: RunContextWrapper[OrderContext],
    item_ids: list[int],
    quantities: list[int],
    address: str | None = None,
    notes: str | None = None,
) -> str:
    """Place an order. Only call this after the customer has explicitly confirmed.

    Args:
        item_ids: Menu item ids, as shown by get_menu / search_menu.
        quantities: Quantity for each item id, same length and order as item_ids.
        address: Delivery address. Omit to use the address saved on the account.
        notes: Kitchen notes, e.g. "no onions".
    """
    address = address or ctx.context.default_address
    if len(item_ids) != len(quantities):
        return "Error: item_ids and quantities must have the same length."
    if not item_ids:
        return "Error: cannot place an empty order."
    if any(q <= 0 for q in quantities):
        return "Error: every quantity must be at least 1."

    settings = get_settings()
    rows = await postgres.fetch(
        "SELECT id, name, price FROM menu_items WHERE id = ANY($1::int[]) AND is_available = TRUE",
        item_ids,
    )
    found = {r["id"]: r for r in rows}
    missing = [i for i in item_ids if i not in found]
    if missing:
        return f"Error: menu items {missing} do not exist or are unavailable. Re-check the menu."

    subtotal = sum(found[i]["price"] * q for i, q in zip(item_ids, quantities))
    tax = subtotal * Decimal(str(settings.restaurant_tax_rate))
    total = subtotal + tax
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

    pool = postgres.get_pool()
    async with pool.acquire() as conn, conn.transaction():
        await conn.execute(
            """
            INSERT INTO orders (id, session_id, customer_id, status,
                                subtotal, tax, total, address, notes)
            VALUES ($1, $2, $3, 'pending', $4, $5, $6, $7, $8)
            """,
            order_id,
            ctx.context.session_id,
            ctx.context.customer_id,
            subtotal,
            tax,
            total,
            address,
            notes,
        )
        await conn.executemany(
            """
            INSERT INTO order_items (order_id, menu_item_id, name, quantity, unit_price)
            VALUES ($1, $2, $3, $4, $5)
            """,
            [
                (order_id, i, found[i]["name"], q, found[i]["price"])
                for i, q in zip(item_ids, quantities)
            ],
        )

    currency = settings.restaurant_currency
    lines = [f"{q}x {found[i]['name']}" for i, q in zip(item_ids, quantities)]
    return (
        f"Order {order_id} placed and sent to the kitchen (status: pending).\n"
        f"Items: {', '.join(lines)}\n"
        f"Subtotal {_money(subtotal)} {currency}, tax {_money(tax)} {currency}, "
        f"total {_money(total)} {currency}.\n"
        f"{'Delivery to ' + address if address else 'Pickup at the restaurant'}."
    )


@function_tool
async def get_order_status(ctx: RunContextWrapper[OrderContext], order_id: str | None = None) -> str:
    """Check the status of an order.

    Args:
        order_id: The order id, e.g. "ORD-1A2B3C4D". Omit for the customer's latest order.
    """
    if order_id:
        order = await postgres.fetchrow(
            "SELECT * FROM orders WHERE id = $1 AND customer_id = $2",
            order_id,
            ctx.context.customer_id,
        )
    else:
        order = await postgres.fetchrow(
            """
            SELECT * FROM orders WHERE customer_id = $1
            ORDER BY created_at DESC LIMIT 1
            """,
            ctx.context.customer_id,
        )
    if order is None:
        return "No matching order found for this customer."

    items = await postgres.fetch(
        "SELECT name, quantity FROM order_items WHERE order_id = $1", order["id"]
    )
    listing = ", ".join(f"{i['quantity']}x {i['name']}" for i in items)
    return (
        f"Order {order['id']} — status: {LABELS.get(order['status'], order['status'])}.\n"
        f"Items: {listing}\n"
        f"Total: {_money(order['total'])} {get_settings().restaurant_currency}\n"
        f"Placed: {order['created_at']:%Y-%m-%d %H:%M %Z}"
    )


@function_tool
async def cancel_order(ctx: RunContextWrapper[OrderContext], order_id: str) -> str:
    """Cancel an order, if the kitchen has not started baking it yet.

    Args:
        order_id: The order id to cancel.
    """
    row = await postgres.fetchrow(
        """
        UPDATE orders SET status = 'cancelled', updated_at = now()
        WHERE id = $1 AND customer_id = $2 AND status = ANY($3::text[])
        RETURNING id
        """,
        order_id,
        ctx.context.customer_id,
        list(CANCELLABLE),
    )
    if row is None:
        return (
            f"Could not cancel {order_id} — it does not belong to this customer, "
            "or the kitchen has already started baking it."
        )
    return f"Order {order_id} has been cancelled."


ORDER_TOOLS = [
    get_menu_categories,
    get_menu,
    search_menu,
    place_order,
    get_order_status,
    cancel_order,
]
