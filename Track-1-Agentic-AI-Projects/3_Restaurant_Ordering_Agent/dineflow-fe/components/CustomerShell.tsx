"use client";

import Image from "next/image";
import AccountMenu from "@/components/AccountMenu";
import ChatPanel from "@/components/ChatPanel";
import type { User } from "@/lib/api";

export default function CustomerShell({ user }: { user: User }) {
  return (
    // h-dvh (not h-screen) so the mobile browser chrome doesn't hide the composer.
    <main className="flex h-dvh flex-col">
      <header className="flex shrink-0 items-center justify-between gap-3 border-b border-neutral-200 px-6 py-4 dark:border-neutral-800">
        <div className="flex items-center gap-3">
          <Image
            src="/logo-mark.png"
            alt=""
            width={512}
            height={512}
            priority
            className="size-11 shrink-0 rounded-full bg-cream ring-1 ring-neutral-200 dark:ring-neutral-700"
          />
          <div>
            <h1 className="text-lg font-semibold tracking-tight">
              Dine<span className="text-brand">Flow</span>
            </h1>
            <p className="text-xs text-neutral-500">
              Your table&apos;s AI waiter — menu, ordering, and status in one
              conversation.
            </p>
          </div>
        </div>
        <AccountMenu user={user} />
      </header>

      <ChatPanel user={user} />
    </main>
  );
}
