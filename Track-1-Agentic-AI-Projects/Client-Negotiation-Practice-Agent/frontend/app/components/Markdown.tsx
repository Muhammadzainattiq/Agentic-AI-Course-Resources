"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Renders the agent's markdown reply. Raw HTML is intentionally NOT enabled
// (react-markdown's default), so model output can't inject markup.
export default function Markdown({ children }: { children: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer nofollow">
              {children}
            </a>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
