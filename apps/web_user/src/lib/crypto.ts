// apps/web/src/lib/crypto.ts
export async function sha256Hex(input: string): Promise<string> {
  const enc = new TextEncoder().encode(input);
  const buf = await crypto.subtle.digest("SHA-256", enc);
  const bytes = Array.from(new Uint8Array(buf));
  return bytes.map(b => b.toString(16).padStart(2, "0")).join("");
}

export function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}

// --- NEW helper ---
export const isHex64 = (s: string) => /^[a-f0-9]{64}$/i.test(s);

// --- add below existing functions ---
export async function sha256HexOfBlob(blob: Blob): Promise<string> {
  const buf = await blob.arrayBuffer();
  const hash = await crypto.subtle.digest("SHA-256", buf);
  const bytes = Array.from(new Uint8Array(hash));
  return bytes.map(b => b.toString(16).padStart(2, "0")).join("");
}
