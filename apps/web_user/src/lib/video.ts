// Small typed helpers for the video watermark API
import { apiUrl } from "../config";

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
  frames_used?: number | null;
};

export async function fetchVideoPresets(): Promise<VideoPreset[]> {
  const r = await fetch(apiUrl("watermark/video/presets"));
  if (!r.ok) throw new Error(`presets: HTTP ${r.status}`);
  const data = await r.json();
  return (data.presets ?? []) as VideoPreset[];
}

export async function postVideoWatermark(fd: FormData): Promise<Response> {
  // Returns the raw Response (body is the MP4)
  return fetch(apiUrl("watermark/video"), { method: "POST", body: fd });
}

export async function postVideoExtract(fd: FormData): Promise<VideoExtractResult> {
  const r = await fetch(apiUrl("watermark/video/extract"), { method: "POST", body: fd });
  if (!r.ok) {
    const txt = await r.text();
    throw new Error(txt || `video/extract: HTTP ${r.status}`);
  }
  return (await r.json()) as VideoExtractResult;
}
