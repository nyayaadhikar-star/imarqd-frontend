from __future__ import annotations
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
import hashlib

from ...db.session import get_db
from ...db.models import MediaId, User

router = APIRouter(prefix="/media", tags=["media"])

def _sha256_hex_lower(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

class MediaIdOut(BaseModel):
    media_id: str
    label: Optional[str] = None
    active: bool
    created_at: str

class MediaIdsResponse(BaseModel):
    owner_email: Optional[str] = None
    owner_email_sha: str
    user_uuid: Optional[str] = None
    items: List[MediaIdOut]

@router.get("/ids/me", response_model=MediaIdsResponse)
def list_my_media_ids(
    db: Session = Depends(get_db),
    # Accept any one of these:
    email: Optional[str] = Query(None, description="Plain email (will be sha256'ed)"),
    owner_sha: Optional[str] = Query(None, description="owner_email sha256 (64-hex)"),
    x_user_email: Optional[str] = Header(None, convert_underscores=False),
    x_owner_sha: Optional[str] = Header(None, convert_underscores=False),
):
    """
    Return all media_ids belonging to the logged-in user.
    Identity can be provided via:
      - ?email=you@example.com   (we sha256 it)
      - ?owner_sha=<64hex>
      - X-User-Email: you@example.com
      - X-Owner-Sha:  <64hex>
    """
    # Resolve identity
    owner_email = None
    owner_sha_hex = None

    if x_owner_sha:
        owner_sha_hex = x_owner_sha.strip().lower().removeprefix("0x")
    elif owner_sha:
        owner_sha_hex = owner_sha.strip().lower().removeprefix("0x")

    if not owner_sha_hex:
        # try email header / query
        owner_email = (x_user_email or email or "").strip()
        if not owner_email:
            raise HTTPException(status_code=400, detail="Provide ?email=, ?owner_sha=, X-User-Email or X-Owner-Sha")
        owner_sha_hex = _sha256_hex_lower(owner_email)

    if len(owner_sha_hex) != 64:
        raise HTTPException(status_code=400, detail="owner_sha must be 64 hex chars")

    # Try to map to a user (optional; response still works if user row not present)
    user = db.query(User).filter(User.email_sha == owner_sha_hex).one_or_none()

    rows = (
        db.query(MediaId)
        .filter(MediaId.owner_email_sha == owner_sha_hex)
        .order_by(MediaId.created_at.desc())
        .all()
    )

    items = [
        MediaIdOut(
            media_id=r.media_id,
            label=r.label,
            active=bool(r.active),
            created_at=r.created_at.isoformat()
        )
        for r in rows
    ]

    return MediaIdsResponse(
        owner_email=user.email if (user and user.email) else owner_email,
        owner_email_sha=owner_sha_hex,
        user_uuid=user.app_uuid if user else None,
        items=items,
    )
