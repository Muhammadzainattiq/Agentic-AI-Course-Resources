"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { logout, type User } from "@/lib/api";

export default function AccountMenu({ user }: { user: User }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function signOut() {
    setBusy(true);
    await logout();
    router.replace("/login");
    router.refresh();
  }

  return (
    <div className="flex items-center gap-3">
      <div className="hidden text-right sm:block">
        <p className="text-sm font-medium leading-tight">
          {user.name ?? user.email}
        </p>
        <p className="text-xs capitalize text-neutral-500">{user.role}</p>
      </div>
      <button
        onClick={signOut}
        disabled={busy}
        className="rounded-md border border-neutral-300 px-3 py-1.5 text-xs transition-colors hover:bg-neutral-100 disabled:opacity-50 dark:border-neutral-700 dark:hover:bg-neutral-800"
      >
        {busy ? "Signing out…" : "Sign out"}
      </button>
    </div>
  );
}
