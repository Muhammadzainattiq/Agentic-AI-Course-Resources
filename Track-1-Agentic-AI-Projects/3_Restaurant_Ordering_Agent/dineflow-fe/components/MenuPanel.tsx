"use client";

import { useEffect, useState } from "react";
import { fetchMenu, type MenuItem } from "@/lib/api";

export default function MenuPanel() {
  const [items, setItems] = useState<MenuItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMenu()
      .then(setItems)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const categories = [...new Set(items.map((i) => i.category))];

  return (
    <div className="flex flex-col gap-5">
      {loading && <p className="text-sm text-neutral-500">Loading menu…</p>}
      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">
          Couldn&apos;t load the menu: {error}
        </p>
      )}

      {categories.map((category) => (
        <section key={category}>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-widest text-brand">
            {category}
          </h3>
          <ul className="flex flex-col gap-2">
            {items
              .filter((i) => i.category === category)
              .map((item) => (
                <li
                  key={item.id}
                  className="rounded-lg border border-neutral-200 bg-white/60 p-3 dark:border-neutral-800 dark:bg-neutral-900/50"
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-sm font-medium">{item.name}</span>
                    <span className="shrink-0 text-sm tabular-nums text-neutral-600 dark:text-neutral-400">
                      ${item.price.toFixed(2)}
                    </span>
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-neutral-500">
                    {item.description}
                  </p>
                  {item.tags.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {item.tags.map((tag) => (
                        <span
                          key={tag}
                          className="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] uppercase tracking-wide text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </li>
              ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
