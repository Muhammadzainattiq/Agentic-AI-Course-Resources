import { proxy } from "@/lib/backend";

export const runtime = "nodejs";

// The backend scopes this to the token holder — no customer_id to pass.
export async function GET() {
  return proxy("/orders");
}
