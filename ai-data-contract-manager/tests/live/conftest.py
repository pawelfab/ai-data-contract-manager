"""Fixtury suity live: realny Contract Forge + realny ADCM, rozmowa wyłącznie po HTTP.

Świadomie nie ma tu `import adcm.*` ani `import contract_forge.*`. Mimo że katalog
leży w drzewie ADCM, to jest test czarnoskrzynkowy publicznego kontraktu, a nie test
jednostkowy modułu — usługi są uruchamiane jako procesy, dokładnie tak jak w
`docker-compose.yml`, tylko bez Dockera (niedostępny na maszynie deweloperskiej).

ADCM startuje przez `uvicorn --factory adcm.adapters.api.composition:build_app`, więc
pod testem jest prawdziwy composition root — jedyna warstwa, której `tests/test_api.py`
nie dotyka, bo buduje aplikację przez `create_app` na fake'ach.
"""

import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx2
import pytest

from helpers import AdcmClient

ADCM_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = ADCM_DIR.parent
FORGE_DIR = REPO_ROOT / "mcp-servers" / "mcp-contract-forge"

HEALTH_TIMEOUT_SECONDS = 45.0
SHUTDOWN_TIMEOUT_SECONDS = 10.0


def _venv_python(service_dir: Path) -> Path:
    if sys.platform == "win32":
        return service_dir / ".venv" / "Scripts" / "python.exe"
    return service_dir / ".venv" / "bin" / "python"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@dataclass
class Service:
    name: str
    base_url: str
    process: subprocess.Popen
    log_path: Path

    def log(self) -> str:
        try:
            return self.log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:  # pragma: no cover - diagnostyka błędu startu
            return "<brak logu>"


def _start_service(
    *,
    name: str,
    service_dir: Path,
    args: list[str],
    env_overrides: dict[str, str],
    port: int,
    health_url: str,
    log_dir: Path,
) -> Service:
    python = _venv_python(service_dir)
    if not python.exists():
        pytest.skip(
            f"brak venv usługi {name} ({python}). Utwórz go zgodnie z sekcją "
            f"'Uruchomienie' w README.md, inaczej testy live nie mają czego uruchomić."
        )

    env = os.environ.copy()
    # Odcinamy konfigurację odziedziczoną po powłoce dewelopera - test ma być
    # powtarzalny niezależnie od tego, co ktoś ma ustawione lokalnie.
    for leaked in ("ADCM_FORGE_URL", "ADCM_INTENT_MODE", "ADCM_MODEL", "ADCM_DEBUG_API", "ADCM_LOG_DIR"):
        env.pop(leaked, None)
    env.update(env_overrides)
    env["PYTHONPATH"] = "src"
    env["PYTHONUNBUFFERED"] = "1"

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{name}.log"
    handle = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [str(python), "-m", "uvicorn", *args, "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(service_dir),
        env=env,
        stdout=handle,
        stderr=subprocess.STDOUT,
    )
    service = Service(name=name, base_url=f"http://127.0.0.1:{port}", process=process, log_path=log_path)
    try:
        _await_health(service, health_url)
    except Exception:
        _stop_service(service)
        handle.close()
        raise
    service._handle = handle  # type: ignore[attr-defined]
    return service


def _await_health(service: Service, health_url: str) -> None:
    deadline = time.monotonic() + HEALTH_TIMEOUT_SECONDS
    with httpx2.Client(timeout=2.0) as probe:
        while time.monotonic() < deadline:
            exit_code = service.process.poll()
            if exit_code is not None:
                raise RuntimeError(
                    f"usługa {service.name} padła przy starcie (exit {exit_code})\n--- log ---\n{service.log()}"
                )
            try:
                if probe.get(health_url).status_code == 200:
                    return
            except httpx2.TransportError:
                pass
            time.sleep(0.25)
    raise RuntimeError(
        f"usługa {service.name} nie wystawiła {health_url} w {HEALTH_TIMEOUT_SECONDS:.0f}s"
        f"\n--- log ---\n{service.log()}"
    )


def _stop_service(service: Service) -> None:
    if service.process.poll() is None:
        service.process.terminate()
        try:
            service.process.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            service.process.kill()
            service.process.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)
    handle = getattr(service, "_handle", None)
    if handle is not None:
        handle.close()


@pytest.fixture(scope="session")
def live_log_dir(tmp_path_factory) -> Path:
    """Logi obu usług idą do tmp, nigdy do `logs/` w repo."""
    return tmp_path_factory.mktemp("live-services")


@pytest.fixture(scope="session")
def forge_service(live_log_dir: Path):
    port = _free_port()
    service = _start_service(
        name="contract-forge",
        service_dir=FORGE_DIR,
        args=["contract_forge.server:app"],
        env_overrides={
            "FORGE_CONTRACT_PATH": "resources/contract.json",
            "FORGE_LOG_BACKEND": "local",
            "FORGE_LOG_DIR": str(live_log_dir / "forge-logs"),
            "FORGE_ENVIRONMENT": "test",
        },
        port=port,
        health_url=f"http://127.0.0.1:{port}/health",
        log_dir=live_log_dir,
    )
    yield service
    _stop_service(service)


def _start_adcm(*, name: str, forge_service: Service, intent_env: dict[str, str], live_log_dir: Path) -> Service:
    port = _free_port()
    return _start_service(
        name=name,
        service_dir=ADCM_DIR,
        args=["--factory", "adcm.adapters.api.composition:build_app"],
        env_overrides={
            "ADCM_FORGE_URL": f"{forge_service.base_url}/mcp",
            "ADCM_RULES_PATH": "resources/ux_rules.json",
            "ADCM_LOG_BACKEND": "local",
            "ADCM_LOG_DIR": str(live_log_dir / f"{name}-logs"),
            "ADCM_ENVIRONMENT": "test",
            **intent_env,
        },
        port=port,
        health_url=f"http://127.0.0.1:{port}/health",
        log_dir=live_log_dir,
    )


@pytest.fixture(scope="session")
def adcm_heuristic(forge_service: Service, live_log_dir: Path):
    service = _start_adcm(
        name="adcm-heuristic",
        forge_service=forge_service,
        intent_env={"ADCM_INTENT_MODE": "heuristic"},
        live_log_dir=live_log_dir,
    )
    yield service
    _stop_service(service)


@pytest.fixture(scope="session")
def adcm_llm(forge_service: Service, live_log_dir: Path):
    """ADCM z prawdziwym resolverem LLM. Startuje leniwie, tylko dla testów `llm`."""
    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("ADCM_MODEL")
    if not base_url or not model:
        pytest.skip("testy llm wymagają OPENAI_BASE_URL i ADCM_MODEL (patrz ai-data-contract-manager/README.md)")
    try:
        with httpx2.Client(timeout=5.0) as probe:
            probe.get(f"{base_url.rstrip('/')}/models")
    except httpx2.TransportError as exc:
        pytest.skip(f"endpoint LLM {base_url} nie odpowiada: {type(exc).__name__}")

    service = _start_adcm(
        name="adcm-llm",
        forge_service=forge_service,
        intent_env={"ADCM_INTENT_MODE": "pydantic-ai", "ADCM_MODEL": model, "OPENAI_BASE_URL": base_url},
        live_log_dir=live_log_dir,
    )
    yield service
    _stop_service(service)


@pytest.fixture
def client(adcm_heuristic: Service):
    api = AdcmClient(adcm_heuristic.base_url)
    yield api
    api.close()


@pytest.fixture
def llm_client(adcm_llm: Service):
    # LLM przez proxy bywa wolny, więc tura dostaje wyraźnie większy budżet niż heurystyka.
    api = AdcmClient(adcm_llm.base_url, timeout=180.0)
    yield api
    api.close()
