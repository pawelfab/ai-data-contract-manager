from pathlib import Path
import importlib.util
import sys


SCRIPT = Path(__file__).parents[1] / "scripts" / "ux_rules_analyzer.py"
spec = importlib.util.spec_from_file_location("ux_rules_analyzer", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_hogan_patterns_are_detected():
    contracts_dir = Path(__file__).parent / "fixtures" / "contracts"
    docs = module.load_yaml_contracts(contracts_dir)
    docs = module.filter_by_source_system(
        docs,
        "HOGAN",
        "metadata.sourceSystemGcpId",
    )

    report = module.build_report(
        docs,
        source_system="HOGAN",
        source_system_path="metadata.sourceSystemGcpId",
        min_presence=0.8,
    )

    assert report["contract_count"] == 3

    constants = report["candidates"]["constants"]
    parquet = next(
        item
        for item in constants
        if item["path"] == "converter.output.format"
    )
    assert parquet["value"] == "parquet"
    assert parquet["confidence"] == "high"

    copies = report["candidates"]["equal_paths"]
    relation = next(
        item
        for item in copies
        if item["path"] == "converter.source.systemZrodlowy"
        and item["source_path"] == "metadata.sourceSystemGcpId"
    )
    assert relation["matches"] == 3

    templates = report["candidates"]["simple_templates"]
    template = next(
        item
        for item in templates
        if item["path"] == "converter.source.filenamePattern"
        and item["source_path"] == "metadata.id"
    )
    assert template["template"] == "{source}_input.TXT"
