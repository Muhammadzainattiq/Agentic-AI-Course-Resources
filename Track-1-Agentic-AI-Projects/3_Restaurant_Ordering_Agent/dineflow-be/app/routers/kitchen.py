"""Chef-only endpoints: see every order, move it through the kitchen lifecycle."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth.dependencies import require_chef
from app.auth.models import User
from app.db import postgres
from app.orders_status import KITCHEN_STATUSES, next_status
from app.schemas import KitchenOrder, OrderItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/kitchen", tags=["kitchen"])


class StatusUpdate(BaseModel):
    status: str


def _to_kitchen_order(row, items: list[OrderItem]) -> KitchenOrder:
    return KitchenOrder(
        id=row["id"],
        status=row["status"],
        subtotal=float(row["subtotal"]),
        tax=float(row["tax"]),
        total=float(row["total"]),
        address=row["address"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        items=items,
        customer_name=row["customer_name"],
        customer_email=row["customer_email"],
        customer_phone=row["customer_phone"],
        next_status=next_status(row["status"]),
    )


async def _items_by_order(order_ids: list[str]) -> dict[str, list[OrderItem]]:
    """One query for every order's items, so the board doesn't fan out N+1."""
    if not order_ids:
        return {}
    rows = await postgres.fetch(
        """
        SELECT order_id, name, quantity, unit_price
        FROM order_items WHERE order_id = ANY($1::text[]) ORDER BY id
        """,
        order_ids,
    )
    grouped: dict[str, list[OrderItem]] = {oid: [] for oid in order_ids}
    for r in rows:
        grouped[r["order_id"]].append(
            OrderItem(
                name=r["name"], quantity=r["quantity"], unit_price=float(r["unit_price"])
            )
        )
    return grouped


@router.get("/orders", response_model=list[KitchenOrder])
async def list_all_orders(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, le=500),
    _chef: User = Depends(require_chef),
) -> list[KitchenOrder]:
    """Every customer's orders, newest first. Optionally filtered by status."""
    if status_filter and status_filter not in KITCHEN_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown status. Must be one of {KITCHEN_STATUSES}",
        )

    rows = await postgres.fetch(
        """
        SELECT o.*,
               u.name  AS customer_name,
               u.email AS customer_email,
               u.phone AS customer_phone
        FROM orders o
        LEFT JOIN users u ON u.id = o.customer_id
        WHERE ($1::text IS NULL OR o.status = $1)
        ORDER BY o.created_at DESC
        LIMIT $2
        """,
        status_filter,
        limit,
    )
    items = await _items_by_order([r["id"] for r in rows])
    return [_to_kitchen_order(r, items.get(r["id"], [])) for r in rows]


@router.patch("/orders/{order_id}/status", response_model=KitchenOrder)
async def set_order_status(
    order_id: str, update: StatusUpdate, chef: User = Depends(require_chef)
) -> KitchenOrder:
    """Move an order to any kitchen status. The chef is trusted to skip steps."""
    if update.status not in KITCHEN_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown status. Must be one of {KITCHEN_STATUSES}",
        )

    row = await postgres.fetchrow(
        """
        UPDATE orders o SET status = $1, updated_at = now()
        WHERE o.id = $2
        RETURNING o.*,
                  (SELECT name  FROM users WHERE id = o.customer_id) AS customer_name,
                  (SELECT email FROM users WHERE id = o.customer_id) AS customer_email,
                  (SELECT phone FROM users WHERE id = o.customer_id) AS customer_phone
        """,
        update.status,
        order_id,
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    logger.info("Chef %s moved %s → %s", chef.id, order_id, update.status)
    items = await _items_by_order([order_id])
    return _to_kitchen_order(row, items.get(order_id, []))


@router.get("/stats")
async def kitchen_stats(_chef: User = Depends(require_chef)) -> dict[str, int]:
    """Order counts per status, for the dashboard header."""
    rows = await postgres.fetch("SELECT status, count(*) AS n FROM orders GROUP BY status")
    counts = {s: 0 for s in KITCHEN_STATUSES}
    for r in rows:
        counts[r["status"]] = r["n"]
    counts["total"] = sum(counts[s] for s in KITCHEN_STATUSES)
    return counts
