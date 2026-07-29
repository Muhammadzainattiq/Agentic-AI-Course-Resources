/**
 * Conversation session id, scoped per user in localStorage.
 *
 * Identity itself lives in the httpOnly auth cookie — this only tracks *which
 * conversation* the user is currently in, so a reload resumes the same thread
 * and a different account on the same browser never lands in someone else's.
 */

const key = (userId: string) => `dineflow.session.${userId}`;

function makeSessionId(): string {
  const rand =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID().replace(/-/g, "").slice(0, 12)
      : Math.random().toString(36).slice(2, 14);
  return `sess_${rand}`;
}

export function loadSessionId(userId: string): string {
  const existing = localStorage.getItem(key(userId));
  if (existing) return existing;

  const created = makeSessionId();
  localStorage.setItem(key(userId), created);
  return created;
}

/** Start a fresh conversation. Long-term memory is unaffected. */
export function resetSession(userId: string): string {
  const sessionId = makeSessionId();
  localStorage.setItem(key(userId), sessionId);
  return sessionId;
}
