"""MongoDB client — holds long-term memories (preferences, personal data)."""

from __future__ import annotations

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.config import get_settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None


async def init_mongo() -> AsyncIOMotorDatabase:
    global _client
    settings = get_settings()
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_uri, tz_aware=True)

    db = _client[settings.mongodb_db]
    await db[settings.mongodb_memories_collection].create_index(
        [("customer_id", 1), ("kind", 1)]
    )
    await db[settings.mongodb_memories_collection].create_index([("updated_at", -1)])
    logger.info("Mongo connected, indexes ensured")
    return db


async def close_mongo() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_db() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("Mongo client not initialised — call init_mongo() on startup")
    return _client[get_settings().mongodb_db]


def memories() -> AsyncIOMotorCollection:
    return get_db()[get_settings().mongodb_memories_collection]
