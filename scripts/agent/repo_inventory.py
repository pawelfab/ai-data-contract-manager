from __future__ import annotations

import argparse
import ast
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import ROOT, load_config, rel, sha256_file, source_files


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


def inspect(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
    suffix = path.suffix.lower()
    symbols = python_symbols(text) if suffix in {".py", ".pyi"} else generic_symbols(text)
    return {
        "path": rel(path),
        "language": LANGUAGE_BY_SUFFIX.get(suffix, suffix.lstrip(".").upper() or "Unknown"),
        "bytes": len(raw),
        "lines": text.count("\n") + (1 if text else 0),
        "sha256": sha256_file(path),
        "symbols": symbols,
    }


def render_map(items: list[dict[str, Any]], generated_at: str) -> str:
    by_top: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        top = item["path"].split("/", 1)[0]
        by_top.setdefault(top, []).append(item)

    lines = [
        "# Generated repository map",
        "",
        f"Generated: `{generated_at}`",
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a language-light repository inventory.")
    parser.parse_args()
    config = load_config()
    items = [inspect(path) for path in source_files(config)]
    generated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "schema_version": 1,
        "generated_at": generated_at,
        "repository_root": str(ROOT),
        "files": items,
    }

    inventory_path = ROOT / config["inventory_json"]
    map_path = ROOT / config["repository_map"]
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    map_path.write_text(render_map(items, generated_at), encoding="utf-8")
    print(f"Indexed {len(items)} source files.")
    print(f"Wrote {inventory_path.relative_to(ROOT)}")
    print(f"Wrote {map_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
