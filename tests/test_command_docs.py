"""Tests for command-doc validation behavior during the skill migration."""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).parent.parent
VALIDATOR = str(REPO_ROOT / "agent-validate-command-docs")


class TestCommandDocsValidator(unittest.TestCase):
    def test_validator_succeeds_without_legacy_claude_commands_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            skill_dir = repo / "skills" / "agentkit-todo-codex"
            skill_dir.mkdir(parents=True)
            shutil.copy(
                REPO_ROOT / "skills" / "agentkit-todo-codex" / "SKILL.md",
                skill_dir / "SKILL.md",
            )

            result = subprocess.run(
                [VALIDATOR, str(repo)],
                capture_output=True,
                text=True,
                env=os.environ,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("command docs validation OK", result.stdout)

    def test_validator_fails_when_no_skill_or_legacy_docs_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            result = subprocess.run(
                [VALIDATOR, str(repo)],
                capture_output=True,
                text=True,
                env=os.environ,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("no skill or legacy command markdown found", result.stderr)


if __name__ == "__main__":
    unittest.main()
