"""Tool-level tests. Postgres is stubbed — these check tool logic, not SQL execution."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from agents.tool_context import ToolContext

from app.agent.tools import ORDER_TOOLS, OrderContext
from app.db import postgres

TOOLS = {t.name: t for t in ORDER_TOOLS}

MENU_ROWS = [
    {
        "id": 1,
        "name": "Margherita Pizza",
        "category": "mains",
        "description": "Tomato, mozzarella, basil.",
        "price": Decimal("12.00"),
        "tags": ["vegetarian"],
    },
    {
        "id": 2,
        "name": "Fresh Lemonade",
        "category": "drinks",
        "description": "Lemon, mint.",
        "price": Decimal("3.50"),
        "tags": ["vegan"],
    },
]


async def call(tool_name: str, **kwargs) -> str:
    args = json.dumps(kwargs)
    ctx = ToolContext(
        OrderContext(session_id="sess_test", customer_id="cust_test"),
        tool_name=tool_name,
        tool_call_id=f"call_{tool_name}",
        tool_arguments=args,
    )
    return await TOOLS[tool_name].on_invoke_tool(ctx, args)


@pytest.fixture
def stub_menu(monkeypatch):
    async def fake_fetch(query: str, *args):
        return MENU_ROWS if "menu_items" in query else []

    monkeypatch.setattr(postgres, "fetch", fake_fetch)


async def test_get_menu_lists_items_with_prices(stub_menu):
    out = await call("get_menu")
    assert "Margherita Pizza" in out
    assert "12.0 USD" in out
    assert "tags: vegetarian" in out


async def test_get_menu_handles_empty_result(monkeypatch):
    async def empty(query, *args):
        return []

    monkeypatch.setattr(postgres, "fetch", empty)
    assert "No menu items match" in await call("get_menu", category="sushi")


async def test_place_order_rejects_mismatched_lengths():
    out = await call("place_order", item_ids=[1, 2], quantities=[1])
    assert "same length" in out


async def test_place_order_rejects_empty_order():
    out = await call("place_order", item_ids=[], quantities=[])
    assert "empty order" in out


async def test_place_order_rejects_zero_quantity():
    out = await call("place_order", item_ids=[1], quantities=[0])
    assert "at least 1" in out


async def test_place_order_rejects_unknown_menu_item(stub_menu):
    """Item 99 is not in the menu, so the order must be refused, not invented."""
    out = await call("place_order", item_ids=[99], quantities=[1])
    assert "do not exist or are unavailable" in out
    assert "99" in out


async def test_place_order_computes_totals_with_tax(monkeypatch):
    captured: dict = {}

    async def fake_fetch(query, *args):
        return MENU_ROWS

    class FakeConn:
        def transaction(self):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def execute(self, query, *args):
            captured["order"] = args

        async def executemany(self, query, rows):
            captured["items"] = rows

    class FakePool:
        def acquire(self):
            return FakeConn()

    monkeypatch.setattr(postgres, "fetch", fake_fetch)
    monkeypatch.setattr(postgres, "get_pool", lambda: FakePool())

    # 2x pizza (12.00) + 1x lemonade (3.50) = 27.50 subtotal, 8% tax = 2.20, total 29.70
    out = await call("place_order", item_ids=[1, 2], quantities=[2, 1], address="1 Main St")

    assert "27.5 USD" in out  # subtotal
    assert "2.2 USD" in out  # tax
    assert "29.7 USD" in out  # total
    assert "Delivery to 1 Main St" in out
    assert "2x Margherita Pizza" in out

    # Identity comes from the run context, never from the model's arguments.
    _order_id, session_id, customer_id, *_ = captured["order"]
    assert session_id == "sess_test"
    assert customer_id == "cust_test"
    assert len(captured["items"]) == 2


async def test_get_order_status_reports_no_order(monkeypatch):
    async def none(query, *args):
        return None

    monkeypatch.setattr(postgres, "fetchrow", none)
    assert "No matching order" in await call("get_order_status")


async def test_cancel_order_refuses_when_not_cancellable(monkeypatch):
    async def none(query, *args):
        return None

    monkeypatch.setattr(postgres, "fetchrow", none)
    out = await call("cancel_order", order_id="ORD-XYZ")
    assert "Could not cancel" in out
