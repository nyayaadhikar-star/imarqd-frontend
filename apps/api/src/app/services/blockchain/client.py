from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Tuple

from dotenv import load_dotenv  # NEW
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_utils import to_checksum_address
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware



ABI_DEFAULT_PATH = Path(__file__).with_suffix("")  # .../services/blockchain/client
ABI_DIR = (ABI_DEFAULT_PATH.parent / "abi").resolve()

# --- NEW: robust .env loader (walk up until we find .env) ---
def _load_dotenv_once() -> None:
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        env = p / ".env"
        if env.exists():
            load_dotenv(env)  # do nothing if already loaded
            break
_load_dotenv_once()
# -------------------------------------------------------------


@dataclass(frozen=True)
class ChainConfig:
    rpc_url: str
    chain_id: int
    contract_address: str
    abi_path: Path
    private_key: str | None

def _env(name: str, default: str | None = None) -> str:
    v = os.getenv(name, default)
    if v is None or v == "":
        raise RuntimeError(f"Missing required env var: {name}")
    return v

def load_chain_config() -> ChainConfig:
    rpc = _env("WEB3_RPC_URL")
    chain_id = int(_env("WEB3_CHAIN_ID"))
    address = _env("PROOF_CONTRACT_ADDRESS")
    abi_env = _env("PROOF_CONTRACT_ABI_PATH")

    # client.py = .../apps/api/src/app/services/blockchain/client.py
    # parents indexes:
    # [0]=.../blockchain
    # [1]=.../services
    # [2]=.../app
    # [3]=.../src
    # [4]=.../apps/api  ✅ this is the app root we want
    APP_ROOT = Path(__file__).resolve().parents[4]

    abi_candidate = Path(abi_env)
    if not abi_candidate.is_absolute():
        abi_candidate = (APP_ROOT / abi_candidate).resolve()

    # If the target ABI doesn't exist or is empty, use the Hardhat artifact
    hardhat_artifact = (
        APP_ROOT / "chain" / "artifacts" / "contracts" /
        "ProofRegistry.sol" / "ProofRegistry.json"
    ).resolve()

    if (not abi_candidate.exists()) or (abi_candidate.stat().st_size == 0):
        if hardhat_artifact.exists() and hardhat_artifact.stat().st_size > 0:
            abi_candidate = hardhat_artifact
        else:
            raise FileNotFoundError(
                f"ABI not found or empty at {abi_candidate}. "
                f"Tried fallback at {hardhat_artifact} and it wasn't usable either."
            )

    pk = os.getenv("WEB3_PRIVATE_KEY")  # optional for read; required for /anchor
    return ChainConfig(
        rpc_url=rpc,
        chain_id=chain_id,
        contract_address=to_checksum_address(address),
        abi_path=abi_candidate,
        private_key=pk,
    )



class Web3Client:
    def __init__(self, cfg: ChainConfig | None = None) -> None:
        self.cfg = cfg or load_chain_config()
        self.w3 = Web3(Web3.HTTPProvider(self.cfg.rpc_url, request_kwargs={"timeout": 60}))
        # Polygon Amoy/Mumbai are PoA-style; add middleware to handle extraData
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        with open(self.cfg.abi_path, "r", encoding="utf-8") as f:
            abi_json = json.load(f)
        abi = abi_json["abi"] if "abi" in abi_json else abi_json
        self.contract = self.w3.eth.contract(address=self.cfg.contract_address, abi=abi)

        self._acct: LocalAccount | None = None
        if self.cfg.private_key:
            Account.enable_unaudited_hdwallet_features()  # no-op for raw keys; keeps API consistent
            self._acct = Account.from_key(self.cfg.private_key)

    # ---- helpers ----
    def _require_signer(self) -> LocalAccount:
        if not self._acct:
            raise RuntimeError(
                "WEB3_PRIVATE_KEY is not set; cannot send transactions. "
                "Set it in apps/api/.env to enable anchoring."
            )
        return self._acct

    def get_chain_id(self) -> int:
        try:
            return self.w3.eth.chain_id
        except Exception:
            return self.cfg.chain_id

    def get_signer_address(self) -> str | None:
        return self._acct.address if self._acct else None

    # ---- calls ----
    def call_get_proof(self, file_hash32: bytes) -> Tuple[bool, bytes, int, str]:
        return self.contract.functions.getProof(file_hash32).call()

    # ---- transactions ----
    def tx_register_proof(self, file_hash32: bytes, email_sha32: bytes, ipfs_cid: str) -> dict[str, Any]:
        acct = self._require_signer()
        nonce = self.w3.eth.get_transaction_count(acct.address)

        # EIP-1559 (Polygon Amoy supports it)
        try:
            max_fee = self.w3.to_wei("120", "gwei")
            max_priority = self.w3.to_wei("30", "gwei")
            tx = self.contract.functions.registerProof(file_hash32, email_sha32, ipfs_cid).build_transaction({
                "from": acct.address,
                "chainId": self.cfg.chain_id,
                "nonce": nonce,
                "maxFeePerGas": max_fee,
                "maxPriorityFeePerGas": max_priority,
            })
        except Exception:
            gas_price = self.w3.eth.gas_price
            tx = self.contract.functions.registerProof(file_hash32, email_sha32, ipfs_cid).build_transaction({
                "from": acct.address,
                "chainId": self.cfg.chain_id,
                "nonce": nonce,
                "gasPrice": gas_price,
            })

        # sign + send (robust to attribute name)
        signed = acct.sign_transaction(tx)
        raw_tx = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction", None)
        if raw_tx is None:
            raise RuntimeError("SignedTransaction has no rawTransaction attribute")

        tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        return {
            "tx_hash": tx_hash.hex(),
            "block_number": receipt.blockNumber,
            "status": int(receipt.status),
        }
