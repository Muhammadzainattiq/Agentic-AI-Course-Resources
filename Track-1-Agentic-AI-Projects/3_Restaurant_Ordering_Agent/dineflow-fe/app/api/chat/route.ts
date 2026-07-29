import { proxy } from "@/lib/backend";

export const runtime = "nodejs";
export const maxDuration = 60; // agent turns with tool calls can be slow

export async function POST(req: Request) {
  const body = await req.text();
  return proxy("/chat", { method: "POST", body });
}
