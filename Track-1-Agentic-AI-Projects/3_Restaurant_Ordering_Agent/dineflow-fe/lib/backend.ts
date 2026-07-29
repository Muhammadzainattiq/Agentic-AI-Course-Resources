/** Server-only helper for talking to the FastAPI backend. */

import "server-only";
import { cookies } from "next/headers";

const BACKEND_URL = (
  process.env.BACKEND_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

/** Name of the httpOnly cookie holding the backend access token. */
export const SESSION_COOKIE = "dineflow_token";

export async function getToken(): Promise<string | undefined> {
  return (await cookies()).get(SESSION_COOKIE)?.value;
}

async function backendHeaders(auth: boolean): Promise<HeadersInit> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };

  if (auth) {
    const token = await getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  if (process.env.API_AUTH_TOKEN) {
    headers["X-Api-Key"] = process.env.API_AUTH_TOKEN;
  }
  return headers;
}

/**
 * Proxy a request to the backend and pass the response straight through,
 * attaching the caller's access token from the httpOnly cookie.
 */
export async function proxy(
  path: string,
  init?: RequestInit & { auth?: boolean },
): Promise<Response> {
  const { auth = true, ...requestInit } = init ?? {};
  const timeout = Number(process.env.BACKEND_TIMEOUT_MS ?? 60_000);

  try {
    const res = await fetch(`${BACKEND_URL}${path}`, {
      ...requestInit,
      headers: {
        ...(await backendHeaders(auth)),
        ...(requestInit.headers ?? {}),
      },
      cache: "no-store",
      signal: AbortSignal.timeout(timeout),
    });
    const body = await res.text();
    return new Response(body, {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Backend unreachable";
    return Response.json({ detail: message }, { status: 502 });
  }
}

/** Read the signed-in user server-side. Returns null when not logged in. */
export async function getCurrentUser(): Promise<{
  id: string;
  email: string;
  name: string | null;
  phone: string | null;
  address: string | null;
  role: "customer" | "chef";
} | null> {
  const token = await getToken();
  if (!token) return null;

  const res = await proxy("/auth/me");
  if (!res.ok) return null;
  return res.json();
}
