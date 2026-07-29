"""The DineFlow agent: assembles memory + prompt + tools, runs a turn, extracts memory.

One turn, end to end:
    long-term memory (Mongo) ──┐
    short-term history (PG) ───┼─→ Agent(gpt-5) ⇄ tools (menu / ordering / status, PG)
    user query ────────────────┘        │
                                        └─→ response ─→ extractor ─→ Mongo
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from agents import Agent, Runner

from app.agent.prompts import build_instructions
from app.agent.tools import ORDER_TOOLS, OrderContext
from app.auth.models import User
from app.config import get_settings
from app.memory import extractor, long_term, short_term

logger = logging.getLogger(__name__)


@dataclass
class TurnResult:
    response: str
    session_id: str
    memories_stored: int


def build_agent(instructions: str) -> Agent[OrderContext]:
    settings = get_settings()
    return Agent[OrderContext](
        name="DineFlow",
        instructions=instructions,
        model=settings.openai_model,
        tools=ORDER_TOOLS,
    )


def profile_block(user: User) -> str:
    """Account details the customer already gave us at signup."""
    fields = [
        ("Name", user.name),
        ("Email", user.email),
        ("Phone", user.phone),
        ("Default delivery address", user.address),
    ]
    return "\n".join(f"- {label}: {value}" for label, value in fields if value)


async def run_turn(session_id: str, user: User, user_query: str) -> TurnResult:
    settings = get_settings()
    customer_id = user.id

    # 1. Assemble context: long-term memories into the prompt, short-term into the input.
    memories = await long_term.as_prompt_block(customer_id)
    instructions = build_instructions(
        settings.restaurant_name,
        settings.restaurant_currency,
        settings.restaurant_tax_rate,
        memories,
        profile_block(user),
    )
    history = await short_term.history(session_id)
    agent_input = [*history, {"role": "user", "content": user_query}]

    # 2. Run the agent (it may call tools against Postgres).
    result = await Runner.run(
        build_agent(instructions),
        agent_input,
        context=OrderContext(
            session_id=session_id,
            customer_id=customer_id,
            default_address=user.address,
        ),
        max_turns=settings.agent_max_turns,
    )
    response = str(result.final_output)

    # 3. Append the turn to short-term memory.
    await short_term.append(session_id, customer_id, "user", user_query)
    await short_term.append(session_id, customer_id, "assistant", response)

    # 4. Distil anything durable into long-term memory.
    stored = await extractor.extract_and_store(customer_id, user_query, response)

    return TurnResult(response=response, session_id=session_id, memories_stored=stored)
