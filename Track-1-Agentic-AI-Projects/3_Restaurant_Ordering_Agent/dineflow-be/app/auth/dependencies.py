"""FastAPI dependencies for authentication and role checks."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.models import User
from app.auth.security import decode_access_token
from app.db import postgres

bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if credentials is None:
        raise CREDENTIALS_ERROR

    claims = decode_access_token(credentials.credentials)
    if claims is None or "sub" not in claims:
        raise CREDENTIALS_ERROR

    # Re-read the user so a deleted or role-changed account can't keep using an
    # old token's claims.
    row = await postgres.fetchrow(
        "SELECT id, email, name, phone, address, role FROM users WHERE id = $1", claims["sub"]
    )
    if row is None:
        raise CREDENTIALS_ERROR
    return User(**dict(row))


async def require_chef(user: User = Depends(get_current_user)) -> User:
    if user.role != "chef":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Chef access required"
        )
    return user


async def require_customer(user: User = Depends(get_current_user)) -> User:
    """The chef account has no cart of its own — keep it out of the ordering flow."""
    if user.role != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is for customer accounts",
        )
    return user
