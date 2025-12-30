import { useEffect, useMemo, useState } from "react";
import { extractImage, ExtractResult } from "../lib/client";
import { loadAuth } from "../lib/auth";
import { apiUrl } from "../config";
import { sha256Hex, normalizeEmail } from "../lib/crypto";

type Me = { uuid: string; email: string; email_sha: string };
type Preset = {
  name: string;
  long_edge: number | null;
  jpeg_quality: number | null;
  defaults: { qim_step: number; repetition: number; ecc_parity_bytes: number; use_y_channel: boolean };
};

// ---- utils ----
async function sha256HexBytes(buf: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", buf);
  const bytes = Array.from(new Uint8Array(digest));
  return bytes.map(b => b.toString(16).padStart(2, "0")).join("");
}
const isHex = (s: string) => /^[0-9a-f]+$/i.test(s);
const toLowerHex = (s: string) => (s || "").toLowerCase();
const strip0x = (s: string) => s?.toLowerCase().startsWith("0x") ? s.slice(2) : s;

// Normalize media id to 64-lower-hex (returns "" if invalid)
function normalizeMediaId(input: string): string {
  const h = strip0x((input || "").trim());
  if (!h || !isHex(h) || (h.length !== 64 && h.length !== 32)) return "";
  return h.length === 64 ? h.toLowerCase() : h.toLowerCase().padStart(64, "0");
}

export default function VerifyOwnership() {
  const [me, setMe] = useState<Me | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string>("");
  const [result, setResult] = useState<ExtractResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  // Parsed from binary payload (v2)
  const [parsedOwnerSha, setParsedOwnerSha] = useState<string>("");
  const [parsedMediaId, setParsedMediaId] = useState<string>("");

  // Presets + overrides
  const [presets, setPresets] = useState<Preset[]>([]);
  const [preset, setPreset] = useState<string>("facebook");
  const [advanced, setAdvanced] = useState(false);
  const [qim, setQim] = useState(24.0);
  const [rep, setRep] = useState(160);
  const [ecc, setEcc] = useState(64);
  const [useY, setUseY] = useState(true);

  // Inputs: owner claim + optional media id
  const [claimInput, setClaimInput] = useState<string>("");
  const [mediaIdInput, setMediaIdInput] = useState<string>("");

  // On-chain checks
  const [onchainBusy, setOnchainBusy] = useState(false);
  const [onchain, setOnchain] = useState<null | {
    exists: boolean;
    owner_email_sha: string;
    timestamp: number;
    ipfs_cid: string;
    file_sha256?: string;
  }>(null);
  const [onchainErr, setOnchainErr] = useState<string>("");

  // ---- session (optional) ----
  useEffect(() => {
    const auth = loadAuth();
    if (!auth?.token) {
      setMe(null);
      setStatus("Tip: you can verify without logging in—just paste your email or claim string below.");
      return;
    }
    (async () => {
      try {
        const r = await fetch(apiUrl("auth/me"), { headers: { Authorization: `Bearer ${auth.token}` } });
        if (r.ok) {
          const data = (await r.json()) as Me;
          setMe(data);
          setClaimInput(`owner:${data.email_sha}`); // prefill
          setStatus("");
        } else {
          setMe(null);
        }
      } catch {
        setMe(null);
      }
    })();
  }, []);

  // ---- presets ----
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(apiUrl("watermark/presets"));
        if (!r.ok) return;
        const data = await r.json();
        const arr: Preset[] = data.presets || [];
        setPresets(arr);
        const fb = arr.find((p) => p.name === "facebook") || arr[0];
        if (fb) {
          setPreset(fb.name);
          setQim(fb.defaults.qim_step);
          setRep(fb.defaults.repetition);
          setEcc(fb.defaults.ecc_parity_bytes);
          setUseY(fb.defaults.use_y_channel);
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

  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);

  // Build the EXACT check text the embedder uses:
  //  - owner:<sha>  OR
  //  - owner:<sha>|media:<id>  (when media id is supplied)
  const checkTextPlanned = useMemo(() => {
    const c = (claimInput || "").trim();
    const mNorm = normalizeMediaId(mediaIdInput);
    if (!c) return "";
    if (c.toLowerCase().includes("|media:")) return c; // user pasted combined form → respect it
    return mNorm ? `${c}|media:${mNorm}` : c;
  }, [claimInput, mediaIdInput]);

  // Convert email → owner:<sha256(email)>
  async function resolveClaimFromInput(raw: string): Promise<string> {
    const s = raw.trim();
    if (!s) return s;
    if (s.toLowerCase().startsWith("owner:")) return s;
    if (s.includes("@")) {
      const norm = normalizeEmail(s);
      const hash = await sha256Hex(norm);
      return `owner:${hash}`;
    }
    return s;
  }

  function onPick(f?: File | null) {
    setResult(null);
    setStatus("");
    setOnchain(null);
    setOnchainErr("");
    setParsedOwnerSha("");
    setParsedMediaId("");
    if (!f) {
      setFile(null);
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
      return;
    }
    setFile(f);
    setPreviewUrl(URL.createObjectURL(f));
  }

  // ---- verify watermark (primary) ----
  async function onVerify() {
    if (!file) { setStatus("Pick an image first."); return; }
    if (!claimInput.trim()) { setStatus("Enter your email or claim string first."); return; }

    setBusy(true);
    setStatus("Verifying…");
    setResult(null);
    setParsedOwnerSha("");
    setParsedMediaId("");

    try {
      const baseClaim = await resolveClaimFromInput(claimInput);
      const mNorm = normalizeMediaId(mediaIdInput);

      const check_text =
        mNorm
          ? (baseClaim.toLowerCase().includes("|media:") ? baseClaim : `${baseClaim}|media:${mNorm}`)
          : baseClaim;

      const r = await extractImage(file, {
        use_y_channel: useY,
        use_ecc: true,
        ecc_parity_bytes: ecc,
        qim_step: qim,
        repetition: rep,
        check_text, // ← EXACT text that embedder uses
      });
      setResult(r);

      let verdict = "⚠️ No match or watermark too degraded. Try the exact preset used for embedding.";

      if (r.ecc_ok) {
        const hex = toLowerHex(r.recovered_hex || "");
        if (hex && isHex(hex) && (hex.length === 64 || hex.length === 128)) {
          const ownerHex = hex.slice(0, 64);
          const mediaHex = hex.length === 128 ? hex.slice(64, 128) : "";
          setParsedOwnerSha(ownerHex);
          if (mediaHex) setParsedMediaId(mediaHex);

          const claimedSha = baseClaim.toLowerCase().startsWith("owner:")
            ? toLowerHex(baseClaim.slice(6))
            : "";

          if (claimedSha && claimedSha === ownerHex) {
            verdict = "✅ Ownership verified (payload owner matches).";
          } else if (!claimedSha) {
            verdict = "✅ Watermark extracted. Owner SHA shown below.";
          } else {
            verdict = "⚠️ Watermark found, but owner hash does not match the claim.";
          }
        } else if (r.match_text_hash) {
          // Legacy “text-wm” path
          verdict = "✅ Ownership verified (text watermark matches).";
        }
      }
      setStatus(verdict);
    } catch (e: any) {
      setStatus(e?.message || "Verification failed.");
    } finally {
      setBusy(false);
    }
  }

  // ---- on-chain exact-file (v1, secondary) ----
  async function onCheckOnChainExact() {
    if (!file) { setOnchainErr("Pick an image first."); return; }
    setOnchainErr("");
    setOnchain(null);
    setOnchainBusy(true);
    try {
      const buf = await file.arrayBuffer();
      const fileSha = await sha256HexBytes(buf);
      const r = await fetch(apiUrl(`registry/verify?file_sha256=${fileSha}`));
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      setOnchain({
        exists: !!data?.exists,
        owner_email_sha: data?.owner_email_sha || "0x0",
        timestamp: Number(data?.timestamp || 0),
        ipfs_cid: data?.ipfs_cid || "",
        file_sha256: fileSha,
      });
    } catch (e: any) {
      setOnchainErr(e?.message || "On-chain check failed.");
    } finally {
      setOnchainBusy(false);
    }
  }

  // ---- on-chain by media id (v2, primary for derivatives) ----
  async function onCheckOnChainByMediaId() {
    setOnchainErr("");
    setOnchain(null);

    // Prefer user-entered media id; otherwise use parsed one from watermark
    const mNorm = normalizeMediaId(mediaIdInput || parsedMediaId);
    if (!mNorm) {
      setOnchainErr("No media_id available. Enter one or verify to parse it from the watermark.");
      return;
    }

    setOnchainBusy(true);
    try {
      // NOTE: backend route is /registry/v2/verify (no chain_id query needed)
      const r = await fetch(apiUrl(`registry/v2/verify?media_id=${mNorm}`));
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      setOnchain({
        exists: !!data?.exists,
        owner_email_sha: data?.owner_email_sha || "0x0",
        timestamp: Number(data?.timestamp || 0),
        ipfs_cid: data?.ipfs_cid || "",
        file_sha256: data?.file_sha256 || undefined,
      });
    } catch (e: any) {
      setOnchainErr(e?.message || "On-chain (media_id) check failed.");
    } finally {
      setOnchainBusy(false);
    }
  }

  const prettyFile = file ? `${file.name} • ${(file.size / 1024 / 1024).toFixed(2)} MB` : "No file selected";
  const hint = useMemo(() => {
    const p = presets.find(x => x.name === preset);
    if (!p) return "";
    const lg = p.long_edge ? `assumes long edge ≈ ${p.long_edge}px` : "assumes no resize";
    const jq = p.jpeg_quality ? ` + JPEG q≈${p.jpeg_quality}` : "";
    return `${lg}${jq}`;
  }, [preset, presets]);

  return (
    <div className="wm-shell">
      {/* Left controls */}
      <section className="panel panel--controls">
        <div className="banner">
          <div className="banner-title">Verify Ownership</div>
          <div className="banner-sub">
            Enter email or claim string (e.g. <code className="kbd">owner:&lt;sha256&gt;</code>) plus optional media id.
            {me && <span style={{ marginLeft: 8, color: "#5b7083" }}>(Prefilled from your session)</span>}
          </div>
        </div>

        {/* Claim input */}
        <div style={{ marginTop: 8 }}>
          <label className="label">Claim</label>
          <input
            className="input"
            placeholder={me ? `owner:${me.email_sha}` : "your@email.com  OR  owner:<sha256>"}
            value={claimInput}
            onChange={(e) => setClaimInput(e.target.value)}
          />
          <div className="small text-muted" style={{ marginTop: 4 }}>
            If you type an email, we’ll verify against <code>owner:sha256(email)</code>.
          </div>
        </div>

        {/* Optional media id */}
        <div style={{ marginTop: 8 }}>
          <label className="label">Media ID (optional, 64-hex)</label>
          <input
            className="input"
            placeholder="e.g. 0e8e5e32aebc2d…"
            value={mediaIdInput}
            onChange={(e) => setMediaIdInput(e.target.value)}
          />
          <div className="small text-muted" style={{ marginTop: 4 }}>
            If provided, we verify exact text <code>owner:&lt;sha&gt;|media:&lt;id&gt;</code> (same as the WM page embeds).
          </div>
        </div>

        {/* Preset + overrides */}
        <div style={{ marginTop: 16 }}>
          <label className="label">Target platform preset</label>
          <select className="select" value={preset} onChange={(e) => setPreset(e.target.value)}>
            <option value="facebook">Facebook (2048px)</option>
            <option value="whatsapp">WhatsApp (1280px)</option>
            <option value="instagram">Instagram (1080px)</option>
            <option value="x_twitter">X / Twitter (2048px)</option>
            <option value="original">Original (no resize)</option>
          </select>
          <div className="small text-muted" style={{ marginTop: 4 }}>{hint}</div>

          <div style={{ marginTop: 10 }}>
            <label className="checkbox">
              <input type="checkbox" checked={advanced} onChange={(e) => setAdvanced(e.target.checked)} />
              <span> Advanced overrides</span>
            </label>
          </div>

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
                  <span> Use Y-channel</span>
                </label>
              </div>
            </div>
          )}
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
          style={{ marginTop: 16 }}
        >
          <div className="dropzone-inner">
            <div className="drop-icon">🖼️</div>
            <div className="drop-title">Drop a received image</div>
            <div className="drop-sub">or</div>
            <label className="btn btn-ghost" htmlFor="v-file">Choose File</label>
            <input
              id="v-file"
              type="file"
              accept="image/*"
              style={{ display: "none" }}
              onChange={(e) => onPick(e.target.files?.[0] ?? null)}
            />
            <div className="file-meta">{prettyFile}</div>
          </div>
        </div>

        {/* Actions */}
        <div className="actions">
          <button
            className={`btn ${busy ? "btn-disabled" : ""}`}
            onClick={onVerify}
            disabled={!file || !claimInput.trim() || busy}
          >
            {busy ? (<><span className="spinner" /> Verifying…</>) : "Verify Ownership"}
          </button>

          <button
            className={`btn ${onchainBusy ? "btn-disabled" : ""}`}
            type="button"
            style={{ marginLeft: 8 }}
            onClick={onCheckOnChainByMediaId}
            disabled={onchainBusy}
          >
            {onchainBusy ? (<><span className="spinner" /> Checking…</>) : "Check on-chain (by media id)"}
          </button>

          <button
            className={`btn ${onchainBusy || !file ? "btn-disabled" : ""}`}
            type="button"
            style={{ marginLeft: 8 }}
            onClick={onCheckOnChainExact}
            disabled={!file || onchainBusy}
          >
            {onchainBusy ? (<><span className="spinner" /> Checking…</>) : "Check on-chain (exact)"}
          </button>

          <button className="btn btn-ghost" type="button" onClick={() => onPick(null)}>
            Reset
          </button>
        </div>

        {status && <div className="status" style={{ marginTop: 12 }}>{status}</div>}

        {/* Quick result chips */}
        {result && (
          <div className="metrics">
            <div className="metrics-title">Result</div>
            <div className="chips">
              <div className="chip"><span className="chip-key">payload_bits</span><span className="chip-val">{result.payload_bitlen}</span></div>
              <div className="chip"><span className="chip-key">ecc_ok</span><span className="chip-val">{String(result.ecc_ok)}</span></div>
              <div className="chip"><span className="chip-key">match_text_hash</span><span className="chip-val">{String(result.match_text_hash)}</span></div>
              <div className="chip"><span className="chip-key">similarity</span><span className="chip-val">{result.similarity ?? "n/a"}</span></div>
              <div className="chip"><span className="chip-key">used_repetition</span><span className="chip-val">{result.used_repetition}</span></div>
              {parsedOwnerSha && (
                <div className="chip"><span className="chip-key">owner_email_sha</span><span className="chip-val">{parsedOwnerSha}</span></div>
              )}
              {parsedMediaId && (
                <div className="chip"><span className="chip-key">media_id</span><span className="chip-val">{parsedMediaId}</span></div>
              )}
            </div>
          </div>
        )}

        {/* On-chain panel */}
        {(onchain || onchainErr) && (
          <div className="metrics" style={{ marginTop: 12 }}>
            <div className="metrics-title">On-chain</div>
            {onchainErr && <div className="status" style={{ color: "red" }}>{onchainErr}</div>}
            {onchain && (
              <div className="chips" style={{ flexWrap: "wrap" }}>
                <div className="chip"><span className="chip-key">exists</span><span className="chip-val">{String(onchain.exists)}</span></div>
                <div className="chip"><span className="chip-key">owner_sha</span><span className="chip-val">{onchain.owner_email_sha}</span></div>
                <div className="chip">
                  <span className="chip-key">timestamp</span>
                  <span className="chip-val">
                    {onchain.timestamp ? new Date(onchain.timestamp * 1000).toLocaleString() : "0"}
                  </span>
                </div>
                {onchain.ipfs_cid && (
                  <div className="chip"><span className="chip-key">ipfs_cid</span><span className="chip-val">{onchain.ipfs_cid}</span></div>
                )}
                {onchain.file_sha256 && (
                  <div className="chip"><span className="chip-key">file_sha256</span><span className="chip-val">{onchain.file_sha256}</span></div>
                )}
              </div>
            )}
          </div>
        )}
      </section>

      {/* Right: preview + verdict */}
      <section className="panel panel--preview">
        <div className="preview-head">
          <div className="preview-title">Image Preview</div>
          {result && (
            <div
              className={
                "verdict " +
                (
                  // Verified if either: (a) legacy text match, or (b) owner from payload matches claim
                  (result.ecc_ok && result.match_text_hash) ||
                  (
                    parsedOwnerSha &&
                    claimInput.toLowerCase().startsWith("owner:") &&
                    toLowerHex(claimInput.slice(6)) === parsedOwnerSha
                  )
                ? "verdict--ok" : "verdict--bad")
              }
              title={
                (result.ecc_ok && result.match_text_hash)
                  ? "Verified (text watermark)"
                  : (parsedOwnerSha ? "Payload decoded" : "Not verified")
              }
            >
              {(result.ecc_ok && result.match_text_hash) ||
               (parsedOwnerSha && claimInput.toLowerCase().startsWith("owner:") &&
                 toLowerHex(claimInput.slice(6)) === parsedOwnerSha)
                ? "Verified"
                : "Not verified"}
            </div>
          )}
        </div>

        <div className="preview">
          {previewUrl ? (
            <img src={previewUrl} alt="to-verify" className="preview-img" />
          ) : (
            <div className="preview-empty">Pick an image to preview and verify.</div>
          )}
        </div>
      </section>
    </div>
  );
}
