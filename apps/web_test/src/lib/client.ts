import { apiUrl } from "../config";
import { loadAuth } from "../lib/auth";

export async function getMe() {
  const auth = loadAuth();
  if (!auth?.token) throw new Error("Not logged in");
  const res = await fetch(apiUrl("/api/auth/me"), {
    headers: { Authorization: `Bearer ${auth.token}` },
  });
  if (!res.ok) throw new Error(`me failed: ${await res.text()}`);
  return res.json(); // { uuid, email, email_sha }
}

export type ExtractResult = {
  payload_bitlen: number;
  similarity: number | null;
  recovered_hex: string;
  ecc_ok?: boolean;
  match_text_hash?: boolean;
  used_repetition?: number;
};

export async function extractImage(
  file: File,
  opts: {
    use_y_channel?: boolean;
    use_ecc?: boolean;
    ecc_parity_bytes?: number;
    qim_step?: number;
    repetition?: number;
    check_text: string;
  }
): Promise<ExtractResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("use_y_channel", String(opts.use_y_channel ?? true));
  form.append("use_ecc", String(opts.use_ecc ?? true));
  form.append("ecc_parity_bytes", String(opts.ecc_parity_bytes ?? 32));
  form.append("qim_step", String(opts.qim_step ?? 18.0));
  form.append("repetition", String(opts.repetition ?? 120));
  form.append("check_text", opts.check_text);

  const res = await fetch(apiUrl("/api/watermark/image/extract"), {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
