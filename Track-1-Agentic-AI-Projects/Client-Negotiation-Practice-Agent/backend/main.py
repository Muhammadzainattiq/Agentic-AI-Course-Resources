from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from agent import get_agent, lifespan_agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with lifespan_agent():
        yield


app = FastAPI(title="Client Negotiation Practice Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    # Identifies a conversation. Reuse the same thread_id to continue a session;
    # the Postgres checkpointer restores that thread's history automatically.
    thread_id: str = "default"


class ChatResponse(BaseModel):
    reply: str
    thread_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    agent = get_agent()
    config = {"configurable": {"thread_id": req.thread_id}}

    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=req.message)]},
        config=config,
    )

    reply = result["messages"][-1].content
    return ChatResponse(reply=reply, thread_id=req.thread_id)
