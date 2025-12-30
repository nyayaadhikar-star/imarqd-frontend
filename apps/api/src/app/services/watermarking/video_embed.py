# apps/api/src/app/services/watermarking/video_embed.py
from __future__ import annotations

import os
import shutil
import tempfile
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List

import numpy as np

# Reuse your image embed bits
from src.app.services.watermarking.schemas import DCTConfig
from src.app.services.watermarking.image_embed import embed_dct_image_ychannel, embed_dct_image
from src.app.services.watermarking.helpers import load_color_bgr_float32, save_color_bgr_uint8
from src.app.services.watermarking.ecc import ecc_encode_sha256

# ---- ffmpeg / ffprobe resolution (NEW retained) ----
FFMPEG  = os.environ.get("FFMPEG_BIN")  or shutil.which("ffmpeg")  or "ffmpeg"
FFPROBE = os.environ.get("FFPROBE_BIN") or shutil.which("ffprobe") or "ffprobe"

# ---- Platform presets (unchanged) ----
VIDEO_PRESETS: Dict[str, Dict[str, Any]] = {
    "original":  { "long_edge": None, "target_fps": None, "crf": 23, "x264_preset": "medium" },
    "facebook":  { "long_edge": 2048, "target_fps": 30,  "crf": 22, "x264_preset": "faster" },
    "instagram": { "long_edge": 1080, "target_fps": 30,  "crf": 22, "x264_preset": "faster" },
    "whatsapp":  { "long_edge": 1280, "target_fps": 30,  "crf": 23, "x264_preset": "faster" },
    "x_twitter": { "long_edge": 2048, "target_fps": 30,  "crf": 23, "x264_preset": "faster" },
}

@dataclass
class DCTVideoConfig:
    # Image embed params
    qim_step: float = 24.0
    repetition: int = 160
    use_y_channel: bool = True
    use_ecc: bool = True
    ecc_parity_bytes: int = 64

    # Video pipeline params
    frame_step: int = 2
    preset: str = "facebook"
    target_fps: Optional[int] = None
    long_edge: Optional[int] = None
    crf: int = 22
    x264_preset: str = "faster"

    # NEW: pre-normalize switch (default ON)
    pre_normalize: bool = True

    # Derived from preset if not explicitly set
    def apply_preset(self) -> None:
        p = VIDEO_PRESETS.get(self.preset.lower(), VIDEO_PRESETS["original"])
        if self.long_edge is None:      self.long_edge = p["long_edge"]
        if self.target_fps is None:     self.target_fps = p["target_fps"]
        if self.crf is None:            self.crf = p["crf"]
        if not self.x264_preset:        self.x264_preset = p["x264_preset"]


def _run(cmd: List[str]) -> None:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr}")


def _ffmpeg_scale_filter(long_edge: Optional[int]) -> Optional[str]:
    if not long_edge:
        return None
    return f"scale='if(gt(iw,ih),{long_edge},-2)':'if(gt(iw,ih),-2,{long_edge})':flags=lanczos"


def _extract_frames(video_path: str, out_dir: Path, target_fps: Optional[int], scale_filter: Optional[str]) -> float:
    out_dir.mkdir(parents=True, exist_ok=True)

    # Probe fps
    probe = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate", "-of", "default=nk=1:nw=1", video_path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    fps_str = (probe.stdout or "30/1").strip()
    try:
        num, den = fps_str.split("/")
        src_fps = float(num) / float(den)
    except Exception:
        src_fps = 30.0

    vf_parts = []
    if scale_filter:
        vf_parts.append(scale_filter)
    if target_fps:
        vf_parts.append(f"fps={int(target_fps)}")
    vf = ",".join(vf_parts) if vf_parts else "null"

    # Extract frames as PNG (lossless) for watermarking
    _run([
        FFMPEG, "-y", "-i", video_path, "-vf", vf,
        str(out_dir / "frame_%08d.png")
    ])
    return src_fps


def _extract_audio(video_path: str, audio_out: Path) -> bool:
    try:
        _run([FFMPEG, "-y", "-i", video_path, "-vn", "-acodec", "aac", "-b:a", "192k", str(audio_out)])
        return audio_out.exists() and audio_out.stat().st_size > 0
    except Exception:
        return False


# ---------- NEW: pre-normalize video to preset spec ----------
def _pre_normalize_video(src: str, dst: Path, long_edge: Optional[int],
                         target_fps: Optional[int], crf: int, x264_preset: str) -> None:
    vf_parts = []
    if long_edge:
        vf_parts.append(f"scale='if(gt(iw,ih),{long_edge},-2)':'if(gt(iw,ih),-2,{long_edge})':flags=lanczos")
    if target_fps:
        vf_parts.append(f"fps={int(target_fps)}")
    vf = ",".join(vf_parts) if vf_parts else "null"

    _run([
        FFMPEG, "-y",
        "-i", src,
        "-vf", vf,
        "-c:v", "libx264", "-preset", x264_preset, "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-profile:v", "main", "-level", "4.1",
        "-g", str((target_fps or 30) * 2), "-keyint_min", str((target_fps or 30)),
        "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart",
        str(dst)
    ])


def embed_dct_video(
    input_video: str,
    output_video: str,
    payload_bytes: bytes,
    vcfg: DCTVideoConfig,
    *, lossless: bool = False   # NEW retained
) -> None:
    vcfg.apply_preset()
    payload_bits = np.unpackbits(np.frombuffer(payload_bytes, dtype=np.uint8)).astype(np.uint8)
    icfg = DCTConfig(qim_step=float(vcfg.qim_step), repetition=int(vcfg.repetition))

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        frames_dir = tmp / "frames"
        marked_dir = tmp / "marked"
        audio_aac = tmp / "audio.aac"
        norm_mp4  = tmp / "pre_norm.mp4"  # NEW

        marked_dir.mkdir(parents=True, exist_ok=True)

        # --------- NEW: pre-normalize once to target platform ---------
        source_for_embed = input_video
        if vcfg.pre_normalize:
            _pre_normalize_video(
                src=input_video, dst=norm_mp4,
                long_edge=vcfg.long_edge, target_fps=vcfg.target_fps,
                crf=vcfg.crf, x264_preset=vcfg.x264_preset
            )
            source_for_embed = str(norm_mp4)

        # 1) Decode frames (+ optional scale/fps) and 2) audio
        # If we already pre-normalized, do NOT scale/fps again here.
        scale_filter = None if vcfg.pre_normalize else _ffmpeg_scale_filter(vcfg.long_edge)
        target_fps_for_extract = None if vcfg.pre_normalize else vcfg.target_fps

        _ = _extract_frames(source_for_embed, frames_dir, target_fps_for_extract, scale_filter)
        has_audio = _extract_audio(source_for_embed, audio_aac)

        # 3) Embed on every Nth frame
        frame_paths = sorted(frames_dir.glob("frame_*.png"))
        if not frame_paths:
            raise RuntimeError("No frames extracted from input video.")

        for idx, fp in enumerate(frame_paths, start=1):
            out_fp = marked_dir / fp.name
            if (idx - 1) % max(1, vcfg.frame_step) == 0:
                if vcfg.use_y_channel:
                    embed_dct_image_ychannel(str(fp), str(out_fp), payload_bits, icfg)
                else:
                    embed_dct_image(str(fp), str(out_fp), payload_bits, icfg)
            else:
                shutil.copy2(fp, out_fp)

        # 4) Re-encode
        video_in_pattern = str(marked_dir / "frame_%08d.png")

        if lossless:
            encode_args = [
                "-c:v", "libx264",
                "-preset", "veryslow",
                "-crf", "0",
                "-g", "1",
                "-pix_fmt", "yuv444p"
            ]
        else:
            encode_args = [
                "-c:v", "libx264",
                "-preset", vcfg.x264_preset,
                "-crf", str(vcfg.crf),
                "-pix_fmt", "yuv420p"
            ]

        if has_audio:
            _run([
                FFMPEG, "-y",
                "-r", str(vcfg.target_fps or 30), "-i", video_in_pattern,
                "-i", str(audio_aac),
                *encode_args,
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                "-movflags", "+faststart",
                output_video
            ])
        else:
            _run([
                FFMPEG, "-y",
                "-r", str(vcfg.target_fps or 30), "-i", video_in_pattern,
                *encode_args,
                "-movflags", "+faststart",
                output_video
            ])


# ---------- Simple CLI for bash testing ----------
def _sha32(text: str) -> bytes:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).digest()

def _build_payload(text: str, use_ecc: bool, parity: int) -> bytes:
    raw32 = _sha32(text)   # 32 bytes
    return ecc_encode_sha256(raw32, parity_bytes=parity) if use_ecc else raw32

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Embed DCT watermark into video (Y-channel).")
    ap.add_argument("--in", dest="inp", required=True, help="input video path")
    ap.add_argument("--out", dest="outp", required=True, help="output mp4 path")
    ap.add_argument("--text", required=True, help="claim text e.g. owner:<email_sha>")
    ap.add_argument("--preset", default="facebook", help="original|facebook|instagram|whatsapp|x_twitter")
    ap.add_argument("--qim", type=float, default=24.0)
    ap.add_argument("--rep", type=int, default=160)
    ap.add_argument("--ecc", type=int, default=64)
    ap.add_argument("--no-ecc", action="store_true", help="disable ECC")
    ap.add_argument("--frame-step", type=int, default=2, help="embed every Nth frame (1=every frame)")
    ap.add_argument("--long-edge", type=int, default=None, help="override preset long-edge")
    ap.add_argument("--fps", type=int, default=None, help="override preset target fps")
    ap.add_argument("--crf", type=int, default=None, help="override preset CRF")
    ap.add_argument("--lossless", action="store_true", help="encode output losslessly (for local testing)")
    # NEW: toggle pre-normalize (default ON)
    ap.add_argument("--pre-normalize", dest="pre_normalize", action="store_true", default=True,
                    help="pre-normalize to preset spec before embedding (default on)")
    ap.add_argument("--no-pre-normalize", dest="pre_normalize", action="store_false")
    args = ap.parse_args()

    payload = _build_payload(args.text, not args.no_ecc, args.ecc)

    vcfg = DCTVideoConfig(
        qim_step=args.qim, repetition=args.rep, use_y_channel=True,
        use_ecc=not args.no_ecc, ecc_parity_bytes=args.ecc,
        frame_step=max(1, args.frame_step), preset=args.preset,
        long_edge=args.long_edge, target_fps=args.fps,
        crf=args.crf if args.crf is not None else 22,
        x264_preset="faster",
        pre_normalize=args.pre_normalize,   # NEW
    )
    embed_dct_video(args.inp, args.outp, payload, vcfg, lossless=args.lossless)

if __name__ == "__main__":
    main()
