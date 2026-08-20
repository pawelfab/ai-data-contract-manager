from __future__ import annotations

import argparse
import asyncio
import json

from .models import Requirement
from .runtime import build_orchestrator
from .settings import load_settings


def _uses_multiline_input(requirement: Requirement | None) -> bool:
    if requirement is None or requirement.unsupported_schema_keywords:
        return False
    schema = requirement.value_schema
    items = schema.get("items")
    return (
        schema.get("type") == "array"
        and isinstance(items, dict)
        and items.get("type") == "object"
    )


def _print_contract(label: str, contract: dict) -> None:
    print(f"\n--- {label} ---")
    print(json.dumps(contract, indent=2, ensure_ascii=False))


def _read_answer(requirement: Requirement | None) -> str:
    if _uses_multiline_input(requirement):
        print("Wklej elementy (JSON albo po jednym rekordzie na linię). Zakończ pustą linią:")
        lines: list[str] = []
        while True:
            try:
                line = input()
            except EOFError:
                break
            if not line.strip():
                break
            lines.append(line)
        return "\n".join(lines)
    return input("> ")


async def run(verbose: bool) -> None:
    settings = load_settings()
    summary = settings.public_runtime_summary()
    print(
        "ADCM runtime: "
        f"forge={summary['forge_gateway']}, llm={summary['llm_mode']}, "
        f"provider={summary['llm_provider']}, model={summary['llm_model']}"
    )
    service = build_orchestrator(settings=settings)
    async with service.gateway:
        try:
            turn = await service.start()
            while True:
                print(f"\nADCM: {turn.message}")
                if verbose and turn.contract:
                    print(json.dumps(turn.contract, indent=2, ensure_ascii=False))
                # A complete or invalid contract is a state, not the end of the session:
                # the user may still come back and change any field.
                if turn.status == "complete":
                    _print_contract("FINAL CONTRACT", turn.contract)
                elif turn.status == "invalid":
                    _print_contract("INVALID CONTRACT", turn.contract)
                try:
                    answer = _read_answer(turn.pending_requirement)
                except EOFError:
                    return
                if answer.strip().lower() in {"quit", "exit", ":q"}:
                    return
                turn = await service.message(turn.session_id, answer)
        finally:
            await service.semantic.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal ADCM terminal client")
    parser.add_argument("--verbose", action="store_true", help="Print contract snapshot after each turn")
    args = parser.parse_args()
    asyncio.run(run(verbose=args.verbose))


if __name__ == "__main__":
    main()
