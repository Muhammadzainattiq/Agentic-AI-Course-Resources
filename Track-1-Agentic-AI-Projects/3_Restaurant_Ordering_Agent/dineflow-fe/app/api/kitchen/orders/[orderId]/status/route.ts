import { proxy } from "@/lib/backend";

export const runtime = "nodejs";

export async function PATCH(
  req: Request,
  ctx: RouteContext<"/api/kitchen/orders/[orderId]/status">,
) {
  const { orderId } = await ctx.params;
  const body = await req.text();
  return proxy(`/kitchen/orders/${encodeURIComponent(orderId)}/status`, {
    method: "PATCH",
    body,
  });
}
