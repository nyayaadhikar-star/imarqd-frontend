// apps/web/src/lib/auth.ts

export type AuthRecord = {
  token: string;
  uuid: string;
  email: string;     // normalized (lowercased)
  email_sha: string; // SHA-256 hex of normalized email
};

const AUTH_STORAGE_KEY = "klyvo_auth";

/** Save auth into localStorage */
export function saveAuth(v: AuthRecord): void {
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(v));
}

/** Load auth from localStorage (or null if not present) */
export function loadAuth(): AuthRecord | null {
  const raw = localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    // Minimal shape check
    if (
      typeof parsed?.token === "string" &&
      typeof parsed?.uuid === "string" &&
      typeof parsed?.email === "string" &&
      typeof parsed?.email_sha === "string"
    ) {
      return parsed as AuthRecord;
    }
  } catch (_) {}
  return null;
}

/** Clear auth+session from localStorage */
export function clearAllAuth(): void {
  localStorage.removeItem(AUTH_STORAGE_KEY);
}
