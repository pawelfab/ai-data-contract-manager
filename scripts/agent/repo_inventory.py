from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any

from common import (
    ROOT,
    content_digest,
    load_config,
    read_staged_file,
    rel,
    source_files,
    source_snapshot_id,
    staged_source_paths,
)


LANGUAGE_BY_SUFFIX = {
    ".py": "Python", ".pyi": "Python",
    ".js": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin",
    ".cs": "C#", ".go": "Go", ".rs": "Rust",
    ".php": "PHP", ".rb": "Ruby", ".sql": "SQL",
    ".graphql": "GraphQL", ".proto": "Protocol Buffers",
    ".yaml": "YAML", ".yml": "YAML", ".json": "JSON", ".toml": "TOML",
}


def python_symbols(text: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    symbols: list[dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append({
                "kind": "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function",
                "name": node.name,
                "line": node.lineno,
            })
        elif isinstance(node, ast.ClassDef):
            methods = []
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append({
                        "name": child.name,
                        "line": child.lineno,
                        "async": isinstance(child, ast.AsyncFunctionDef),
                    })
            symbols.append({
                "kind": "class",
                "name": node.name,
                "line": node.lineno,
                "methods": methods,
            })
    return symbols


GENERIC_PATTERNS = [
    ("class", re.compile(r"^\s*(?:export\s+)?(?:public\s+|private\s+|protected\s+|internal\s+)?(?:abstract\s+)?class\s+([A-Za-z_]\w*)", re.M)),
    ("interface", re.compile(r"^\s*(?:export\s+)?(?:public\s+)?interface\s+([A-Za-z_]\w*)", re.M)),
    ("function", re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_]\w*)\s*\(", re.M)),
    ("function", re.compile(r"^\s*(?:pub\s+)?fn\s+([A-Za-z_]\w*)\s*\(", re.M)),
    ("function", re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*\(", re.M)),
]


def generic_symbols(text: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for kind, pattern in GENERIC_PATTERNS:
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            found.append({"kind": kind, "name": match.group(1), "line": line})
    return sorted(found, key=lambda item: (item["line"], item["name"]))


def inspect_bytes(path: str, raw: bytes) -> dict[str, Any]:
    # Normalize first so the inventory is identical whether it was generated from the Git
    # index (LF) or from a core.autocrlf working tree (CRLF).
    raw = raw.replace(b"\r\n", b"\n")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
    suffix = Path(path).suffix.lower()
    symbols = python_symbols(text) if suffix in {".py", ".pyi"} else generic_symbols(text)
    return {
        "path": path,
        "language": LANGUAGE_BY_SUFFIX.get(suffix, suffix.lstrip(".").upper() or "Unknown"),
        "bytes": len(raw),
        "lines": text.count("\n") + (1 if text else 0),
        "sha256": content_digest(raw),
        "symbols": symbols,
    }


def inspect(path: Path) -> dict[str, Any]:
    return inspect_bytes(rel(path), path.read_bytes())


def render_map(items: list[dict[str, Any]], snapshot_id: str) -> str:
    by_top: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        top = item["path"].split("/", 1)[0]
        by_top.setdefault(top, []).append(item)

    lines = [
        "# Generated repository map",
        "",
        f"Source snapshot: `{snapshot_id}`",
        "",
        "> Navigation aid generated mechanically. Symbol extraction outside Python is heuristic.",
        "",
        f"Source files indexed: **{len(items)}**",
        "",
    ]
    for top, group in sorted(by_top.items()):
        lines.extend([f"## `{top}/`", ""])
        for item in group:
            lines.append(f"### `{item['path']}`")
            lines.append(f"- Language: {item['language']}")
            lines.append(f"- Lines: {item['lines']}")
            if item["symbols"]:
                lines.append("- Symbols:")
                for symbol in item["symbols"][:80]:
                    lines.append(f"  - `{symbol['kind']} {symbol['name']}` — line {symbol['line']}")
                    for method in symbol.get("methods", [])[:40]:
                        prefix = "async " if method.get("async") else ""
                        lines.append(f"    - `{prefix}{method['name']}` — line {method['line']}")
            else:
                lines.append("- Symbols: none extracted")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def generate(config: dict[str, Any], *, staged: bool = False) -> list[dict[str, Any]]:
    if staged:
        items = [inspect_bytes(path, read_staged_file(path)) for path in staged_source_paths(config)]
    else:
        items = [inspect(path) for path in source_files(config)]
    snapshot_id = source_snapshot_id({item["path"]: item["sha256"] for item in items})
    payload = {
        "schema_version": 1,
        "source_snapshot": snapshot_id,
        "repository_root": ".",
        "files": items,
    }

    inventory_path = ROOT / config["inventory_json"]
    map_path = ROOT / config["repository_map"]
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    map_path.write_text(render_map(items, snapshot_id), encoding="utf-8")
    print(f"Indexed {len(items)} source files.")
    print(f"Wrote {inventory_path.relative_to(ROOT)}")
    print(f"Wrote {map_path.relative_to(ROOT)}")
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a language-light repository inventory.")
    parser.add_argument("--staged", action="store_true", help="Read source files from the Git index.")
    args = parser.parse_args()
    generate(load_config(), staged=args.staged)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
