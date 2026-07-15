# Client Negotiation Practice Agent — API

Backend for a chat-based negotiation practice agent. The agent role-plays as a
client so the user can practice negotiating. Conversation history is kept
server-side per session, so the frontend only needs to send the latest message.

## Base URL

```
http://localhost:8000
```

Interactive docs (Swagger UI): `http://localhost:8000/docs`

## Conversation model

- Each conversation is identified by a **`thread_id`** (any string you choose,
  e.g. a UUID per practice session).
- The backend stores the full history for that `thread_id`. **Send only the new
  message each turn** — do NOT resend prior messages.
- Reuse the same `thread_id` to continue a conversation; use a new one to start
  a fresh scenario.

---

## Endpoints

### `GET /health`

Health check.

**Response `200`**
```json
{ "status": "ok" }
```

---

### `POST /chat`

Send a message to the agent and get its reply.

**Request body** (`application/json`)

| Field       | Type   | Required | Description                                              |
|-------------|--------|----------|----------------------------------------------------------|
| `message`   | string | yes      | The user's latest message.                               |
| `thread_id` | string | no       | Conversation id. Defaults to `"default"`. Pass a unique value per session. |

```json
{
  "message": "I can offer $2000 for the full project.",
  "thread_id": "session-abc-123"
}
```

**Response `200`** (`application/json`)

| Field       | Type   | Description                          |
|-------------|--------|--------------------------------------|
| `reply`     | string | The agent's (client's) response.     |
| `thread_id` | string | Echoes the conversation id used.     |

```json
{
  "reply": "$2000 feels steep for what you've described. A competitor quoted me less — what makes your offer worth the premium?",
  "thread_id": "session-abc-123"
}
```

**Errors**

| Status | When |
|--------|------|
| `422`  | Body validation failed (e.g. `message` missing). |
| `500`  | Server/agent error (LLM or database issue).      |

---

## Example (fetch)

```js
async function sendMessage(message, threadId) {
  const res = await fetch("http://localhost:8000/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, thread_id: threadId }),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
  const data = await res.json();
  return data.reply;
}
```

## Example (curl)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hi, I wanted to discuss the project scope.", "thread_id": "demo-1"}'
```

## Notes for the frontend

- **CORS:** not configured yet. If you call from a browser on a different
  origin, ask the backend dev to enable CORS for your dev URL.
- **Streaming:** not supported yet — `/chat` returns the full reply in one
  response.
- **Auth:** none currently. `thread_id` is trusted as-is; treat it as a
  non-secret session key.
- **Latency:** each call round-trips to GPT-4o, so expect ~1–5s per reply. Show
  a loading state.
