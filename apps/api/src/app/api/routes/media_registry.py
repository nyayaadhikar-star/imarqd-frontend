# apps/api/src/app/api/routes/media_registry.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import MediaId, User

router = APIRouter(prefix="/media", tags=["media"])

# ---------------------------
# Pydantic request / responses
# ---------------------------

class MediaCreate(BaseModel):
    email: str
    email_sha: str  # 64-hex
    media_id: str   # 64-hex (with or without 0x is OK)
    user_uuid: Optional[str] = None
    label: Optional[str] = None

    @field_validator("email_sha")
    @classmethod
    def _email_sha64(cls, v: str) -> str:
        s = v.lower().removeprefix("0x")
        if len(s) != 64:
            raise ValueError("email_sha must be 32 bytes (64 hex chars)")
        int(s, 16)
        return s

    @field_validator("media_id")
    @classmethod
    def _media64(cls, v: str) -> str:
        s = v.lower().removeprefix("0x")
        if len(s) != 64:
            raise ValueError("media_id must be 32 bytes (64 hex chars)")
        int(s, 16)
        return s


class MediaRow(BaseModel):
    id: int
    owner_email_sha: str
    media_id: str
    user_uuid: Optional[str]
    label: Optional[str]
    created_at: datetime
    revoked_at: Optional[datetime]

# ---------------------------
# Helpers
# ---------------------------

def _get_or_create_user(
    db: Session,
    *,
    email: str,
    email_sha: str,
    app_uuid: Optional[str] = None,
    user_uuid: Optional[str] = None,
) -> User:
    """
    Backwards compatible: accepts either app_uuid or user_uuid.
    If neither is provided, generates one.
    """
    # Prefer an existing user by email
    user = db.query(User).filter(User.email == email).one_or_none()
    if user:
        # Update app_uuid if missing and caller supplied one
        incoming_uuid = app_uuid or user_uuid
        if incoming_uuid and not user.app_uuid:
            user.app_uuid = incoming_uuid
            db.flush()
        return user

    # Create new user
    new_uuid = app_uuid or user_uuid or str(uuid.uuid4())
    user = User(email=email, email_sha=email_sha, app_uuid=new_uuid)
    db.add(user)
    db.flush()
    return user


def _ensure_hex64(s: str, what: str) -> str:
    v = s.lower().removeprefix("0x")
    if len(v) != 64:
        raise HTTPException(400, f"{what} must be 32 bytes (64 hex chars)")
    try:
        int(v, 16)
    except Exception:
        raise HTTPException(400, f"{what} must be hex")
    return v


def _owner_sha_from_session_or_query(me: dict | None, owner_email_sha_q: str | None) -> str:
    if me and me.get("email_sha"):
        return me["email_sha"].lower()
    if owner_email_sha_q:
        return _ensure_hex64(owner_email_sha_q, "owner_email_sha")
    raise HTTPException(401, "Not authenticated and no owner_email_sha provided")

# ---------------------------
# Routes
# ---------------------------

@router.post("/", response_model=MediaRow)
def create_media(body: MediaCreate, db: Session = Depends(get_db)):
    """
    Upsert a (owner_email_sha, media_id).
    Also ensures a User row exists (email, email_sha, app_uuid).
    """
    user = _get_or_create_user(
        db,
        email=body.email,
        email_sha=body.email_sha,
        user_uuid=body.user_uuid,   # <— now accepted by helper
    )

    owner_sha = _ensure_hex64(body.email_sha, "email_sha")
    media_id = _ensure_hex64(body.media_id, "media_id")

    row = (
        db.query(MediaId)
        .filter(
            and_(
                MediaId.owner_email_sha == owner_sha,
                MediaId.media_id == media_id,
            )
        )
        .one_or_none()
    )

    if row:
        # Refresh metadata if provided
        changed = False
        if body.label and row.label != body.label:
            row.label = body.label
            changed = True
        if body.user_uuid and row.user_uuid != body.user_uuid:
            row.user_uuid = body.user_uuid
            changed = True
        if not row.active:
            row.active = True
            row.revoked_at = None
            changed = True
        if changed:
            db.flush()
    else:
        row = MediaId(
            owner_email_sha=owner_sha,
            media_id=media_id,
            user_uuid=body.user_uuid,
            label=body.label,
            active=True,
        )
        db.add(row)
        db.flush()

    db.commit()
    return MediaRow(
        id=row.id,
        owner_email_sha=row.owner_email_sha,
        media_id=row.media_id,
        user_uuid=row.user_uuid,
        label=row.label,
        created_at=row.created_at,
        revoked_at=row.revoked_at,
    )


@router.get("/mine")
def list_my_media_ids(
    owner_email_sha: str | None = Query(
        None, description="64-hex fallback when session is not wired"
    ),
    db: Session = Depends(get_db),
):
    me = None  # TODO: plug your auth if available
    owner_sha = _owner_sha_from_session_or_query(me, owner_email_sha)

    rows = (
        db.query(MediaId)
        .filter(MediaId.owner_email_sha == owner_sha, MediaId.active == True)
        .order_by(MediaId.id.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "media_id": r.media_id,
            "label": r.label,
            "user_uuid": r.user_uuid,
            "created_at": r.created_at,
            "revoked_at": r.revoked_at,
        }
        for r in rows
    ]


@router.post("/auto-save")
def auto_save_media_id(
    email: str,
    email_sha: str,
    media_id: str,
    label: str | None = None,
    user_uuid: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Lightweight endpoint you can call right after watermarking
    to ensure the media_id is registered. Returns {ok: true}.
    """
    body = MediaCreate(
        email=email,
        email_sha=email_sha,
        media_id=media_id,
        user_uuid=user_uuid,
        label=label,
    )
    _ = create_media(body, db)  # reuse insert/upsert logic
    return {"ok": True}
