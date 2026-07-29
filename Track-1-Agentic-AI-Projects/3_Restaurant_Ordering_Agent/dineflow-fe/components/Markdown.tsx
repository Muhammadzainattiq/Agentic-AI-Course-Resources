"use client";

import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import DishCards from "@/components/DishCards";

/**
 * Renders assistant messages as GitHub-flavoured Markdown.
 *
 * The agent is instructed to lay the menu out as tables (see the backend's
 * prompts.py), so table support here is what makes that instruction pay off —
 * without it the customer would see raw `|---|` pipes.
 *
 * Only inline formatting, lists, tables and code are styled: the agent has no
 * business emitting images or headings above h3 inside a chat bubble.
 */
const COMPONENTS: Components = {
  table: ({ children }) => (
    // Long menus scroll sideways inside the bubble rather than stretching it.
    <div className="my-2 -mx-1 overflow-x-auto">
      <table className="w-full border-collapse text-left text-[13px]">
        {children}
      </table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="border-b border-neutral-300 dark:border-neutral-600">
      {children}
    </thead>
  ),
  th: ({ children, style }) => (
    <th
      style={style}
      className="whitespace-nowrap px-2 py-1.5 text-xs font-semibold uppercase tracking-wide text-neutral-500"
    >
      {children}
    </th>
  ),
  td: ({ children, style }) => (
    <td
      style={style}
      className="border-t border-neutral-200/70 px-2 py-1.5 align-top tabular-nums dark:border-neutral-700/70"
    >
      {children}
    </td>
  ),
  h1: ({ children }) => <h3 className="mt-3 mb-1 font-semibold">{children}</h3>,
  h2: ({ children }) => <h3 className="mt-3 mb-1 font-semibold">{children}</h3>,
  h3: ({ children }) => (
    <h3 className="mt-3 mb-1 text-xs font-semibold uppercase tracking-wide text-neutral-500 first:mt-0">
      {children}
    </h3>
  ),
  p: ({ children }) => <p className="my-1.5 first:mt-0 last:mb-0">{children}</p>,
  ul: ({ children }) => (
    <ul className="my-1.5 list-disc space-y-0.5 pl-5">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="my-1.5 list-decimal space-y-0.5 pl-5">{children}</ol>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold">{children}</strong>
  ),
  // ```dish-cards blocks become a photo grid; everything else stays code.
  code: ({ children, className }) => {
    if (className?.includes("language-dish-cards")) {
      return <DishCards source={String(children)} />;
    }
    return (
      <code className="rounded bg-black/5 px-1 py-0.5 font-mono text-[12px] dark:bg-white/10">
        {children}
      </code>
    );
  },
  // react-markdown wraps fenced blocks in <pre>; unwrap so the grid isn't
  // rendered inside a monospace, scrolling code block.
  pre: ({ children }) => <>{children}</>,
  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="underline underline-offset-2"
    >
      {children}
    </a>
  ),
  hr: () => (
    <hr className="my-2 border-neutral-200 dark:border-neutral-700" />
  ),
};

export default function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={COMPONENTS}>
      {children}
    </ReactMarkdown>
  );
}
