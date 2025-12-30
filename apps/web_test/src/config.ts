// src/config.ts

// Supports:
// - DEV:  VITE_API_BASE_URL=http://127.0.0.1:8000
// - PROD: VITE_API_BASE_URL=https://imarqd-backend-app.azurewebsites.net
//
// This helper ensures backend routes always go through /api
// unless your BASE already ends with /api or your path starts with api/.

const RAW_API_BASE: string = (import.meta.env.VITE_API_BASE_URL as string) ?? "";

// trim any trailing slashes on the base
const BASE = (RAW_API_BASE || "").trim().replace(/\/+$/, "");

function stripLeadingSlashes(s: string) {
  return s.trim().replace(/^\/+/, "");
}

export function apiUrl(path: string): string {
  const clean = stripLeadingSlashes(path);

  // If no BASE is configured, assume dev proxy and return a relative /api/* URL
  if (!BASE) {
    const p = clean.startsWith("api/") ? clean.slice(4) : clean;
    return `/api/${p}`;
  }

  const baseEndsWithApi = /\/api$/.test(BASE);
  const pathStartsWithApi = clean.startsWith("api/");

  // If BASE already ends with /api, do not add /api again
  // If caller already included api/, do not add again
  let normalizedPath = clean;

  if (baseEndsWithApi && pathStartsWithApi) {
    normalizedPath = clean.slice(4); // strip api/ to avoid /api/api/*
  } else if (!baseEndsWithApi && !pathStartsWithApi) {
    normalizedPath = `api/${clean}`; // add api/ in production when BASE is an origin
  }

  return `${BASE}/${normalizedPath}`;
}

export const API_BASE = BASE;

// Registry base used by v2 anchoring/verification routes (if you have them)
export const REGISTRY_BASE = apiUrl("registry");

// Explorer (optional env override)
export const POLYGON_EXPLORER =
  (import.meta.env.VITE_POLYGON_EXPLORER as string) ?? "https://amoy.polygonscan.com";
