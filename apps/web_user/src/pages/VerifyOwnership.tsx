import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { apiUrl } from "../config";
import { loadAuth } from "../lib/auth";
import { isHex64 } from "../lib/crypto";

type VerifyResponse = {
  exists: boolean;
  ecc_ok?: boolean | null;
  match_text_hash?: boolean | null;
  similarity?: number | null;
  used_repetition?: number;
  payload_bits?: number;
  owner_email_sha?: string;
  matched_media_id?: string | null;
  checked_media_ids?: number;
  preset?: string;
  // allow other backend keys without TS errors
  [k: string]: unknown;
};

export default function Verify() {
  const [file, setFile] = useState<File | null>(null);

  // owner input can be email OR a 64-hex SHA. We won’t hash on FE; we’ll
  // pass the value through to the server and let /hash/email resolve if needed.
  const [ownerInput, setOwnerInput] = useState<string>("");
  const [ownerSha, setOwnerSha] = useState<string>("");

  // params (keep same defaults you used in Swagger)
  const [preset, setPreset] = useState<string>("facebook");
  const [useECC, setUseECC] = useState<boolean>(true);
  const [eccParity, setEccParity] = useState<number>(64);
  const [useY, setUseY] = useState<boolean>(true);
  const [repetition, setRepetition] = useState<number>(160);

  const [busy, setBusy] = useState<boolean>(false);
  const [err, setErr] = useState<string | null>(null);
  const [res, setRes] = useState<VerifyResponse | null>(null);

  const auth = useMemo(() => loadAuth(), []);
  const token = auth?.token;

  // Resolve ownerInput into a SHA using your new server helper when needed.
  // If user already typed a 64-hex, keep it. Otherwise call /hash/email.
  useEffect(() => {
    let cancelled = false;

    (async () => {
      const raw = ownerInput.trim();
      if (!raw) {
        setOwnerSha("");
        return;
      }
      try {
        if (isHex64(raw)) {
          if (!cancelled) setOwnerSha(raw.toLowerCase());
          return;
        }
        const url = new URL(`${apiUrl}/hash/email`);
        url.searchParams.set("email", raw);
        const r = await axios.get(url.toString(), {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
          validateStatus: () => true,
        });
        if (r.status === 200 && r.data?.sha256) {
          if (!cancelled) setOwnerSha(String(r.data.sha256).toLowerCase());
        } else {
          if (!cancelled) setOwnerSha("");
        }
      } catch {
        if (!cancelled) setOwnerSha("");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [ownerInput, apiUrl, token]); // apiUrl is from module, safe to include

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setRes(null);

    if (!file) {
      setErr("Please choose an image first.");
      return;
    }
    if (!ownerSha) {
      setErr("Enter an owner email or a valid 64-hex SHA first.");
      return;
    }

    try {
      setBusy(true);

      // Build URL with query params (matches how you tested in Swagger)
      const url = new URL(`${apiUrl}/verify/auto`);
      url.searchParams.set("owner_email_sha", ownerSha);
      url.searchParams.set("preset", preset);
      url.searchParams.set("use_ecc", String(!!useECC));
      if (useECC) url.searchParams.set("ecc_parity_bytes", String(eccParity));
      url.searchParams.set("use_y_channel", String(!!useY));
      url.searchParams.set("repetition", String(repetition));

      const form = new FormData();
      form.append("file", file);

      const r = await axios.post(url.toString(), form, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        validateStatus: () => true,
      });

      if (r.status >= 200 && r.status < 300) {
        setRes(r.data as VerifyResponse);
      } else {
        setErr(`Verification failed (HTTP ${r.status})`);
      }
    } catch (e: any) {
      setErr(e?.message || "Verification failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="container mx-auto max-w-3xl p-4">
      <h1 className="text-2xl font-semibold mb-4">Verify Watermark</h1>

      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium">Image to verify</label>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="mt-1"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium">
              Owner (email or 64-hex SHA)
            </label>
            <input
              value={ownerInput}
              onChange={(e) => setOwnerInput(e.target.value)}
              placeholder="you@example.com or <sha256-hex>"
              className="mt-1 w-full border rounded px-2 py-1"
            />
            <p className="text-xs text-gray-500 mt-1 font-mono break-all">
              resolved sha: {ownerSha || "(none)"}
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium">Preset</label>
            <select
              value={preset}
              onChange={(e) => setPreset(e.target.value)}
              className="mt-1 w-full border rounded px-2 py-1"
            >
              <option value="facebook">facebook</option>
              <option value="whatsapp">whatsapp</option>
              <option value="instagram">instagram</option>
              <option value="x_twitter">x_twitter</option>
              <option value="original">original</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium">Use ECC</label>
            <label className="inline-flex items-center gap-2 mt-1">
              <input
                type="checkbox"
                checked={useECC}
                onChange={(e) => setUseECC(e.target.checked)}
              />
              enable
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium">ECC parity (bytes)</label>
            <input
              type="number"
              value={eccParity}
              disabled={!useECC}
              onChange={(e) => setEccParity(Number(e.target.value) || 0)}
              className="mt-1 w-full border rounded px-2 py-1"
            />
          </div>

          <div>
            <label className="block text-sm font-medium">Use Y channel</label>
            <label className="inline-flex items-center gap-2 mt-1">
              <input
                type="checkbox"
                checked={useY}
                onChange={(e) => setUseY(e.target.checked)}
              />
              enable
            </label>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium">Repetition</label>
            <input
              type="number"
              value={repetition}
              onChange={(e) => setRepetition(Number(e.target.value) || 0)}
              className="mt-1 w-full border rounded px-2 py-1"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={busy}
          className="px-4 py-2 rounded bg-indigo-600 text-white disabled:opacity-60"
        >
          {busy ? "Verifying…" : "Verify"}
        </button>
      </form>

      {err && <div className="mt-4 text-red-600">{err}</div>}

      {res && (
        <div className="mt-6 p-4 border rounded bg-gray-50">
          <h2 className="font-semibold mb-2">Result</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            <Row k="exists" v={String(res.exists)} />
            {"ecc_ok" in res && <Row k="ecc_ok" v={String(res.ecc_ok)} />}
            {"match_text_hash" in res && (
              <Row k="match_text_hash" v={String(res.match_text_hash)} />
            )}
            {"similarity" in res && (
              <Row
                k="similarity"
                v={
                  res.similarity === null || res.similarity === undefined
                    ? "-"
                    : res.similarity.toFixed(3)
                }
              />
            )}
            {"used_repetition" in res && (
              <Row k="used_repetition" v={String(res.used_repetition)} />
            )}
            {"payload_bits" in res && (
              <Row k="payload_bits" v={String(res.payload_bits)} />
            )}
            {"owner_email_sha" in res && (
              <Row k="owner_email_sha" v={String(res.owner_email_sha)} />
            )}
            {"matched_media_id" in res && (
              <Row
                k="matched_media_id"
                v={String(res.matched_media_id ?? "-")}
              />
            )}
            {"checked_media_ids" in res && (
              <Row k="checked_media_ids" v={String(res.checked_media_ids)} />
            )}
            {"preset" in res && <Row k="preset" v={String(res.preset)} />}
          </div>

          {/* Raw JSON for debugging */}
          <details className="mt-4">
            <summary className="cursor-pointer text-sm text-gray-600">
              Raw response
            </summary>
            <pre className="text-xs mt-2 p-2 bg-white border rounded overflow-auto">
{JSON.stringify(res, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between">
      <div className="text-gray-600">{k}</div>
      <div className="font-mono break-all">{v}</div>
    </div>
  );
}
