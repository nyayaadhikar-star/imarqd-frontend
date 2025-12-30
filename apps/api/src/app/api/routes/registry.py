from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...services.blockchain.registry import ProofRegistryService

router = APIRouter(prefix="/registry", tags=["registry"])
svc = ProofRegistryService()

class AnchorPayload(BaseModel):
    email_sha: str = Field(..., description="32-byte hex (keccak256 of lowercase email recommended)")
    file_sha256: str = Field(..., description="32-byte hex SHA-256 of the media file")
    kind: str = Field(..., description="image|video|audio|other", examples=["image"])
    filename: str = Field(..., description="Original filename", examples=["watermarked.png"])
    ipfs_cid: str | None = Field(None, description="Optional metadata CID")

@router.get("/health")
def health():
    return svc.health()

@router.post("/anchor")
def anchor(payload: AnchorPayload):
    try:
        res = svc.anchor(
            file_sha256_hex=payload.file_sha256,
            email_sha_hex=payload.email_sha,
            ipfs_cid=payload.ipfs_cid or "",
        )
        return {
            "tx_hash": res.tx_hash,
            "block_number": res.block_number,
            "ipfs_cid": res.ipfs_cid,
            "status": res.status,
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"anchor failed: {e}") from e

@router.get("/verify")
def verify(file_sha256: str = Query(..., description="32-byte hex SHA-256 of the media file")):
    try:
        return svc.verify(file_sha256_hex=file_sha256)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"verify failed: {e}") from e
