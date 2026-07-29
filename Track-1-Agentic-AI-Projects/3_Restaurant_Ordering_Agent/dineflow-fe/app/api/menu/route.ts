import { proxy } from "@/lib/backend";

export const runtime = "nodejs";

export async function GET(req: Request) {
  const category = new URL(req.url).searchParams.get("category");
  const qs = category ? `?category=${encodeURIComponent(category)}` : "";
  return proxy(`/menu${qs}`);
}
