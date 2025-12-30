// src/lib/api.ts
import axios from "axios";
import { apiUrl, REGISTRY_BASE } from "../config";
import { loadAuth } from "./auth";

export type LoginResp = { token: string; uuid: string; email: string };

// --- Auth ---
export async function apiLogin(email: string, password: string): Promise<LoginResp> {
  const res = await axios.post(apiUrl("auth/login"), { email, password }, {
    headers: { "Content-Type": "application/json" },
  });
  return res.data as LoginResp;
}

// --- PGP / Key registry ---
export async function registerPublicKey(opts: {
  publicKeyArmored: string;
  email?: string;
  displayName?: string;
}) {
  const form = new FormData();
  form.append("public_key_armored", opts.publicKeyArmored);
  if (opts.email) form.append("email", opts.email);
  if (opts.displayName) form.append("display_name", opts.displayName);

  const res = await axios.post(apiUrl("pgp/register"), form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data as { fingerprint: string; user_id: number };
}

export async function verifySignature(opts: {
  text: string;
  publicKeyArmored: string;
  signatureArmored: string;
}) {
  const form = new FormData();
  form.append("text", opts.text);
  form.append("pgp_public_key", opts.publicKeyArmored);
  form.append("pgp_signature", opts.signatureArmored);

  const res = await axios.post(apiUrl("pgp_debug/verify"), form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data as { ok: boolean; fingerprint?: string; detail?: string | null };
}

// If your backend supports uploading user public key to their profile/session
export async function apiUploadPublicKey(publicKeyArmored: string) {
  const auth = loadAuth();
  if (!auth) throw new Error("Not logged in");

  const form = new FormData();
  form.append("public_key_armored", publicKeyArmored);

  const res = await axios.post(apiUrl("pgp/upload"), form, {
    headers: {
      "Content-Type": "multipart/form-data",
      Authorization: `Bearer ${auth.token}`,
    },
  });
  return res.data as { ok: boolean };
}

// --- Registry v2 (anchoring / verifying) ---
// Adjust route names here only if your backend uses different paths.

export async function anchorProof(payload: {
  media_id: string;
  owner_email_sha: string;
  proof_json: unknown;
}) {
  const auth = loadAuth();
  if (!auth) throw new Error("Not logged in");

  const res = await axios.post(`${REGISTRY_BASE}/v2/anchor`, payload, {
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${auth.token}`,
    },
  });
  return res.data as { tx_hash?: string; anchor_id?: string; ok?: boolean; detail?: string };
}

export async function verifyProof(payload: {
  media_id: string;
  owner_email_sha: string;
  proof_json: unknown;
}) {
  const res = await axios.post(`${REGISTRY_BASE}/v2/verify`, payload, {
    headers: { "Content-Type": "application/json" },
  });
  return res.data as { ok: boolean; tx_hash?: string; detail?: string };
}
