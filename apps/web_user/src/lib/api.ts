import axios from 'axios';
import { apiUrl, REGISTRY_BASE } from '../config';


export async function registerPublicKey(opts: { publicKeyArmored: string; email?: string; displayName?: string }) {
  const form = new FormData();
  form.append('public_key_armored', opts.publicKeyArmored);
  if (opts.email) form.append('email', opts.email);
  if (opts.displayName) form.append('display_name', opts.displayName);

  const res = await axios.post(apiUrl('pgp/register'), form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data as { fingerprint: string; user_id: number };
}

export async function verifySignature(opts: { text: string; publicKeyArmored: string; signatureArmored: string }) {
  const form = new FormData();
  form.append('text', opts.text);
  form.append('pgp_public_key', opts.publicKeyArmored);
  form.append('pgp_signature', opts.signatureArmored);

  const res = await axios.post(apiUrl('pgp_debug/verify'), form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data as { ok: boolean; fingerprint?: string; detail?: string | null };
}



export type LoginResp = { token: string; uuid: string; email: string };

export async function apiLogin(email: string, password: string): Promise<LoginResp> {
  const res = await axios.post(apiUrl("auth/login"), { email, password });
  return res.data;
}

export async function apiUploadPublicKey(uuid: string, publicKeyArmored: string, token?: string) {
  const form = new FormData();
  form.append("uuid", uuid);
  form.append("public_key_armored", publicKeyArmored);
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return axios.post(apiUrl("keys/upload"), form, { headers });
}






export type AnchorPayload = {
  email_sha: string;
  file_sha256: string;
  kind: string;
  filename: string;
  ipfs_cid?: string;
};

export type AnchorResponse = {
  tx_hash: string;
  block_number: number;
  ipfs_cid: string;
  status: "anchored" | "failed";
};

export type VerifyResponse = {
  exists: boolean;
  owner_email_sha: string;
  timestamp: number;
  ipfs_cid: string;
};

export async function anchorProof(payload: AnchorPayload): Promise<AnchorResponse> {
  const res = await axios.post(`${REGISTRY_BASE}/anchor`, payload, {
    headers: { "Content-Type": "application/json" },
  });
  return res.data;
}

export async function verifyProof(fileSha256: string): Promise<VerifyResponse> {
  const res = await axios.get(`${REGISTRY_BASE}/verify`, {
    params: { file_sha256: fileSha256 },
  });
  return res.data;
}


// lib/api.ts (add near bottom)

// 1️⃣ Fetch all media for a user
export async function fetchUserMedia(emailSha: string) {
  return await fetch(`${REGISTRY_BASE}/media/owner/${emailSha}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  }).then((res) => res.json());
}

// 2️⃣ Verify a media automatically
export async function verifyMediaAuto(emailSha: string, file: File, preset = "facebook") {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(
    `${REGISTRY_BASE}/verify/auto?owner_email_sha=${emailSha}&preset=${preset}&use_ecc=true`,
    { method: "POST", body: formData }
  );
  return await res.json();
}

// 3️⃣ Get SHA for a given email (optional)
export async function getOwnerSha(email: string) {
  const res = await fetch(`${REGISTRY_BASE}/owner/sha?email=${encodeURIComponent(email)}`);
  return await res.json();
}

