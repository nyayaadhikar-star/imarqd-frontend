const RAW_API_BASE: string = (import.meta.env.VITE_API_BASE as string) ?? "";

// trim any trailing slashes on the base
const BASE = (RAW_API_BASE || "").trim().replace(/\/+$/, "");

function stripLeadingSlashes(s: string) {
  return s.trim().replace(/^\/+/, "");
}

export function apiUrl(path: string): string {
  const clean = stripLeadingSlashes(path);

  if (!BASE) {
    const p = clean.startsWith("api/") ? clean.slice(4) : clean;
    return `/api/${p}`;
  }

  const endsWithApi = /\/api$/.test(BASE);
  const startsWithApi = clean.startsWith("api/");
  const normalized = endsWithApi && startsWithApi ? clean.slice(4) : clean;

  return `${BASE}/${normalized}`;
}

export const API_BASE = BASE;

// --- NEW for Web3 integration ---
export const REGISTRY_BASE = `${BASE ? BASE : "/api"}/registry`;
export const POLYGON_EXPLORER =
  import.meta.env.VITE_POLYGON_EXPLORER ?? "https://amoy.polygonscan.com";
