"use client";

import Image from "next/image";
import { createContext, useContext } from "react";
import type { MenuItem } from "@/lib/api";

/**
 * The menu, keyed by id, shared with every message bubble on the page.
 *
 * The agent only ever emits dish *ids*; names, prices and photos are read from
 * here — i.e. straight from the database — so a card can never show a
 * hallucinated price.
 */
export const MenuContext = createContext<Map<number, MenuItem>>(new Map());

const FALLBACK_IMAGE = "/menu.jpeg";

function DishCard({ item }: { item: MenuItem }) {
  return (
    <li className="flex flex-col overflow-hidden rounded-xl border border-neutral-200 bg-white dark:border-neutral-700 dark:bg-neutral-900">
      <div className="relative aspect-[16/10] w-full bg-neutral-100 dark:bg-neutral-800">
        <Image
          src={item.image_url || FALLBACK_IMAGE}
          alt={item.name}
          fill
          sizes="(max-width: 640px) 100vw, 220px"
          className="object-cover"
        />
      </div>

      <div className="flex flex-1 flex-col gap-1 p-3">
        <div className="flex items-baseline justify-between gap-2">
          <h4 className="text-[13px] font-semibold leading-snug">{item.name}</h4>
          <span className="shrink-0 text-[13px] font-semibold tabular-nums text-brand">
            {item.price.toLocaleString()}
          </span>
        </div>

        <p className="line-clamp-2 text-xs leading-relaxed text-neutral-500">
          {item.description}
        </p>

        {item.tags.length > 0 && (
          <div className="mt-auto flex flex-wrap gap-1 pt-1.5">
            {item.tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-neutral-100 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-neutral-500 dark:bg-neutral-800"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </li>
  );
}

/** Renders a ```dish-cards block: a JSON array of menu item ids. */
export default function DishCards({ source }: { source: string }) {
  const menu = useContext(MenuContext);

  let ids: number[];
  try {
    const parsed = JSON.parse(source.trim());
    if (!Array.isArray(parsed)) throw new Error("not an array");
    ids = parsed.map(Number).filter((n) => Number.isInteger(n));
  } catch {
    // A malformed block is the agent's mistake, not the customer's problem —
    // stay quiet rather than showing them a parse error.
    return null;
  }

  const items = ids
    .map((id) => menu.get(id))
    .filter((item): item is MenuItem => item !== undefined);

  if (items.length === 0) {
    return menu.size === 0 ? (
      <p className="my-2 text-xs text-neutral-500">Loading dishes…</p>
    ) : null;
  }

  return (
    <ul className="my-2.5 grid grid-cols-2 gap-2.5 sm:grid-cols-3">
      {items.map((item) => (
        <DishCard key={item.id} item={item} />
      ))}
    </ul>
  );
}
