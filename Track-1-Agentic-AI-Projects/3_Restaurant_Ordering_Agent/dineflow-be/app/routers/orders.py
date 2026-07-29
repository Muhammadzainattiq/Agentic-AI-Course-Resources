"""Customer-facing order views. A customer only ever sees their own orders —
the chef's view lives in routers/kitchen.py.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.db import postgres
from app.schemas import Order, OrderItem

router = APIRouter(prefix="/orders", tags=["orders"])


async def _items(order_id: str) -> list[OrderItem]:
    rows = await postgres.fetch(
        "SELECT name, quantity, unit_price FROM order_items WHERE order_id = $1 ORDER BY id",
        order_id,
    )
    return [
        OrderItem(name=r["name"], quantity=r["quantity"], unit_price=float(r["unit_price"]))
        for r in rows
    ]


def _to_order(row, items: list[OrderItem]) -> Order:
    return Order(
        id=row["id"],
        status=row["status"],
        subtotal=float(row["subtotal"]),
        tax=float(row["tax"]),
        total=float(row["total"]),
        address=row["address"],
        notes=row["notes"],
        created_at=row["created_at"],
        items=items,
    )


@router.get("", response_model=list[Order])
async def list_orders(limit: int = 20, user: User = Depends(get_current_user)) -> list[Order]:
    rows = await postgres.fetch(
        "SELECT * FROM orders WHERE customer_id = $1 ORDER BY created_at DESC LIMIT $2",
        user.id,
        limit,
    )
    return [_to_order(r, await _items(r["id"])) for r in rows]


@router.get("/{order_id}", response_model=Order)
async def get_order(order_id: str, user: User = Depends(get_current_user)) -> Order:
    row = await postgres.fetchrow(
        "SELECT * FROM orders WHERE id = $1 AND customer_id = $2", order_id, user.id
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return _to_order(row, await _items(order_id))
