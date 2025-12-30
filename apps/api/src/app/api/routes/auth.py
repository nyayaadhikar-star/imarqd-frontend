# apps/api/src/app/api/routes/auth.py
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from uuid import uuid5, NAMESPACE_URL
import secrets, hashlib
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...services.db import crud

router = APIRouter(prefix="/auth", tags=["auth"])

# ------- helpers -------
def normalize_email(e: str) -> str:
    return e.strip().lower()

def email_sha256(email_norm: str) -> str:
    return hashlib.sha256(email_norm.encode("utf-8")).hexdigest()

# In-memory token store for MVP (replace with JWT later)
_TOKENS: dict[str, str] = {}   # token -> app_uuid

# ------- models -------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str | None = None  # not used yet

class LoginResponse(BaseModel):
    token: str
    uuid: str
    email: EmailStr
    email_sha: str

class MeResponse(BaseModel):
    uuid: str
    email: str
    email_sha: str

# ------- routes -------
@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    email_norm = normalize_email(body.email)
    user_uuid = str(uuid5(NAMESPACE_URL, f"klyvo:{email_norm}"))
    token = secrets.token_urlsafe(24)
    email_sha = email_sha256(email_norm)

    # Upsert user
    crud.upsert_user_by_app_uuid(
        db,
        app_uuid=user_uuid,
        email=email_norm,
        email_sha=email_sha,
    )

    # Save token -> uuid
    _TOKENS[token] = user_uuid

    return LoginResponse(
        token=token,
        uuid=user_uuid,
        email=email_norm,
        email_sha=email_sha,
    )

@router.get("/me", response_model=MeResponse)
def me(authorization: str | None = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    app_uuid = _TOKENS.get(token)
    if not app_uuid:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = crud.get_user_by_app_uuid(db, app_uuid=app_uuid)
    if not user:
        raise HTTPException(status_code=404, detail="Not Found")

    return MeResponse(uuid=user.app_uuid, email=user.email, email_sha=user.email_sha)
