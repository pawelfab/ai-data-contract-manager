import asyncio
import json

from adcm.runtime import build_orchestrator


async def main():
    service = build_orchestrator()
    async with service.gateway:
        try:
            turn = await service.start()
            answers = [
                "roket",
                "customer_accounts_daily",
                "data-platform@example.com",
                "gs://raw-zone/accounts/accounts.dat",
                "account_id 0 8 STRING NOT NULL\nbalance 8 20 NUMERIC",
            ]
            for answer in answers:
                turn = await service.message(turn.session_id, answer)
            assert turn.status == "complete", turn.validation_errors
            print(json.dumps(turn.contract, indent=2, ensure_ascii=False))
        finally:
            await service.semantic.close()


if __name__ == "__main__":
    asyncio.run(main())
