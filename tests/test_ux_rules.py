import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[1]
RULES_PATH = REPOSITORY_ROOT / "contracts" / "ux_rules.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def all_rules(document: dict) -> list[dict]:
    rules = list(document["defaults"]["rules"])
    for system in document["systems"].values():
        rules.extend(system["rules"])
    return rules


def rules_by_id(document: dict) -> dict[str, dict]:
    return {rule["id"]: rule for rule in all_rules(document)}


def test_ux_rules_use_supported_universal_actions_and_unique_ids() -> None:
    document = read_json(RULES_PATH)
    supported = set(document["supported_actions"])
    rules = all_rules(document)

    assert {"set_default", "copy_value", "format_value"} <= supported
    assert len(rules) == len({rule["id"] for rule in rules})

    for rule in rules:
        assert rule["action"] in supported
        assert rule["when_path"]
        assert "when_value" in rule
        assert rule["path"]
        if rule["action"] == "set_default":
            assert "value" in rule


def test_ux_rules_target_paths_match_the_contract_boundary() -> None:
    contract = read_json(REPOSITORY_ROOT / "contracts" / "contract.json")
    rules = read_json(RULES_PATH)

    assert "sourceSystemGcpId" in contract["$defs"]["Metadata"]["properties"]
    assert set(contract["properties"]) >= {
        "metadata",
        "source",
        "converter",
        "preparator",
        "targets",
        "orchestration",
    }

    canonical_paths = {
        "metadata.sourceSystemGcpId",
        "metadata.version",
        "metadata.owner",
        "source.sourceType",
        "converter.enabled",
        "converter.output.format",
        "preparator.enabled",
        "preparator.operations.unpack.enabled",
        "preparator.operations.unpack.format",
    }
    for rule in all_rules(rules):
        assert rule["path"] in canonical_paths
        assert rule["when_path"] in canonical_paths


def test_rocket_enrichment_defaults() -> None:
    rules = rules_by_id(read_json(RULES_PATH))

    expected = {
        "rocket.source.type.fixed_width": ("source.sourceType", "fixed_width"),
        "rocket.metadata.version": ("metadata.version", "1.0.0"),
        "rocket.metadata.owner": ("metadata.owner", "rocket team"),
        "rocket.preparator.enabled": ("preparator.enabled", True),
        "rocket.preparator.unpack.enabled": (
            "preparator.operations.unpack.enabled",
            True,
        ),
        "rocket.preparator.unpack.format.zip": (
            "preparator.operations.unpack.format",
            "zip",
        ),
        "rocket.converter.enabled": ("converter.enabled", True),
    }
    for rule_id, (path, value) in expected.items():
        assert rules[rule_id]["path"] == path
        assert rules[rule_id]["value"] == value

    assert rules["rocket.preparator.unpack.enabled"]["when_path"] == "preparator.enabled"
    assert rules["rocket.preparator.unpack.enabled"]["when_value"] is True
    assert rules["rocket.preparator.unpack.format.zip"]["when_path"] == (
        "preparator.operations.unpack.enabled"
    )
    assert rules["rocket.preparator.unpack.format.zip"]["when_value"] is True


def test_sap_enrichment_defaults() -> None:
    rules = rules_by_id(read_json(RULES_PATH))

    assert rules["sap.source.type.csv"]["value"] == "csv"
    assert rules["sap.preparator.disabled"]["value"] is False
    assert rules["sap.converter.enabled"]["value"] is True
    assert all(rule["when_value"] == "SAP" for rule in rules.values() if rule["id"].startswith("sap."))
