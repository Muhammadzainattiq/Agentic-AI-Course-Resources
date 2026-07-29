"""Short-term memory: the rolling transcript of a session, stored in Postgres."""

from __future__ import annotations

from app.config import get_settings
from app.db import postgres


async def append(session_id: str, customer_id: str | None, role: str, content: str) -> None:
    await postgres.execute(
        """
        INSERT INTO conversation_messages (session_id, customer_id, role, content)
        VALUES ($1, $2, $3, $4)
        """,
        session_id,
        customer_id,
        role,
        content,
    )


async def history(session_id: str, limit: int | None = None) -> list[dict[str, str]]:
    """Return the last N turns, oldest-first, shaped for the Agents SDK input list."""
    limit = limit or get_settings().short_term_window
    rows = await postgres.fetch(
        """
        SELECT role, content
        FROM conversation_messages
        WHERE session_id = $1
        ORDER BY id DESC
        LIMIT $2
        """,
        session_id,
        limit,
    )
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


async def clear(session_id: str, customer_id: str) -> None:
    await postgres.execute(
        "DELETE FROM conversation_messages WHERE session_id = $1 AND customer_id = $2",
        session_id,
        customer_id,
    )
