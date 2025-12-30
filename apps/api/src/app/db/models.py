# apps/api/src/app/db/models.py
from __future__ import annotations
from datetime import datetime
import uuid

from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, Text, Boolean, JSON, func,
    UniqueConstraint, Index
)

from sqlalchemy.orm import relationship, Mapped, mapped_column, foreign  # add 'foreign'

from app.db.session import Base


# ------------------------
# User (single, canonical)
# ------------------------


# --- User ---
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    app_uuid: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    email_sha: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    pgp_keys: Mapped[list["PGPKey"]] = relationship("PGPKey", back_populates="user", cascade="all, delete-orphan")
    assets: Mapped[list["MediaAsset"]] = relationship("MediaAsset", back_populates="user", cascade="all, delete-orphan")

    # View-only join via email_sha -> owner_email_sha (no FK in DB)
    media_ids = relationship(
        "MediaId",
        primaryjoin=lambda: User.email_sha == foreign(MediaId.owner_email_sha),
        viewonly=True,
        lazy="selectin",
    )



# ---------------
# PGP key records
# ---------------
class PGPKey(Base):
    __tablename__ = "pgp_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # FK must match users.id type -> String
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    fingerprint: Mapped[str] = mapped_column(String(80), index=True)  # hex string
    public_key_armored: Mapped[str] = mapped_column(Text)             # ASCII-armored public key
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="pgp_keys")


# ----------------
# Watermarked media
# ----------------
class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # FK must match users.id type -> String
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    original_filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(1024))  # dev: local path
    sha256_hex: Mapped[str] = mapped_column(String(64), index=True)

    # PGP-related (optional, kept)
    pgp_fingerprint: Mapped[str | None] = mapped_column(String(80), nullable=True)
    pgp_signature_armored: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Watermark/ECC params
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="assets")


# ------------------------
# Media IDs (owner + media)
# ------------------------
class MediaId(Base):
    __tablename__ = "media_ids"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_email_sha = Column(String(64), nullable=False)   # lowercased 64-hex
    media_id = Column(String(64), nullable=False)          # lowercased 64-hex
    user_uuid = Column(String(64), nullable=True)
    label = Column(String(120), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("owner_email_sha", "media_id", name="uq_owner_media"),
        Index("ix_media_ids_owner", "owner_email_sha"),
        Index("ix_media_ids_media", "media_id"),
        Index("ix_media_ids_user", "user_uuid"),
    )

