"use client";

import Image from "next/image";
import { useCallback, useLayoutEffect, useRef, useState } from "react";
import { RefreshIcon, SendIcon, UserIcon } from "./icons";
import Markdown from "./Markdown";

type Role = "user" | "agent";

interface Message {
  id: string;
  role: Role;
  text: string;
  at: number;
}

const OPENERS = [
  "Hi! I'd love to walk you through my proposal for the redesign.",
  "Thanks for making time. Shall we start with the project scope?",
  "I can offer a 3-month engagement at $8,000/month.",
  "I understand budget is tight — what range were you hoping for?",
];

function uid() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);
}

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

const THREAD_KEY = "bargn-thread-id";

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  // One thread id per browser session (survives reloads); lazily read on the
  // client so we never touch localStorage during SSR.
  const threadIdRef = useRef<string | null>(null);

  const getThreadId = useCallback(() => {
    if (threadIdRef.current) return threadIdRef.current;
    let id = window.localStorage.getItem(THREAD_KEY);
    if (!id) {
      id = uid();
      window.localStorage.setItem(THREAD_KEY, id);
    }
    threadIdRef.current = id;
    return id;
  }, []);

  // Keep the conversation pinned to the latest message.
  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, sending]);

  // Auto-grow the textarea.
  useLayoutEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "0px";
    el.style.height = Math.min(el.scrollHeight, 168) + "px";
  }, [input]);

  const send = useCallback(
    async (raw: string) => {
      const text = raw.trim();
      if (!text || sending) return;

      setError(null);
      setInput("");
      const userMsg: Message = { id: uid(), role: "user", text, at: Date.now() };
      setMessages((prev) => [...prev, userMsg]);
      setSending(true);

      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text, thread_id: getThreadId() }),
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data?.error ?? `Request failed (${res.status}).`);
        }
        setMessages((prev) => [
          ...prev,
          { id: uid(), role: "agent", text: data.reply, at: Date.now() },
        ]);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Something went wrong. Please try again.",
        );
      } finally {
        setSending(false);
        textareaRef.current?.focus();
      }
    },
    [sending, getThreadId],
  );

  function newSession() {
    if (sending) return;
    const id = uid();
    window.localStorage.setItem(THREAD_KEY, id);
    threadIdRef.current = id;
    setMessages([]);
    setError(null);
    setInput("");
    textareaRef.current?.focus();
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send(input);
    }
  }

  const isEmpty = messages.length === 0;

  return (
    <div className="flex h-dvh flex-col bg-background">
      {/* Header */}
      <header className="sticky top-0 z-10 border-b border-border bg-surface/85 backdrop-blur">
        <div className="mx-auto flex w-full max-w-3xl items-center gap-3 px-4 py-3 sm:px-6">
          <Image
            src="/logo.png"
            alt="Bargn AI"
            width={40}
            height={40}
            priority
            className="h-10 w-10 rounded-xl object-cover shadow-sm ring-1 ring-border"
          />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h1 className="truncate text-base font-semibold tracking-tight">
                Bargn AI
              </h1>
              <span className="rounded-full bg-brand-soft px-2 py-0.5 text-[11px] font-medium text-brand">
                Practice
              </span>
            </div>
            <p className="truncate text-xs text-muted">
              Your AI client for negotiation rehearsals
            </p>
          </div>
          <button
            onClick={newSession}
            disabled={sending}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-50"
            title="Start a fresh scenario"
          >
            <RefreshIcon className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">New session</span>
          </button>
        </div>
      </header>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="thin-scroll flex-1 overflow-y-auto"
        aria-live="polite"
      >
        <div className="mx-auto w-full max-w-3xl px-4 py-6 sm:px-6">
          {isEmpty ? (
            <EmptyState onPick={(t) => void send(t)} disabled={sending} />
          ) : (
            <ul className="flex flex-col gap-5">
              {messages.map((m) => (
                <MessageRow key={m.id} message={m} />
              ))}
              {sending && <TypingRow />}
            </ul>
          )}

          {error && (
            <div
              role="alert"
              className="mt-5 rounded-xl border border-red-300/60 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300"
            >
              {error}
            </div>
          )}
        </div>
      </div>

      {/* Composer */}
      <div className="border-t border-border bg-surface/85 backdrop-blur">
        <div className="mx-auto w-full max-w-3xl px-4 py-3 sm:px-6">
          <div className="flex items-end gap-2 rounded-2xl border border-border bg-surface p-2 shadow-sm transition-colors focus-within:border-brand">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              rows={1}
              placeholder="Make your offer, ask a question, or respond to the client…"
              className="max-h-42 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm text-foreground outline-none placeholder:text-muted"
            />
            <button
              onClick={() => void send(input)}
              disabled={sending || input.trim().length === 0}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand text-white transition-all hover:bg-brand-strong disabled:cursor-not-allowed disabled:opacity-40"
              aria-label="Send message"
            >
              <SendIcon className="h-[18px] w-[18px]" />
            </button>
          </div>
          <p className="mt-2 px-1 text-center text-[11px] text-muted">
            Bargn AI role-plays as a client. Press{" "}
            <kbd className="rounded border border-border bg-surface-muted px-1 font-sans">
              Enter
            </kbd>{" "}
            to send,{" "}
            <kbd className="rounded border border-border bg-surface-muted px-1 font-sans">
              Shift + Enter
            </kbd>{" "}
            for a new line.
          </p>
        </div>
      </div>
    </div>
  );
}

function MessageRow({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <li
      className={`flex animate-fade-in-up items-start gap-3 ${
        isUser ? "flex-row-reverse" : ""
      }`}
    >
      <Avatar role={message.role} />
      <div
        className={`flex max-w-[82%] flex-col gap-1 ${
          isUser ? "items-end" : "items-start"
        }`}
      >
        <div
          className={`break-words rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm ${
            isUser
              ? "whitespace-pre-wrap rounded-tr-md bg-brand text-white"
              : "rounded-tl-md border border-border bg-surface text-foreground"
          }`}
        >
          {isUser ? message.text : <Markdown>{message.text}</Markdown>}
        </div>
        <span className="px-1 text-[11px] text-muted">
          {isUser ? "You" : "Client"} · {formatTime(message.at)}
        </span>
      </div>
    </li>
  );
}

function TypingRow() {
  return (
    <li className="flex animate-fade-in-up items-start gap-3">
      <Avatar role="agent" />
      <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-md border border-border bg-surface px-4 py-3 shadow-sm">
        {[0, 0.15, 0.3].map((d) => (
          <span
            key={d}
            className="h-2 w-2 animate-blink rounded-full bg-muted"
            style={{ animationDelay: `${d}s` }}
          />
        ))}
      </div>
    </li>
  );
}

function Avatar({ role }: { role: Role }) {
  if (role === "user") {
    return (
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-muted text-muted">
        <UserIcon className="h-4.5 w-4.5" />
      </span>
    );
  }
  return (
    <Image
      src="/logo.png"
      alt="Client"
      width={32}
      height={32}
      className="h-8 w-8 shrink-0 rounded-full object-cover shadow-sm ring-1 ring-border"
    />
  );
}

function EmptyState({
  onPick,
  disabled,
}: {
  onPick: (text: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex flex-col items-center py-10 text-center sm:py-16">
      <Image
        src="/logo.png"
        alt="Bargn AI"
        width={72}
        height={72}
        className="h-18 w-18 rounded-2xl object-cover shadow-md ring-1 ring-border"
      />
      <h2 className="mt-5 text-xl font-semibold tracking-tight">
        Practice your next negotiation
      </h2>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-muted">
        Bargn AI plays the role of a demanding client. Pitch your services,
        defend your rates, and close the deal. Start with an opener below or
        write your own.
      </p>

      <div className="mt-8 grid w-full max-w-xl gap-3 sm:grid-cols-2">
        {OPENERS.map((o) => (
          <button
            key={o}
            onClick={() => onPick(o)}
            disabled={disabled}
            className="group rounded-xl border border-border bg-surface p-4 text-left text-sm text-foreground shadow-sm transition-all hover:-translate-y-0.5 hover:border-brand hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
          >
            <span className="line-clamp-3">{o}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
