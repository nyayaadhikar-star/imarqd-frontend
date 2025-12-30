import React, { useEffect, useMemo, useState } from "react";
import { loadAuth } from "../lib/auth";
import { fetchVideoPresets, postVideoWatermark, postVideoExtract, VideoPreset, VideoExtractResult } from "../lib/video";

export default function VideoWatermark(): JSX.Element {
  const auth = loadAuth();
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string>("");
  const [headers, setHeaders] = useState<Record<string, string>>({});
  const [presets, setPresets] = useState<VideoPreset[]>([]);
  const [preset, setPreset] = useState<string>("whatsapp");

  // advanced overrides
  const [advanced, setAdvanced] = useState<boolean>(false);
  const [qim, setQim] = useState<number>(24.0);
  const [rep, setRep] = useState<number>(160);
  const [ecc, setEcc] = useState<number>(64);
  const [frameStep, setFrameStep] = useState<number>(1);

  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [wmBlob, setWmBlob] = useState<Blob | null>(null);

  const [verifyBusy, setVerifyBusy] = useState<boolean>(false);
  const [verifyStatus, setVerifyStatus] = useState<string>("");
  const [verifyResult, setVerifyResult] = useState<VideoExtractResult | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const ps = await fetchVideoPresets();
        setPresets(ps);
        const start = ps.find((p) => p.name === "whatsapp");
        if (start) {
          setQim(start.defaults.qim_step);
          setRep(start.defaults.repetition);
          setEcc(start.defaults.ecc_parity_bytes);
          setFrameStep(start.defaults.frame_step ?? 1);
        }
      } catch (e) {
        // eslint-disable-next-line no-console
        console.error(e);
      }
    })();
  }, []);

  useEffect(() => {
    if (!advanced && presets.length) {
      const p = presets.find((x) => x.name === preset);
      if (p) {
        setQim(p.defaults.qim_step);
        setRep(p.defaults.repetition);
        setEcc(p.defaults.ecc_parity_bytes);
        setFrameStep(p.defaults.frame_step ?? 1);
      }
    }
  }, [preset, advanced, presets]);

  if (!auth) return <p>Please log in first.</p>;
  const claim = `owner:${auth.email_sha}`; // or `owner:${auth.email_sha}` if you prefer

  const hint = useMemo<string>(() => {
    const p = presets.find((x) => x.name === preset);
    if (!p) return "";
    const lg = p.long_edge ? `resize to long edge ${p.long_edge}px` : "no resize";
    const fps = p.target_fps ? `, ${p.target_fps} fps` : "";
    return `${lg}${fps}`;
  }, [preset, presets]);

  function onPick(f?: File | null): void {
    setStatus("");
    setVerifyStatus("");
    setVerifyResult(null);
    setWmBlob(null);
    setHeaders({});
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

  async function onSubmit(e: React.FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    if (!file) { setStatus("Pick a video file."); return; }

    setStatus("Embedding watermark (this may take a bit)...");
    setHeaders({});
    setWmBlob(null);
    setVerifyStatus("");
    setVerifyResult(null);

    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("text", claim);
      fd.append("preset", preset);
      fd.append("use_ecc", "true");
      fd.append("frame_step", String(frameStep));
      // lossless=false by default (backend chooses good H.264 settings)

      if (advanced) {
        fd.append("use_y_channel", "true");
        fd.append("qim_step", String(qim));
        fd.append("repetition", String(rep));
        fd.append("ecc_parity_bytes", String(ecc));
      }

      const res = await postVideoWatermark(fd);
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || `HTTP ${res.status}`);
      }

      // read headers (x-*)
      const hs: Record<string, string> = {};
      res.headers.forEach((value, key) => {
        if (key.startsWith("x-")) hs[key] = value;
      });
      setHeaders(hs);

      const blob = await res.blob();
      setWmBlob(blob);

      // provide a local download/preview URL
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      const u = URL.createObjectURL(blob);
      setPreviewUrl(u);

      setStatus("Done! Watermarked video below.");
    } catch (err: unknown) {
      setStatus((err as Error).message || "Watermark failed");
    }
  }

  async function onVerifyNow(): Promise<void> {
    if (!wmBlob) { setVerifyStatus("Nothing to verify yet."); return; }
    setVerifyBusy(true);
    setVerifyStatus("Verifying…");
    setVerifyResult(null);
    try {
      // Use params from headers if present
      const num = (s?: string): number | undefined => (s ? Number(s) : undefined);
      const bool = (s?: string): boolean => (s ?? "").toLowerCase() === "true";

      const fd = new FormData();
      fd.append("file", new File([wmBlob], "wm.mp4", { type: "video/mp4" }));
      fd.append("use_y_channel", String(bool(headers["x-params-usey"] || "true")));
      fd.append("use_ecc", String(bool(headers["x-params-useecc"] || "true")));
      fd.append("ecc_parity_bytes", String(num(headers["x-params-ecc-parity"]) ?? ecc));
      fd.append("qim_step", String(num(headers["x-params-qim"]) ?? qim));
      fd.append("repetition", String(num(headers["x-params-repetition"]) ?? rep));
      fd.append("frame_step", String(num(headers["x-params-framestep"]) ?? frameStep));
      fd.append("check_text", claim);

      const data = await postVideoExtract(fd);
      setVerifyResult(data);
      setVerifyStatus(data.ecc_ok && data.match_text_hash
        ? "✅ Verified (watermark intact)."
        : "⚠️ Not verified.");
    } catch (e: unknown) {
      setVerifyStatus((e as Error).message || "Verification failed.");
    } finally {
      setVerifyBusy(false);
    }
  }

  const prettyFile = file ? `${file.name} • ${(file.size / 1024 / 1024).toFixed(2)} MB` : "No file selected";

  return (
    <div className="wm-shell">
      <section className="panel panel--controls">
        <div className="banner">
          <div className="banner-title">Video Watermark</div>
          <div className="banner-sub">
            Preset:&nbsp;<code className="kbd">{preset}</code>&nbsp;({hint})
          </div>
        </div>

        <form onSubmit={onSubmit}>
          <div className="field">
            <label style={{ fontWeight: 600 }}>Target platform</label>
            <select value={preset} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setPreset(e.target.value)}>
              <option value="whatsapp">WhatsApp</option>
              <option value="facebook">Facebook</option>
              <option value="instagram">Instagram</option>
              <option value="x_twitter">X / Twitter</option>
              <option value="original">Original</option>
            </select>
          </div>

          <div className="dropzone" onDragOver={(e) => { e.preventDefault(); }} onDrop={(e) => {
            e.preventDefault();
            const f = e.dataTransfer.files?.[0];
            if (f) onPick(f);
          }}>
            <div className="dropzone-inner">
              <div className="drop-title">Drop a video file</div>
              <div className="drop-sub">or</div>
              <label className="btn btn-ghost" htmlFor="vfile">Choose File</label>
              <input id="vfile" type="file" accept="video/*" style={{ display: "none" }}
                     onChange={(e: React.ChangeEvent<HTMLInputElement>) => onPick(e.target.files?.[0] ?? null)} />
              <div className="file-meta">{prettyFile}</div>
            </div>
          </div>

          <div className="field" style={{ marginTop: 12 }}>
            <label className="inline">
              <input type="checkbox" checked={advanced}
                     onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAdvanced(e.target.checked)} />
              &nbsp;Advanced overrides
            </label>
          </div>

          {advanced && (
            <div className="grid-2">
              <div className="field">
                <label>QIM step</label>
                <input type="number" step={0.5} value={qim} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setQim(parseFloat(e.target.value))} />
              </div>
              <div className="field">
                <label>Repetition</label>
                <input type="number" value={rep} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRep(parseInt(e.target.value, 10))} />
              </div>
              <div className="field">
                <label>ECC parity bytes</label>
                <input type="number" value={ecc} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEcc(parseInt(e.target.value, 10))} />
              </div>
              <div className="field">
                <label>Frame step</label>
                <input type="number" value={frameStep} min={1} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFrameStep(parseInt(e.target.value, 10))} />
              </div>
            </div>
          )}

          <div className="actions">
            <button className="btn" type="submit">Embed Watermark</button>
          </div>
        </form>

        {status && <div className="status">{status}</div>}

        <div style={{ marginTop: 10 }}>
          <button className="btn" type="button" onClick={onVerifyNow} disabled={!wmBlob || verifyBusy}>
            {verifyBusy ? "Verifying…" : "Verify This Video Now"}
          </button>
          {verifyStatus && <div className="status" style={{ marginTop: 8 }}>{verifyStatus}</div>}
          {verifyResult && (
            <div className="metrics">
              <div className="metrics-title">Result</div>
              <div className="chips">
                <div className="chip"><span className="chip-key">payload_bits</span><span className="chip-val">{verifyResult.payload_bitlen}</span></div>
                <div className="chip"><span className="chip-key">ecc_ok</span><span className="chip-val">{String(verifyResult.ecc_ok)}</span></div>
                <div className="chip"><span className="chip-key">match_text_hash</span><span className="chip-val">{String(verifyResult.match_text_hash)}</span></div>
                <div className="chip"><span className="chip-key">similarity</span><span className="chip-val">{verifyResult.similarity ?? "n/a"}</span></div>
                <div className="chip"><span className="chip-key">used_repetition</span><span className="chip-val">{verifyResult.used_repetition}</span></div>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="panel panel--preview">
        <div className="preview-head">
          <div className="preview-title">Video Preview</div>
        </div>
        <div className="preview">
          {previewUrl ? (
            <video src={previewUrl} controls className="preview-img" />
          ) : (
            <div className="preview-empty">Pick/produce a video to preview.</div>
          )}
        </div>
        {previewUrl && (
          <div style={{ marginTop: 10 }}>
            <a className="btn btn-ghost" href={previewUrl} download="watermarked.mp4">Download MP4</a>
          </div>
        )}
      </section>
    </div>
  );
}
