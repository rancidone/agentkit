"""CLI smoke tests for agent-index build and pack subcommands."""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from tests.conftest import make_tmp_repo

REPO_ROOT = pathlib.Path(__file__).parent.parent
AGENT_INDEX = str(REPO_ROOT / "agent-index")


class TestAgentIndexBuild(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.repo = make_tmp_repo(self.tmp)
        self.state_dir = pathlib.Path(tempfile.mkdtemp())
        self.env = {**os.environ, "AGENTKIT_STATE_DIR": str(self.state_dir)}

    def test_build_exits_zero(self):
        result = subprocess.run(
            [sys.executable, AGENT_INDEX, "build", "--repo", str(self.repo)],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_build_outputs_json(self):
        result = subprocess.run(
            [sys.executable, AGENT_INDEX, "build", "--repo", str(self.repo)],
            capture_output=True,
            text=True,
            env=self.env,
        )
        data = json.loads(result.stdout)
        self.assertIn("files_indexed", data)
        self.assertIn("tasks_indexed", data)

    def test_build_indexes_files(self):
        result = subprocess.run(
            [sys.executable, AGENT_INDEX, "build", "--repo", str(self.repo)],
            capture_output=True,
            text=True,
            env=self.env,
        )
        data = json.loads(result.stdout)
        self.assertGreater(data["files_indexed"], 0)

    def test_build_indexes_tasks(self):
        result = subprocess.run(
            [sys.executable, AGENT_INDEX, "build", "--repo", str(self.repo)],
            capture_output=True,
            text=True,
            env=self.env,
        )
        data = json.loads(result.stdout)
        self.assertGreater(data["tasks_indexed"], 0)


class TestAgentIndexPack(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.repo = make_tmp_repo(self.tmp)
        self.state_dir = pathlib.Path(tempfile.mkdtemp())
        self.env = {**os.environ, "AGENTKIT_STATE_DIR": str(self.state_dir)}
        self.out_file = str(self.state_dir / "pack.json")
        # Build index first
        subprocess.run(
            [sys.executable, AGENT_INDEX, "build", "--repo", str(self.repo)],
            capture_output=True,
            env=self.env,
            check=True,
        )

    def test_pack_exits_zero(self):
        result = subprocess.run(
            [
                sys.executable, AGENT_INDEX, "pack",
                "--repo", str(self.repo),
                "--task", "test task one",
                "--out", self.out_file,
            ],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_pack_creates_output_file(self):
        subprocess.run(
            [
                sys.executable, AGENT_INDEX, "pack",
                "--repo", str(self.repo),
                "--task", "test task one",
                "--out", self.out_file,
            ],
            capture_output=True,
            env=self.env,
            check=True,
        )
        self.assertTrue(os.path.exists(self.out_file))

    def test_pack_output_is_valid_json(self):
        subprocess.run(
            [
                sys.executable, AGENT_INDEX, "pack",
                "--repo", str(self.repo),
                "--task", "test task one",
                "--out", self.out_file,
            ],
            capture_output=True,
            env=self.env,
            check=True,
        )
        with open(self.out_file) as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)

    def test_pack_output_has_files_key(self):
        subprocess.run(
            [
                sys.executable, AGENT_INDEX, "pack",
                "--repo", str(self.repo),
                "--task", "test task one",
                "--out", self.out_file,
            ],
            capture_output=True,
            env=self.env,
            check=True,
        )
        with open(self.out_file) as f:
            data = json.load(f)
        self.assertIn("selected_files", data)


if __name__ == "__main__":
    unittest.main()
