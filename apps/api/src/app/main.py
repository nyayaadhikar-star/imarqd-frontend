import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from app.services.db.bootstrap import create_all 

from app.core.config import settings

# existing routers you already had
from app.api.routes.root import router as root_router
from app.api.routes.upload import router as upload_router

# 👉 use the new watermarking router we created (watermarking.py)
from app.api.routes.watermarking import router as watermarking_router

from app.api.routes import watermarking

from app.db.session import engine, Base
from app.db import models
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Klyvo API", version="0.1.0")

# CORS for local dev (web at 5173, expo web at 19006, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:19006",
        "http://127.0.0.1:19006",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# mount routers under your configured API prefix
app.include_router(root_router, prefix=settings.api_prefix)
app.include_router(upload_router, prefix=settings.api_prefix)
app.include_router(watermarking_router, prefix=settings.api_prefix)

app.include_router(watermarking.router, prefix="/api")



# health endpoints
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "env": settings.environment}

# Static file serving for uploaded / generated images
os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/files", StaticFiles(directory=settings.upload_dir), name="files")


from app.db.session import engine, Base
Base.metadata.create_all(bind=engine)


from app.api.routes.pgp import router as pgp_router
app.include_router(pgp_router, prefix=settings.api_prefix)


from app.api.routes.pgp_debug import router as pgp_debug_router

# After other includes:
app.include_router(pgp_debug_router, prefix=settings.api_prefix)



from app.api.routes import keys as keys_router
app.include_router(keys_router.router, prefix=settings.api_prefix)


# apps/api/src/app/main.py
from app.api.routes import auth as auth_router
# ...
app.include_router(auth_router.router, prefix=settings.api_prefix)  # settings.api_prefix should be "/api"


from app.api.routes import keys as keys_router
app.include_router(keys_router.router, prefix=settings.api_prefix)


# ... existing imports ...
from app.api.routes.auth import router as auth_router  # ✅ add this

# ... existing FastAPI + CORS setup ...

from app.api.routes.auth import router as auth_router  # ✅ add this

# ...

from app.api.routes.video import router as video_router

app.include_router(root_router, prefix=settings.api_prefix)
app.include_router(upload_router, prefix=settings.api_prefix)
app.include_router(watermarking.router, prefix=settings.api_prefix)  # whatever you named it earlier
app.include_router(auth_router, prefix=settings.api_prefix)          # ✅ add this
app.include_router(video_router, prefix="/api")


app.include_router(video_router, prefix=settings.api_prefix)

from app.api.routes.registry import router as registry_router
app.include_router(registry_router, prefix="/api")


from app.api.routes.registry_v2 import router as registry_router_v2
app.include_router(registry_router_v2, prefix="/api")



try:
    create_all()
except Exception:
    pass




from app.api.routes.media_registry import router as media_router
from app.api.routes.verify_auto import router as verify_auto_router
from app.api.routes.media_ids import router as media_ids_router


app.include_router(media_router)
app.include_router(verify_auto_router, prefix="/api")

app.include_router(media_ids_router, prefix="/api")

# from app.api.routes.verify_auto import verify_auto
# app.include_router(verify_auto.router, prefix="/api")


# wherever you include routers
from app.api.routes.owner_sha import router as owner_router

app.include_router(owner_router, prefix="/api")  # matches your existing /api/* routes




app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:19006",
        "http://127.0.0.1:19006",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[  # ← add this
        "X-PSNR-Y",
        "X-SSIM-Y",
        "X-Params-QIM",
        "X-Params-Repetition",
        "X-Params-ECC-Parity",
        "X-Payload-Bits",
        "X-Preset",
        "X-Pre-Long-Edge",
        "X-Pre-JPEG-Q",
        "X-Pre-Generic",
        "X-Profile",
    ],
)




