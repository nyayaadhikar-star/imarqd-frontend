from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, Dict, Any
import tempfile
import hashlib
import numpy as np
import re  # <<< for claim parsing

from sqlalchemy.orm import Session
from fastapi import Depends

from ...db.session import get_db
from ...services.db import crud
from ...services.db.crud import register_media_id  # <<< auto-save media id

from ...services.watermarking.schemas import DCTConfig
from ...services.watermarking.image_embed import (
    embed_dct_image,
    embed_dct_image_ychannel,
    build_payload_from_text,
)
from ...services.watermarking.image_extract import (
    extract_dct_image,
    extract_dct_image_ychannel,
)
from ...services.watermarking.helpers import (
    bits_to_bytes,
    load_color_bgr_float32,
    save_color_bgr_uint8,
    bgr_to_ycbcr,
    psnr,
    ssim_y,
    preprocess_for_preset,   # platform-aware preproc
)
from ...services.watermarking.ecc import ecc_encode_sha256, ecc_decode_to_sha256
from ...services.crypto.pgp_utils import key_fingerprint, verify_detached_signature

router = APIRouter(prefix="/watermark", tags=["watermark"])

DATA_DIR = Path(__file__).resolve().parents[4] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# -------- helpers for auto-register --------
_CLAIM_RE = re.compile(r"owner:([0-9a-fA-F]{64})(?:\|media:([0-9a-fA-F]{64}))?$")

def _hex64(s: str) -> str:
    v = (s or "").lower().removeprefix("0x")
    if len(v) != 64:
        raise HTTPException(400, "Value error, must be 32 bytes (64 hex chars)")
    try:
        int(v, 16)
    except Exception:
        raise HTTPException(400, "Value error, must be hex")
    return v
# ------------------------------------------

# Legacy profiles (used only when no preset is given)
PROFILES: Dict[str, Dict[str, Any]] = {
    "light":            {"qim_step": 8.0,  "repetition": 30, "ecc_parity_bytes": 24, "use_y_channel": True},
    "medium":           {"qim_step": 10.0, "repetition": 40, "ecc_parity_bytes": 32, "use_y_channel": True},
    "robust_whatsapp":  {"qim_step": 14.0, "repetition": 60, "ecc_parity_bytes": 48, "use_y_channel": True},
}

# New platform presets
PRESETS: Dict[str, Dict[str, Any]] = {
    "original": {
        "long_edge": None, "jpeg_quality": None,
        "qim_step": 18.0, "repetition": 120, "ecc_parity_bytes": 32,
        "use_y_channel": True,
    },
    "facebook": {
        "long_edge": 2048, "jpeg_quality": 85,
        "qim_step": 24.0, "repetition": 160, "ecc_parity_bytes": 64,
        "use_y_channel": True,
    },
    "whatsapp": {
        "long_edge": 1280, "jpeg_quality": 85,
        "qim_step": 24.0, "repetition": 160, "ecc_parity_bytes": 64,
        "use_y_channel": True,
    },
    "instagram": {
        "long_edge": 1080, "jpeg_quality": 85,
        "qim_step": 24.0, "repetition": 160, "ecc_parity_bytes": 64,
        "use_y_channel": True,
    },
    "x_twitter": {
        "long_edge": 2048, "jpeg_quality": 85,
        "qim_step": 24.0, "repetition": 160, "ecc_parity_bytes": 64,
        "use_y_channel": True,
    },
}

class ExtractResponse(BaseModel):
    payload_bitlen: int
    similarity: Optional[float] = None
    recovered_hex: str
    ecc_ok: Optional[bool] = None
    match_text_hash: Optional[bool] = None
    used_repetition: Optional[int] = None

@router.get("/presets")
def list_presets():
    return {
        "presets": [
            {
                "name": name,
                "long_edge": cfg.get("long_edge"),
                "jpeg_quality": cfg.get("jpeg_quality"),
                "defaults": {
                    "qim_step": cfg.get("qim_step"),
                    "repetition": cfg.get("repetition"),
                    "ecc_parity_bytes": cfg.get("ecc_parity_bytes"),
                    "use_y_channel": cfg.get("use_y_channel", True),
                },
            }
            for name, cfg in PRESETS.items()
        ]
    }

@router.post("/image")
async def watermark_image(
    file: UploadFile = File(...),
    text: str = Form(...),

    # Optional overrides
    qim_step: Optional[float] = Form(None),
    repetition: Optional[int] = Form(None),
    use_y_channel: Optional[bool] = Form(None),
    use_ecc: bool = Form(True),
    ecc_parity_bytes: Optional[int] = Form(None),

    # Back-compat
    profile: Optional[str] = Form(None, description="light | medium | robust_whatsapp"),
    pre_whatsapp: bool = Form(False),

    # Preset + optional generic overrides (kept minimal)
    preset: Optional[str] = Form(None, description="original|facebook|whatsapp|instagram|x_twitter"),
    pre_generic: bool = Form(False, description="override: enable generic pre-resize"),
    pre_generic_long_edge: Optional[int] = Form(None),
    pre_generic_jpeg_q: Optional[int] = Form(None),

    # PGP (optional)
    pgp_public_key: Optional[str] = Form(None),
    pgp_signature: Optional[str] = Form(None),

    # >>> NEW: auto-register toggles / overrides
    auto_register_media: bool = Form(True, description="If text is owner|media, upsert to DB"),
    override_owner_email_sha: Optional[str] = Form(None, description="Optional if not present in text"),
    override_media_id: Optional[str] = Form(None, description="Optional if not present in text"),
    media_label: Optional[str] = Form(None, description="Friendly label saved with media id"),
    user_uuid: Optional[str] = Form(None, description="Attach to your app user, optional"),

    db: Session = Depends(get_db),
):
    try:
        suffix = Path(file.filename).suffix or ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_in:
            tmp_in.write(await file.read())
            tmp_in_path = Path(tmp_in.name)

        # --- Resolve preset (strict)
        preset_name = (preset or "").lower().strip()
        preset_cfg = {}
        if preset_name:
            if preset_name not in PRESETS:
                raise HTTPException(status_code=400, detail=f"Unknown preset '{preset_name}'")
            preset_cfg = PRESETS[preset_name]

        # --- Param defaults: preset → profile → baseline
        qim_default = 18.0
        rep_default = 120
        par_default = 32
        usey_default = True

        if preset_cfg:
            qim_default = preset_cfg.get("qim_step", qim_default)
            rep_default = preset_cfg.get("repetition", rep_default)
            par_default = preset_cfg.get("ecc_parity_bytes", par_default)
            usey_default = preset_cfg.get("use_y_channel", usey_default)
        elif profile:
            prof = PROFILES.get(profile, {})
            qim_default = prof.get("qim_step", qim_default)
            rep_default = prof.get("repetition", rep_default)
            par_default = prof.get("ecc_parity_bytes", par_default)
            usey_default = prof.get("use_y_channel", usey_default)

        qim_val = float(qim_step if qim_step is not None else qim_default)
        rep_val = int(repetition if repetition is not None else rep_default)
        ecc_par = int(ecc_parity_bytes if ecc_parity_bytes is not None else par_default)
        use_y   = bool(use_y_channel if use_y_channel is not None else usey_default)

        # --- Preprocess (preset or explicit overrides)
        long_edge = pre_generic_long_edge if pre_generic else preset_cfg.get("long_edge") if preset_cfg else None
        jpeg_q    = pre_generic_jpeg_q   if pre_generic else preset_cfg.get("jpeg_quality") if preset_cfg else None

        orig_bgr = load_color_bgr_float32(str(tmp_in_path))
        work_bgr = preprocess_for_preset(orig_bgr, long_edge=long_edge, jpeg_quality=jpeg_q) if (long_edge or jpeg_q) else orig_bgr

        # --- Optional PGP verification (not embedded)
        pgp_fpr = None
        if pgp_public_key and pgp_signature:
            if not verify_detached_signature(pgp_public_key, text.encode("utf-8"), pgp_signature):
                raise HTTPException(status_code=400, detail="PGP signature verification failed")
            pgp_fpr = key_fingerprint(pgp_public_key)

        # --- Payload = ECC(SHA256(text)) for robustness
        sha32 = hashlib.sha256(text.encode("utf-8")).digest()
        payload_bytes = ecc_encode_sha256(sha32, parity_bytes=ecc_par) if use_ecc else sha32
        payload_bits = np.unpackbits(np.frombuffer(payload_bytes, dtype=np.uint8)).astype(np.uint8)

        # --- Embed
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_work:
            save_color_bgr_uint8(tmp_work.name, work_bgr)
            work_in_path = Path(tmp_work.name)

        out_path = DATA_DIR / f"wm_{tmp_in_path.stem}.png"
        cfg = DCTConfig(qim_step=float(qim_val), repetition=int(rep_val))
        if use_y:
            embed_dct_image_ychannel(str(work_in_path), str(out_path), payload_bits, cfg)
        else:
            embed_dct_image(str(work_in_path), str(out_path), payload_bits, cfg)

        out_bgr = load_color_bgr_float32(str(out_path))
        psnr_y = psnr(bgr_to_ycbcr(work_bgr)[0], bgr_to_ycbcr(out_bgr)[0])
        ssim_y_val = ssim_y(work_bgr, out_bgr)

        # Cleanup temps
        tmp_in_path.unlink(missing_ok=True)
        work_in_path.unlink(missing_ok=True)

        headers = {
            "X-PSNR-Y": f"{psnr_y:.3f}",
            "X-SSIM-Y": f"{ssim_y_val:.4f}",
            "X-Params-QIM": str(qim_val),
            "X-Params-Repetition": str(rep_val),
            "X-Params-ECC-Parity": str(ecc_par if use_ecc else 0),
            "X-Params-UseY": str(use_y).lower(),
            "X-Params-UseECC": str(use_ecc).lower(),
            "X-Profile": (profile or "custom"),
            "X-Preset": (preset_name or "custom"),
            "X-Pre-WhatsApp": str(pre_whatsapp).lower(),
            "X-Pre-Generic": str(bool(pre_generic)).lower(),
            "X-Pre-Long-Edge": str(long_edge or ""),
            "X-Pre-JPEG-Q": str(jpeg_q or ""),
            "X-Payload-Bits": str((32 + int(ecc_par if use_ecc else 0)) * 8),
        }

        filehash = hashlib.sha256(open(str(out_path), "rb").read()).hexdigest()

        params_dict = {
            "profile": profile or "custom",
            "preset": preset_name or "custom",
            "pre_generic": bool(pre_generic),
            "pre_long_edge": long_edge,
            "pre_jpeg_q": jpeg_q,
            "qim_step": float(qim_val),
            "repetition": int(rep_val),
            "use_ecc": bool(use_ecc),
            "ecc_parity_bytes": int(ecc_par if use_ecc else 0),
            "use_y_channel": bool(use_y),
            "psnr_y": float(psnr_y),
            "ssim_y": float(ssim_y_val),
        }

        crud.create_media_asset(
            db=db,
            user_id=None,
            original_filename=Path(file.filename or "upload").name,
            stored_path=str(out_path),
            sha256_hex=filehash,
            pgp_fingerprint=pgp_fpr,
            pgp_signature_armored=pgp_signature if (pgp_public_key and pgp_signature) else None,
            params=params_dict
        )

        # -------- Auto-register owner/media id (idempotent) --------
        if auto_register_media:
            owner_sha = None
            media_id = None

            m = _CLAIM_RE.fullmatch(text.strip())
            if m:
                owner_sha = m.group(1)
                media_id = m.group(2)
            else:
                # fall back to explicit overrides
                if override_owner_email_sha:
                    owner_sha = _hex64(override_owner_email_sha)
                if override_media_id:
                    media_id = _hex64(override_media_id)

            if owner_sha and media_id:
                register_media_id(
                    db,
                    owner_email_sha=owner_sha,
                    media_id=media_id,
                    user_uuid=user_uuid,
                    label=media_label,
                )
        # -----------------------------------------------------------

        return FileResponse(str(out_path), media_type="image/png", filename=out_path.name, headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Watermark failed: {e}")

@router.post("/image/extract", response_model=ExtractResponse)
async def extract_image(
    file: UploadFile = File(...),
    payload_bitlen: Optional[int] = Form(None),   # optional when use_ecc=True
    qim_step: float = Form(8.0),
    repetition: int = Form(20),
    check_text: Optional[str] = Form(None),
    use_y_channel: bool = Form(False),
    use_ecc: bool = Form(True),
    ecc_parity_bytes: int = Form(24),
):
    try:
        suffix = Path(file.filename).suffix or ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_in:
            tmp_in.write(await file.read())
            tmp_in_path = Path(tmp_in.name)

        if use_ecc and (payload_bitlen is None):
            payload_bitlen = (32 + ecc_parity_bytes) * 8
        elif payload_bitlen is None:
            payload_bitlen = 256

        cfg = DCTConfig(qim_step=qim_step, repetition=repetition)
        if use_y_channel:
            recovered_bits = extract_dct_image_ychannel(str(tmp_in_path), payload_bitlen, cfg)
        else:
            recovered_bits = extract_dct_image(str(tmp_in_path), payload_bitlen, cfg)

        tmp_in_path.unlink(missing_ok=True)

        used_repetition = repetition
        recovered_bytes = bits_to_bytes(recovered_bits)
        recovered_hex = hashlib.sha256(recovered_bytes).hexdigest()

        similarity = None
        match_text_hash = None
        ecc_ok = None

        if use_ecc:
            orig32, ok = ecc_decode_to_sha256(recovered_bytes, parity_bytes=ecc_parity_bytes)
            ecc_ok = bool(ok)

            if check_text:
                want32 = hashlib.sha256(check_text.encode("utf-8")).digest()
                match_text_hash = bool(want32 == orig32)

                expected_codeword = ecc_encode_sha256(want32, parity_bytes=ecc_parity_bytes)
                expected_bits = np.unpackbits(np.frombuffer(expected_codeword, dtype=np.uint8)).astype(np.uint8)
                L = min(len(recovered_bits), len(expected_bits))
                similarity = float(np.mean(recovered_bits[:L] == expected_bits[:L]))
        else:
            if check_text:
                target_bits = build_payload_from_text(check_text)
                L = min(len(recovered_bits), len(target_bits))
                similarity = float(np.mean(recovered_bits[:L] == target_bits[:L]))

        return ExtractResponse(
            payload_bitlen=payload_bitlen,
            similarity=similarity,
            recovered_hex=recovered_hex,
            ecc_ok=ecc_ok,
            match_text_hash=match_text_hash,
            used_repetition=used_repetition,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Extraction failed: {e}")
