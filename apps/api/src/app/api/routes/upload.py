import os
import io
import uuid
from typing import Annotated

from fastapi import APIRouter, File, UploadFile, HTTPException, Request
from PIL import Image

from app.core.config import settings
from app.services.watermark import apply_text_watermark


router = APIRouter(prefix="", tags=["upload"])


@router.post("/upload")
async def upload_image(request: Request, file: Annotated[UploadFile, File(...)]):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are allowed")

    # Read bytes
    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file")

    # Resize (keep aspect ratio), max width/height 1024
    max_dim = 1024
    img.thumbnail((max_dim, max_dim))

    # Optional watermark (defaults for now; can be extended with query params)
    img = apply_text_watermark(
        img,
        text="Klyvo",
        position="bottom-right",
        opacity=0.35,
        scale=0.12,
        margin=12,
        color="#ffffff",
    )

    # Ensure upload directory exists
    os.makedirs(settings.upload_dir, exist_ok=True)

    # Decide output extension by content-type or original filename
    allowed_exts = {"jpg", "jpeg", "png", "webp"}
    inferred_from_ct = (file.content_type.split("/")[-1] if file.content_type else "").lower()
    inferred_from_name = (file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "").lower()
    ext = inferred_from_ct or inferred_from_name or "jpg"
    if ext == "jpeg":
        ext = "jpg"
    if ext not in allowed_exts:
        ext = "jpg"

    # Ensure mode compatible with chosen format
    if ext == "jpg" and img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")

    filename = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(settings.upload_dir, filename)

    # Save optimized
    save_kwargs = {"optimize": True}
    if ext in ("jpg", "jpeg"):
        save_kwargs["quality"] = 82
    try:
        img.save(path, **save_kwargs)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save image: {exc}")

    # Build absolute URL
    base = str(request.base_url).rstrip("/")
    url = f"{base}/files/{filename}"
    return {"filename": filename, "url": url}


