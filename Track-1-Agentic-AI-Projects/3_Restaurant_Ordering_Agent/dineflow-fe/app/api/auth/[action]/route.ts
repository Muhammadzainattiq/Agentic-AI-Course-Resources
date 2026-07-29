/**
 * Login and signup. The backend returns a bearer token; we store it in an
 * httpOnly cookie so page JavaScript (and therefore XSS) can never read it.
 */

import { cookies } from "next/headers";
import { SESSION_COOKIE, proxy } from "@/lib/backend";

export const runtime = "nodejs";

const ALLOWED = new Set(["login", "signup"]);

export async function POST(
  req: Request,
  ctx: RouteContext<"/api/auth/[action]">,
) {
  const { action } = await ctx.params;
  if (!ALLOWED.has(action)) {
    return Response.json({ detail: "Not found" }, { status: 404 });
  }

  const body = await req.text();
  const res = await proxy(`/auth/${action}`, { method: "POST", body, auth: false });
  const payload = await res.json();

  if (!res.ok) {
    return Response.json(payload, { status: res.status });
  }

  (await cookies()).set(SESSION_COOKIE, payload.access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: payload.expires_in,
  });

  // The token itself stays server-side; the client only needs the profile.
  return Response.json({ user: payload.user });
}
