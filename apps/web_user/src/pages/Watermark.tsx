// top imports (existing)
import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { apiUrl } from "../config";
import { loadAuth } from "../lib/auth";
// --- keep TxLink
import TxLink from "../components/TxLink";

// crypto helpers you already use
import { isHex64, sha256HexOfBlob } from "../lib/crypto";

// NOTE: Removed POLYGON_EXPLORER here; TxLink imports it internally.

type ApiResult = {
  ok: boolean;
  headers?: Record<string, string>;
  filename?: string;
  blobUrl?: string;
  error?: string;
};

export default function Watermark() {
  const [file, setFile] = useState<File | null>(null);
  const [ownerEmail, setOwnerEmail] = useState<string>("");
  const [ownerEmailSha, setOwnerEmailSha] = useState<string>("");
  const [label, setLabel] = useState<string>("");

  // watermark params
  const [preset, setPreset] = useState<string>("facebook");
  const [useECC, setUseECC] = useState<boolean>(true);
  const [eccParity, setEccParity] = useState<number>(64);
  const [useY, setUseY] = useState<boolean>(true);
  const [repetition, setRepetition] = useState<number>(160);
  const [qimStep, setQimStep] = useState<number>(24);

  // auto-register toggle
  const [autoRegister, setAutoRegister] = useState<boolean>(true);

  const [busy, setBusy] = useState<boolean>(false);
  const [result, setResult] = useState<ApiResult | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // derive owner SHA server-side-compatible (or accept user-provided hex)
  useEffect(() => {
    let cancel = false;
    (async () => {
      if (!ownerEmail) {
        setOwnerEmailSha("");
        return;
      }
      try {
        // If user types a 64-hex, accept it as-is, else compute sha256(email)
        if (isHex64(ownerEmail.trim())) {
          if (!cancel) setOwnerEmailSha(ownerEmail.trim().toLowerCase());
        } else {
          const enc = new TextEncoder().encode(ownerEmail.trim());
          const buf = await crypto.subtle.digest("SHA-256", enc);
          const hex = Array.from(new Uint8Array(buf))
            .map((b) => b.toString(16).padStart(2, "0"))
            .join("");
          if (!cancel) setOwnerEmailSha(hex);
        }
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancel = true;
    };
  }, [ownerEmail]);

  const auth = useMemo(() => loadAuth(), []);
  const token = auth?.token;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setResult(null);
    if (!file) {
      setErr("Please choose an image first.");
      return;
    }

    try {
      setBusy(true);

      // payload text = "owner:<sha>|media:<id>" if label set we’ll still embed SHA, label is only metadata
      const ownerPart = ownerEmailSha || (await sha256HexOfBlob(new Blob([ownerEmail || ""])));
      const mediaId = ""; // watermark route doesn’t need media id in payload; server registers if autoRegister=true
      const text = `owner:${ownerPart}${mediaId ? `|media:${mediaId}` : ""}`;

      const form = new FormData();
      form.append("file", file);
      form.append("text", text);

      // preset controls (server will pick sensible defaults if omitted)
      form.append("preset", preset);
      form.append("use_ecc", String(!!useECC));
      if (useECC) form.append("ecc_parity_bytes", String(eccParity));
      form.append("use_y_channel", String(!!useY));
      form.append("repetition", String(repetition));
      form.append("qim_step", String(qimStep));

      // metadata & auto-registry
      form.append("auto_register_media", String(!!autoRegister));
      if (label) form.append("media_label", label);
      if (ownerEmailSha) form.append("override_owner_email_sha", ownerEmailSha);

      const resp = await axios.post(`${apiUrl}/watermark/image`, form, {
        responseType: "blob",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        validateStatus: () => true,
      });

      if (resp.status >= 200 && resp.status < 300) {
        // Read headers into plain object
        const headers: Record<string, string> = {};
        resp.headers &&
          Object.keys(resp.headers).forEach((k) => {
            headers[k.toLowerCase()] = (resp.headers as any)[k];
          });

        // create a blob url to preview / download
        const blob = resp.data as Blob;
        const blobUrl = URL.createObjectURL(blob);

        const cd = headers["content-disposition"] || "";
        const m = /filename="?([^"]+)"?/.exec(cd);
        const filename = m?.[1] || "watermarked.png";

        setResult({
          ok: true,
          headers,
          filename,
          blobUrl,
        });
      } else {
        const text = await (resp.data?.text?.() ?? Promise.resolve(""));
        setErr(text || `Watermark failed with status ${resp.status}`);
      }
    } catch (e: any) {
      setErr(e?.message || "Watermark failed");
    } finally {
      setBusy(false);
    }
  }

  const anchorTx =
    result?.headers?.["x-anchor-tx"] ||
    result?.headers?.["x-anchor-tx-hash"] ||
    ""; // your backend sets x-anchor-tx; normalize if needed

  return (
    <div className="container mx-auto max-w-3xl p-4">
      <h1 className="text-2xl font-semibold mb-4">Watermark & Auto-Register</h1>

      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium">Image</label>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="mt-1"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium">Owner email (or SHA-256 hex)</label>
            <input
              value={ownerEmail}
              onChange={(e) => setOwnerEmail(e.target.value)}
              placeholder="you@example.com or 64-hex"
              className="mt-1 w-full border rounded px-2 py-1"
            />
            <p className="text-xs text-gray-500 mt-1">
              Derived SHA-256: <span className="font-mono break-all">{ownerEmailSha || "(none)"}</span>
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium">Media label (optional)</label>
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="my-lion-post"
              className="mt-1 w-full border rounded px-2 py-1"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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

          <div>
            <label className="block text-sm font-medium">ECC parity (bytes)</label>
            <input
              type="number"
              value={eccParity}
              onChange={(e) => setEccParity(Number(e.target.value) || 0)}
              disabled={!useECC}
              className="mt-1 w-full border rounded px-2 py-1"
            />
            <label className="inline-flex items-center gap-2 mt-1">
              <input
                type="checkbox"
                checked={useECC}
                onChange={(e) => setUseECC(e.target.checked)}
              />
              Use ECC
            </label>
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

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium">Repetition</label>
            <input
              type="number"
              value={repetition}
              onChange={(e) => setRepetition(Number(e.target.value) || 0)}
              className="mt-1 w-full border rounded px-2 py-1"
            />
          </div>
          <div>
            <label className="block text-sm font-medium">QIM step</label>
            <input
              type="number"
              step="0.1"
              value={qimStep}
              onChange={(e) => setQimStep(Number(e.target.value) || 0)}
              className="mt-1 w-full border rounded px-2 py-1"
            />
          </div>
          <div>
            <label className="block text-sm font-medium">Auto-register media</label>
            <label className="inline-flex items-center gap-2 mt-1">
              <input
                type="checkbox"
                checked={autoRegister}
                onChange={(e) => setAutoRegister(e.target.checked)}
              />
              enable
            </label>
          </div>
        </div>

        <button
          type="submit"
          disabled={busy}
          className="px-4 py-2 rounded bg-indigo-600 text-white disabled:opacity-60"
        >
          {busy ? "Working…" : "Watermark"}
        </button>
      </form>

      {err && (
        <div className="mt-4 text-red-600">
          {err}
        </div>
      )}

      {result?.ok && (
        <div className="mt-6 p-4 border rounded bg-gray-50">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-gray-600">Output</div>
              <div className="font-mono text-sm break-all">{result.filename}</div>
            </div>
            {result.blobUrl && (
              <a
                href={result.blobUrl}
                download={result.filename}
                className="px-3 py-1.5 rounded bg-gray-800 text-white"
              >
                Download
              </a>
            )}
          </div>

          {/* Optional anchor / blockchain info */}
          {anchorTx && (
            <div className="mt-6 border-t border-gray-200 pt-4">
              <TxLink txHash={anchorTx} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
