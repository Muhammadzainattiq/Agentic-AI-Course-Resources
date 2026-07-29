"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { login, signup } from "@/lib/api";

const FIELD =
  "w-full rounded-lg border border-neutral-300 bg-transparent px-3.5 py-2.5 text-sm outline-none transition-colors focus:border-brand disabled:opacity-60 dark:border-neutral-700";

export default function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setBusy(true);

    const data = new FormData(e.currentTarget);
    const email = String(data.get("email") ?? "").trim();
    const password = String(data.get("password") ?? "");

    try {
      const user =
        mode === "login"
          ? await login(email, password)
          : await signup({
              email,
              password,
              name: String(data.get("name") ?? "").trim(),
              phone: String(data.get("phone") ?? "").trim() || undefined,
              address: String(data.get("address") ?? "").trim() || undefined,
            });

      // The chef has no ordering UI; send them straight to the kitchen board.
      router.replace(user.role === "chef" ? "/chef" : "/");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setBusy(false);
    }
  }

  const isSignup = mode === "signup";

  return (
    <div className="flex flex-1 items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <Image
            src="/logo-mark.png"
            alt=""
            width={512}
            height={512}
            priority
            className="size-16 rounded-full bg-cream ring-1 ring-neutral-200 dark:ring-neutral-700"
          />
          <h1 className="mt-4 text-xl font-semibold tracking-tight">
            {isSignup ? "Create your account" : "Welcome back"}
          </h1>
          <p className="mt-1 text-sm text-neutral-500">
            {isSignup
              ? "DineFlow remembers your preferences across visits."
              : "Sign in to pick up where you left off."}
          </p>
        </div>

        <form onSubmit={onSubmit} className="flex flex-col gap-3">
          {isSignup && (
            <input
              name="name"
              required
              autoComplete="name"
              placeholder="Full name"
              className={FIELD}
            />
          )}

          <input
            name="email"
            type="email"
            required
            autoComplete="email"
            placeholder="Email"
            className={FIELD}
          />

          <input
            name="password"
            type="password"
            required
            minLength={isSignup ? 8 : 1}
            autoComplete={isSignup ? "new-password" : "current-password"}
            placeholder={isSignup ? "Password (min 8 characters)" : "Password"}
            className={FIELD}
          />

          {isSignup && (
            <>
              <input
                name="phone"
                autoComplete="tel"
                placeholder="Phone (optional)"
                className={FIELD}
              />
              <input
                name="address"
                autoComplete="street-address"
                placeholder="Delivery address (optional)"
                className={FIELD}
              />
            </>
          )}

          {error && (
            <p
              role="alert"
              className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-950/40 dark:text-red-300"
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="mt-1 rounded-lg bg-brand px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-hover disabled:opacity-50"
          >
            {busy
              ? isSignup
                ? "Creating account…"
                : "Signing in…"
              : isSignup
                ? "Create account"
                : "Sign in"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-neutral-500">
          {isSignup ? "Already have an account? " : "New here? "}
          <Link
            href={isSignup ? "/login" : "/signup"}
            className="font-medium text-brand hover:underline"
          >
            {isSignup ? "Sign in" : "Create an account"}
          </Link>
        </p>
      </div>
    </div>
  );
}
