# apps/api/src/app/api/routes/video.py
from __future__ import annotations

import json
import os
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse

# reuse existing image/video libs you already have
from ...services.watermarking.video_embed import (
    DCTVideoConfig,
    embed_dct_video,
    VIDEO_PRESETS,   # dict of platform presets
)
from ...services.watermarking.ecc import ecc_encode_sha256

router = APIRouter(prefix="/watermark/video", tags=["watermark-video"])

# resolve ffmpeg/ffprobe + python
FFMPEG = os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = os.environ.get("FFPROBE_BIN") or shutil.which("ffprobe") or "ffprobe"
PYTHON = os.environ.get("PYTHON_BIN") or shutil.which("python") or "python"


# ---------- helpers ----------
def _sha256_bytes(s: str) -> bytes:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).digest()

def _build_payload(text: str, use_ecc: bool, parity: int) -> bytes:
    raw32 = _sha256_bytes(text)
    return ecc_encode_sha256(raw32, parity_bytes=int(parity)) if use_ecc else raw32


# ---------- routes ----------
@router.get("/presets")
def list_video_presets():
    """Expose video presets so the frontend can populate the selector."""
    out = []
    for name, cfg in VIDEO_PRESETS.items():
        out.append({
            "name": name,
            "long_edge": cfg.get("long_edge"),
            "target_fps": cfg.get("target_fps"),
            "crf": cfg.get("crf"),
            "x264_preset": cfg.get("x264_preset"),
            # sensible defaults for embed params (mirror your working WA/FB values)
            "defaults": {
                "qim_step": 24.0 if name != "whatsapp" else 28.0,
                "repetition": 160 if name != "whatsapp" else 240,
                "ecc_parity_bytes": 64,
                "use_y_channel": True,
                "frame_step": 1 if name == "whatsapp" else 2,
            }
        })
    return {"presets": out}


@router.post("")
async def watermark_video(
    file: UploadFile = File(...),
    text: str = Form(...),

    # platform preset + overrides
    preset: str = Form("facebook"),
    qim_step: Optional[float] = Form(None),
    repetition: Optional[int] = Form(None),
    use_y_channel: Optional[bool] = Form(None),
    use_ecc: bool = Form(True),
    ecc_parity_bytes: Optional[int] = Form(None),
    frame_step: Optional[int] = Form(None),

    # video pipeline overrides (optional)
    long_edge: Optional[int] = Form(None),
    fps: Optional[int] = Form(None),
    crf: Optional[int] = Form(None),
    lossless: bool = Form(False, description="encode output losslessly for local tests (libx264 crf=0 yuv444p)"),
):
    """
    Embed a robust invisible watermark into MP4 and return the watermarked file.
    """
    try:
        # persist upload
        suffix = Path(file.filename or "upload.mp4").suffix or ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_in:
            tmp_in.write(await file.read())
            tmp_in_path = Path(tmp_in.name)

        # build payload (ECC(SHA256(text)))
        ecc_par = int(ecc_parity_bytes) if ecc_parity_bytes is not None else 64
        payload = _build_payload(text, use_ecc, ecc_par)

        # init config from preset + overrides (stays consistent w/ your CLI)
        vcfg = DCTVideoConfig(
            preset=preset,
            qim_step=(qim_step if qim_step is not None else (28.0 if preset == "whatsapp" else 24.0)),
            repetition=(repetition if repetition is not None else (240 if preset == "whatsapp" else 160)),
            use_y_channel=(use_y_channel if use_y_channel is not None else True),
            use_ecc=use_ecc,
            ecc_parity_bytes=ecc_par,
            frame_step=(frame_step if frame_step is not None else (1 if preset == "whatsapp" else 2)),
            long_edge=long_edge,
            target_fps=fps,
            crf=(crf if crf is not None else (23 if preset != "facebook" else 22)),
            x264_preset="faster",
        )

        # output path
        out_path = Path(tempfile.gettempdir()) / f"wm_{tmp_in_path.stem}.mp4"

        # run
        embed_dct_video(str(tmp_in_path), str(out_path), payload, vcfg, lossless=bool(lossless))

        # cleanup upload asap
        tmp_in_path.unlink(missing_ok=True)

        # headers: echo back params so FE can store them for later verify
        headers = {
            "X-Preset": preset,
            "X-Params-QIM": str(vcfg.qim_step),
            "X-Params-Repetition": str(vcfg.repetition),
            "X-Params-FrameStep": str(vcfg.frame_step),
            "X-Params-UseY": str(bool(vcfg.use_y_channel)).lower(),
            "X-Params-UseECC": str(bool(vcfg.use_ecc)).lower(),
            "X-Params-ECC-Parity": str(vcfg.ecc_parity_bytes),
            "X-Pre-Long-Edge": str(vcfg.long_edge or ""),
            "X-Pre-FPS": str(vcfg.target_fps or ""),
            "X-CRF": str(vcfg.crf),
        }

        return FileResponse(
            str(out_path),
            media_type="video/mp4",
            filename=out_path.name,
            headers=headers,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Video watermark failed: {e}")


@router.post("/extract")
async def extract_video(
    file: UploadFile = File(...),
    # exact params *usually* not required for the extractor, but allow overrides:
    qim_step: float = Form(24.0),
    repetition: int = Form(160),
    frame_step: int = Form(2),
    use_ecc: bool = Form(True),
    ecc_parity_bytes: int = Form(64),
    check_text: str = Form(..., description="the claim originally embedded (e.g. owner:<email_sha>)"),
):
    """
    Verify watermark in a video. Uses your tested CLI extractor under the hood to
    remain consistent with your terminal runs.
    """
    try:
        # persist upload
        suffix = Path(file.filename or "video.mp4").suffix or ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_in:
            tmp_in.write(await file.read())
            tmp_in_path = Path(tmp_in.name)

        # build CLI
        # python -m app.services.watermarking.video_extract --in foo.mp4 --qim 28 --rep 240 --frame-step 1 --use-ecc --ecc 64 --check-text "..."
        mod = "app.services.watermarking.video_extract"
        cmd = [
            PYTHON, "-m", mod,
            "--in", str(tmp_in_path),
            "--qim", str(qim_step),
            "--rep", str(repetition),
            "--frame-step", str(frame_step),
            "--ecc", str(ecc_parity_bytes),
            "--check-text", check_text,
        ]
        if use_ecc:
            cmd.append("--use-ecc")
        else:
            cmd.append("--no-ecc")

        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        tmp_in_path.unlink(missing_ok=True)

        if proc.returncode != 0:
            raise RuntimeError(proc.stderr or "Extractor failed")

        # stdout is JSON (as per your CLI). Return it directly.
        data = json.loads(proc.stdout.strip())
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Video extract failed: {e}")
