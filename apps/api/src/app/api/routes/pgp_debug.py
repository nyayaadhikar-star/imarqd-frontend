from fastapi import APIRouter, Form, HTTPException
from pydantic import BaseModel

# You said your tree uses "services", not "modules"
from ...services.crypto.pgp_utils import key_fingerprint, verify_detached_signature

router = APIRouter(prefix="/pgp_debug", tags=["pgp"])

class VerifyResp(BaseModel):
    ok: bool
    fingerprint: str | None = None
    detail: str | None = None

@router.post("/verify", response_model=VerifyResp)
def verify_pgp_signature(
    text: str = Form(..., description="The exact message that was signed"),
    pgp_public_key: str = Form(..., description="ASCII-armored PGP public key"),
    pgp_signature: str = Form(..., description="ASCII-armored detached signature"),
):
    """
    Verifies a detached PGP signature over `text`.
    Returns ok=true and the key fingerprint if verification succeeds.
    """
    try:
        ok = verify_detached_signature(pgp_public_key, text.encode("utf-8"), pgp_signature)
        if not ok:
            return VerifyResp(ok=False, fingerprint=None, detail="Signature verification failed")
        fpr = key_fingerprint(pgp_public_key)
        return VerifyResp(ok=True, fingerprint=fpr)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PGP error: {e}")
