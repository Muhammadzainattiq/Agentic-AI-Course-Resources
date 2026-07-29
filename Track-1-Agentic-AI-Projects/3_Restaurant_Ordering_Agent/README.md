# DineFlow

A conversational restaurant ordering agent. Customers chat; DineFlow reads the
menu, takes the order, and tracks it — remembering their name, address, allergies
and preferences across conversations.

| Layer | Choice |
| --- | --- |
| Frontend | Next.js 16 (App Router) on Vercel — `dineflow-fe/` |
| Backend | FastAPI on Hugging Face Docker Spaces — `dineflow-be/` |
| Agent framework | OpenAI Agents SDK |
| LLM | OpenAI `gpt-5` (extractor on `gpt-5-mini`) |
| Short-term memory + ordering | Postgres (Neon serverless) |
| Long-term memory | MongoDB |

## Architecture

```
                ┌──────────────── Backend (FastAPI) ────────────────┐
                │                                                   │
                │   long-term memories ──┐        ┌──→ extractor ──→ MongoDB
                │   (MongoDB)            │        │    (gpt-5-mini)
                │                        ▼        │
  Browser  ──── │   system prompt ──→  Agent (gpt-5)                │
  (Next.js)     │                        ▲   │                      │
           ◄─── │   short-term history ──┘   │ tool calls           │
                │   (Postgres)               ▼                      │
                │                    menu · ordering · status       │
                │                          (Postgres)               │
                └───────────────────────────────────────────────────┘
```

The browser never talks to FastAPI directly — Next.js route handlers in
`dineflow-fe/app/api/*` proxy to it, so the backend URL and auth token stay
server-side.

## Quick start

```bash
# 1. Backend
cd dineflow-be
cp .env.example .env          # fill in OPENAI_API_KEY, DATABASE_URL, MONGODB_URI
uv sync
uv run python -m app.seed
uv run uvicorn app.main:app --reload   # :8000

# 2. Frontend (new terminal)
cd dineflow-fe
cp .env.example .env.local    # BACKEND_URL=http://localhost:8000
npm install
npm run dev                   # :3000
```

See `dineflow-be/README.md` for the API surface and the turn lifecycle.

## Accounts

| Role | How to get one | Lands on |
| --- | --- | --- |
| Customer | Sign up at `/signup` | `/` — chat, menu, your orders |
| Chef | Seeded on startup: `chef@gmail.com` / `chef@1234` | `/chef` — every order, live |

Both roles are `users` rows in Postgres. A customer's short-term transcript, their
long-term memories, and their orders are all keyed to their user id, so nothing
leaks between accounts. The chef sees every order and is the only role that can
change an order's status:

```
pending ──→ baking ──→ baked ──→ in_delivery
```

Change the chef credentials with `CHEF_EMAIL` / `CHEF_PASSWORD` before deploying.

## Environment variables

Each side has its own `.env.example`. The three with no default — the app will
not boot without them — are all in the backend:

- `OPENAI_API_KEY`
- `DATABASE_URL` (Neon pooled connection string)
- `MONGODB_URI`
- `JWT_SECRET` — 32+ bytes; generate with
  `python -c "import secrets; print(secrets.token_urlsafe(48))"`
