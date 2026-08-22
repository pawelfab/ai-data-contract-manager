import json
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_SERVICE_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    forge_mcp_url: str = "http://127.0.0.1:8001/mcp"
    max_stabilization_rounds: int = 20
    llm_mode: str = "pydantic-ai"
    llm_model: str = "test"
    llm_base_url: str | None = None
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "ADCM_OPENAI_API_KEY"),
    )
    context_mcp_urls: dict[str, str] = Field(default_factory=dict)

    @field_validator("context_mcp_urls", mode="before")
    @classmethod
    def parse_context_urls(cls, value):
        if isinstance(value, str):
            return json.loads(value)
        return value

    model_config = SettingsConfigDict(env_prefix="ADCM_", env_file=_SERVICE_ROOT / ".env", extra="ignore")
