from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv


DEFAULT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


@dataclass(frozen=True)
class AppSettings:
    model: str
    contract_transport: Literal["stdio", "inprocess"]
    max_automatic_repair_attempts: int
    host: str
    port: int
    mcp_timeout_seconds: float = 15.0

    @classmethod
    def from_env(cls, env_file: str | Path | None = None) -> "AppSettings":
        load_dotenv(
            dotenv_path=Path(env_file) if env_file else DEFAULT_ENV_FILE,
            override=False,
        )
        transport = os.getenv("ACDM_CONTRACT_TRANSPORT", "stdio").lower()
        if transport not in {"stdio", "inprocess"}:
            raise ValueError(
                "ACDM_CONTRACT_TRANSPORT musi mieć wartość stdio albo inprocess."
            )
        attempts = int(os.getenv("ACDM_MAX_AUTOMATIC_REPAIR_ATTEMPTS", "2"))
        if attempts < 0:
            raise ValueError(
                "ACDM_MAX_AUTOMATIC_REPAIR_ATTEMPTS nie może być ujemne."
            )
        mcp_timeout = float(os.getenv("ACDM_MCP_TIMEOUT_SECONDS", "15"))
        if mcp_timeout <= 0:
            raise ValueError(
                "ACDM_MCP_TIMEOUT_SECONDS musi być większe od zera."
            )
        return cls(
            model=os.getenv("ACDM_MODEL", "openai:gpt-5.2"),
            contract_transport=transport,  # type: ignore[arg-type]
            max_automatic_repair_attempts=attempts,
            host=os.getenv("ACDM_HOST", "127.0.0.1"),
            port=int(os.getenv("ACDM_PORT", "7932")),
            mcp_timeout_seconds=mcp_timeout,
        )
