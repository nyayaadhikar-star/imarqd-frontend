import React, { useMemo, useState } from "react";
import { postVideoExtract, VideoExtractResult } from "../lib/video";
import { loadAuth } from "../lib/auth";

export default function VideoVerify(): JSX.Element {
  const auth = loadAuth();
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string>("");
  const [busy, setBusy] = useState<boolean>(false);
  const [result, setResult] = useState<VideoExtractResult | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const claim = useMemo<string>(() => (auth ? `owner:${auth.email_sha}` : ""), [auth]);

  function onPick(f?: File | null): void {
    setResult(null);
    setStatus("");
    if (!f) {
      setFile(null);
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
      return;
    }
    setFile(f);
    const u = URL.createObjectURL(f);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(u);
  }

  async function onVerify(): Promise<void> {
    if (!file) { setStatus("Pick a video first."); return; }
    setBusy(true);
    setStatus("Verifying…");
    setResult(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      // Defaults aligned with WhatsApp/FB pipeline; change if needed
      fd.append("use_y_channel", "true");
      fd.append("use_ecc", "true");
      fd.append("ecc_parity_bytes", String(64));
      fd.append("qim_step", String(28.0));
      fd.append("repetition", String(240));
      fd.append("frame_step", String(1));
      fd.append("check_text", claim);

      const data = await postVideoExtract(fd);
      setResult(data);
      setStatus(data.ecc_ok && data.match_text_hash ? "✅ Verified." : "⚠️ Not verified.");
    } catch (e: unknown) {
      setStatus((e as Error).message || "Verification failed.");
    } finally {
      setBusy(false);
    }
  }

  const prettyFile = file ? `${file.name} • ${(file.size / 1024 / 1024).toFixed(2)} MB` : "No file selected";

  return (
    <div className="wm-shell">
      <section className="panel panel--controls">
        <div className="banner">
          <div className="banner-title">Verify Video</div>
          <div className="banner-sub">Against claim: <code className="kbd">{claim || "—"}</code></div>
        </div>

        <div className="dropzone" onDragOver={(e) => { e.preventDefault(); }}
             onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) onPick(f); }}>
          <div className="dropzone-inner">
            <div className="drop-title">Drop a received video</div>
            <div className="drop-sub">or</div>
            <label className="btn btn-ghost" htmlFor="vvfile">Choose File</label>
            <input id="vvfile" type="file" accept="video/*" style={{ display: "none" }}
                   onChange={(e: React.ChangeEvent<HTMLInputElement>) => onPick(e.target.files?.[0] ?? null)} />
            <div className="file-meta">{prettyFile}</div>
          </div>
        </div>

        <div className="actions">
          <button className={`btn ${busy ? "btn-disabled" : ""}`} onClick={onVerify} disabled={!file || busy}>
            {busy ? "Verifying…" : "Verify"}
          </button>
          <button className="btn btn-ghost" onClick={() => onPick(null)} type="button">Reset</button>
        </div>

        {status && <div className="status">{status}</div>}

        {result && (
          <div className="metrics">
            <div className="metrics-title">Result</div>
            <div className="chips">
              <div className="chip"><span className="chip-key">payload_bits</span><span className="chip-val">{result.payload_bitlen}</span></div>
              <div className="chip"><span className="chip-key">ecc_ok</span><span className="chip-val">{String(result.ecc_ok)}</span></div>
              <div className="chip"><span className="chip-key">match_text_hash</span><span className="chip-val">{String(result.match_text_hash)}</span></div>
              <div className="chip"><span className="chip-key">similarity</span><span className="chip-val">{result.similarity ?? "n/a"}</span></div>
              <div className="chip"><span className="chip-key">used_repetition</span><span className="chip-val">{result.used_repetition}</span></div>
            </div>
          </div>
        )}
      </section>

      <section className="panel panel--preview">
        <div className="preview-head"><div className="preview-title">Preview</div></div>
        <div className="preview">
          {previewUrl ? <video src={previewUrl} controls className="preview-img" /> : <div className="preview-empty">Pick a video to verify.</div>}
        </div>
      </section>
    </div>
  );
}
