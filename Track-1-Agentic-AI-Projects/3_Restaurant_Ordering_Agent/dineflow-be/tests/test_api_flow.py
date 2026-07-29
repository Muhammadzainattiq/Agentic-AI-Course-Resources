"""End-to-end API tests against a real Postgres.

Skipped unless TEST_DATABASE_URL points at a throwaway database:

    createdb dineflow_test
    TEST_DATABASE_URL=postgresql://localhost/dineflow_test uv run pytest tests/test_api_flow.py

Mongo (long-term memory) and the LLM are stubbed — this exercises auth, role
gating, ownership scoping, and the kitchen status flow, not the agent.
"""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

TEST_DB = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB, reason="TEST_DATABASE_URL not set; skipping DB-backed tests"
)

CHEF = {"email": "chef@gmail.com", "password": "chef@1234"}


@pytest.fixture
async def client(monkeypatch):
    """An app instance wired to the test database, with Mongo stubbed out."""
    monkeypatch.setenv("DATABASE_URL", TEST_DB)
    monkeypatch.setenv("JWT_SECRET", "integration-test-secret-at-least-32-bytes")

    from app.config import get_settings

    get_settings.cache_clear()

    from app.db import mongo, postgres

    # Long-term memory is out of scope here; keep it in-process.
    memories: list[dict] = []

    class FakeCollection:
        async def create_index(self, *a, **kw):
            return None

        def find(self, *a, **kw):
            class Cursor:
                def sort(self, *a, **kw):
                    return self

                def limit(self, *a, **kw):
                    return self

                def __aiter__(self):
                    async def gen():
                        for m in memories:
                            yield m

                    return gen()

            return Cursor()

        async def update_one(self, *a, **kw):
            return None

        async def delete_many(self, *a, **kw):
            class R:
                deleted_count = 0

            return R()

    monkeypatch.setattr(mongo, "init_mongo", lambda: _noop())
    monkeypatch.setattr(mongo, "close_mongo", lambda: _noop())
    monkeypatch.setattr(mongo, "memories", lambda: FakeCollection())

    from app.main import app

    await postgres.init_pool()
    await _reset(postgres)
    from app.auth.bootstrap import ensure_chef_account

    await ensure_chef_account()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await postgres.close_pool()


async def _noop():
    return None


async def _reset(postgres) -> None:
    """Clear data between tests, keeping the schema."""
    await postgres.execute(
        "TRUNCATE order_items, orders, conversation_messages, users RESTART IDENTITY CASCADE"
    )


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def signup(client, email="diner@example.com", **extra) -> tuple[str, dict]:
    res = await client.post(
        "/auth/signup",
        json={"email": email, "password": "sup3rsecret", "name": "Test Diner", **extra},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    return body["access_token"], body["user"]


async def chef_token(client) -> str:
    res = await client.post("/auth/login", json=CHEF)
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


# ── Auth ────────────────────────────────────────────────────────────────────


async def test_signup_creates_a_customer(client):
    _token, user = await signup(client)
    assert user["role"] == "customer"
    assert user["email"] == "diner@example.com"
    assert "password" not in user and "password_hash" not in user


async def test_signup_rejects_duplicate_email(client):
    await signup(client)
    res = await client.post(
        "/auth/signup",
        json={"email": "diner@example.com", "password": "another1", "name": "Impostor"},
    )
    assert res.status_code == 409


async def test_login_with_wrong_password_is_rejected(client):
    await signup(client)
    res = await client.post(
        "/auth/login", json={"email": "diner@example.com", "password": "wrong-one"}
    )
    assert res.status_code == 401


async def test_unknown_email_gives_the_same_error_as_a_wrong_password(client):
    """Don't leak which accounts exist."""
    res = await client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "whatever1"}
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Incorrect email or password"


async def test_protected_routes_require_a_token(client):
    for method, path in [
        ("get", "/auth/me"),
        ("get", "/orders"),
        ("get", "/kitchen/orders"),
        ("get", "/chat/memories"),
    ]:
        res = await getattr(client, method)(path)
        assert res.status_code == 401, f"{path} was not protected"


async def test_profile_update_persists(client):
    token, _ = await signup(client)
    res = await client.patch(
        "/auth/me", json={"address": "12 Flour Street"}, headers=auth(token)
    )
    assert res.status_code == 200
    assert res.json()["address"] == "12 Flour Street"

    me = await client.get("/auth/me", headers=auth(token))
    assert me.json()["address"] == "12 Flour Street"


# ── Role separation ─────────────────────────────────────────────────────────


async def test_chef_account_is_seeded_and_can_log_in(client):
    res = await client.post("/auth/login", json=CHEF)
    assert res.status_code == 200
    assert res.json()["user"]["role"] == "chef"


async def test_customer_cannot_reach_the_kitchen(client):
    token, _ = await signup(client)
    res = await client.get("/kitchen/orders", headers=auth(token))
    assert res.status_code == 403


async def test_chef_cannot_use_the_ordering_chat(client):
    token = await chef_token(client)
    res = await client.post("/chat", json={"message": "hi"}, headers=auth(token))
    assert res.status_code == 403


# ── Order ownership and the kitchen flow ────────────────────────────────────


async def _place_order(client, token, user_id) -> str:
    """Insert an order directly — the agent path needs a live LLM."""
    from app.db import postgres

    await postgres.execute(
        "INSERT INTO menu_items (name, category, price) VALUES ('Test Pizza', 'mains', 10.00)"
        " ON CONFLICT (name) DO NOTHING"
    )
    item_id = (await postgres.fetchrow("SELECT id FROM menu_items WHERE name='Test Pizza'"))["id"]
    order_id = f"ORD-{user_id[-6:].upper()}"
    await postgres.execute(
        """
        INSERT INTO orders (id, session_id, customer_id, status, subtotal, tax, total)
        VALUES ($1, 'sess_test', $2, 'pending', 10.00, 0.80, 10.80)
        """,
        order_id,
        user_id,
    )
    await postgres.execute(
        """
        INSERT INTO order_items (order_id, menu_item_id, name, quantity, unit_price)
        VALUES ($1, $2, 'Test Pizza', 1, 10.00)
        """,
        order_id,
        item_id,
    )
    return order_id


async def test_customer_sees_only_their_own_orders(client):
    token_a, user_a = await signup(client, email="a@example.com")
    token_b, _ = await signup(client, email="b@example.com")
    order_a = await _place_order(client, token_a, user_a["id"])

    mine = await client.get("/orders", headers=auth(token_a))
    assert [o["id"] for o in mine.json()] == [order_a]

    theirs = await client.get("/orders", headers=auth(token_b))
    assert theirs.json() == []

    # And can't fetch it directly by id either.
    direct = await client.get(f"/orders/{order_a}", headers=auth(token_b))
    assert direct.status_code == 404


async def test_chef_sees_every_order_with_customer_details(client):
    token, user = await signup(client)
    order_id = await _place_order(client, token, user["id"])

    res = await client.get("/kitchen/orders", headers=auth(await chef_token(client)))
    assert res.status_code == 200
    board = res.json()
    assert len(board) == 1
    assert board[0]["id"] == order_id
    assert board[0]["customer_name"] == "Test Diner"
    assert board[0]["customer_email"] == "diner@example.com"
    assert board[0]["next_status"] == "baking"
    assert board[0]["items"][0]["name"] == "Test Pizza"


async def test_chef_advances_an_order_through_the_whole_flow(client):
    token, user = await signup(client)
    order_id = await _place_order(client, token, user["id"])
    chef = auth(await chef_token(client))

    for status, expected_next in [
        ("baking", "baked"),
        ("baked", "in_delivery"),
        ("in_delivery", None),
    ]:
        res = await client.patch(
            f"/kitchen/orders/{order_id}/status", json={"status": status}, headers=chef
        )
        assert res.status_code == 200, res.text
        assert res.json()["status"] == status
        assert res.json()["next_status"] == expected_next

    # The change is real, not just echoed back: the customer sees it too.
    mine = await client.get("/orders", headers=auth(token))
    assert mine.json()[0]["status"] == "in_delivery"


async def test_chef_cannot_set_an_unknown_status(client):
    token, user = await signup(client)
    order_id = await _place_order(client, token, user["id"])
    res = await client.patch(
        f"/kitchen/orders/{order_id}/status",
        json={"status": "incinerated"},
        headers=auth(await chef_token(client)),
    )
    assert res.status_code == 400


async def test_customer_cannot_change_order_status(client):
    """The status endpoint is chef-only — no customer route touches it."""
    token, user = await signup(client)
    order_id = await _place_order(client, token, user["id"])
    res = await client.patch(
        f"/kitchen/orders/{order_id}/status",
        json={"status": "in_delivery"},
        headers=auth(token),
    )
    assert res.status_code == 403


async def test_kitchen_stats_counts_by_status(client):
    token, user = await signup(client)
    await _place_order(client, token, user["id"])
    res = await client.get("/kitchen/stats", headers=auth(await chef_token(client)))
    assert res.status_code == 200
    assert res.json()["pending"] == 1
    assert res.json()["total"] == 1


# ── Conversation scoping ────────────────────────────────────────────────────


async def test_history_of_another_users_session_is_not_readable(client):
    from app.db import postgres

    token_a, user_a = await signup(client, email="a@example.com")
    token_b, _ = await signup(client, email="b@example.com")

    await postgres.execute(
        """
        INSERT INTO conversation_messages (session_id, customer_id, role, content)
        VALUES ('sess_private', $1, 'user', 'my usual please')
        """,
        user_a["id"],
    )

    mine = await client.get(
        "/chat/history", params={"session_id": "sess_private"}, headers=auth(token_a)
    )
    assert mine.status_code == 200
    assert mine.json()[0]["content"] == "my usual please"

    theirs = await client.get(
        "/chat/history", params={"session_id": "sess_private"}, headers=auth(token_b)
    )
    assert theirs.status_code == 404
