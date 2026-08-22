from pathlib import Path


def test_adcm_domain_and_application_do_not_hardcode_contract_v1_paths():
    root = Path(__file__).parents[2] / "src" / "adcm"
    forbidden = ["sourceSystemGcpId", "silver_sap", "dataFileId"]
    scanned = [root / "domain", root / "application"]
    hits = []
    for base in scanned:
        for path in base.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                if token in text:
                    hits.append(f"{path.relative_to(root)}: {token}")
    assert not hits, "Contract-format details leaked into ADCM core: " + ", ".join(hits)
