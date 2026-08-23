from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import common
import doc_freshness
import documentation_update
import repo_inventory


class StagedDocumentationUpdateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.config = {
            "source_roots": ["service/src"],
            "source_extensions": [".py"],
            "exclude_dirs": [".git", "docs/generated"],
            "inventory_json": "docs/generated/repository-inventory.json",
            "repository_map": "docs/generated/repository-map.md",
            "documentation_impact_report": "docs/generated/documentation-impact.md",
            "freshness_file": "docs/.freshness.json",
            "documentation_relevant_patterns": [r"^service/src/"],
            "documentation_map": [{"source_pattern": r"^service/src/", "docs": ["docs/architecture.md"]}],
        }
        self.patchers = [
            patch.object(common, "ROOT", self.root),
            patch.object(doc_freshness, "ROOT", self.root),
            patch.object(documentation_update, "ROOT", self.root),
            patch.object(repo_inventory, "ROOT", self.root),
        ]
        for patcher in self.patchers:
            patcher.start()

        (self.root / "service" / "src").mkdir(parents=True)
        (self.root / "docs").mkdir()
        self.source = self.root / "service" / "src" / "module.py"
        self.source.write_text("def initial() -> None:\n    pass\n", encoding="utf-8")
        self.git("init")
        self.git("config", "user.email", "tests@example.com")
        self.git("config", "user.name", "Documentation tests")
        self.git("add", ".")
        self.git("commit", "-m", "initial")

    def tearDown(self) -> None:
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.temporary_directory.cleanup()

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout

    def test_staged_generation_is_committed_without_follow_up_changes(self) -> None:
        self.source.write_text("def staged() -> None:\n    pass\n", encoding="utf-8")
        self.git("add", "service/src/module.py")

        self.assertTrue(documentation_update.generate(self.config, staged=True))
        report_path = self.root / "docs" / "generated" / "documentation-impact.md"
        first_report = report_path.read_text(encoding="utf-8")
        self.assertTrue(documentation_update.generate(self.config, staged=True))
        self.assertEqual(first_report, report_path.read_text(encoding="utf-8"))

        staged = self.git("diff", "--cached", "--name-only").splitlines()
        self.assertEqual(
            {
                "docs/.freshness.json",
                "docs/generated/documentation-impact.md",
                "docs/generated/repository-inventory.json",
                "docs/generated/repository-map.md",
                "service/src/module.py",
            },
            set(staged),
        )
        self.git("commit", "-m", "source change with generated documentation")
        self.assertEqual("", self.git("status", "--porcelain"))

    def test_staged_generation_ignores_unstaged_source_content(self) -> None:
        self.source.write_text("def staged() -> None:\n    pass\n", encoding="utf-8")
        self.git("add", "service/src/module.py")
        self.source.write_text("def unstaged() -> None:\n    pass\n", encoding="utf-8")

        documentation_update.generate(self.config, staged=True)

        inventory = json.loads(
            (self.root / "docs" / "generated" / "repository-inventory.json").read_text(encoding="utf-8")
        )
        self.assertEqual("staged", inventory["files"][0]["symbols"][0]["name"])

    def test_no_staged_source_change_does_not_write_or_stage_artifacts(self) -> None:
        self.assertFalse(documentation_update.generate(self.config, staged=True))
        self.assertEqual("", self.git("status", "--porcelain"))
