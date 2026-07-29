import { proxy } from "@/lib/backend";

export const runtime = "nodejs";

export async function GET() {
  return proxy("/kitchen/stats");
}
