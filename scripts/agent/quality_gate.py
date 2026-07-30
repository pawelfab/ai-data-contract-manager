from __future__ import annotations

import argparse
import subprocess
from typing import Any

from common import ROOT, load_config


def run_stages(stages: list[str], config: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    results: list[dict[str, Any]] = []
    all_ok = True
    commands_by_stage = config.get("quality_commands", {})
    for stage in stages:
        commands = commands_by_stage.get(stage, [])
        for command in commands:
            print(f"[{stage}] {command}", flush=True)
            completed = subprocess.run(command, cwd=ROOT, shell=True, text=True)
            ok = completed.returncode == 0
            results.append({"stage": stage, "command": command, "returncode": completed.returncode})
            all_ok = all_ok and ok
            if not ok:
                print(f"FAILED: {command}")
    return all_ok, results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run configured repository quality commands.")
    parser.add_argument("--stage", action="append", dest="stages", help="Stage name; may be repeated.")
    parser.add_argument("--profile", choices=["pre-commit", "pre-push", "stop"])
    args = parser.parse_args()

    config = load_config()
    stages = args.stages or []
    if args.profile:
        key = args.profile.replace("-", "_") + "_quality_stages"
        stages.extend(config.get(key, []))
    stages = list(dict.fromkeys(stages))
    if not stages:
        print("No quality stages configured.")
        return 0
    ok, _ = run_stages(stages, config)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
