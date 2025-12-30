# apps/api/src/app/api/routes/registry_v2.py

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, field_validator
from hexbytes import HexBytes
from pathlib import Path
from web3 import Web3, HTTPProvider
import json, os
from app.core.config import settings

router = APIRouter(prefix="/registry/v2", tags=["registry-v2"])

# -------------------------------------------------------------------
# helpers to read env / settings robustly

def _get_env(name_upper: str, name_lower: str = None, default=None):
    if hasattr(settings, name_upper):
        v = getattr(settings, name_upper)
        if v not in (None, ""):
            return v
    if name_lower and hasattr(settings, name_lower):
        v = getattr(settings, name_lower)
        if v not in (None, ""):
            return v
    v = os.getenv(name_upper)
    if v not in (None, ""):
        return v
    if name_lower:
        v = os.getenv(name_lower)
        if v not in (None, ""):
            return v
    return default

_W3 = None
_CONTRACT = None

def _ensure_contract():
    """Lazy-init Web3 + contract with clear error messages."""
    global _W3, _CONTRACT
    if _W3 is not None and _CONTRACT is not None:
        return _W3, _CONTRACT

    rpc = _get_env("WEB3_RPC_URL", "web3_rpc_url")
    address = _get_env("PROOF_V2_CONTRACT_ADDRESS", "proof_v2_contract_address")
    abi_path = _get_env("PROOF_V2_ABI_PATH", "proof_v2_abi_path") or \
               "src/app/services/blockchain/abi/ProofRegistryV2.json"

    if not rpc:
        raise HTTPException(status_code=500, detail="WEB3_RPC_URL not set")
    if not address:
        raise HTTPException(status_code=500, detail="PROOF_V2_CONTRACT_ADDRESS not set")

    try:
        _W3 = Web3(HTTPProvider(rpc, request_kwargs={"timeout": 30}))
        if not _W3.is_connected():
            raise HTTPException(status_code=503, detail=f"Cannot connect to RPC {rpc}")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Web3 init failed for {rpc}: {e}")

    # Load ABI (accept pure abi or hardhat artifact with 'abi')
    try:
        p = Path(abi_path)
        data = json.loads(p.read_text(encoding="utf-8"))
        abi = data.get("abi", data)
        if not isinstance(abi, list):
            raise ValueError("ABI is not a list")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed reading ABI from {abi_path}: {e}")

    try:
        _CONTRACT = _W3.eth.contract(
            address=Web3.to_checksum_address(address),
            abi=abi
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed creating contract at {address}: {e}")

    return _W3, _CONTRACT

def _is_fn(contract, name: str) -> bool:
    return any(e.get("type") == "function" and e.get("name") == name for e in contract.abi)

def _b32(x: str) -> HexBytes:
    s = (x or "").lower()
    if s.startswith("0x"):
        s = s[2:]
    if len(s) != 64:
        raise HTTPException(status_code=400, detail=f"'{x}' must be 32 bytes (64 hex)")
    try:
        int(s, 16)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid hex: {x}")
    return HexBytes("0x" + s)

def _safe_int(v) -> int:
    """Make best effort to coerce common types to int; otherwise 0."""
    if v is None:
        return 0
    if isinstance(v, int):
        return v
    if isinstance(v, (bytes, bytearray, HexBytes)):
        # hex bytes -> int
        try:
            return int(v.hex(), 16)
        except Exception:
            return 0
    try:
        # strings like '0', '123', etc. Guard empty-string
        s = str(v).strip()
        if s == "":
            return 0
        return int(s)
    except Exception:
        return 0

# -------------------------------------------------------------------
# request/response models

class AnchorReq(BaseModel):
    media_id: str          # 64-hex
    owner_email_sha: str   # 64-hex
    file_sha256: str       # 64-hex
    ipfs_cid: str | None = ""

    @field_validator("media_id", "owner_email_sha", "file_sha256")
    @classmethod
    def _hex64(cls, v: str) -> str:
        vv = (v or "").lower().removeprefix("0x")
        if len(vv) != 64:
            raise ValueError("must be 32 bytes (64 hex chars)")
        int(vv, 16)
        return vv

class AnchorResp(BaseModel):
    txHash: str
    blockNumber: int | None = None

class LookupResp(BaseModel):
    exists: bool
    owner_email_sha: str
    file_sha256: str
    timestamp: int
    ipfs_cid: str

# -------------------------------------------------------------------
# routes

@router.post("/anchor", response_model=AnchorResp)
def anchor(req: AnchorReq):
    w3, contract = _ensure_contract()
    media_b = _b32(req.media_id)
    owner_b = _b32(req.owner_email_sha)
    file_b  = _b32(req.file_sha256)
    ipfs_cid = req.ipfs_cid or ""

    # prefer v2 name, fallback to an older one
    if _is_fn(contract, "registerMedia"):
        fn = contract.functions.registerMedia(media_b, owner_b, file_b, ipfs_cid)
    elif _is_fn(contract, "register"):
        fn = contract.functions.register(media_b, owner_b, file_b, ipfs_cid)
    else:
        names = [e.get("name") for e in contract.abi if e.get("type") == "function"]
        raise HTTPException(status_code=500, detail=f"No register function in ABI. Functions: {names}")

    try:
        acct = w3.eth.account.from_key(_get_env("WEB3_PRIVATE_KEY", "web3_private_key"))
        # chain id may be empty; fall back to provider's chain id
        chain_id_cfg = _get_env("WEB3_CHAIN_ID", "web3_chain_id")
        chain_id = int(chain_id_cfg) if chain_id_cfg not in (None, "") else int(w3.eth.chain_id)

        nonce = w3.eth.get_transaction_count(acct.address)
        tx = fn.build_transaction({
            "from": acct.address,
            "nonce": nonce,
            "chainId": chain_id,
            "gasPrice": w3.eth.gas_price,
        })
        signed = acct.sign_transaction(tx)
        raw = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction", None)
        if raw is None:
            raise RuntimeError("Signed tx missing raw_transaction/rawTransaction")

        tx_hash = w3.eth.send_raw_transaction(raw)
        rec = w3.eth.wait_for_transaction_receipt(tx_hash)
        return AnchorResp(txHash=tx_hash.hex(), blockNumber=rec.blockNumber)

    except Exception as e:
        # map common revert
        msg = str(e)
        if "already registered" in msg.lower():
            raise HTTPException(status_code=409, detail="already registered")
        raise HTTPException(status_code=500, detail=msg)

@router.get("/verify", response_model=LookupResp)
def verify(media_id: str = Query(..., description="32-byte hex (with or without 0x)")):
    """
    Tolerates multiple ABI shapes:

    - getByMediaId(bytes32) -> (bool exists, bytes32 owner, bytes32 file, uint256 ts, string ipfs)
    - get(bytes32)          -> same as above (older name)
    - proofs(bytes32)       -> (bytes32 owner, bytes32 file, uint256 ts, string ipfs)
    - struct/tuple with slight order differences
    """
    w3, contract = _ensure_contract()
    media_b = _b32(media_id)

    # choose best-matching getter
    if _is_fn(contract, "getByMediaId"):
        getter = contract.functions.getByMediaId(media_b)
    elif _is_fn(contract, "get"):
        getter = contract.functions.get(media_b)
    elif _is_fn(contract, "proofs"):
        getter = contract.functions.proofs(media_b)  # public mapping getter
    else:
        names = [e.get("name") for e in contract.abi if e.get("type") == "function"]
        raise HTTPException(status_code=500, detail=f"No verify getter in ABI. Functions: {names}")

    try:
        res = getter.call()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"contract call failed: {e}")

    # Normalize outputs from different ABIs
    exists = False
    owner_sha = "0x" + "00"*32
    file_sha  = "0x" + "00"*32
    ts        = 0
    ipfs_cid  = ""

    try:
        # If it's a tuple/list
        if isinstance(res, (list, tuple)):
            # 5-tuple: (exists, owner, file, ts, ipfs)
            if len(res) == 5 and isinstance(res[0], (bool, int)):
                exists = bool(res[0])
                owner_sha = Web3.to_hex(res[1]).lower()
                file_sha  = Web3.to_hex(res[2]).lower()
                ts        = _safe_int(res[3])
                ipfs_cid  = str(res[4] or "")
            # 4-tuple: (owner, file, ts, ipfs) from public mapping
            elif len(res) == 4:
                owner_sha = Web3.to_hex(res[0]).lower()
                file_sha  = Web3.to_hex(res[1]).lower()
                ts        = _safe_int(res[2])
                ipfs_cid  = str(res[3] or "")
                # consider it exists if owner is non-zero or ts > 0
                exists = owner_sha != ("0x" + "00"*32) or ts > 0
            else:
                # Best-effort generic unpack
                for item in res:
                    if isinstance(item, (bytes, HexBytes)) and len(item) in (32, 64):
                        hx = Web3.to_hex(item).lower()
                        if owner_sha == "0x" + "00"*32:
                            owner_sha = hx
                        elif file_sha == "0x" + "00"*32:
                            file_sha = hx
                    elif isinstance(item, str) and not ipfs_cid:
                        ipfs_cid = item
                    else:
                        ts = ts or _safe_int(item)
                exists = owner_sha != ("0x" + "00"*32) or ts > 0
        else:
            # Unknown object type; do nothing special
            pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"decode error: {e}")

    return LookupResp(
        exists=bool(exists),
        owner_email_sha=owner_sha,
        file_sha256=file_sha,
        timestamp=int(ts or 0),
        ipfs_cid=ipfs_cid or "",
    )
