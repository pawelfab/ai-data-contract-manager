from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

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
    return subprocess.run(
        ["git", *args],
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


def index_files() -> list[str]:
    """Return paths represented by the Git index, excluding unstaged files."""

    if not git_available():
        raise RuntimeError("A staged snapshot requires a Git repository.")
    result = run_git(["ls-files", "--cached"])
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Unable to list index files.")
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


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


def is_excluded_relative(path: str, config: dict[str, Any]) -> bool:
    normalized_path = PurePosixPath(path).as_posix().strip("/")
    parts = set(PurePosixPath(normalized_path).parts)
    for item in config.get("exclude_dirs", []):
        normalized_item = PurePosixPath(item).as_posix().strip("/")
        if "/" in normalized_item:
            if normalized_item in normalized_path:
                return True
        elif normalized_item in parts:
            return True
    return False


def configured_source_paths(config: dict[str, Any], candidates: Iterable[str]) -> list[str]:
    """Filter repository-relative paths using the configured source inventory rules."""

    extensions = {item.lower() for item in config.get("source_extensions", [])}
    roots = [PurePosixPath(item).as_posix().strip("/") for item in config.get("source_roots", [])]
    result: list[str] = []
    for candidate in candidates:
        relative = PurePosixPath(candidate).as_posix().strip("/")
        if is_excluded_relative(relative, config):
            continue
        if extensions and PurePosixPath(relative).suffix.lower() not in extensions:
            continue
        if roots and not any(relative == root or relative.startswith(f"{root}/") for root in roots):
            continue
        result.append(relative)
    return sorted(set(result))


def source_files(config: dict[str, Any]) -> list[Path]:
    candidates = [rel(path) for path in git_files() if path.exists() and path.is_file()]
    return [ROOT / path for path in configured_source_paths(config, candidates)]


def staged_source_paths(config: dict[str, Any]) -> list[str]:
    """Return configured source paths from the staged Git index."""

    return configured_source_paths(config, index_files())


def read_staged_file(path: str) -> bytes:
    """Read one file from the Git index, never from the working tree."""

    if not git_available():
        raise RuntimeError("A staged snapshot requires a Git repository.")
    result = subprocess.run(
        ["git", "show", f":{path}"],
        cwd=ROOT,
        capture_output=True,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(detail or f"Unable to read {path} from the Git index.")
    return result.stdout


def current_source_hashes(config: dict[str, Any]) -> dict[str, str]:
    return {rel(path): sha256_file(path) for path in source_files(config)}


def staged_source_hashes(config: dict[str, Any]) -> dict[str, str]:
    return {
        path: hashlib.sha256(read_staged_file(path)).hexdigest()
        for path in staged_source_paths(config)
    }


def source_snapshot_id(source_hashes: dict[str, str]) -> str:
    canonical = "".join(f"{path}\0{digest}\n" for path, digest in sorted(source_hashes.items()))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def documentation_relevant(path: str, config: dict[str, Any]) -> bool:
    patterns = config.get("documentation_relevant_patterns", [])
    return any(re.search(pattern, path, flags=re.IGNORECASE) for pattern in patterns)


def staged_files() -> list[str]:
    if not git_available():
        return []
    result = run_git(["diff", "--cached", "--name-only", "--diff-filter=ACMRD"])
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def architecture_dir(config: dict[str, Any]) -> Path:
    return ROOT / config["architecture_docs_dir"]


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
