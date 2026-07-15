"""LangGraph negotiation agent with a PostgreSQL checkpointer for short-term memory.

The checkpointer persists the conversation state per `thread_id`, so each chat
session keeps its own running history in Postgres between requests.
"""

from contextlib import asynccontextmanager

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from config import settings
from prompts import SYSTEM_PROMPT

# Populated during app startup (see main.py lifespan).
agent: CompiledStateGraph | None = None


@asynccontextmanager
async def lifespan_agent():
    """Open a Postgres checkpointer pool and build the agent for the app's lifetime."""
    global agent

    async with AsyncPostgresSaver.from_conn_string(settings.database_url) as checkpointer:
        # Creates the checkpoint tables if they don't exist yet.
        await checkpointer.setup()

        llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.7,
        )

        agent = create_react_agent(
            model=llm,
            tools=[],  # no tools yet — pure role-play agent
            prompt=SYSTEM_PROMPT,
            checkpointer=checkpointer,
        )

        yield
        agent = None


def get_agent() -> CompiledStateGraph:
    if agent is None:
        raise RuntimeError("Agent not initialized. Is the app running via its lifespan?")
    return agent
