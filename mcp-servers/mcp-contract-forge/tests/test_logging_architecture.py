from pathlib import Path


SOURCE = Path(__file__).parents[1] / "src" / "contract_forge"


def test_logging_infrastructure_and_service_boundaries() -> None:
    for layer in ("domain", "application", "ports"):
        for path in (SOURCE / layer).rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            assert "google.cloud" not in source, path
            assert "from adcm" not in source, path
            assert "insert_rows_json" not in source, path
            if layer in {"domain", "application"}:
                assert "from pathlib import" not in source, path
                assert ".open(" not in source, path
