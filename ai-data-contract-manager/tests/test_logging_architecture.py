from pathlib import Path


SOURCE = Path(__file__).parents[1] / "src" / "adcm"


def test_infrastructure_dependencies_stay_outside_core() -> None:
    for layer in ("domain", "application", "ports"):
        for path in (SOURCE / layer).rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            assert "google.cloud" not in source, path
            assert "contract_forge" not in source, path
            assert "insert_rows_json" not in source, path
            if layer in {"domain", "application"}:
                assert "from pathlib import" not in source, path
                assert ".open(" not in source, path
