import asyncio
import json

from adcm.runtime import build_orchestrator


async def main():
    service = build_orchestrator()
    async with service.gateway:
        try:
            turn = await service.start()
            turn = await service.message(turn.session_id, "0 6 * * *")
            turn = await service.message(
                turn.session_id,
                "Rocket. pipeline: customer_accounts_daily; "
                "owner: data-platform@example.com; "
                "uri: gs://raw-zone/accounts/accounts.dat",
            )
            assert turn.pending_path == "source.columns", turn.model_dump(mode="json")
            assert turn.contract["orchestration"]["schedule"] == "0 6 * * *", (
                service.sessions[turn.session_id].facts,
                turn.candidate_issues,
            )

            turn = await service.message(
                turn.session_id,
                "account_id 0 8 STRING NOT NULL\nbalance 8 20 NUMERIC",
            )
            assert turn.status == "complete", turn.validation_errors
            print(json.dumps(turn.contract, indent=2, ensure_ascii=False))
        finally:
            await service.semantic.close()


if __name__ == "__main__":
    asyncio.run(main())
