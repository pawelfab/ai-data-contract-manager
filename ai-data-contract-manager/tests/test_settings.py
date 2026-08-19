from pathlib import Path

import pytest
from pydantic import ValidationError

from adcm.settings import ADCMSettings, load_settings


OPENAI_ENV_KEYS = (
    "ADCM_LLM_MODE",
    "ADCM_LLM_PROVIDER",
    "ADCM_MODEL",
    "ADCM_VERTEX_MODEL",
    "OPENAI_BASE_URL",
    "OPENAI_API_KEY",
    "ADCM_LLM_CONFIDENCE_THRESHOLD",
)


def _clear_llm_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in OPENAI_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_settings_load_project_style_env_file_without_exposing_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_environment(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            (
                "ADCM_LLM_MODE=pydantic",
                "ADCM_LLM_PROVIDER=openai_compatible",
                "ADCM_MODEL=auto",
                "OPENAI_BASE_URL=http://127.0.0.1:3030/v1",
                "OPENAI_API_KEY=test-secret",
                "ADCM_LLM_CONFIDENCE_THRESHOLD=0.91",
            )
        ),
        encoding="utf-8",
    )

    settings = load_settings(env_file)

    assert settings.llm_mode == "pydantic"
    assert settings.resolved_llm_provider == "openai_compatible"
    assert settings.model == "auto"
    assert settings.openai_base_url == "http://127.0.0.1:3030/v1"
    assert settings.openai_api_key is not None
    assert settings.openai_api_key.get_secret_value() == "test-secret"
    assert settings.llm_confidence_threshold == 0.91
    assert "test-secret" not in repr(settings.public_runtime_summary())


def test_openai_compatible_settings_require_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_environment(monkeypatch)

    with pytest.raises(ValidationError, match="OPENAI_API_KEY"):
        ADCMSettings(
            _env_file=None,
            llm_mode="pydantic",
            llm_provider="openai_compatible",
            model="auto",
            openai_base_url="http://127.0.0.1:3030/v1",
        )


def test_process_environment_overrides_env_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_environment(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text("ADCM_MODEL=file-model\n", encoding="utf-8")
    monkeypatch.setenv("ADCM_MODEL", "process-model")

    settings = load_settings(env_file)

    assert settings.model == "process-model"


def test_auto_provider_preserves_vertex_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_environment(monkeypatch)
    settings = ADCMSettings(
        _env_file=None,
        llm_mode="pydantic",
        llm_provider="auto",
        vertex_model="gemini-test",
        openai_base_url="http://127.0.0.1:3030/v1",
        openai_api_key="test-secret",
    )

    assert settings.resolved_llm_provider == "vertex"
    assert settings.semantic_model_name == "gemini-test"
