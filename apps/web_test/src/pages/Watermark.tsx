// top imports (existing)
import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { apiUrl } from "../config";
import { loadAuth } from "../lib/auth";
// --- NEW imports ---
import TxLink from "../components/TxLink";

// ❌ (old) import was for v1 anchoring; no longer used for v2
// import { anchorProof } from "../lib/api";

import { isHex64, sha256HexOfBlob } from "../lib/crypto";   // <-- already noted in your header
import { POLYGON_EXPLORER } from "../config";

type Preset = {
  name: string;
  long_edge: number | null;
  jpeg_quality: number | null;
  defaults: { qim_step: number; repetition: number; ecc_parity_bytes: number; use_y_channel: boolean };
};

type ExtractResult = {
  payload_bitlen: number;
  similarity?: number | null;
  recovered_hex: string;
  ecc_ok?: boolean | null;
  match_text_hash?: boolean | null;
  used_repetition?: number | null;
};

export default function WatermarkPage() {
  const auth = loadAuth();
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState("");
  const [headers, setHeaders] = useState<Record<string, string>>({});
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [wmBlob, setWmBlob] = useState<Blob | null>(null);

  const [presets, setPresets] = useState<Preset[]>([]);
  const [preset, setPreset] = useState<string>("facebook");
  const [advanced, setAdvanced] = useState(false);
  const [qim, setQim] = useState(24.0);
  const [rep, setRep] = useState(160);
  const [ecc, setEcc] = useState(64);
  const [useY, setUseY] = useState(true);

  const [verifyBusy, setVerifyBusy] = useState(false);
  const [verifyStatus, setVerifyStatus] = useState<string>("");
  const [verifyResult, setVerifyResult] = useState<ExtractResult | null>(null);

  // --- NEW state for persistent media id + on-chain anchor ---
  const [mediaId, setMediaId] = useState<string | null>(null); // 0x + 64 hex
  const [anchorBusy, setAnchorBusy] = useState(false);
  const [anchorTx, setAnchorTx] = useState<string | null>(null);
  const [anchorBlock, setAnchorBlock] = useState<number | null>(null);
  const [anchorError, setAnchorError] = useState<string>("");

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(apiUrl("watermark/presets"));
        if (r.ok) {
          const data = await r.json();
          const list: Preset[] = data.presets || [];
          setPresets(list);
          const fb = list.find((x) => x.name === "facebook") || list[0];
          if (fb) {
            setPreset(fb.name);
            setQim(fb.defaults.qim_step);
            setRep(fb.defaults.repetition);
            setEcc(fb.defaults.ecc_parity_bytes);
            setUseY(fb.defaults.use_y_channel);
          }
        }
      } catch {/* ignore */}
    })();
  }, []);

  useEffect(() => {
    if (!advanced && presets.length) {
      const p = presets.find((x) => x.name === preset);
      if (p) {
        setQim(p.defaults.qim_step);
        setRep(p.defaults.repetition);
        setEcc(p.defaults.ecc_parity_bytes);
        setUseY(p.defaults.use_y_channel);
      }
    }
  }, [preset, advanced, presets]);

  useEffect(() => {
    return () => { if (previewUrl) URL.revokeObjectURL(previewUrl); };
  }, [previewUrl]);

  if (!auth) return <p className="status">Please log in first.</p>;

  // --- NEW: build claim dynamically so it includes media_id once generated
  const claim = useMemo(() => {
    const owner = `owner:${auth.email_sha}`;
    return mediaId ? `${owner}|media:${mediaId}` : owner;
  }, [auth.email_sha, mediaId]);

  const hint = useMemo(() => {
    const p = presets.find(x => x.name === preset);
    if (!p) return "";
    const lg = p.long_edge ? `resizes long edge to ≈ ${p.long_edge}px` : "no platform resize assumed";
    const jq = p.jpeg_quality ? ` + JPEG q≈${p.jpeg_quality}` : "";
    return `${lg}${jq}`;
  }, [preset, presets]);

  function onPick(f?: File | null) {
    setStatus("");
    setVerifyStatus("");
    setVerifyResult(null);
    setHeaders({});
    setWmBlob(null);
    setAnchorTx(null);
    setAnchorBlock(null);
    setAnchorError("");
    // keep mediaId; user may want to reuse the previously generated id

    if (!f) {
      setFile(null);
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
      return;
    }
    setFile(f);
    const url = URL.createObjectURL(f);
    setPreviewUrl(url);
  }

  // --- NEW: helper to generate a 32-byte random id (0x + 64 hex)
  function genMediaId(): string {
    const b = new Uint8Array(32);
    crypto.getRandomValues(b);
    return "0x" + Array.from(b).map(x => x.toString(16).padStart(2, "0")).join("");
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) { setStatus("Please choose an image first."); return; }

    setStatus("Embedding watermark…");
    setHeaders({});
    setWmBlob(null);
    setVerifyStatus("");
    setVerifyResult(null);

    try {
      // --- NEW: create a persistent media id if not present
      const id = mediaId ?? genMediaId();
      setMediaId(id);
      localStorage.setItem("last_media_id", id);

      const fd = new FormData();
      fd.append("file", file);
      // --- CHANGED: embed both owner and media id in the payload
      // const emailSha = auth?.email_sha?.toLowerCase() ?? "";
      fd.append("text", `owner:${auth?.email_sha ?? ""}|media:${id}`);
      fd.append("preset", preset);

      if (advanced) {
        fd.append("use_y_channel", String(useY));
        fd.append("qim_step", String(qim));
        fd.append("repetition", String(rep));
        fd.append("use_ecc", "true");
        fd.append("ecc_parity_bytes", String(ecc));
      } else {
        fd.append("use_ecc", "true");
      }

      const res = await axios.post(apiUrl("watermark/image"), fd, {
        responseType: "blob",
        validateStatus: () => true,
      });

      if (res.status !== 200) {
        const text = await (res.data?.text?.() ?? Promise.resolve(""));
        throw new Error(text || `Server error: ${res.status}`);
      }

      const hs: Record<string, string> = {};
      Object.keys(res.headers || {}).forEach((k) => {
        const v = (res.headers as any)[k];
        if (k.startsWith("x-")) hs[k] = v;
      });
      setHeaders(hs);

      setWmBlob(res.data);
      const url = URL.createObjectURL(res.data);
      setPreviewUrl(url);
      setStatus("✅ Done! Watermarked image below. You can download or verify it now.");
    } catch (err: any) {
      setStatus(err?.message || "Watermark failed.");
    }
  }

  async function onVerifyNow() {
    if (!wmBlob) { setVerifyStatus("Nothing to verify yet. Please embed first."); return; }
    setVerifyBusy(true);
    setVerifyStatus("Verifying…");
    setVerifyResult(null);

    try {
      const toBool = (s?: string) => (s ?? "").toLowerCase() === "true";
      const toNum  = (s?: string) => (s ? Number(s) : undefined);

      const use_y_channel = toBool(headers["x-params-usey"] || "true");
      const use_ecc       = toBool(headers["x-params-useecc"] || "true");
      const ecc_parity    = toNum(headers["x-params-ecc-parity"]) ?? (advanced ? ecc : 64);
      const qim_used      = toNum(headers["x-params-qim"]) ?? (advanced ? qim : 24.0);
      const rep_used      = toNum(headers["x-params-repetition"]) ?? (advanced ? rep : 160);

      const fd = new FormData();
      fd.append("file", new File([wmBlob], "watermarked.png", { type: "image/png" }));
      fd.append("use_y_channel", String(use_y_channel));
      fd.append("use_ecc", String(use_ecc));
      fd.append("ecc_parity_bytes", String(ecc_parity));
      fd.append("qim_step", String(qim_used));
      fd.append("repetition", String(rep_used));
      fd.append("check_text", claim);

      const resp = await fetch(apiUrl("watermark/image/extract"), { method: "POST", body: fd });
      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }
      const data = (await resp.json()) as ExtractResult;
      setVerifyResult(data);
      setVerifyStatus(data.ecc_ok && data.match_text_hash
        ? "✅ Ownership verified (watermark intact)."
        : "⚠️ No match or watermark too degraded."
      );
    } catch (e: any) {
      setVerifyStatus(e?.message || "Verification failed.");
    } finally {
      setVerifyBusy(false);
    }
  }

  const prettyFile = file
    ? `${file.name} • ${(file.size / 1024 / 1024).toFixed(2)} MB`
    : "No file selected";

  async function onAnchor() {
    setAnchorError("");
    setAnchorTx(null);
    setAnchorBlock(null);

    try {
      if (!wmBlob) {
        setAnchorError("Watermark the image first.");
        return;
      }

      // ensure we have a media_id
      const id = mediaId ?? (localStorage.getItem("last_media_id") || genMediaId());
      setMediaId(id);
      localStorage.setItem("last_media_id", id);

      // 1) try to read the hash from headers (back-end path)
      let fileShaHex =
        (headers["x-file-sha256"] ||
          headers["x-output-sha256"] ||
          headers["x-sha256"] ||
          "").toLowerCase();

      // 2) fallback: compute SHA-256 of the watermarked blob locally (front-end path)
      if (!isHex64(fileShaHex)) {
        fileShaHex = await sha256HexOfBlob(wmBlob);
      }
      if (!isHex64(fileShaHex)) {
        setAnchorError("Invalid file SHA256");
        return;
      }

      const emailSha = auth?.email_sha?.toLowerCase() ?? "";
      if (!isHex64(emailSha)) {
        setAnchorError("Bad session: email hash invalid");
        return;
      }

      setAnchorBusy(true);

      // --- CHANGED: call v2 anchor endpoint with media_id
      const r = await fetch(apiUrl("registry/v2/anchor"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          owner_email_sha: emailSha,
          media_id: id,
          file_sha256: fileShaHex,
          ipfs_cid: ""
        }),
      });

      if (!r.ok) {
        const t = await r.text();
        throw new Error(t || `HTTP ${r.status}`);
      }
      const resp = await r.json();
      setAnchorTx(resp.tx_hash || null);
      setAnchorBlock(resp.block_number ?? null);
      setStatus("✅ Anchored on-chain");
    } catch (e: any) {
      setAnchorError(e?.message || "Anchor failed");
    } finally {
      setAnchorBusy(false);
    }
  }

  return (
    <div className="wm-shell">
      {/* Left column: controls */}
      <section className="panel panel--controls">
        <div className="banner">
          <div className="banner-title">Watermark</div>
          <div className="banner-sub">
            Claim:&nbsp;<code className="kbd">{claim}</code>
          </div>
        </div>

        {/* Target platform */}
        <div className="field">
          <label className="label">Target platform</label>
          <select className="select" value={preset} onChange={(e) => setPreset(e.target.value)}>
            <option value="facebook">Facebook (2048px)</option>
            <option value="whatsapp">WhatsApp (1280px)</option>
            <option value="instagram">Instagram (1080px)</option>
            <option value="x_twitter">X / Twitter (2048px)</option>
            <option value="original">Original (no resize)</option>
          </select>
          <div className="small text-muted" style={{ marginTop: 4 }}>
            {useMemo(() => {
              const p = presets.find(x => x.name === preset);
              if (!p) return "";
              const lg = p.long_edge ? `resizes long edge ≈ ${p.long_edge}px` : "no resize";
              const jq = p.jpeg_quality ? ` + JPEG q≈${p.jpeg_quality}` : "";
              return `${lg}${jq}`;
            }, [preset, presets])}
          </div>
        </div>

        {/* Drop zone */}
        <div
          className="dropzone"
          onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
          onDrop={(e) => {
            e.preventDefault();
            const f = e.dataTransfer.files?.[0];
            if (f) onPick(f);
          }}
        >
          <div className="dropzone-inner">
            <div className="drop-icon">🖼️</div>
            <div className="drop-title">Drop an image to watermark</div>
            <div className="drop-sub">or</div>
            <label className="btn btn-ghost" htmlFor="wm-file">Choose File</label>
            <input
              id="wm-file"
              type="file"
              accept="image/*"
              style={{ display: "none" }}
              onChange={(e) => onPick(e.target.files?.[0] ?? null)}
            />
            <div className="file-meta">{prettyFile}</div>
          </div>
        </div>

        {/* Advanced overrides */}
        <div className="field" style={{ marginTop: 10 }}>
          <label className="checkbox">
            <input type="checkbox" checked={advanced} onChange={(e) => setAdvanced(e.target.checked)} />
            <span> Advanced overrides</span>
          </label>

          {advanced && (
            <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div>
                <label className="label">QIM step</label>
                <input className="input" type="number" step="0.5" value={qim}
                  onChange={(e) => setQim(parseFloat(e.target.value))} />
              </div>
              <div>
                <label className="label">Repetition</label>
                <input className="input" type="number" value={rep}
                  onChange={(e) => setRep(parseInt(e.target.value))} />
              </div>
              <div>
                <label className="label">ECC parity bytes</label>
                <input className="input" type="number" value={ecc}
                  onChange={(e) => setEcc(parseInt(e.target.value))} />
              </div>
              <div style={{ display: "flex", alignItems: "end" }}>
                <label className="checkbox">
                  <input type="checkbox" checked={useY} onChange={(e) => setUseY(e.target.checked)} />
                  <span> Embed on Y channel</span>
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="actions">
          <button className="btn" onClick={onSubmit as any}>Embed Watermark</button>
          <button
            className={`btn ${!wmBlob ? "btn-disabled" : ""}`}
            type="button"
            onClick={onVerifyNow}
            disabled={!wmBlob || verifyBusy}
          >
            {verifyBusy ? (<><span className="spinner" /> Verifying…</>) : "Verify This Image Now"}
          </button>

          {/* --- NEW: Anchor on-chain button (v2) --- */}
          <button
            className={`btn ${!wmBlob ? "btn-disabled" : ""}`}
            type="button"
            onClick={onAnchor}
            disabled={!wmBlob || anchorBusy}
          >
            {anchorBusy ? (<>Anchoring…</>) : "Anchor on-chain"}
          </button>
          {anchorError && <div className="status" style={{ color: "#dc2626" }}>{anchorError}</div>}
          {anchorTx && (
            <div className="status">
              Anchored: <a href={`${POLYGON_EXPLORER}/tx/${anchorTx}`} target="_blank" rel="noreferrer">{anchorTx.slice(0, 10)}…</a>
              {anchorBlock != null ? ` • block ${anchorBlock}` : null}
            </div>
          )}

          {anchorTx && (
            <TxLink txHash={anchorTx} blockNumber={anchorBlock} />
          )}

          {anchorError && <div style={{ color: "red", marginTop: 4 }}>{anchorError}</div>}

          <div className="status">{status}</div>
          {verifyStatus && <div className="status" style={{ marginTop: 6 }}>{verifyStatus}</div>}
        </div>

        {/* Quick result chips (verify-now) */}
        {verifyResult && (
          <div className="metrics">
            <div className="metrics-title">Verification (local)</div>
            <div className="chips">
              <div className="chip"><span className="chip-key">payload_bits</span><span className="chip-val">{verifyResult.payload_bitlen}</span></div>
              <div className="chip"><span className="chip-key">ecc_ok</span><span className="chip-val">{String(verifyResult.ecc_ok)}</span></div>
              <div className="chip"><span className="chip-key">match_text_hash</span><span className="chip-val">{String(verifyResult.match_text_hash)}</span></div>
              <div className="chip"><span className="chip-key">similarity</span><span className="chip-val">{verifyResult.similarity ?? "n/a"}</span></div>
              <div className="chip"><span className="chip-key">used_repetition</span><span className="chip-val">{verifyResult.used_repetition}</span></div>
            </div>
          </div>
        )}

        {/* Show the media_id so user can copy it if needed */}
        {mediaId && (
          <div className="metrics" style={{ marginTop: 12 }}>
            <div className="metrics-title">Media ID</div>
            <div className="chips">
              <div className="chip">
                <span className="chip-key">media_id</span>
                <span className="chip-val">{mediaId}</span>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Right column: preview & embed status */}
      <section className="panel panel--preview">
        <div className="preview-head">
          <div className="preview-title">Preview</div>
          {!!wmBlob && (
            <div className="verdict verdict--ok" title="Ready">
              Embedded
            </div>
          )}
        </div>

        <div className="preview">
          {previewUrl ? (
            <img src={previewUrl} alt="watermarked" className="preview-img" />
          ) : (
            <div className="preview-empty">Pick an image to preview and watermark.</div>
          )}
        </div>

        <div style={{ marginTop: 16 }}>
          <h4 className="metrics-title" style={{ marginBottom: 8 }}>Embed Status</h4>
          {Object.keys(headers).length === 0 ? (
            <p className="text-muted">No output yet.</p>
          ) : (
            <div className="chips" style={{ flexWrap: "wrap" }}>
              {Object.entries(headers).map(([k, v]) => (
                <div className="chip" key={k}>
                  <span className="chip-key">{k}</span>
                  <span className="chip-val">{v}</span>
                </div>
              ))}
            </div>
          )}

          {previewUrl && (
            <div style={{ marginTop: 12 }}>
              <a className="btn btn-ghost" href={previewUrl} download="watermarked.png">Download PNG</a>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
