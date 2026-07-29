/**
 * Client for the DineFlow backend.
 *
 * Browser calls go through the Next.js route handlers in `app/api/*`, which
 * attach the access token from an httpOnly cookie and proxy to FastAPI. The
 * token itself is never visible to page JavaScript.
 */

export type Role = "customer" | "chef";

export interface User {
  id: string;
  email: string;
  name: string | null;
  phone: string | null;
  address: string | null;
  role: Role;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  customer_id: string;
  memories_stored: number;
}

export interface MenuItem {
  id: number;
  name: string;
  category: string;
  description: string;
  price: number;
  tags: string[];
  is_available: boolean;
  /** Served from /public; null until a dish gets its own photo. */
  image_url: string | null;
}

export interface OrderItem {
  name: string;
  quantity: number;
  unit_price: number;
}

export interface Order {
  id: string;
  status: OrderStatus;
  subtotal: number;
  tax: number;
  total: number;
  address: string | null;
  notes: string | null;
  created_at: string;
  items: OrderItem[];
}

export interface KitchenOrder extends Order {
  updated_at: string;
  customer_name: string | null;
  customer_email: string | null;
  customer_phone: string | null;
  next_status: OrderStatus | null;
}

export type OrderStatus =
  | "pending"
  | "baking"
  | "baked"
  | "in_delivery"
  | "cancelled";

/** The chef advances an order through these, in order. */
export const KITCHEN_FLOW: OrderStatus[] = [
  "pending",
  "baking",
  "baked",
  "in_delivery",
];

export const STATUS_LABEL: Record<OrderStatus, string> = {
  pending: "Pending",
  baking: "Baking",
  baked: "Baked",
  in_delivery: "In Delivery",
  cancelled: "Cancelled",
};

async function json<T>(res: Response): Promise<T> {
  const payload = await res.json().catch(() => null);
  if (!res.ok) {
    const detail =
      (payload && (payload.detail ?? payload.message)) ||
      `Request failed with ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return payload as T;
}

// ── Auth ────────────────────────────────────────────────────────────────────

export async function login(email: string, password: string): Promise<User> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return (await json<{ user: User }>(res)).user;
}

export async function signup(input: {
  email: string;
  password: string;
  name: string;
  phone?: string;
  address?: string;
}): Promise<User> {
  const res = await fetch("/api/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return (await json<{ user: User }>(res)).user;
}

export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST" });
}

// ── Customer ────────────────────────────────────────────────────────────────

export async function sendMessage(
  message: string,
  sessionId: string | null,
): Promise<ChatResponse> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  return json<ChatResponse>(res);
}

export async function fetchMenu(): Promise<MenuItem[]> {
  return json<MenuItem[]>(await fetch("/api/menu"));
}

export async function fetchOrders(): Promise<Order[]> {
  return json<Order[]>(await fetch("/api/orders"));
}

export async function fetchHistory(sessionId: string): Promise<ChatMessage[]> {
  return json<ChatMessage[]>(
    await fetch(`/api/history?session_id=${encodeURIComponent(sessionId)}`),
  );
}

// ── Chef ────────────────────────────────────────────────────────────────────

export async function fetchKitchenOrders(
  status?: OrderStatus,
): Promise<KitchenOrder[]> {
  const qs = status ? `?status=${status}` : "";
  return json<KitchenOrder[]>(await fetch(`/api/kitchen/orders${qs}`));
}

export async function fetchKitchenStats(): Promise<Record<string, number>> {
  return json<Record<string, number>>(await fetch("/api/kitchen/stats"));
}

export async function setOrderStatus(
  orderId: string,
  status: OrderStatus,
): Promise<KitchenOrder> {
  const res = await fetch(`/api/kitchen/orders/${orderId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  return json<KitchenOrder>(res);
}
