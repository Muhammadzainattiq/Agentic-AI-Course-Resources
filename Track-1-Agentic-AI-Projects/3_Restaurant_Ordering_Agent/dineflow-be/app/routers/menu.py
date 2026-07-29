"""Menu endpoints — the source of truth the chat UI renders dish cards from."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.db import postgres
from app.schemas import MenuItem

router = APIRouter(prefix="/menu", tags=["menu"])

COLUMNS = "id, name, category, description, price, tags, is_available, image_url"


def _to_item(row) -> MenuItem:
    return MenuItem(**{**dict(row), "price": float(row["price"])})


@router.get("", response_model=list[MenuItem])
async def list_menu(
    category: str | None = None,
    available_only: bool = True,
    ids: str | None = Query(
        default=None,
        description="Comma-separated item ids, e.g. `12,15,18`. Overrides other filters.",
    ),
) -> list[MenuItem]:
    if ids is not None:
        wanted = [int(i) for i in ids.split(",") if i.strip().lstrip("-").isdigit()]
        if not wanted:
            return []
        rows = await postgres.fetch(
            f"SELECT {COLUMNS} FROM menu_items WHERE id = ANY($1::int[])", wanted
        )
        # Preserve the order the caller asked for — the agent ranks its picks.
        by_id = {r["id"]: r for r in rows}
        return [_to_item(by_id[i]) for i in wanted if i in by_id]

    rows = await postgres.fetch(
        f"""
        SELECT {COLUMNS}
        FROM menu_items
        WHERE ($1::text IS NULL OR lower(category) = lower($1))
          AND ($2 = FALSE OR is_available = TRUE)
        ORDER BY category, name
        """,
        category,
        available_only,
    )
    return [_to_item(r) for r in rows]


@router.get("/categories", response_model=list[str])
async def list_categories() -> list[str]:
    rows = await postgres.fetch(
        "SELECT DISTINCT category FROM menu_items WHERE is_available = TRUE ORDER BY category"
    )
    return [r["category"] for r in rows]
