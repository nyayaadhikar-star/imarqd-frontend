from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
import tempfile

from sqlalchemy.orm import Session
from ...db.session import get_db
from ...services.db import crud

# Reuse the same watermarking/extraction helpers & presets
from .watermarking import PRESETS   # constant only, avoids duplicate params
from ...services.watermarking.schemas import DCTConfig
from ...services.watermarking.image_extract import (
    extract_dct_image,
    extract_dct_image_ychannel,
)
from ...services.watermarking.helpers import bits_to_bytes
from ...services.watermarking.ecc import ecc_encode_sha256, ecc_decode_to_sha256

router = APIRouter(prefix="/verify", tags=["verify"])

class AutoVerifyResult(BaseModel):
    exists: bool
    ecc_ok: Optional[bool] = None
    match_text_hash: Optional[bool] = None
    similarity: Optional[float] = None
    used_repetition: Optional[int] = None
    payload_bits: int
    owner_email_sha: str
    matched_media_id: Optional[str] = None
    checked_media_ids: int
    preset: Optional[str] = None


def _hex64_from_any(v) -> str:
    """Return 64-lower-hex for a media_id value stored as bytes/hex/0xhex."""
    if isinstance(v, (bytes, bytearray)):
        h = v.hex()
    else:
        h = str(v).strip().lower()
        if h.startswith("0x"):
            h = h[2:]
    # basic sanity
    if len(h) != 64:
        # will raise on bad input instead of silently failing
        _ = bytes.fromhex(h)  # validates hex
        raise HTTPException(400, "media_id must be 32 bytes (64 hex)")
    # hex() earlier guarantees valid; but do one more parse to be safe:
    bytes.fromhex(h)
    return h



def _resolve_params(
    preset: Optional[str],
    use_ecc: bool,
    ecc_parity_bytes: Optional[int],
    repetition: Optional[int],
    use_y_channel: Optional[bool],
):
    # Mirror defaults used in /watermark/image + /watermark/image/extract
    qim_step = 24.0
    rep_default = 160
    ecc_default = 64
    usey_default = True

    preset_name = (preset or "").strip().lower()
    if preset_name:
        if preset_name not in PRESETS:
            raise HTTPException(400, f"Unknown preset '{preset_name}'")
        cfg = PRESETS[preset_name]
        qim_step = float(cfg.get("qim_step", qim_step))
        rep_default = int(cfg.get("repetition", rep_default))
        ecc_default = int(cfg.get("ecc_parity_bytes", ecc_default))
        usey_default = bool(cfg.get("use_y_channel", usey_default))

    rep = int(repetition if repetition is not None else rep_default)
    parity = int(ecc_parity_bytes if (use_ecc and ecc_parity_bytes is not None) else (ecc_default if use_ecc else 0))
    use_y = bool(use_y_channel if use_y_channel is not None else usey_default)

    if qim_step <= 0:
        raise HTTPException(400, "qim_step must be > 0")
    if rep <= 0:
        raise HTTPException(400, "repetition must be > 0")
    if use_ecc and parity <= 0:
        raise HTTPException(400, "ecc_parity_bytes must be > 0 when use_ecc=true")

    payload_bits = (32 + parity) * 8 if use_ecc else 256
    return preset_name or None, qim_step, rep, parity, use_y, payload_bits

def _try_one_candidate(
    work_path: str,
    check_text: str,
    payload_bits: int,
    qim_step: float,
    repetition: int,
    use_y: bool,
    use_ecc: bool,
    ecc_parity_bytes: int,
):
    cfg = DCTConfig(qim_step=qim_step, repetition=repetition)
    if use_y:
        rec_bits = extract_dct_image_ychannel(work_path, payload_bits, cfg)
    else:
        rec_bits = extract_dct_image(work_path, payload_bits, cfg)

    # ECC-aware verification, identical to /watermark/image/extract
    recovered_bytes = bits_to_bytes(rec_bits)
    ecc_ok = None
    match_text_hash = None
    similarity = None

    if use_ecc:
        want32 = __import__("hashlib").sha256(check_text.encode("utf-8")).digest()
        expected_codeword = ecc_encode_sha256(want32, parity_bytes=ecc_parity_bytes)
        import numpy as np
        expected_bits = np.unpackbits(
            np.frombuffer(expected_codeword, dtype=np.uint8)
        ).astype(np.uint8)
        L = min(len(rec_bits), len(expected_bits))
        similarity = float((rec_bits[:L] == expected_bits[:L]).mean())

        orig32, ok = ecc_decode_to_sha256(recovered_bytes, parity_bytes=ecc_parity_bytes)
        ecc_ok = bool(ok)
        match_text_hash = bool(ok and (orig32 == want32))
        return match_text_hash, similarity, ecc_ok
    else:
        # non-ECC path
        want_bits = __import__("numpy").unpackbits(
            __import__("numpy").frombuffer(check_text.encode("utf-8"), dtype=__import__("numpy").uint8)
        ).astype(__import__("numpy").uint8)
        L = min(len(rec_bits), len(want_bits))
        similarity = float((rec_bits[:L] == want_bits[:L]).mean())
        match_text_hash = None
        ecc_ok = None
        return (similarity > 0.95), similarity, ecc_ok

@router.post("/auto", response_model=AutoVerifyResult)
async def verify_auto(
    file: UploadFile = File(...),
    owner_email_sha: str = Form(...),

    # Optional knobs (aligned with your extract endpoint)
    preset: Optional[str] = Form(None),
    use_ecc: bool = Form(True),
    ecc_parity_bytes: Optional[int] = Form(None),
    repetition: Optional[int] = Form(None),
    use_y_channel: Optional[bool] = Form(None),

    db: Session = Depends(get_db),
):
    # 1) Canonicalize params the same way as the existing routes
    preset_name, qim_step, rep, parity, use_y, payload_bits = _resolve_params(
        preset, use_ecc, ecc_parity_bytes, repetition, use_y_channel
    )

    # 2) Persist the uploaded file to a temp path (same pattern as your routes)
    suffix = Path(file.filename).suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        vpath = tmp.name

    # 3) Get all media_ids for this owner
    media_ids: List[str] = crud.list_media_ids_by_owner_sha(db, owner_email_sha)
    if not media_ids:
        # No registrations for this owner
        return AutoVerifyResult(
            exists=False,
            ecc_ok=False if use_ecc else None,
            match_text_hash=False,
            similarity=None,
            used_repetition=rep,
            payload_bits=payload_bits,
            owner_email_sha=owner_email_sha,
            matched_media_id=None,
            checked_media_ids=0,
            preset=preset_name,
        )

    for mid in media_ids:
        hex_id = _hex64_from_any(mid)
        candidates = (
            f"owner:{owner_email_sha}|media:{hex_id}",      # no 0x
            f"owner:{owner_email_sha}|media:0x{hex_id}",    # with 0x
        )
        for check_text in candidates:
            hit, sim, ecc_ok = _try_one_candidate(
                vpath, check_text, payload_bits, qim_step=qim_step,
                repetition=rep, use_y=use_y, use_ecc=use_ecc, ecc_parity_bytes=parity
            )
            if hit:
                return AutoVerifyResult(
                    exists=True,
                    ecc_ok=ecc_ok,
                    match_text_hash=True if use_ecc else None,
                    similarity=sim,
                    used_repetition=rep,
                    payload_bits=payload_bits,
                    owner_email_sha=owner_email_sha,
                    matched_media_id=f"0x{hex_id}",  # surface a friendly form
                    checked_media_ids=len(media_ids),
                    preset=preset_name,
                )

    # 5) No match
    return AutoVerifyResult(
        exists=False,
        ecc_ok=False if use_ecc else None,
        match_text_hash=False,
        similarity=None,
        used_repetition=rep,
        payload_bits=payload_bits,
        owner_email_sha=owner_email_sha,
        matched_media_id=None,
        checked_media_ids=len(media_ids),
        preset=preset_name,
    )
