from sqlalchemy.orm import Session
from app.db import models

def get_or_create_user(db: Session, email: str | None, display_name: str | None = None) -> models.User:
    if email:
        obj = db.query(models.User).filter(models.User.email == email).one_or_none()
        if obj:
            return obj
    obj = models.User(email=email, display_name=display_name)
    db.add(obj)
    db.flush()
    return obj

def create_pgp_key(db: Session, user_id: int, fingerprint: str, public_key_armored: str) -> models.PGPKey:
    obj = models.PGPKey(user_id=user_id, fingerprint=fingerprint, public_key_armored=public_key_armored, is_active=True)
    db.add(obj)
    db.flush()
    return obj

def get_active_pgp_by_fpr(db: Session, fingerprint: str) -> models.PGPKey | None:
    return db.query(models.PGPKey).filter(models.PGPKey.fingerprint == fingerprint, models.PGPKey.is_active.is_(True)).one_or_none()

def create_media_asset(
    db: Session,
    user_id: int | None,
    original_filename: str,
    stored_path: str,
    sha256_hex: str,
    pgp_fingerprint: str | None,
    pgp_signature_armored: str | None,
    params: dict | None
) -> models.MediaAsset:
    obj = models.MediaAsset(
        user_id=user_id,
        original_filename=original_filename,
        stored_path=stored_path,
        sha256_hex=sha256_hex,
        pgp_fingerprint=pgp_fingerprint,
        pgp_signature_armored=pgp_signature_armored,
        params=params
    )
    db.add(obj)
    db.flush()
    return obj




from datetime import datetime

def upsert_user_by_app_uuid(db, app_uuid: str, email: str, email_sha: str):
    user = db.query(models.User).filter(models.User.app_uuid == app_uuid).first()
    if user:
        user.email = email
        user.email_sha = email_sha
        user.updated_at = datetime.utcnow()   # <-- ensure it changes on update
    else:
        user = models.User(
            app_uuid=app_uuid,
            email=email,
            email_sha=email_sha,
            # created_at will default, updated_at will default
        )
        db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_app_uuid(db: Session, app_uuid: str) -> models.User | None:
    return db.query(models.User).filter(models.User.app_uuid == app_uuid).first()





from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db.models import MediaId

def register_media_id(
    db: Session,
    *,
    owner_email_sha: str,
    media_id: str,
    user_uuid: str | None = None,
    label: str | None = None,
) -> MediaId:
    """
    Upsert-like: insert if not existing (owner+media unique), otherwise return current row.
    """
    row = (
        db.query(MediaId)
        .filter(
            MediaId.owner_email_sha == owner_email_sha,
            MediaId.media_id == media_id,
        )
        .one_or_none()
    )
    if row:
        # update optional fields if provided
        changed = False
        if user_uuid and row.user_uuid != user_uuid:
            row.user_uuid = user_uuid
            changed = True
        if label and row.label != label:
            row.label = label
            changed = True
        if changed:
            db.commit()
            db.refresh(row)
        return row

    row = MediaId(
        owner_email_sha=owner_email_sha.lower(),
        media_id=media_id.lower(),
        user_uuid=user_uuid,
        label=label,
        active=True,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # someone raced us; return the existing one
        row = (
            db.query(MediaId)
            .filter(
                MediaId.owner_email_sha == owner_email_sha,
                MediaId.media_id == media_id,
            )
            .one()
        )
        return row

    db.refresh(row)
    return row



# in services/db/crud.py
def list_media_ids_by_owner_sha(db, owner_email_sha: str) -> list[str]:
    return [row.media_id for row in db.query(MediaId).filter_by(owner_email_sha=owner_email_sha.strip().lower()).all()]

