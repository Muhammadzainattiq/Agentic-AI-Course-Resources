"""Password hashing, JWT round-trips, and the kitchen status flow."""

from __future__ import annotations

import time

import jwt
import pytest

from app.auth.security import (
    ALGORITHM,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.config import get_settings
from app.orders_status import CANCELLABLE, KITCHEN_FLOW, KITCHEN_STATUSES, next_status


def test_password_round_trip():
    hashed = hash_password("chef@1234")
    assert hashed != "chef@1234"
    assert verify_password("chef@1234", hashed)
    assert not verify_password("chef@12345", hashed)


def test_same_password_hashes_differently():
    """Distinct salts — two users with the same password must not collide."""
    assert hash_password("hunter22") != hash_password("hunter22")


def test_verify_rejects_malformed_hash():
    assert not verify_password("anything", "not-a-bcrypt-hash")


def test_token_carries_identity_and_role():
    token = create_access_token("usr_abc", "a@b.com", "chef")
    claims = decode_access_token(token)
    assert claims is not None
    assert claims["sub"] == "usr_abc"
    assert claims["email"] == "a@b.com"
    assert claims["role"] == "chef"


def test_token_signed_with_another_secret_is_rejected():
    forged = jwt.encode(
        {"sub": "usr_attacker", "role": "chef", "exp": time.time() + 3600},
        "wrong-secret",
        algorithm=ALGORITHM,
    )
    assert decode_access_token(forged) is None


def test_expired_token_is_rejected():
    settings = get_settings()
    expired = jwt.encode(
        {"sub": "usr_abc", "role": "customer", "exp": time.time() - 10},
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )
    assert decode_access_token(expired) is None


def test_garbage_token_is_rejected():
    assert decode_access_token("not.a.token") is None


@pytest.mark.parametrize(
    ("current", "expected"),
    [
        ("pending", "baking"),
        ("baking", "baked"),
        ("baked", "in_delivery"),
        ("in_delivery", None),  # end of the line
        ("cancelled", None),  # not part of the flow
        ("bogus", None),
    ],
)
def test_next_status(current, expected):
    assert next_status(current) == expected


def test_status_vocabulary_matches_the_spec():
    assert KITCHEN_FLOW == ("pending", "baking", "baked", "in_delivery")
    assert set(KITCHEN_STATUSES) == {*KITCHEN_FLOW, "cancelled"}


def test_only_pending_orders_are_customer_cancellable():
    """Once the kitchen starts baking, the food is committed."""
    assert CANCELLABLE == ("pending",)
