from copy import deepcopy

from contract_forge.domain.definition import ContractDefinition


class ContractDefinitionNormalizer:
    """Only place that knows the external contract file's top-level conventions.

    Baseline understands JSON Schema plus an existing `x-contract-enrichment` collection.
    Adapt this class to the owner's real file format; the Forge engines stay unchanged.
    """

    def normalize(self, raw: dict) -> ContractDefinition:
        schema = deepcopy(raw)
        enrichments = schema.pop("x-contract-enrichment", []) or []
        if isinstance(enrichments, dict):
            enrichments = enrichments.get("rules", [])
        version = str(raw.get("x-contract-version") or raw.get("$id") or "unknown")
        return ContractDefinition(version=version, schema_document=schema, enrichments=list(enrichments))
