import type { NextRequest } from "next/server";

// Proxy to the Python backend. Doing this server-side sidesteps the browser
// CORS restriction noted in API.md (backend has no CORS configured yet).
const BACKEND_URL =
  process.env.BACKEND_URL ?? "https://client-neg-prc-agent-be.fastapicloud.dev";

export async function POST(request: NextRequest) {
  let body: { message?: unknown; thread_id?: unknown };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  const message = typeof body.message === "string" ? body.message.trim() : "";
  const threadId =
    typeof body.thread_id === "string" && body.thread_id.length > 0
      ? body.thread_id
      : "default";

  if (!message) {
    return Response.json({ error: "`message` is required." }, { status: 400 });
  }

  try {
    const res = await fetch(`${BACKEND_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, thread_id: threadId }),
      // Never cache negotiation turns.
      cache: "no-store",
    });

    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      return Response.json(
        {
          error: `The agent could not respond (status ${res.status}).`,
          detail: detail.slice(0, 500),
        },
        { status: 502 },
      );
    }

    const data = (await res.json()) as { reply?: string; thread_id?: string };
    return Response.json({
      reply: data.reply ?? "",
      thread_id: data.thread_id ?? threadId,
    });
  } catch {
    return Response.json(
      {
        error:
          "Couldn't reach the negotiation backend. Make sure it's running on " +
          BACKEND_URL +
          ".",
      },
      { status: 503 },
    );
  }
}
