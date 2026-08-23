"""Gating and fixtures for the live integration tests.

These tests talk to the real Contract Forge MCP service and the real LLM endpoint. They are
skipped unless ADCM_LIVE=1 *and* both services answer, so the pre-push quality gate
(`pytest ai-data-contract-manager/tests -q`) stays fast and green without them.
"""

from __future__ import annotations

import json
import os
import socket
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import pytest

from adcm.bootstrap.container import build_container
from adcm.bootstrap.settings import Settings

from recording import RecordingForge, RecordingHeuristics, TurnRecord

_SERVICE_ROOT = Path(__file__).resolve().parents[2]

ENABLE_ENV = "ADCM_LIVE"
TIMEOUT_ENV = "ADCM_LIVE_TURN_TIMEOUT"
STRICT_ENV = "ADCM_LIVE_STRICT"
ARTIFACT_ENV = "ADCM_LIVE_ARTIFACT_DIR"


def _flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _reachable(url: str, timeout: float = 3.0) -> bool:
    parsed = urllib.parse.urlparse(url)
    if not parsed.hostname:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((parsed.hostname, port), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def live_settings() -> Settings:
    settings = Settings()
    if settings.llm_mode != "pydantic-ai":
        pytest.skip(
            f"ADCM_LLM_MODE={settings.llm_mode!r}; the live test must not silently fall back "
            "to ConservativeLocalHeuristics. Set ADCM_LLM_MODE=pydantic-ai."
        )
    return settings


@pytest.fixture(scope="session")
def turn_timeout() -> float:
    return float(os.getenv(TIMEOUT_ENV, "240"))


@pytest.fixture(scope="session")
def strict_mode() -> bool:
    return _flag(STRICT_ENV)


@pytest.fixture(scope="session", autouse=True)
def live_gate(live_settings: Settings) -> None:
    """Skip the whole directory unless explicitly enabled and both services answer."""

    if not _flag(ENABLE_ENV):
        pytest.skip(f"live tests are opt-in: set {ENABLE_ENV}=1 to run them")

    if not _reachable(live_settings.forge_mcp_url):
        pytest.skip(
            f"Contract Forge MCP not reachable at {live_settings.forge_mcp_url}. Start it with "
            "`mcp-servers\\mcp-contract-forge\\.venv\\Scripts\\python.exe -m contract_forge.main`."
        )

    if live_settings.llm_base_url and not _reachable(live_settings.llm_base_url):
        pytest.skip(
            f"LLM endpoint not reachable at {live_settings.llm_base_url}. "
            "Start the OpenAI-compatible proxy or point ADCM_LLM_BASE_URL elsewhere."
        )


@pytest.fixture
def recorded_container(live_settings: Settings):
    """The real container, with passthrough spies on the Forge and LLM ports.

    Both spies delegate to the production adapters — nothing about the flow changes, we just
    get to see the individual stabilization rounds.
    """

    container = build_container(live_settings)
    stabilizer = container.handle_message.stabilizer

    forge_spy = RecordingForge(stabilizer.forge)
    llm_spy = RecordingHeuristics(container.handle_message.heuristics)

    stabilizer.forge = forge_spy
    stabilizer.heuristics = llm_spy
    container.handle_message.heuristics = llm_spy

    return container, forge_spy, llm_spy


class Transcript:
    """Collects turns and writes a human-readable artifact, including on failure."""

    def __init__(self, name: str, directory: Path):
        self.name = name
        self.directory = directory
        self.turns: list[TurnRecord] = []
        self.started = datetime.now(timezone.utc)

    def add(self, record: TurnRecord) -> None:
        self.turns.append(record)

    def write(self) -> Path | None:
        if not self.turns:
            return None
        self.directory.mkdir(parents=True, exist_ok=True)
        stamp = self.started.strftime("%Y%m%d-%H%M%S")
        base = self.directory / f"{stamp}-{self.name}"
        base.with_suffix(".md").write_text(self._markdown(), encoding="utf-8")
        base.with_suffix(".json").write_text(self._json(), encoding="utf-8")
        return base.with_suffix(".md")

    def _markdown(self) -> str:
        lines = [
            f"# Live transcript — {self.name}",
            "",
            f"Started: {self.started.isoformat()}",
            "",
        ]
        for record in self.turns:
            lines.append(f"## Tura {record.index}")
            lines.append("")
            lines.append(f"u: {record.user}")
            lines.append("")
            if record.result is not None:
                lines.append("```json")
                lines.append(record.result.model_dump_json(indent=2))
                lines.append("```")
            if record.error:
                lines.append("```")
                lines.append(record.error)
                lines.append("```")
            lines.append("")
            lines.append(
                f"_{len(record.forge_rounds)} runda(y) Forge, {len(record.llm_calls)} wywołań LLM, "
                f"{record.duration_s:.1f}s_"
            )
            lines.append("")
            for index, forge_round in enumerate(record.forge_rounds, start=1):
                lines.append(
                    f"- runda {index}: requirements={forge_round.requirement_paths} "
                    f"suggestions={forge_round.suggestion_pairs} valid={forge_round.evaluation.valid}"
                )
            for call in record.llm_calls:
                lines.append(f"- llm {call.kind} ({call.duration_s:.1f}s): {call.detail}")
            for failure in record.hard_failures:
                lines.append(f"- **HARD FAIL** {failure}")
            for failure in record.soft_failures:
                lines.append(f"- SOFT {failure}")
            lines.append("")
        return "\n".join(lines)

    def _json(self) -> str:
        payload = [
            {
                "index": record.index,
                "user": record.user,
                "result": json.loads(record.result.model_dump_json()) if record.result else None,
                "forge_rounds": [
                    {
                        "requirements": forge_round.requirement_paths,
                        "suggestions": [list(pair) for pair in forge_round.suggestion_pairs],
                        "valid": forge_round.evaluation.valid,
                        "duration_s": round(forge_round.duration_s, 3),
                    }
                    for forge_round in record.forge_rounds
                ],
                "llm_calls": [
                    {"kind": c.kind, "duration_s": round(c.duration_s, 3), "detail": c.detail}
                    for c in record.llm_calls
                ],
                "duration_s": round(record.duration_s, 3),
                "hard_failures": record.hard_failures,
                "soft_failures": record.soft_failures,
                "error": record.error,
            }
            for record in self.turns
        ]
        return json.dumps(payload, ensure_ascii=False, indent=2)


@pytest.fixture
def transcript(request):
    directory = Path(os.getenv(ARTIFACT_ENV) or (_SERVICE_ROOT / "logs" / "live"))
    collector = Transcript(request.node.name, directory)
    yield collector
    path = collector.write()
    if path:
        print(f"\n[live] transkrypt: {path}")
