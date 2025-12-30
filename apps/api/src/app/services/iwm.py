from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from pgpy import PGPKey, PGPMessage


@dataclass(frozen=True)
class WatermarkPayload:
    uuidv7: str
    iso8601_ts: str
    pgp_fpr: str

    @staticmethod
    def new(uuidv7: str, pgp_fpr: str, at: Optional[datetime] = None) -> "WatermarkPayload":
        ts = (at or datetime.now(timezone.utc)).isoformat()
        return WatermarkPayload(uuidv7=uuidv7, iso8601_ts=ts, pgp_fpr=pgp_fpr)

    def to_bytes(self) -> bytes:
        # Deterministic concatenation
        # uuid|ts|fingerprint
        joined = f"{self.uuidv7}|{self.iso8601_ts}|{self.pgp_fpr}".encode("utf-8")
        return joined


def sha256_digest(payload: WatermarkPayload) -> bytes:
    return hashlib.sha256(payload.to_bytes()).digest()


def sha256_hex(payload: WatermarkPayload) -> str:
    return hashlib.sha256(payload.to_bytes()).hexdigest()


def encrypt_with_pgp_public(hex_digest: str, public_key_armored: str) -> str:
    """
    Encrypt the digest with the owner's PGP public key. Returns ASCII-armored string.
    """
    key, _ = PGPKey.from_blob(public_key_armored)
    msg = PGPMessage.new(hex_digest)
    enc = key.encrypt(msg)
    return str(enc)


def build_watermark(payload: WatermarkPayload, public_key_armored: Optional[str] = None) -> dict:
    digest_bytes = sha256_digest(payload)
    digest_hex = digest_bytes.hex()
    out: dict = {
        "digest_hex": digest_hex,
        "digest_b64": base64.b64encode(digest_bytes).decode("ascii"),
        "uuidv7": payload.uuidv7,
        "iso8601_ts": payload.iso8601_ts,
        "pgp_fpr": payload.pgp_fpr,
    }
    if public_key_armored:
        out["pgp_encrypted"] = encrypt_with_pgp_public(digest_hex, public_key_armored)
    return out


