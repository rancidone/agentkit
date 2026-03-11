"""Shared test helpers for agentkit unittest suite."""
from __future__ import annotations

import os
import pathlib
import subprocess
import tempfile

REPO_ROOT = pathlib.Path(__file__).parent.parent


def make_tmp_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    """Create a minimal git repo in a temp directory for CLI smoke tests."""
    subprocess.run(["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    todo = tmp_path / "TODO.md"
    todo.write_text("# TODO\n\n## Phase 1: Test\n\n- [ ] test task one\n")
    src = tmp_path / "main.py"
    src.write_text("def hello():\n    pass\n\ndef world(x: int) -> str:\n    return str(x)\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    return tmp_path
