import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2] / "src" / "adcm"

# Where the ban is absolute. Adapters translate between worlds; domain and application code
# must stay contract-shape agnostic.
GUARDED = ("domain", "application")

# A pointer into contract v1. ADCM may legitimately *receive* "/source/sourceType" from Forge
# and pass it on — that is data. Writing it down in ADCM is hardcoded logic, and would mean a
# contract or discovery change starts requiring an ADCM change.
CONTRACT_POINTER = re.compile(
    r"^/(metadata|orchestration|source|silver|gold|bronzeTable|preparator|converter|rawData)(/|$)"
)

# Names that only ever come from contract v1.
CONTRACT_TOKENS = (
    "JdbcSourceConfig",
    "JsonSourceConfig",
    "TxtSourceConfig",
    "FixedWidthSourceConfig",
    "sourceSystemGcpId",
    "dataFileId",
    "silver_sap",
)


def guarded_files() -> list[Path]:
    return sorted(path for area in GUARDED for path in (ROOT / area).rglob("*.py"))


def string_literals(path: Path) -> list[str]:
    """Only real string constants — comments and docstrings may discuss the contract freely."""

    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = {
        node.body[0].value
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    }
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node not in docstrings
    ]


def test_guarded_areas_exist():
    assert guarded_files()


def test_no_contract_pointer_is_written_down_in_adcm_core():
    hits = [
        f"{path.relative_to(ROOT)}: {value!r}"
        for path in guarded_files()
        for value in string_literals(path)
        if CONTRACT_POINTER.match(value)
    ]
    assert not hits, (
        "ADCM core hardcodes a contract path: " + ", ".join(hits) + ". "
        "Paths arrive from Forge requirements at runtime; they are data, never literals."
    )


@pytest.mark.parametrize("token", CONTRACT_TOKENS)
def test_no_contract_identifier_is_written_down_in_adcm_core(token: str):
    hits = [
        str(path.relative_to(ROOT))
        for path in guarded_files()
        for value in string_literals(path)
        if token in value
    ]
    assert not hits, (
        f"{token!r} leaked into ADCM core: {hits}. "
        "Contract identifiers belong to Forge contract adapters and discovery policies."
    )
