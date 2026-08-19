"""Minimal conversation against a running Contract Forge MCP service.

Run this with the ADCM virtual environment after starting `contract-forge-mcp`.
"""

import asyncio

from adcm.runtime import build_orchestrator


async def main() -> None:
    service = build_orchestrator()
    async with service.gateway:
        try:
            turn = await service.start()
            print("ADCM:", turn.message)
            for answer in ("rocket", "pipeline: daily_clients"):
                print("USER:", answer)
                turn = await service.message(turn.session_id, answer)
                print("ADCM:", turn.message)
        finally:
            await service.semantic.close()


if __name__ == "__main__":
    asyncio.run(main())
