"""The kitchen order lifecycle, in one place.

    pending → baking → baked → in_delivery
       └──────────────────────────→ cancelled (customer, before baking starts)

Keep this in sync with the `orders_status_check` constraint in db/schema.sql.
"""

from __future__ import annotations

# Order matters: this is the sequence the chef advances through.
KITCHEN_FLOW: tuple[str, ...] = ("pending", "baking", "baked", "in_delivery")

KITCHEN_STATUSES: tuple[str, ...] = (*KITCHEN_FLOW, "cancelled")

# Statuses a customer may still cancel from.
CANCELLABLE: tuple[str, ...] = ("pending",)

LABELS: dict[str, str] = {
    "pending": "Pending",
    "baking": "Baking",
    "baked": "Baked",
    "in_delivery": "In Delivery",
    "cancelled": "Cancelled",
}


def next_status(current: str) -> str | None:
    """The next step in the flow, or None if there is nowhere further to go."""
    if current not in KITCHEN_FLOW:
        return None
    index = KITCHEN_FLOW.index(current)
    return KITCHEN_FLOW[index + 1] if index + 1 < len(KITCHEN_FLOW) else None
