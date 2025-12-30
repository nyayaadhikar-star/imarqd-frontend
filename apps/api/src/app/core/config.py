from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    api_prefix: str = "/api"
    environment: str = "dev"
    upload_dir: str = "uploads"
    database_url: str = "sqlite:///./klyvo_dev.db"  # dev default; set to postgres later
    model_config = ConfigDict(extra="allow")

    # class Config:
    #     env_file = ".env"


# apps/api/src/app/core/config.py
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # Load .env, accept extra keys without failing
    api_prefix: str = "/api"
    environment: str = "dev"
    upload_dir: str = "uploads"
    database_url: str = "sqlite:///./klyvo_dev.db"  # dev default; set to postgres later
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",          # don't crash on unknown env vars
    )

    # ------------------------------------------------------------------
    # Existing fields you already had (keep them here)...
    # e.g. api_base_url: str = "http://127.0.0.1:8000"
    # ------------------------------------------------------------------

    # --- Web3 / Chain ---
    web3_rpc_url: str = Field(..., description="RPC URL, e.g. https://rpc-amoy.polygon.technology/")
    web3_chain_id: int = Field(..., description="EVM chain id, e.g. 80002 for Polygon Amoy")
    web3_private_key: str = Field(..., description="Deployer/signer private key (0x...)")

    # --- V2 contract (preferred names) ---
    proof_v2_contract_address: str | None = Field(
        default=None, description="Address of ProofRegistryV2"
    )
    proof_v2_contract_abi_path: str | None = Field(
        default=None,
        description="Path to ProofRegistryV2.json (ABI)",
    )

    # --- Backward-compat / alternative names (both supported) ---
    # If your .env already uses these, we’ll still pick them up via code in registry_v2.py
    proof_contract_v2_address: str | None = None
    proof_contract_v2_abi_path: str | None = None
    proof_contract_address: str | None = None  # legacy v1

    # Optional: convenience to resolve paths
    def resolve_path(self, p: str | None) -> str | None:
        if not p:
            return None
        pp = Path(p)
        if pp.is_absolute():
            return str(pp)
        # resolve relative to this file’s project root
        root = Path(__file__).resolve().parents[3]  # .../apps/api/src/app/core/config.py -> up to repo root
        return str((root / pp).resolve())


settings = Settings()


