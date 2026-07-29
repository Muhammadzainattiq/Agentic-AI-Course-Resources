"""DineFlow backend — FastAPI app wiring."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.bootstrap import ensure_chef_account
from app.config import get_settings
from app.db import mongo, postgres
from app.routers import auth, chat, kitchen, menu, orders

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("dineflow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await postgres.init_pool()
    await mongo.init_mongo()
    await ensure_chef_account()
    logger.info("DineFlow backend up (env=%s, model=%s)", settings.environment, settings.openai_model)
    yield
    await postgres.close_pool()
    await mongo.close_mongo()


app = FastAPI(
    title="DineFlow API",
    description="Restaurant ordering agent — menu, ordering, and conversational memory.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(menu.router)
app.include_router(orders.router)
app.include_router(kitchen.router)


@app.get("/", tags=["health"])
async def root() -> dict[str, str]:
    return {"service": "DineFlow", "status": "ok", "docs": "/docs"}


@app.get("/health", tags=["health"])
async def health() -> dict[str, object]:
    checks: dict[str, object] = {"postgres": False, "mongo": False}
    try:
        await postgres.fetchrow("SELECT 1")
        checks["postgres"] = True
    except Exception as exc:  # noqa: BLE001 — health checks report, never raise
        checks["postgres_error"] = str(exc)
    try:
        await mongo.get_db().command("ping")
        checks["mongo"] = True
    except Exception as exc:  # noqa: BLE001 — health checks report, never raise
        checks["mongo_error"] = str(exc)
    checks["status"] = "ok" if checks["postgres"] and checks["mongo"] else "degraded"
    return checks
