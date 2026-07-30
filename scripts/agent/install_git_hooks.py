from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

from common import ROOT, git_available


def main() -> int:
    if not git_available():
        print("Not inside a Git repository.")
        return 1
    hooks_dir = ROOT / "githooks"
    for path in hooks_dir.iterdir():
        if path.is_file() and not path.suffix:
            path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    result = subprocess.run(
        ["git", "config", "core.hooksPath", "githooks"],
        cwd=ROOT,
        text=True,
    )
    if result.returncode != 0:
        return result.returncode
    print("Configured Git hooks path: githooks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
