"""Postgres (Neon) connection pool — holds short-term memory and all ordering data."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import asyncpg

from app.config import get_settings

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


async def init_pool() -> asyncpg.Pool:
    """Create the pool and apply the schema. Called once on app startup."""
    global _pool
    if _pool is not None:
        return _pool

    settings = get_settings()
    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        # Neon pools via pgbouncer; server-side prepared statements are not shareable.
        statement_cache_size=0,
    )
    async with _pool.acquire() as conn:
        await conn.execute(SCHEMA_PATH.read_text())
    logger.info("Postgres pool ready, schema applied")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Postgres pool not initialised — call init_pool() on startup")
    return _pool


async def fetch(query: str, *args: Any) -> list[asyncpg.Record]:
    async with get_pool().acquire() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query: str, *args: Any) -> asyncpg.Record | None:
    async with get_pool().acquire() as conn:
        return await conn.fetchrow(query, *args)


async def execute(query: str, *args: Any) -> str:
    async with get_pool().acquire() as conn:
        return await conn.execute(query, *args)
