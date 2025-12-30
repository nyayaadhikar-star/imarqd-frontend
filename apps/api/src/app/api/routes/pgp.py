from fastapi import APIRouter, HTTPException, Form, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.db import crud
from ...services.crypto.pgp_utils import key_fingerprint  # NOTE: you said "services", not "modules"

router = APIRouter(prefix="/pgp", tags=["pgp"])

class PGPRegisterResp(BaseModel):
    fingerprint: str
    user_id: int

@router.post("/register", response_model=PGPRegisterResp)
def register_pgp(
    public_key_armored: str = Form(...),
    email: str | None = Form(None),
    display_name: str | None = Form(None),
    db: Session = Depends(get_db)
):
    try:
        fpr = key_fingerprint(public_key_armored)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid public key: {e}")

    user = crud.get_or_create_user(db, email=email, display_name=display_name)
    crud.create_pgp_key(db, user_id=user.id, fingerprint=fpr, public_key_armored=public_key_armored)
    return PGPRegisterResp(fingerprint=fpr, user_id=user.id)
