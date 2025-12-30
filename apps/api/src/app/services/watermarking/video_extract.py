# apps/api/src/app/services/watermarking/video_extract.py
from __future__ import annotations

import tempfile
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

import numpy as np

from src.app.services.watermarking.schemas import DCTConfig
from src.app.services.watermarking.image_extract import extract_dct_image_ychannel, extract_dct_image
from src.app.services.watermarking.helpers import bits_to_bytes
from src.app.services.watermarking.ecc import ecc_decode_to_sha256, ecc_encode_sha256


@dataclass
class DCTVideoExtractConfig:
    qim_step: float = 24.0
    repetition: int = 160
    use_y_channel: bool = True

    # which frames to sample
    frame_step: int = 2                   # analyze every Nth frame
    max_frames: Optional[int] = 120       # cap to speed up (None = all)

def _run(cmd: List[str]) -> None:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stderr}")

def _extract_frames_for_read(video_path: str, out_dir: Path, frame_step: int) -> List[Path]:
    """
    Extract frames at full rate, then pick every Nth by filename ordering.
    (Simpler than filter_complex; OK for v1.)
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    _run(["ffmpeg", "-y", "-i", video_path, str(out_dir / "frame_%08d.png")])
    frames = sorted(out_dir.glob("frame_*.png"))
    if frame_step > 1:
        frames = frames[::frame_step]
    return frames

def _majority_vote(batches: List[np.ndarray]) -> np.ndarray:
    """
    Combine multiple bit arrays (same length) by majority vote per position.
    """
    if not batches:
        return np.zeros(0, dtype=np.uint8)
    M = np.stack(batches, axis=0).astype(np.uint8)
    ones = M.sum(axis=0)
    zeros = M.shape[0] - ones
    return (ones >= zeros).astype(np.uint8)

def extract_dct_video(
    input_video: str,
    payload_bitlen: int,
    ecfg: DCTVideoExtractConfig,
    use_ecc: bool = True,
    ecc_parity_bytes: int = 64,
    check_text: Optional[str] = None,
):
    """
    Decode frames, run image-extract on every Nth frame, majority-vote bits, then
    optionally ECC-decode and compare to SHA256(check_text).
    Returns dict similar to your image API.
    """
    icfg = DCTConfig(qim_step=float(ecfg.qim_step), repetition=int(ecfg.repetition))

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        frames_dir = td_path / "frames"
        frames = _extract_frames_for_read(input_video, frames_dir, max(1, ecfg.frame_step))
        if ecfg.max_frames:
            frames = frames[:ecfg.max_frames]
        if not frames:
            raise RuntimeError("No frames to analyze.")

        recovered_sets: List[np.ndarray] = []
        for fp in frames:
            if ecfg.use_y_channel:
                bits = extract_dct_image_ychannel(str(fp), payload_bitlen, icfg)
            else:
                bits = extract_dct_image(str(fp), payload_bitlen, icfg)
            recovered_sets.append(bits.astype(np.uint8))

        voted = _majority_vote(recovered_sets)
        rec_bytes = bits_to_bytes(voted)
        result = {
            "payload_bitlen": int(payload_bitlen),
            "used_repetition": int(ecfg.repetition),
            "frames_used": len(recovered_sets),
            "similarity": None,
            "ecc_ok": None,
            "match_text_hash": None,
            "recovered_hex": __import__("hashlib").sha256(rec_bytes).hexdigest(),
        }

        if use_ecc:
            orig32, ok = ecc_decode_to_sha256(rec_bytes, parity_bytes=ecc_parity_bytes)
            result["ecc_ok"] = bool(ok)
            if check_text:
                want32 = __import__("hashlib").sha256(check_text.encode("utf-8")).digest()
                result["match_text_hash"] = bool(want32 == orig32)

                # build expected codeword to compute similarity at bit-level
                expected_codeword = ecc_encode_sha256(want32, parity_bytes=ecc_parity_bytes)
                exp_bits = np.unpackbits(np.frombuffer(expected_codeword, dtype=np.uint8)).astype(np.uint8)
                L = min(len(voted), len(exp_bits))
                result["similarity"] = float(np.mean(voted[:L] == exp_bits[:L]))
        else:
            if check_text:
                want_bits = np.unpackbits(np.frombuffer(
                    __import__("hashlib").sha256(check_text.encode("utf-8")).digest(),
                    dtype=np.uint8
                )).astype(np.uint8)
                L = min(len(voted), len(want_bits))
                result["similarity"] = float(np.mean(voted[:L] == want_bits[:L]))

        return result


# ---------- Simple CLI for bash testing ----------
def main():
    import argparse, math
    ap = argparse.ArgumentParser(description="Extract DCT watermark from video (Y-channel).")
    ap.add_argument("--in", dest="inp", required=True, help="input video path")
    ap.add_argument("--qim", type=float, default=24.0)
    ap.add_argument("--rep", type=int, default=160)
    ap.add_argument("--use-y", action="store_true", default=True)
    ap.add_argument("--frame-step", type=int, default=2)
    ap.add_argument("--max-frames", type=int, default=120)
    ap.add_argument("--use-ecc", action="store_true", default=True)
    ap.add_argument("--ecc", type=int, default=64)
    ap.add_argument("--check-text", type=str, default=None, help="owner:<email_sha> to verify claim")
    ap.add_argument("--payload-bits", type=int, default=None, help="override payload bits; default = (32+ecc)*8 when ECC")
    args = ap.parse_args()

    payload_bits = args.payload_bits
    if payload_bits is None:
        payload_bits = (32 + (args.ecc if args.use_ecc else 0)) * 8

    ecfg = DCTVideoExtractConfig(
        qim_step=args.qim, repetition=args.rep, use_y_channel=True,
        frame_step=max(1, args.frame_step), max_frames=args.max_frames
    )
    out = extract_dct_video(
        args.inp, payload_bits, ecfg,
        use_ecc=args.use_ecc, ecc_parity_bytes=args.ecc, check_text=args.check_text
    )
    # Pretty print
    import json
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
