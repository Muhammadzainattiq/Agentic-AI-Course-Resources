"use client";

import { useEffect, useRef, useState } from "react";
import { MenuContext } from "@/components/DishCards";
import Markdown from "@/components/Markdown";
import {
  fetchHistory,
  fetchMenu,
  sendMessage,
  type ChatMessage,
  type MenuItem,
  type User,
} from "@/lib/api";
import { loadSessionId, resetSession } from "@/lib/session";

function greeting(user: User): ChatMessage {
  const name = user.name?.split(" ")[0];
  return {
    role: "assistant",
    content: `Hi${name ? `, ${name}` : ""}! I'm DineFlow. I can walk you through the menu, take your order, and check on it after. What are you in the mood for?`,
  };
}

const SUGGESTIONS = [
  "What's on the menu?",
  "Something vegan under 800",
  "Where's my order?",
];

export default function ChatPanel({ user }: { user: User }) {
  const [messages, setMessages] = useState<ChatMessage[]>([greeting(user)]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [menu, setMenu] = useState<Map<number, MenuItem>>(new Map());
  const bottomRef = useRef<HTMLDivElement>(null);

  // A ref, not state: the session id is never rendered, and setting it
  // synchronously means a message sent before history loads still resumes the
  // right conversation instead of silently starting a new one.
  const sessionIdRef = useRef<string | null>(null);

  // Resume this user's conversation and replay it from short-term memory.
  useEffect(() => {
    let cancelled = false;
    sessionIdRef.current = loadSessionId(user.id);

    fetchHistory(sessionIdRef.current)
      .then((history) => {
        if (!cancelled && history.length > 0) setMessages(history);
      })
      .catch(() => {
        /* first visit, or backend down — the greeting stands */
      });

    return () => {
      cancelled = true;
    };
  }, [user.id]);

  // The whole menu, once. Dish cards read names/prices/photos from here rather
  // than from the model's text, so they're always the real database values.
  useEffect(() => {
    let cancelled = false;
    fetchMenu()
      .then((items) => {
        if (!cancelled) setMenu(new Map(items.map((i) => [i.id, i])));
      })
      .catch(() => {
        /* cards degrade to nothing; the surrounding prose still reads fine */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function submit(text: string) {
    const trimmed = text.trim();
    if (!trimmed || sending) return;

    setInput("");
    setError(null);
    setSending(true);
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);

    try {
      const result = await sendMessage(trimmed, sessionIdRef.current);
      sessionIdRef.current = result.session_id;
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: result.response },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setSending(false);
    }
  }

  function startNewConversation() {
    sessionIdRef.current = resetSession(user.id);
    setMessages([greeting(user)]);
    setError(null);
  }

  return (
    // min-h-0 lets the transcript below actually shrink and scroll inside the
    // flex column, instead of pushing the composer off the bottom of the page.
    <MenuContext.Provider value={menu}>
      <div className="flex min-h-0 flex-1 flex-col">
        <header className="flex shrink-0 items-center justify-between border-b border-neutral-200 px-5 py-3 dark:border-neutral-800">
          <div>
            <h2 className="text-sm font-semibold">Chat</h2>
            <p className="text-xs text-neutral-500">
              {sending ? "DineFlow is thinking…" : "Powered by gpt-5"}
            </p>
          </div>
          <button
            onClick={startNewConversation}
            className="rounded-md border border-neutral-300 px-3 py-1.5 text-xs transition-colors hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800"
          >
            New conversation
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          <div className="mx-auto flex max-w-2xl flex-col gap-3">
            {messages.map((message, i) => (
              <div
                key={i}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {message.role === "user" ? (
                  <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl bg-brand px-4 py-2.5 text-sm leading-relaxed text-white">
                    {message.content}
                  </div>
                ) : (
                  // Assistant replies are Markdown — menus come back as tables,
                  // which need more width than a chat bubble usually gets.
                  <div className="max-w-full min-w-0 rounded-2xl bg-neutral-100 px-4 py-2.5 text-sm leading-relaxed text-neutral-900 sm:max-w-[92%] dark:bg-neutral-800 dark:text-neutral-100">
                    <Markdown>{message.content}</Markdown>
                  </div>
                )}
              </div>
            ))}

            {sending && (
              <div className="flex justify-start">
                <div className="flex gap-1 rounded-2xl bg-neutral-100 px-4 py-3 dark:bg-neutral-800">
                  {[0, 150, 300].map((delay) => (
                    <span
                      key={delay}
                      className="h-1.5 w-1.5 animate-bounce rounded-full bg-neutral-400"
                      style={{ animationDelay: `${delay}ms` }}
                    />
                  ))}
                </div>
              </div>
            )}

            {error && (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-950/40 dark:text-red-300">
                {error}
              </p>
            )}

            <div ref={bottomRef} />
          </div>
        </div>

        {/* Composer: pinned to the bottom of the column, and sticky as a backstop
          so it stays put even if an ancestor ends up scrolling. */}
        <div className="sticky bottom-0 shrink-0 border-t border-neutral-200 bg-background/85 backdrop-blur-sm dark:border-neutral-800">
          {messages.length <= 1 && (
            <div className="mx-auto flex max-w-2xl flex-wrap gap-2 px-4 pt-3">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => submit(suggestion)}
                  className="rounded-full border border-neutral-300 px-3 py-1.5 text-xs text-neutral-600 transition-colors hover:bg-neutral-100 dark:border-neutral-700 dark:text-neutral-400 dark:hover:bg-neutral-800"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              submit(input);
            }}
            className="p-4 pb-[max(1rem,env(safe-area-inset-bottom))]"
          >
            <div className="mx-auto flex max-w-2xl gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Order something, or ask what's good…"
                disabled={sending}
                className="flex-1 rounded-lg border border-neutral-300 bg-transparent px-4 py-2.5 text-sm outline-none transition-colors focus:border-brand disabled:opacity-60 dark:border-neutral-700"
              />
              <button
                type="submit"
                disabled={sending || !input.trim()}
                className="rounded-lg bg-brand px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-hover disabled:opacity-40"
              >
                Send
              </button>
            </div>
          </form>
        </div>
      </div>
    </MenuContext.Provider>
  );
}
