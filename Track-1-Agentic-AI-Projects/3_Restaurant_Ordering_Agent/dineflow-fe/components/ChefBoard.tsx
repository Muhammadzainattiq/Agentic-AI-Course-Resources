"use client";

import { useCallback, useEffect, useState } from "react";
import StatusBadge from "@/components/StatusBadge";
import {
  KITCHEN_FLOW,
  STATUS_LABEL,
  fetchKitchenOrders,
  setOrderStatus,
  type KitchenOrder,
  type OrderStatus,
} from "@/lib/api";

const FILTERS: (OrderStatus | "all")[] = ["all", ...KITCHEN_FLOW, "cancelled"];
const POLL_MS = 15_000;

export default function ChefBoard() {
  const [orders, setOrders] = useState<KitchenOrder[]>([]);
  const [filter, setFilter] = useState<OrderStatus | "all">("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setOrders(await fetchKitchenOrders());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't load orders.");
    } finally {
      setLoading(false);
    }
  }, []);

  // Orders arrive while the chef is looking at the board, so keep it fresh.
  // The first fetch is deferred to a microtask rather than run inline, so the
  // effect never updates state during the mount render pass.
  useEffect(() => {
    let cancelled = false;
    const refresh = () => {
      if (!cancelled) void load();
    };

    queueMicrotask(refresh);
    const timer = setInterval(refresh, POLL_MS);

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [load]);

  async function advance(order: KitchenOrder, status: OrderStatus) {
    setBusyId(order.id);
    setError(null);
    try {
      const updated = await setOrderStatus(order.id, status);
      setOrders((prev) => prev.map((o) => (o.id === order.id ? updated : o)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't update the order.");
    } finally {
      setBusyId(null);
    }
  }

  const visible =
    filter === "all" ? orders : orders.filter((o) => o.status === filter);

  const counts = orders.reduce<Record<string, number>>((acc, o) => {
    acc[o.status] = (acc[o.status] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap gap-2">
        {FILTERS.map((name) => (
          <button
            key={name}
            onClick={() => setFilter(name)}
            className={`rounded-full px-3.5 py-1.5 text-xs font-medium transition-colors ${
              filter === name
                ? "bg-brand text-white"
                : "border border-neutral-300 text-neutral-600 hover:bg-neutral-100 dark:border-neutral-700 dark:text-neutral-400 dark:hover:bg-neutral-800"
            }`}
          >
            {name === "all" ? "All" : STATUS_LABEL[name]}
            <span className="ml-1.5 opacity-60">
              {name === "all" ? orders.length : (counts[name] ?? 0)}
            </span>
          </button>
        ))}
      </div>

      {error && (
        <p
          role="alert"
          className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300"
        >
          {error}
        </p>
      )}

      {loading && <p className="text-sm text-neutral-500">Loading orders…</p>}

      {!loading && visible.length === 0 && (
        <p className="rounded-lg border border-dashed border-neutral-300 px-4 py-10 text-center text-sm text-neutral-500 dark:border-neutral-700">
          No orders here yet.
        </p>
      )}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {visible.map((order) => (
          <article
            key={order.id}
            className="flex flex-col gap-3 rounded-xl border border-neutral-200 bg-white/60 p-4 dark:border-neutral-800 dark:bg-neutral-900/50"
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="font-mono text-xs text-neutral-500">{order.id}</p>
                <p className="mt-0.5 text-sm font-medium">
                  {order.customer_name ?? "Unknown customer"}
                </p>
                <p className="text-xs text-neutral-500">
                  {order.customer_phone ?? order.customer_email ?? "—"}
                </p>
              </div>
              <StatusBadge status={order.status} />
            </div>

            <ul className="border-y border-neutral-200 py-2 text-sm dark:border-neutral-800">
              {order.items.map((item, i) => (
                <li key={i} className="flex justify-between gap-2">
                  <span>
                    <span className="font-medium">{item.quantity}×</span>{" "}
                    {item.name}
                  </span>
                  <span className="tabular-nums text-neutral-500">
                    {(item.quantity * item.unit_price).toFixed(2)}
                  </span>
                </li>
              ))}
            </ul>

            <div className="text-xs text-neutral-500">
              {order.address ? (
                <p>Deliver to: {order.address}</p>
              ) : (
                <p>Pickup at the restaurant</p>
              )}
              {order.notes && <p className="mt-1">Notes: {order.notes}</p>}
              <p className="mt-1">
                Placed {new Date(order.created_at).toLocaleString()}
              </p>
            </div>

            <div className="mt-auto flex items-center justify-between gap-2 pt-1">
              <span className="text-sm font-semibold tabular-nums">
                {order.total.toFixed(2)}
              </span>

              <div className="flex flex-wrap justify-end gap-2">
                {/* Every forward step, so the chef can skip ahead if needed. */}
                {KITCHEN_FLOW.filter(
                  (s) =>
                    order.status !== "cancelled" &&
                    KITCHEN_FLOW.indexOf(s) >
                      KITCHEN_FLOW.indexOf(order.status as OrderStatus),
                ).map((status) => (
                  <button
                    key={status}
                    onClick={() => advance(order, status)}
                    disabled={busyId === order.id}
                    className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-40 ${
                      status === order.next_status
                        ? "bg-brand text-white hover:bg-brand-hover"
                        : "border border-neutral-300 text-neutral-600 hover:bg-neutral-100 dark:border-neutral-700 dark:text-neutral-400 dark:hover:bg-neutral-800"
                    }`}
                  >
                    {status === order.next_status ? "→ " : ""}
                    {STATUS_LABEL[status]}
                  </button>
                ))}
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
