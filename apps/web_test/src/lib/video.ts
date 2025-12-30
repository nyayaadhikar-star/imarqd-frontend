// src/lib/video.ts
import { apiUrl } from "../config";
import { loadAuth } from "./auth";

export type VideoPreset = {
  name: string;
  long_edge: number | null;
  target_fps: number | null;
  crf: number;
  x264_preset: string;
  defaults: {
    qim_step: number;
    repetition: number;
    ecc_parity_bytes: number;
    use_y_channel: boolean;
    frame_step: number;
  };
};

export type VideoExtractResult = {
  payload_bitlen: number;
  similarity?: number | null;
  recovered_hex: string;
  ecc_ok?: boolean | null;
  match_text_hash?: boolean | null;
  used_repetition?: number | null;
  used_frame_step?: number | null;
};

export async function fetchVideoPresets(): Promise<VideoPreset[]> {
  const r = await fetch(apiUrl("watermark/presets/video"));
  if (!r.ok) throw new Error(await r.text());
  return (await r.json()) as VideoPreset[];
}

export async function postVideoWatermark(fd: FormData): Promise<Response> {
  const auth = loadAuth();
  if (!auth) throw new Error("Not logged in");

  // Returns raw Response (MP4 body)
  return fetch(apiUrl("watermark/video"), {
    method: "POST",
    headers: { Authorization: `Bearer ${auth.token}` },
    body: fd,
  });
}

export async function postVideoExtract(fd: FormData): Promise<VideoExtractResult> {
  const auth = loadAuth();
  if (!auth) throw new Error("Not logged in");

  const r = await fetch(apiUrl("watermark/video/extract"), {
    method: "POST",
    headers: { Authorization: `Bearer ${auth.token}` },
    body: fd,
  });

  if (!r.ok) {
    const txt = await r.text();
    throw new Error(txt || `video/extract: HTTP ${r.status}`);
  }
  return (await r.json()) as VideoExtractResult;
}
