"""The system prompt is a `.format()` template, which makes literal braces a
runtime footgun: one stray `{` breaks every chat turn. These tests pin that
down, plus the facts the prompt promises the customer.
"""

from __future__ import annotations

import pytest

from app.agent.prompts import SYSTEM_PROMPT, build_instructions
from app.config import get_settings
from app.orders_status import LABELS


@pytest.fixture
def rendered() -> str:
    return build_instructions(
        restaurant_name="Dine&Rush",
        currency="PKR",
        tax_rate=0.05,
        memories="- [preference] spice_level: likes it hot",
        profile="- Name: Aisha Khan",
    )


def test_template_has_no_unescaped_braces(rendered):
    """Every `{...}` in the template must be a real placeholder."""
    assert "{" not in rendered
    assert "}" not in rendered


def test_all_placeholders_are_supplied(rendered):
    assert "Dine&Rush" in rendered
    assert "PKR" in rendered
    assert "Aisha Khan" in rendered
    assert "likes it hot" in rendered


def test_quoted_tax_matches_the_rate_it_was_built_with(rendered):
    """The prompt must never promise a different tax than place_order charges."""
    assert "Tax of 5% is added at checkout." in rendered
    assert "8%" not in rendered


def test_default_tax_rate_flows_through_unchanged():
    settings = get_settings()
    out = build_instructions("X", "PKR", settings.restaurant_tax_rate, "", "")
    assert f"Tax of {settings.restaurant_tax_rate * 100:.0f}%" in out


def test_missing_profile_degrades_to_a_sentence():
    out = build_instructions("X", "PKR", 0.05, "no memories", profile="")
    assert "No profile details saved." in out


def test_prompt_teaches_the_dish_cards_block(rendered):
    """The UI renders ```dish-cards as a photo grid — the prompt must ask for it
    by exactly that name, and must say to emit ids only."""
    assert "```dish-cards" in rendered
    assert "[14, 17, 12]" in rendered
    assert "You never write out the name, price or description yourself" in rendered


def test_prompt_forbids_inventing_dish_ids(rendered):
    assert "Never guess one." in rendered


def test_prompt_still_teaches_tables_for_non_dish_data(rendered):
    assert "---:" in rendered  # right-aligned numeric column
    assert "Plain Markdown tables are still right" in rendered


def test_prompt_guards_against_dumping_the_whole_menu(rendered):
    assert "Never dump the whole menu." in rendered


def test_prompt_uses_the_real_status_vocabulary(rendered):
    for status in ("pending", "baking", "baked", "in_delivery"):
        assert LABELS[status] in rendered


def test_template_is_the_single_source_of_the_placeholder_set():
    """Adding a placeholder without wiring it up should fail loudly here."""
    import string

    placeholders = {
        name for _, name, _, _ in string.Formatter().parse(SYSTEM_PROMPT) if name
    }
    assert placeholders == {
        "restaurant_name",
        "currency",
        "tax_pct",
        "profile",
        "memories",
    }
