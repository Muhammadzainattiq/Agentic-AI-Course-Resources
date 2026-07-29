"use client";

import { useCallback, useEffect, useState } from "react";
import StatusBadge from "@/components/StatusBadge";
import { fetchOrders, type Order } from "@/lib/api";

const POLL_MS = 20_000;

export default function OrdersPanel({ refreshKey }: { refreshKey: number }) {
  const [orders, setOrders] = useState<Order[]>([]);

  const load = useCallback(() => {
    fetchOrders()
      .then(setOrders)
      .catch(() => setOrders([]));
  }, []);

  // Reload after every agent turn (an order may have just been placed) and on a
  // timer, so the customer sees the chef move it through the kitchen.
  useEffect(() => {
    load();
    const timer = setInterval(load, POLL_MS);
    return () => clearInterval(timer);
  }, [load, refreshKey]);

  if (orders.length === 0) {
    return (
      <p className="text-sm text-neutral-500">
        No orders yet. Ask DineFlow for the menu to get started.
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-3">
      {orders.map((order) => (
        <li
          key={order.id}
          className="rounded-lg border border-neutral-200 bg-white/60 p-3 dark:border-neutral-800 dark:bg-neutral-900/50"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="font-mono text-xs">{order.id}</span>
            <StatusBadge status={order.status} />
          </div>
          <ul className="mt-2 text-xs text-neutral-600 dark:text-neutral-400">
            {order.items.map((item, i) => (
              <li key={i}>
                {item.quantity}× {item.name}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-sm font-medium tabular-nums">
            ${order.total.toFixed(2)}
          </p>
        </li>
      ))}
    </ul>
  );
}
