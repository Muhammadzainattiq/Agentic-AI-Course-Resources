import type { SVGProps } from "react";

export function LogoMark(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden {...props}>
      <path
        d="M4 15.5V6.2c0-.66.53-1.2 1.2-1.2H14c.66 0 1.2.54 1.2 1.2v6.1c0 .66-.54 1.2-1.2 1.2H8.2L4 15.5Z"
        fill="currentColor"
        opacity="0.35"
      />
      <path
        d="M9.8 19V9.7c0-.66.54-1.2 1.2-1.2h7.8c.66 0 1.2.54 1.2 1.2v6.1c0 .66-.54 1.2-1.2 1.2H14L9.8 19Z"
        fill="currentColor"
      />
    </svg>
  );
}

export function SendIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden {...props}>
      <path
        d="M4.4 11.9 19.3 5c.9-.42 1.83.5 1.42 1.4l-6.9 14.9c-.42.9-1.72.83-2.05-.1l-1.9-5.3a1 1 0 0 0-.62-.62l-5.3-1.9c-.94-.34-1-1.64-.1-2.06Z"
        fill="currentColor"
      />
    </svg>
  );
}

export function RefreshIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden {...props}>
      <path
        d="M20 11a8 8 0 1 0-.6 3M20 5v6h-6"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function UserIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden {...props}>
      <path
        d="M12 12.5a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM5 19.5c.9-3 3.6-4.5 7-4.5s6.1 1.5 7 4.5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
