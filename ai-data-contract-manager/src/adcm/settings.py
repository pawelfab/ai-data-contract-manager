from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


LLMMode = Literal["local", "pydantic"]
LLMProvider = Literal["auto", "model", "openai_compatible", "vertex"]


class ADCMSettings(BaseSettings):
    """Single runtime configuration source for CLI and API entry points."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    mcp_url: str = Field(default="http://127.0.0.1:8001/mcp", validation_alias="ADCM_MCP_URL")

    llm_mode: LLMMode = Field(default="local", validation_alias="ADCM_LLM_MODE")
    llm_provider: LLMProvider = Field(default="auto", validation_alias="ADCM_LLM_PROVIDER")
    model: str = Field(default="openai:gpt-5.2", validation_alias="ADCM_MODEL")
    vertex_model: str | None = Field(default=None, validation_alias="ADCM_VERTEX_MODEL")
    openai_base_url: str | None = Field(default=None, validation_alias="OPENAI_BASE_URL")
    openai_api_key: SecretStr | None = Field(default=None, validation_alias="OPENAI_API_KEY")

    api_host: str = Field(default="127.0.0.1", validation_alias="ADCM_API_HOST")
    api_port: int = Field(default=8080, ge=1, le=65535, validation_alias="ADCM_API_PORT")

    @property
    def resolved_llm_provider(self) -> Literal["model", "openai_compatible", "vertex"]:
        if self.llm_provider != "auto":
            return self.llm_provider
        if self.vertex_model:
            return "vertex"
        if self.openai_base_url:
            return "openai_compatible"
        return "model"

    @property
    def semantic_model_name(self) -> str:
        if self.resolved_llm_provider == "vertex":
            return self.vertex_model or "<missing>"
        return self.model

    def public_runtime_summary(self) -> dict[str, str]:
        """Return observable runtime choices without exposing credentials."""
        return {
            "forge_gateway": "mcp",
            "llm_mode": self.llm_mode,
            "llm_provider": self.resolved_llm_provider if self.llm_mode == "pydantic" else "disabled",
            "llm_model": self.semantic_model_name if self.llm_mode == "pydantic" else "disabled",
        }

    @model_validator(mode="after")
    def validate_enabled_llm(self) -> "ADCMSettings":
        if self.llm_mode != "pydantic":
            return self

        provider = self.resolved_llm_provider
        if provider == "vertex" and not self.vertex_model:
            raise ValueError("ADCM_VERTEX_MODEL is required for the vertex LLM provider")
        if provider == "openai_compatible":
            if not self.openai_base_url:
                raise ValueError("OPENAI_BASE_URL is required for the openai_compatible LLM provider")
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required for the openai_compatible LLM provider")
        return self


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_settings(env_file: str | Path | None = None) -> ADCMSettings:
    """Load process environment with an optional project-root `.env` fallback."""
    resolved_env_file = project_root() / ".env" if env_file is None else env_file
    return ADCMSettings(_env_file=resolved_env_file, _env_file_encoding="utf-8")
