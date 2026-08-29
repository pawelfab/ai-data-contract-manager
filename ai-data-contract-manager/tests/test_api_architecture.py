"""Guardrail: HTTP jest szczegółem adaptera.

`docs/architecture-guardials.md` §3 i §19 wymagają, aby domain, application i ports
nie znały frameworka webowego. Bez tego testu publiczny kontrakt API może niepostrzeżenie
wciekać do core.
"""

from pathlib import Path

SOURCE = Path(__file__).parents[1] / "src" / "adcm"
FORBIDDEN = ("fastapi", "starlette", "HTTPException")


def test_core_does_not_depend_on_http_framework() -> None:
    for layer in ("domain", "application", "ports"):
        for path in (SOURCE / layer).rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for token in FORBIDDEN:
                assert token not in source, f"{path} must not reference {token}"
