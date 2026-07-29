"""Seed the single chef account from environment credentials on startup.

There is no chef signup route by design — the kitchen account is provisioned by
whoever deploys the service, not self-registered.
"""

from __future__ import annotations

import logging

from app.auth.security import hash_password
from app.config import get_settings
from app.db import postgres

logger = logging.getLogger(__name__)

CHEF_ID = "usr_chef"


async def ensure_chef_account() -> None:
    settings = get_settings()
    email = settings.chef_email.lower()

    await postgres.execute(
        """
        INSERT INTO users (id, email, password_hash, name, role)
        VALUES ($1, $2, $3, 'Head Chef', 'chef')
        ON CONFLICT (id) DO UPDATE
        SET email         = EXCLUDED.email,
            password_hash = EXCLUDED.password_hash,
            role          = 'chef'
        """,
        CHEF_ID,
        email,
        hash_password(settings.chef_password),
    )
    logger.info("Chef account ready: %s", email)
