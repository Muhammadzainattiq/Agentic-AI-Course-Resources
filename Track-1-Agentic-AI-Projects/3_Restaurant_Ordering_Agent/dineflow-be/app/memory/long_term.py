"""Long-term memory: durable facts about a customer, stored in MongoDB.

Facts are written by the extractor (see `extractor.py`) after each turn and read
back into the system prompt on the next turn.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.config import get_settings
from app.db import mongo

MemoryKind = Literal["preference", "personal_data", "dietary", "order_habit", "other"]


class Memory(BaseModel):
    key: str = Field(description="Stable snake_case identifier, e.g. 'address' or 'spice_level'")
    value: str = Field(description="The fact itself, phrased as a short standalone statement")
    kind: MemoryKind = "other"


async def upsert_many(customer_id: str, items: list[Memory]) -> int:
    """Insert or update memories, keyed by (customer_id, key). Returns rows touched."""
    if not items:
        return 0

    now = datetime.now(UTC)
    coll = mongo.memories()
    for item in items:
        await coll.update_one(
            {"customer_id": customer_id, "key": item.key},
            {
                "$set": {
                    "value": item.value,
                    "kind": item.kind,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
    return len(items)


async def get_all(customer_id: str, limit: int | None = None) -> list[dict[str, Any]]:
    limit = limit or get_settings().long_term_max_injected
    cursor = mongo.memories().find(
        {"customer_id": customer_id},
        {"_id": 0, "key": 1, "value": 1, "kind": 1},
    ).sort("updated_at", -1).limit(limit)
    return [doc async for doc in cursor]


async def as_prompt_block(customer_id: str) -> str:
    """Render stored memories for injection into the system prompt."""
    items = await get_all(customer_id)
    if not items:
        return "No stored memories for this customer yet."
    return "\n".join(f"- [{i['kind']}] {i['key']}: {i['value']}" for i in items)


async def forget(customer_id: str, key: str | None = None) -> int:
    query: dict[str, Any] = {"customer_id": customer_id}
    if key:
        query["key"] = key
    result = await mongo.memories().delete_many(query)
    return result.deleted_count
