from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from common import LOCAL_CONFIG, DEFAULT_CONFIG, ROOT


def run(command: list[str]) -> int:
    print("+ " + " ".join(command))
    return subprocess.run(command, cwd=ROOT).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize and validate the repository agent workflow.")
    parser.add_argument("--install-hooks", action="store_true", help="Configure Git to use the included githooks directory.")
    parser.add_argument("--mark-initial-current", action="store_true", help="Mark initial documentation current after you have verified it.")
    args = parser.parse_args()

    if not LOCAL_CONFIG.exists():
        LOCAL_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DEFAULT_CONFIG, LOCAL_CONFIG)
        print(f"Created {LOCAL_CONFIG.relative_to(ROOT)} from config.example.json")
    else:
        print(f"Using existing {LOCAL_CONFIG.relative_to(ROOT)}")

    if run([sys.executable, "scripts/agent/validate_setup.py"]) != 0:
        return 1
    if run([sys.executable, "scripts/agent/repo_inventory.py"]) != 0:
        return 1
    if args.install_hooks and run([sys.executable, "scripts/agent/install_git_hooks.py"]) != 0:
        return 1
    if args.mark_initial_current:
        return run([
            sys.executable,
            "scripts/agent/doc_freshness.py",
            "--mark-current",
            "--reason",
            "initial repository documentation verified",
        ])

    print("Setup complete. Bootstrap or verify docs before marking them current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
