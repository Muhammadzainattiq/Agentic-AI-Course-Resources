"""Pin settings for tests so a developer's local .env can't change assertions."""

from __future__ import annotations

import os

import pytest

TEST_ENV = {
    "OPENAI_API_KEY": "sk-test",
    "DATABASE_URL": "postgresql://test/test",
    "MONGODB_URI": "mongodb://test",
    "JWT_SECRET": "test-secret-that-is-at-least-32-bytes-long",
    "RESTAURANT_CURRENCY": "USD",
    "RESTAURANT_TAX_RATE": "0.08",
    "RESTAURANT_NAME": "DineFlow Kitchen",
    "MEMORY_EXTRACTION_ENABLED": "false",
}

for key, value in TEST_ENV.items():
    os.environ[key] = value


@pytest.fixture(autouse=True)
def _fresh_settings():
    """Settings are cached; drop the cache so overrides in a test take effect."""
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
