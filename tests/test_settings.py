from __future__ import annotations

import os

from acdm.settings import AppSettings


def test_settings_are_loaded_from_dotenv(tmp_path, monkeypatch) -> None:
    names = (
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "ACDM_MODEL",
        "ACDM_CONTRACT_TRANSPORT",
        "ACDM_MCP_TIMEOUT_SECONDS",
        "ACDM_MAX_AUTOMATIC_REPAIR_ATTEMPTS",
        "ACDM_HOST",
        "ACDM_PORT",
        "ACDM_AUDIT_ENABLED",
        "ACDM_AUDIT_DIR",
        "ACDM_AUDIT_INCLUDE_MODEL_IO",
        "ACDM_AUDIT_INCLUDE_MCP_PAYLOADS",
    )
    for name in names:
        monkeypatch.delenv(name, raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=test-key",
                "OPENAI_BASE_URL=https://llm.example.test/v1",
                "ACDM_MODEL=openai:test-model",
                "ACDM_CONTRACT_TRANSPORT=stdio",
                "ACDM_MCP_TIMEOUT_SECONDS=7.5",
                "ACDM_MAX_AUTOMATIC_REPAIR_ATTEMPTS=3",
                "ACDM_HOST=0.0.0.0",
                "ACDM_PORT=9000",
                "ACDM_AUDIT_ENABLED=true",
                "ACDM_AUDIT_DIR=audit-logs",
                "ACDM_AUDIT_INCLUDE_MODEL_IO=false",
                "ACDM_AUDIT_INCLUDE_MCP_PAYLOADS=true",
            ]
        ),
        encoding="utf-8",
    )

    settings = AppSettings.from_env(env_file)

    assert os.environ["OPENAI_API_KEY"] == "test-key"
    assert os.environ["OPENAI_BASE_URL"] == "https://llm.example.test/v1"
    assert settings.model == "openai:test-model"
    assert settings.contract_transport == "stdio"
    assert settings.mcp_timeout_seconds == 7.5
    assert settings.max_automatic_repair_attempts == 3
    assert settings.host == "0.0.0.0"
    assert settings.port == 9000
    assert settings.audit_enabled is True
    assert settings.audit_dir == tmp_path / "audit-logs"
    assert settings.audit_include_model_io is False
    assert settings.audit_include_mcp_payloads is True
