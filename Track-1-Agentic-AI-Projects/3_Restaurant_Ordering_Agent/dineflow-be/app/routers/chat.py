"""Chat endpoint — the single entry point the customer UI talks to.

Identity is never taken from the request body: the session belongs to whoever
holds the access token, so one customer cannot read or extend another's
conversation, and their memories stay their own.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.agent import dineflow_agent
from app.auth.dependencies import get_current_user, require_customer
from app.auth.models import User
from app.db import postgres
from app.memory import long_term, short_term
from app.schemas import ChatRequest, ChatResponse, MessageOut, OkResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


async def _owned_session(session_id: str, user: User) -> None:
    """404 rather than 403 — don't confirm that another user's session exists."""
    row = await postgres.fetchrow(
        """
        SELECT 1 FROM conversation_messages
        WHERE session_id = $1 AND customer_id <> $2 LIMIT 1
        """,
        session_id,
        user.id,
    )
    if row is not None:
        raise HTTPException(status_code=404, detail="Session not found")


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, user: User = Depends(require_customer)) -> ChatResponse:
    session_id = req.session_id or f"sess_{uuid.uuid4().hex[:12]}"
    await _owned_session(session_id, user)

    try:
        result = await dineflow_agent.run_turn(session_id, user, req.message)
    except Exception as exc:
        logger.exception("Agent turn failed for user %s", user.id)
        raise HTTPException(status_code=502, detail=f"Agent run failed: {exc}") from exc

    return ChatResponse(
        response=result.response,
        session_id=session_id,
        customer_id=user.id,
        memories_stored=result.memories_stored,
    )


@router.get("/history", response_model=list[MessageOut])
async def get_history(
    session_id: str, limit: int = 50, user: User = Depends(get_current_user)
) -> list[MessageOut]:
    await _owned_session(session_id, user)
    return [MessageOut(**m) for m in await short_term.history(session_id, limit)]


@router.delete("/session", response_model=OkResponse)
async def clear_session(session_id: str, user: User = Depends(get_current_user)) -> OkResponse:
    """Clear short-term memory for a session. Long-term memories are untouched."""
    await _owned_session(session_id, user)
    await short_term.clear(session_id, user.id)
    return OkResponse(detail=f"Session {session_id} cleared")


@router.get("/memories")
async def get_memories(limit: int = 50, user: User = Depends(get_current_user)) -> list[dict]:
    """A user can only ever read their own long-term memories."""
    return await long_term.get_all(user.id, limit)


@router.delete("/memories", response_model=OkResponse)
async def forget_memories(
    key: str | None = None, user: User = Depends(get_current_user)
) -> OkResponse:
    deleted = await long_term.forget(user.id, key)
    return OkResponse(detail=f"Deleted {deleted} memories")
