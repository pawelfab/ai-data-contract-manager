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

            turn = await service.message(turn.session_id, "account_id,balance")
            partial = service.sessions[turn.session_id].get_partial("source.columns")
            assert partial is not None
            assert partial.missing == ["start", "end", "dataType"]
            assert "columns" not in turn.contract["source"]
            assert "columns" not in turn.contract.get("targets", {}).get("bronze", {})
            assert service.sessions[turn.session_id].get_fact("targets.bronze.columns") is None
            after_partial = await service.state(turn.session_id)
            assert "targets.bronze.columns" not in after_partial.origins, after_partial.model_dump(mode="json")

            turn = await service.message(
                turn.session_id,
                "account_id 0 8 STRING NOT NULL\nbalance 8 20 NUMERIC",
            )
            assert turn.status == "complete", turn.validation_errors
            forge_state = await service.state(turn.session_id)
            assert forge_state.origins["targets.bronze.columns"] == "generic_enrichment", (
                forge_state.origins["targets.bronze.columns"],
                service.sessions[turn.session_id].facts,
            )
            assert turn.contract["targets"]["bronze"]["columns"][0]["mode"] == "REQUIRED"
            assert turn.contract["targets"]["bronze"]["columns"][0]["sourcePath"] == (
                "source.columns.account_id"
            )
            print(json.dumps(turn.contract, indent=2, ensure_ascii=False))
        finally:
            await service.semantic.close()


if __name__ == "__main__":
    asyncio.run(main())
