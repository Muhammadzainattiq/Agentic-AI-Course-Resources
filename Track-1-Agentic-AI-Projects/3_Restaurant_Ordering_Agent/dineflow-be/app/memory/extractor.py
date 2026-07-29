"""Long-term memory extractor.

Runs after each turn on (user query + ai response) and distils anything durable
about the customer into structured memories. Deliberately a small, cheap model —
it never talks to the customer.
"""

from __future__ import annotations

import logging

from agents import Agent, Runner
from pydantic import BaseModel

from app.config import get_settings
from app.memory.long_term import Memory, upsert_many

logger = logging.getLogger(__name__)

EXTRACTOR_INSTRUCTIONS = """\
You extract durable, long-term facts about a restaurant customer from a single
conversation turn.

Extract ONLY things that stay true beyond this conversation:
- personal_data: name, phone number, delivery address
- preference: favourite dishes, spice level, drink of choice, portion size
- dietary: allergies, vegetarian/vegan/halal, intolerances
- order_habit: recurring patterns ("always orders on Fridays", "usually pays by card")

Do NOT extract:
- anything about the current order in progress (quantities, cart contents, order ids)
- transient state ("wants it in 10 minutes", "is hungry right now")
- facts about the restaurant, the menu, or the assistant
- guesses, inferences, or anything the customer did not actually state

Use stable snake_case keys so repeat mentions overwrite instead of duplicating
(`name`, `phone`, `address`, `spice_level`, `allergy_peanuts`, ...).
Phrase each value as a short standalone statement.
If there is nothing durable in the turn, return an empty list.\
"""


class ExtractionResult(BaseModel):
    memories: list[Memory]


def build_extractor() -> Agent:
    return Agent(
        name="Memory Extractor",
        instructions=EXTRACTOR_INSTRUCTIONS,
        model=get_settings().openai_extractor_model,
        output_type=ExtractionResult,
    )


async def extract_and_store(customer_id: str, user_query: str, ai_response: str) -> int:
    """Extract memories from one turn and persist them. Never raises."""
    if not get_settings().memory_extraction_enabled:
        return 0

    turn = f"Customer said:\n{user_query}\n\nAssistant replied:\n{ai_response}"
    try:
        result = await Runner.run(build_extractor(), turn, max_turns=2)
        extracted: ExtractionResult = result.final_output
        stored = await upsert_many(customer_id, extracted.memories)
        if stored:
            logger.info("Stored %d long-term memories for %s", stored, customer_id)
        return stored
    except Exception:
        # Memory extraction is best-effort: a failure here must not break the chat.
        logger.exception("Memory extraction failed for customer %s", customer_id)
        return 0
