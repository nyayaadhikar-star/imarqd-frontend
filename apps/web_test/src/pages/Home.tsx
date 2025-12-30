import React from "react";
import { apiUrl } from "../config";

export function Home() {
  const [file, setFile] = React.useState<File | null>(null);
  const [uploading, setUploading] = React.useState(false);
  const [resultUrl, setResultUrl] = React.useState<string | null>(null);
  const [wmDigest, setWmDigest] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setError(null);
    setResultUrl(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(apiUrl("api/upload"), {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(msg || `Upload failed (${res.status})`);
      }
      const data = (await res.json()) as { url: string };
      setResultUrl(data.url);
      // Build watermark digest metadata (demo values)
      try {
        const wmRes = await fetch(apiUrl("api/wm/build"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            uuidv7: crypto.randomUUID(),
            pgp_fingerprint: "0000000000000000000000000000000000000000",
          }),
        });
        if (wmRes.ok) {
          const wm = await wmRes.json();
          setWmDigest(wm.digest_hex ?? null);
        }
      } catch {}
    } catch (e: any) {
      setError(e.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <section style={{ display: "grid", gap: 16 }}>
      <div style={{ background: "linear-gradient(135deg,#eff6ff,#f5f3ff)", padding: 24, borderRadius: 16, border: "1px solid #e5e7eb" }}>
        <h1 style={{ margin: 0, fontSize: 28, fontWeight: 700 }}>Klyvo Web</h1>
        <p style={{ marginTop: 8, color: "#4b5563" }}>Upload an image to resize it locally. A download link will appear after processing.</p>
      </div>

      <div style={{ display: "grid", gap: 12, maxWidth: 560 }}>
        <label style={{ fontWeight: 600 }}>Select image</label>
        <input
          type="file"
          accept="image/*"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          style={{ padding: 8, borderRadius: 8, border: "1px solid #e5e7eb" }}
        />

        <details>
          <summary style={{ cursor: "pointer", fontWeight: 600 }}>Watermark preview</summary>
          <p style={{ color: "#6b7280" }}>Uploads will be resized to max 1024px and watermarked “Klyvo” in the bottom-right.</p>
        </details>

        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <button
            disabled={!file || uploading}
            onClick={handleUpload}
            style={{
              padding: "10px 16px",
              borderRadius: 8,
              border: "1px solid transparent",
              background: uploading ? "#9ca3af" : "#2563eb",
              color: "#fff",
              fontWeight: 600,
            }}
          >
            {uploading ? "Uploading..." : "Upload and Resize"}
          </button>

          {resultUrl && (
            <a
              href={resultUrl}
              download
              target="_blank"
              rel="noreferrer"
              style={{ padding: "10px 16px", borderRadius: 8, border: "1px solid #e5e7eb", background: "#f3f4f6", color: "#111827", fontWeight: 600 }}
            >
              Download Resized Image
            </a>
          )}
        </div>

        {wmDigest && (
          <div style={{ color: "#065f46", background: "#ecfdf5", border: "1px solid #a7f3d0", padding: 12, borderRadius: 8 }}>
            Watermark digest (hex): {wmDigest}
          </div>
        )}
        {error && (
          <div style={{ color: "#b91c1c", fontWeight: 600, background: "#fee2e2", border: "1px solid #fecaca", padding: 12, borderRadius: 8 }}>
            {error}
          </div>
        )}
      </div>
    </section>
  );
}


