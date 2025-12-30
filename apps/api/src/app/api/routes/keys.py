from fastapi import APIRouter, Form, HTTPException, Depends
from pathlib import Path

from ...db.session import get_db
from ...services.db import crud
from ...db import models
from ...services.crypto.pgp_utils import key_fingerprint

router = APIRouter(prefix="/keys", tags=["keys"])

KEYS_DIR = Path(__file__).resolve().parents[4] / "keys"
KEYS_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload")
def upload_public_key(
    uuid: str = Form(...),                # app_uuid from login
    public_key_armored: str = Form(...),  # ASCII-armored pubkey
    db = Depends(get_db),
):
    # Find the user by app_uuid
    user = crud.get_user_by_app_uuid(db, uuid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Compute fingerprint
    try:
            fpr = key_fingerprint(public_key_armored)   # this is where pgpy would explode on SHA-3 keys
    except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid public key: {e}. Please regenerate keys (RSA-4096, SHA-256 prefs) and try again."
            )

    # Save file alongside (for dev/demo)
    path = KEYS_DIR / f"{uuid}.asc"
    path.write_text(public_key_armored, encoding="utf-8")

    # Upsert a PGPKey row (simple “insert new active”)
    key = models.PGPKey(
        user_id=user.id,
        fingerprint=fpr,
        public_key_armored=public_key_armored,
        is_active=True,
    )
    db.add(key)
    db.commit()
    db.refresh(key)

    return {"ok": True, "fingerprint": fpr, "path": str(path)}
