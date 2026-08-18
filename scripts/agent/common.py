from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "scripts" / "agent" / "config.example.json"
LOCAL_CONFIG = ROOT / "scripts" / "agent" / "config.json"


def load_config() -> dict[str, Any]:
    path = LOCAL_CONFIG if LOCAL_CONFIG.exists() else DEFAULT_CONFIG
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def run_git(args: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    safe_root = ROOT.resolve().as_posix()
    return subprocess.run(
        ["git", "-c", f"safe.directory={safe_root}", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def git_available() -> bool:
    result = run_git(["rev-parse", "--is-inside-work-tree"])
    return result.returncode == 0 and result.stdout.strip() == "true"


def git_files() -> list[Path]:
    if not git_available():
        return [p for p in ROOT.rglob("*") if p.is_file()]
    result = run_git(["ls-files", "-co", "--exclude-standard"])
    return [ROOT / line for line in result.stdout.splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_excluded(path: Path, config: dict[str, Any]) -> bool:
    parts = set(path.parts)
    for item in config.get("exclude_dirs", []):
        normalized = Path(item).as_posix().strip("/")
        if "/" in normalized:
            try:
                if normalized in rel(path):
                    return True
            except ValueError:
                return True
        elif normalized in parts:
            return True
    return False


def source_files(config: dict[str, Any]) -> list[Path]:
    extensions = {x.lower() for x in config.get("source_extensions", [])}
    roots = [ROOT / x for x in config.get("source_roots", [])]
    active_roots = [p.resolve() for p in roots if p.exists()]
    if not active_roots:
        raise RuntimeError("None of the configured source_roots exists")
    result: list[Path] = []
    for path in git_files():
        if not path.exists() or not path.is_file() or is_excluded(path, config):
            continue
        if extensions and path.suffix.lower() not in extensions:
            continue
        resolved = path.resolve()
        if active_roots and not any(resolved == root or root in resolved.parents for root in active_roots):
            continue
        result.append(path)
    return sorted(set(result), key=rel)


def current_source_hashes(config: dict[str, Any]) -> dict[str, str]:
    return {rel(path): sha256_file(path) for path in source_files(config)}


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, path, flags=re.IGNORECASE) for pattern in patterns)


def documentation_relevant(path: str, config: dict[str, Any]) -> bool:
    return matches_any(path, config.get("documentation_relevant_patterns", []))


def architecture_doc_files(config: dict[str, Any]) -> list[Path]:
    base = ROOT / config["architecture_docs_dir"]
    if not base.exists():
        return []
    include = config.get("documentation_evidence_patterns", [r"\.md$"])
    exclude = config.get("documentation_non_evidence_patterns", [])
    result: list[Path] = []
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        relative = rel(path)
        if matches_any(relative, include) and not matches_any(relative, exclude):
            result.append(path)
    return sorted(result, key=rel)


def current_architecture_doc_hashes(config: dict[str, Any]) -> dict[str, str]:
    return {rel(path): sha256_file(path) for path in architecture_doc_files(config)}


def hash_delta(previous: dict[str, str], current: dict[str, str]) -> dict[str, list[str]]:
    added = sorted(set(current) - set(previous))
    deleted = sorted(set(previous) - set(current))
    modified = sorted(path for path in set(current) & set(previous) if current[path] != previous[path])
    return {
        "added": added,
        "deleted": deleted,
        "modified": modified,
        "changed": sorted(set(added + deleted + modified)),
    }


def staged_files() -> list[str]:
    if not git_available():
        return []
    result = run_git(["diff", "--cached", "--name-only", "--diff-filter=ACMRD"])
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def working_tree_changed_files() -> list[str]:
    if not git_available():
        return []
    result = run_git(["status", "--porcelain=v1", "--untracked-files=all"])
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        raw = line[3:]
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        paths.append(raw.strip().strip('"').replace("\\", "/"))
    return sorted(set(path for path in paths if path))


def architecture_dir(config: dict[str, Any]) -> Path:
    return ROOT / config["architecture_docs_dir"]


def session_state_path(config: dict[str, Any], session_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id or "unknown")
    return ROOT / config.get("session_state_dir", ".agent-state") / f"session-{safe}.json"


def json_print(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def read_stdin_json() -> dict[str, Any]:
    try:
        raw = os.sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def hook_output(
    *,
    continue_: bool = True,
    system_message: str | None = None,
    stop_reason: str | None = None,
    specific: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {"continue": continue_}
    if system_message:
        payload["systemMessage"] = system_message
    if stop_reason:
        payload["stopReason"] = stop_reason
    if specific:
        payload["hookSpecificOutput"] = specific
    json_print(payload)
