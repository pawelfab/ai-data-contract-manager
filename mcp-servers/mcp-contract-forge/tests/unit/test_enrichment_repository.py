import json
from pathlib import Path

from contract_forge.adapters.outbound.enrichment_composite.repository import CompositeEnrichmentRepository
from contract_forge.adapters.outbound.enrichment_json.adapter import JsonEnrichmentRepository
from contract_forge.adapters.outbound.enrichment_user_store.memory import InMemoryUserEnrichmentRepository
from contract_forge.application.services.enrichment_resolver import (
    requirements_complete,
    resolve_enrichment,
)
from contract_forge.domain.enrichment.models import EnrichmentContext, EnrichmentRule, EnrichmentScope


def test_system_enrichment_requires_matching_context(tmp_path: Path):
    path = tmp_path / "ux_rules.json"
    path.write_text(json.dumps({"rules": [{"id": "sap.dataset", "scope": "system", "system": "sap", "path": "/silver/dataset", "value": "aaa_dataset"}]}), encoding="utf-8")
    repo = JsonEnrichmentRepository(path)
    rules = repo.get_rules(EnrichmentContext())
    assert resolve_enrichment({}, rules, EnrichmentContext(), eligible_paths={"/silver/dataset"}, open_requirement_paths=set()) == []
    suggestions = resolve_enrichment({}, rules, EnrichmentContext(source_system="SAP"), eligible_paths={"/silver/dataset"}, open_requirement_paths=set())
    assert suggestions[0].value == "aaa_dataset"
    assert suggestions[0].source == "system_enrichment"


def test_user_repository_overrides_system_repository(tmp_path: Path):
    path = tmp_path / "ux_rules.json"
    path.write_text(json.dumps({"rules": [{"id": "sap.dataset", "scope": "system", "system": "sap", "path": "/silver/dataset", "value": "aaa_dataset"}]}), encoding="utf-8")
    system_repo = JsonEnrichmentRepository(path)
    user_repo = InMemoryUserEnrichmentRepository({"u1": [EnrichmentRule(id="user.sap.dataset", path="/silver/dataset", value="my_dataset", scope=EnrichmentScope.USER)]})
    context = EnrichmentContext(user_id="u1", source_system="sap")
    rules = CompositeEnrichmentRepository(system_repo, user_repo).get_rules(context)
    suggestions = resolve_enrichment({}, rules, context, eligible_paths={"/silver/dataset"}, open_requirement_paths=set())
    assert suggestions[0].value == "my_dataset"
    assert suggestions[0].source == "user_enrichment"


def test_global_template_copy_and_interpolation(tmp_path: Path):
    path = tmp_path / "ux_rules.json"
    path.write_text(json.dumps({"rules": [
        {"id": "copy", "scope": "global", "path": "/metadata/id", "value": "{/metadata/sourceSystemGcpId}"},
        {"id": "uri", "scope": "global", "path": "/rawData/gcsBucketPath", "value": "gs://landing/{/metadata/sourceSystemGcpId}/{/metadata/dataFileId}"}
    ]}), encoding="utf-8")
    doc = {"metadata": {"sourceSystemGcpId": "sap", "dataFileId": "customer"}}
    rules = JsonEnrichmentRepository(path).get_rules(EnrichmentContext())
    suggestions = resolve_enrichment(doc, rules, EnrichmentContext(), eligible_paths={"/metadata/id", "/rawData/gcsBucketPath"}, open_requirement_paths=set())
    values = {x.path: x.value for x in suggestions}
    assert values["/metadata/id"] == "sap"
    assert values["/rawData/gcsBucketPath"] == "gs://landing/sap/customer"


def test_path_pattern_applies_only_to_current_eligible_paths(tmp_path: Path):
    path = tmp_path / "ux_rules.json"
    path.write_text(json.dumps({"rules": [{"id": "source", "scope": "global", "pathPattern": "/**/systemZrodlowy", "value": "{/metadata/sourceSystemGcpId}"}]}), encoding="utf-8")
    doc = {"metadata": {"sourceSystemGcpId": "sap"}}
    rules = JsonEnrichmentRepository(path).get_rules(EnrichmentContext())
    suggestions = resolve_enrichment(doc, rules, EnrichmentContext(), eligible_paths={"/some/source/systemZrodlowy", "/other/value"}, open_requirement_paths=set())
    assert [(x.path, x.value) for x in suggestions] == [("/some/source/systemZrodlowy", "sap")]


def test_requirements_complete_is_a_prefix_question_about_open_formal_requirements():
    # The prefix itself and anything below it count; a sibling branch never does.
    assert requirements_complete("/source", {"/source/encoding"}) is False
    assert requirements_complete("/source", {"/source"}) is False
    assert requirements_complete("/source", {"/silver/tables/0/pk"}) is True
    assert requirements_complete("/source", set()) is True
    # "/sourceName" is not under "/source" — segment boundaries, not string prefixes.
    assert requirements_complete("/source", {"/sourceName"}) is True


def test_requirements_complete_condition_gates_a_rule_through_the_json_adapter(tmp_path: Path):
    path = tmp_path / "ux_rules.json"
    path.write_text(
        json.dumps({"rules": [{
            "id": "gated",
            "scope": "global",
            "path": "/silver/enabled",
            "value": True,
            "when": [{"path": "/source", "requirementsComplete": True}],
        }]}),
        encoding="utf-8",
    )
    rules = JsonEnrichmentRepository(path).get_rules(EnrichmentContext())
    assert rules[0].conditions[0].requirements_complete is True

    blocked = resolve_enrichment(
        {}, rules, EnrichmentContext(),
        eligible_paths={"/silver/enabled"},
        open_requirement_paths={"/source/encoding"},
    )
    assert blocked == []

    allowed = resolve_enrichment(
        {}, rules, EnrichmentContext(),
        eligible_paths={"/silver/enabled"},
        open_requirement_paths={"/silver/tables/0/pk"},
    )
    assert [(x.path, x.value) for x in allowed] == [("/silver/enabled", True)]
