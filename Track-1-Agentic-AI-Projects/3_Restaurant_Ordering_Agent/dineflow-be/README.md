# DineFlow — Backend

FastAPI + OpenAI Agents SDK. Serves one conversational ordering agent backed by
two databases: Postgres (Neon) for short-term memory and ordering, MongoDB for
long-term memory.

## Turn lifecycle

```
long-term memory (Mongo) ──┐
short-term history (PG) ───┼─→ Agent (gpt-5) ⇄ tools ⇄ Postgres (menu, orders)
user query ────────────────┘        │
                                    └─→ response ─→ extractor (gpt-5-mini) ─→ Mongo
```

1. `long_term.as_prompt_block()` pulls the customer's stored facts into the system prompt.
2. `short_term.history()` replays the last `SHORT_TERM_WINDOW` turns from Postgres.
3. The agent runs, calling `get_menu` / `search_menu` / `place_order` /
   `get_order_status` / `cancel_order` against Postgres.
4. The turn is appended to short-term memory.
5. The extractor distils anything durable (name, address, allergies, preferences)
   into Mongo, keyed so repeat mentions overwrite rather than duplicate.

Session and customer identity live in the run context, never in tool arguments —
the model cannot place or cancel an order on someone else's account.

## Layout

```
app/
  main.py               FastAPI wiring, CORS, lifespan, /health
  config.py             env-backed settings (see .env.example)
  schemas.py            request/response models
  seed.py               idempotent menu seeder
  db/
    postgres.py         asyncpg pool; applies schema.sql on startup
    schema.sql          customers, conversation_messages, menu_items, orders, order_items
    mongo.py            motor client + indexes
  memory/
    short_term.py       transcript in Postgres
    long_term.py        durable facts in Mongo
    extractor.py        post-turn memory extraction agent
  agent/
    dineflow_agent.py   assembles memory + prompt + tools, runs a turn
    prompts.py          system prompt
    tools.py            menu + ordering + status tools
  routers/
    chat.py  menu.py  orders.py
```

## Run locally

```bash
cp .env.example .env      # then fill in OPENAI_API_KEY, DATABASE_URL, MONGODB_URI
uv sync
uv run python -m app.seed              # seed the menu (idempotent)
uv run uvicorn app.main:app --reload   # http://localhost:8000/docs
```

`init_pool()` applies `schema.sql` on every startup, so there is no migration step.

## Test and lint

```bash
uv run pytest -q
uv run ruff check app tests
```

## Deploy — Hugging Face Docker Space

The `Dockerfile` listens on `$PORT` (7860 on Spaces) and runs as a non-root user,
as Spaces requires. Push the repo to a Space with SDK `docker`, then set
`OPENAI_API_KEY`, `DATABASE_URL`, `MONGODB_URI`, and `CORS_ALLOW_ORIGINS` (your
Vercel URL) as **Repository secrets**, not plain variables.

## Accounts and roles

Two roles, both rows in `users`:

- **customer** — self-registers at `/auth/signup`. Owns their profile, their
  conversations, their memories, and their orders.
- **chef** — a single account seeded on startup from `CHEF_EMAIL` /
  `CHEF_PASSWORD`. There is deliberately no chef signup route.

Auth is a bearer JWT (HS256). Every request re-reads the user from Postgres, so
a deleted or role-changed account cannot keep trading on an old token. Identity
is taken from the token, never from the request body or a tool argument.

## Order lifecycle

```
pending ──→ baking ──→ baked ──→ in_delivery
   └──→ cancelled          (customer only, while still pending)
```

Only the chef moves an order forward, via `PATCH /kitchen/orders/{id}/status`.
The vocabulary lives in `app/orders_status.py` and the matching CHECK constraint
in `db/schema.sql`.

## API

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/auth/signup` | — | Register a customer, returns a token |
| `POST` | `/auth/login` | — | Log in as customer or chef |
| `GET` `PATCH` | `/auth/me` | any | Read / update your profile |
| `POST` | `/chat` | customer | Send a message, get the agent's reply |
| `GET` | `/chat/history?session_id=` | any | Replay your short-term memory |
| `DELETE` | `/chat/session?session_id=` | any | Clear a session (memories survive) |
| `GET` `DELETE` | `/chat/memories` | any | Inspect / forget your long-term memories |
| `GET` | `/menu`, `/menu/categories` | — | Menu for the UI |
| `GET` | `/orders`, `/orders/{id}` | any | *Your own* orders only |
| `GET` | `/kitchen/orders` | chef | Every order, with customer details |
| `PATCH` | `/kitchen/orders/{id}/status` | chef | Move an order along the line |
| `GET` | `/kitchen/stats` | chef | Counts per status |
| `GET` | `/health` | — | Postgres + Mongo connectivity |

## Schema migrations

`schema.sql` is applied on every startup and is written to be idempotent — it
renames the pre-auth `customers` table to `users`, backfills the auth columns,
and remaps old order statuses onto the new vocabulary. Running it against a
fresh database and against a v0 database both produce the same result.
