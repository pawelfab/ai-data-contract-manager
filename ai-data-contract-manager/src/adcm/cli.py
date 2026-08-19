from __future__ import annotations

import argparse
import asyncio
import json

from .runtime import build_orchestrator
from .settings import load_settings


def _read_answer(pending_path: str | None) -> str:
    if pending_path == "source.columns":
        print("Wklej kolumny (JSON albo po jednej kolumnie na linię). Zakończ pustą linią:")
        lines: list[str] = []
        while True:
            line = input()
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
                if turn.status == "complete":
                    print("\n--- FINAL CONTRACT ---")
                    print(json.dumps(turn.contract, indent=2, ensure_ascii=False))
                    return
                if turn.status == "invalid":
                    print("\n--- INVALID CONTRACT ---")
                    print(json.dumps(turn.contract, indent=2, ensure_ascii=False))
                    return
                answer = _read_answer(turn.pending_path)
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
