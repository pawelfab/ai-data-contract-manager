from typing import Literal

from pydantic import BaseModel, model_validator


ContractForgeTransport = Literal["mock", "fixture", "remote"]


class Settings(BaseModel):
    llm_model: str = "openai:gpt-5.6-sol"
    session_backend: str = "memory"
    audit_backend: str = "jsonl"
    contract_forge_transport: ContractForgeTransport = "mock"
    contract_forge_source: str | None = None
    contract_forge_endpoint: str | None = None

    @model_validator(mode="after")
    def validate_contract_forge_selection(self) -> "Settings":
        """Validate adapter selection without opening or parsing Forge artifacts."""
        source = self.contract_forge_source
        endpoint = self.contract_forge_endpoint

        if source is not None and not source.strip():
            raise ValueError("contract_forge_source must be non-blank when supplied")
        if endpoint is not None and not endpoint.strip():
            raise ValueError("contract_forge_endpoint must be non-blank when supplied")

        if self.contract_forge_transport == "mock":
            if source is not None or endpoint is not None:
                raise ValueError(
                    "mock contract_forge_transport does not accept "
                    "contract_forge_source or contract_forge_endpoint"
                )
        elif self.contract_forge_transport == "fixture":
            if source is None:
                raise ValueError("fixture contract_forge_transport requires contract_forge_source")
            if endpoint is not None:
                raise ValueError(
                    "fixture contract_forge_transport does not accept contract_forge_endpoint"
                )
        elif source is None or endpoint is None:
            raise ValueError(
                "remote contract_forge_transport requires contract_forge_source "
                "and contract_forge_endpoint"
            )

        return self
