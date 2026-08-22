from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


_SERVICE_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    contract_path: str = str(_SERVICE_ROOT / "resources" / "contract.json")
    enrichment_path: str = str(_SERVICE_ROOT / "resources" / "ux_rules.json")
    discovery_path: str = str(_SERVICE_ROOT / "resources" / "discovery_rules.json")
    discovery_strict: bool = False
    host: str = "127.0.0.1"
    port: int = 8001

    model_config = SettingsConfigDict(env_prefix="FORGE_", env_file=_SERVICE_ROOT / ".env", extra="ignore")
