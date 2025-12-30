from __future__ import annotations

import binascii
from dataclasses import dataclass
from typing import Optional

from web3 import Web3

from .client import Web3Client, load_chain_config

HEX_0X = ("0x", "0X")

def _normalize_hex32(s: str, *, name: str) -> bytes:
    """Accepts hex with or without 0x, validates 32 bytes, returns bytes32."""
    val = s.strip()
    if val.startswith(HEX_0X):
        val = val[2:]
    try:
        raw = binascii.unhexlify(val)
    except binascii.Error as e:
        raise ValueError(f"{name} must be hex: {e}") from e
    if len(raw) != 32:
        raise ValueError(f"{name} must be 32 bytes (64 hex chars); got {len(raw)} bytes")
    return raw

@dataclass
class AnchorResult:
    tx_hash: str
    block_number: int
    ipfs_cid: Optional[str]
    status: str

class ProofRegistryService:
    def __init__(self, client: Optional[Web3Client] = None) -> None:
        self.client = client or Web3Client()
        self.cfg = load_chain_config()

    def health(self) -> dict:
        return {
            "connected": self.client.w3.is_connected(),
            "chain_id": self.client.get_chain_id(),
            "contract": self.cfg.contract_address,
            "has_signer": self.client.get_signer_address() is not None,
            "signer": self.client.get_signer_address(),
        }

    def anchor(self, *, file_sha256_hex: str, email_sha_hex: str, ipfs_cid: str = "") -> AnchorResult:
        file_b32 = _normalize_hex32(file_sha256_hex, name="file_sha256")
        email_b32 = _normalize_hex32(email_sha_hex, name="email_sha")
        tx_info = self.client.tx_register_proof(file_b32, email_b32, ipfs_cid or "")
        return AnchorResult(
            tx_hash=tx_info["tx_hash"],
            block_number=tx_info["block_number"],
            ipfs_cid=ipfs_cid or "",
            status="anchored" if tx_info.get("status", 0) == 1 else "failed",
        )

    def verify(self, *, file_sha256_hex: str) -> dict:
        file_b32 = _normalize_hex32(file_sha256_hex, name="file_sha256")
        exists, owner_email_sha, ts, cid = self.client.call_get_proof(file_b32)
        return {
            "exists": bool(exists),
            "owner_email_sha": Web3.to_hex(owner_email_sha) if isinstance(owner_email_sha, (bytes, bytearray)) else str(owner_email_sha),
            "timestamp": int(ts),
            "ipfs_cid": cid,
        }
