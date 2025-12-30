# src/app/api/routes/owner_sha.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr
from typing import List

import hashlib

router = APIRouter(prefix="/owner", tags=["owner"])


# ---------- helpers ----------
def _normalize_email(e: str) -> str:
    # canonicalize: trim, collapse unicode case to lower
    return (e or "").strip().lower()


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------- schemas ----------
class EmailIn(BaseModel):
    email: EmailStr


class EmailOut(BaseModel):
    owner_email: str
    owner_email_sha: str
    owner_email_sha_0x: str  # convenience for clients that like 0x-prefixed


class EmailBatchIn(BaseModel):
    emails: List[EmailStr]


class EmailBatchOut(BaseModel):
    items: List[EmailOut]


# ---------- routes ----------
@router.post("/sha", response_model=EmailOut)
def post_sha(body: EmailIn):
    norm = _normalize_email(body.email)
    if not norm:
        raise HTTPException(status_code=400, detail="Empty email")
    h = _sha256_hex(norm)
    return EmailOut(owner_email=norm, owner_email_sha=h, owner_email_sha_0x=f"0x{h}")


# convenience GET for quick tests (same response shape)
@router.get("/sha", response_model=EmailOut)
def get_sha(email: EmailStr = Query(..., description="Email to hash")):
    norm = _normalize_email(str(email))
    h = _sha256_hex(norm)
    return EmailOut(owner_email=norm, owner_email_sha=h, owner_email_sha_0x=f"0x{h}")


@router.post("/sha/batch", response_model=EmailBatchOut)
def post_sha_batch(body: EmailBatchIn):
    items = []
    for e in body.emails:
        norm = _normalize_email(str(e))
        h = _sha256_hex(norm)
        items.append(EmailOut(owner_email=norm, owner_email_sha=h, owner_email_sha_0x=f"0x{h}"))
    return EmailBatchOut(items=items)
