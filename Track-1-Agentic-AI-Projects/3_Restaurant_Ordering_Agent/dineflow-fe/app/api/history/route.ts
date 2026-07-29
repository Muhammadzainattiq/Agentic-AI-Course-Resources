import { proxy } from "@/lib/backend";

export const runtime = "nodejs";

export async function GET(req: Request) {
  const sessionId = new URL(req.url).searchParams.get("session_id");
  if (!sessionId) {
    return Response.json({ detail: "session_id is required" }, { status: 400 });
  }
  return proxy(`/chat/history?session_id=${encodeURIComponent(sessionId)}`);
}
