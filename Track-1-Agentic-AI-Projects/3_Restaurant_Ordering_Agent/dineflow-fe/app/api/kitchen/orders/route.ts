import { proxy } from "@/lib/backend";

export const runtime = "nodejs";

export async function GET(req: Request) {
  const status = new URL(req.url).searchParams.get("status");
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return proxy(`/kitchen/orders${qs}`);
}
