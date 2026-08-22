# ADCM system overview

ADCM is a conversational coordinator for building data-pipeline contracts. Formal contract knowledge remains in Contract Forge; semantic interpretation remains in ADCM/PydanticAI.

## Core behavior

A user may provide all information in the first message, in attachments, or via references such as Jira. ADCM stores the material as evidence. Forge progressively discovers formal requirements from the current document. Each newly discovered requirement is matched against all relevant existing evidence before the user is asked again.

Forge is called deterministically until the contract reaches a fixed point. Defaults and enrichment are Forge-derived values; direct user values and explicitly user-referenced evidence such as `JIRA-4323` have higher authority.

## External MCPs

Atlassian, Schema Explorer, Repository and Visualizer are optional context/action tools available to the PydanticAI layer. Their results retain provenance. For example, if Jira says `ddd_dataset`, Forge enrichment suggests `aaa_dataset`, and existing SAP pipelines use `yyy_dataset`, ADCM can preserve the Jira value while showing the convention conflict and asking the user to decide.

## Evolvability

- contract source format is isolated behind `ContractParserPort`;
- enrichment storage is isolated behind `EnrichmentRepositoryPort`;
- current enrichment is JSON, but per-user persistence can be added as another adapter;
- `user_id` is evaluation context and never part of the generated contract;
- ADCM does not depend on the structure of `contract.json` or enrichment files.

## Architecture evolution contract

All future feature planning and LLM-assisted coding sessions must follow [`architecture-guardrails.md`](architecture-guardrails.md). The key goal is local change: contract-format evolution stays behind `ContractParserPort`, enrichment persistence/personalization stays behind `EnrichmentRepositoryPort`, mandatory Forge evaluation stays outside agent tool choice, and optional context MCPs stay behind the PydanticAI context/tool boundary.
