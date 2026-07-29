"""Signup, login, and profile endpoints."""

from __future__ import annotations

import logging
import uuid

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.auth.models import AuthResponse, LoginRequest, ProfileUpdate, SignupRequest, User
from app.auth.security import create_access_token, hash_password, verify_password
from app.config import get_settings
from app.db import postgres

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
)


def _auth_response(user: User) -> AuthResponse:
    settings = get_settings()
    return AuthResponse(
        access_token=create_access_token(user.id, user.email, user.role),
        expires_in=settings.jwt_expire_minutes * 60,
        user=user,
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(req: SignupRequest) -> AuthResponse:
    user_id = f"usr_{uuid.uuid4().hex[:16]}"
    try:
        row = await postgres.fetchrow(
            """
            INSERT INTO users (id, email, password_hash, name, phone, address, role)
            VALUES ($1, $2, $3, $4, $5, $6, 'customer')
            RETURNING id, email, name, phone, address, role
            """,
            user_id,
            req.email.lower(),
            hash_password(req.password),
            req.name,
            req.phone,
            req.address,
        )
    except asyncpg.UniqueViolationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists",
        ) from exc

    logger.info("New customer signed up: %s", user_id)
    return _auth_response(User(**dict(row)))


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest) -> AuthResponse:
    row = await postgres.fetchrow(
        """
        SELECT id, email, password_hash, name, phone, address, role
        FROM users WHERE lower(email) = lower($1)
        """,
        req.email,
    )
    # Same error for "no such user" and "wrong password" — don't leak which.
    if row is None or not row["password_hash"]:
        raise INVALID_CREDENTIALS
    if not verify_password(req.password, row["password_hash"]):
        raise INVALID_CREDENTIALS

    user = User(**{k: v for k, v in dict(row).items() if k != "password_hash"})
    return _auth_response(user)


@router.get("/me", response_model=User)
async def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=User)
async def update_me(
    req: ProfileUpdate, user: User = Depends(get_current_user)
) -> User:
    """Partial update — only the fields that were sent are written."""
    row = await postgres.fetchrow(
        """
        UPDATE users
        SET name    = COALESCE($2, name),
            phone   = COALESCE($3, phone),
            address = COALESCE($4, address)
        WHERE id = $1
        RETURNING id, email, name, phone, address, role
        """,
        user.id,
        req.name,
        req.phone,
        req.address,
    )
    return User(**dict(row))
