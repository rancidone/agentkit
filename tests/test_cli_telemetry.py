"""CLI smoke tests for agent-telemetry ingest and report subcommands."""
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
AGENT_TELEMETRY = str(REPO_ROOT / "agent-telemetry")


def make_tmp_telemetry_env(tmp: pathlib.Path, repo: pathlib.Path) -> dict[str, str]:
    """Create minimal fixture dirs and files for telemetry ingest."""
    state_dir = tmp / "state"
    state_dir.mkdir()
    claude_home = tmp / "claude_home"
    claude_home.mkdir()
    codex_home = tmp / "codex_home"
    codex_home.mkdir()
    events_file = tmp / "agent-events.jsonl"
    events_file.write_text("")
    return {
        "state_dir": str(state_dir),
        "claude_home": str(claude_home),
        "codex_home": str(codex_home),
        "events_file": str(events_file),
    }


class TestAgentTelemetryIngest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.repo = make_tmp_repo(self.tmp / "repo")
        self.fixtures = make_tmp_telemetry_env(self.tmp, self.repo)
        self.env = {
            **os.environ,
            "AGENTKIT_STATE_DIR": self.fixtures["state_dir"],
        }

    def test_ingest_exits_zero(self):
        result = subprocess.run(
            [
                sys.executable, AGENT_TELEMETRY, "ingest",
                "--repo", str(self.repo),
                "--claude-home", self.fixtures["claude_home"],
                "--codex-home", self.fixtures["codex_home"],
                "--events", self.fixtures["events_file"],
            ],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_ingest_outputs_json(self):
        result = subprocess.run(
            [
                sys.executable, AGENT_TELEMETRY, "ingest",
                "--repo", str(self.repo),
                "--claude-home", self.fixtures["claude_home"],
                "--codex-home", self.fixtures["codex_home"],
                "--events", self.fixtures["events_file"],
            ],
            capture_output=True,
            text=True,
            env=self.env,
        )
        data = json.loads(result.stdout)
        self.assertIsInstance(data, dict)

    def test_ingest_output_has_expected_keys(self):
        result = subprocess.run(
            [
                sys.executable, AGENT_TELEMETRY, "ingest",
                "--repo", str(self.repo),
                "--claude-home", self.fixtures["claude_home"],
                "--codex-home", self.fixtures["codex_home"],
                "--events", self.fixtures["events_file"],
            ],
            capture_output=True,
            text=True,
            env=self.env,
        )
        data = json.loads(result.stdout)
        self.assertIn("repo", data)
        self.assertIn("usage_events_ingested", data)
        self.assertIn("task_events_ingested", data)

    def test_ingest_incremental_flag(self):
        result = subprocess.run(
            [
                sys.executable, AGENT_TELEMETRY, "ingest",
                "--repo", str(self.repo),
                "--claude-home", self.fixtures["claude_home"],
                "--codex-home", self.fixtures["codex_home"],
                "--events", self.fixtures["events_file"],
            ],
            capture_output=True,
            text=True,
            env=self.env,
        )
        data = json.loads(result.stdout)
        self.assertTrue(data.get("incremental"))


class TestAgentTelemetryReport(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.repo = make_tmp_repo(self.tmp / "repo")
        self.fixtures = make_tmp_telemetry_env(self.tmp, self.repo)
        self.env = {
            **os.environ,
            "AGENTKIT_STATE_DIR": self.fixtures["state_dir"],
        }
        # Ingest first so the DB exists
        subprocess.run(
            [
                sys.executable, AGENT_TELEMETRY, "ingest",
                "--repo", str(self.repo),
                "--claude-home", self.fixtures["claude_home"],
                "--codex-home", self.fixtures["codex_home"],
                "--events", self.fixtures["events_file"],
            ],
            capture_output=True,
            env=self.env,
            check=True,
        )

    def test_report_exits_zero(self):
        result = subprocess.run(
            [
                sys.executable, AGENT_TELEMETRY, "report",
                "--repo", str(self.repo),
            ],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_report_produces_output(self):
        result = subprocess.run(
            [
                sys.executable, AGENT_TELEMETRY, "report",
                "--repo", str(self.repo),
            ],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertTrue(len(result.stdout) > 0)

    def test_report_output_is_valid_json(self):
        result = subprocess.run(
            [
                sys.executable, AGENT_TELEMETRY, "report",
                "--repo", str(self.repo),
            ],
            capture_output=True,
            text=True,
            env=self.env,
        )
        data = json.loads(result.stdout)
        self.assertIsInstance(data, dict)

    def test_report_output_has_repo_key(self):
        result = subprocess.run(
            [
                sys.executable, AGENT_TELEMETRY, "report",
                "--repo", str(self.repo),
            ],
            capture_output=True,
            text=True,
            env=self.env,
        )
        data = json.loads(result.stdout)
        self.assertIn("repo", data)


class TestAgentTelemetryTrend(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.repo = make_tmp_repo(self.tmp / "repo")
        self.fixtures = make_tmp_telemetry_env(self.tmp, self.repo)
        self.env = {
            **os.environ,
            "AGENTKIT_STATE_DIR": self.fixtures["state_dir"],
        }
        # Ingest first so the DB exists
        subprocess.run(
            [
                sys.executable, AGENT_TELEMETRY, "ingest",
                "--repo", str(self.repo),
                "--claude-home", self.fixtures["claude_home"],
                "--codex-home", self.fixtures["codex_home"],
                "--events", self.fixtures["events_file"],
            ],
            capture_output=True,
            env=self.env,
            check=True,
        )

    def test_trend_exits_zero(self):
        result = subprocess.run(
            [sys.executable, AGENT_TELEMETRY, "trend", "--repo", str(self.repo)],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_trend_output_is_valid_json(self):
        result = subprocess.run(
            [sys.executable, AGENT_TELEMETRY, "trend", "--repo", str(self.repo)],
            capture_output=True,
            text=True,
            env=self.env,
        )
        data = json.loads(result.stdout)
        self.assertIsInstance(data, dict)

    def test_trend_output_has_days_key(self):
        result = subprocess.run(
            [sys.executable, AGENT_TELEMETRY, "trend", "--repo", str(self.repo)],
            capture_output=True,
            text=True,
            env=self.env,
        )
        data = json.loads(result.stdout)
        self.assertIn("days", data)
        self.assertIsInstance(data["days"], list)

    def test_trend_with_window_days(self):
        result = subprocess.run(
            [sys.executable, AGENT_TELEMETRY, "trend", "--repo", str(self.repo), "--window-days", "30"],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(result.returncode, 0)

    def test_trend_with_since_flag(self):
        result = subprocess.run(
            [sys.executable, AGENT_TELEMETRY, "trend", "--repo", str(self.repo), "--since", "2026-01-01"],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data.get("since"), "2026-01-01")

    def test_trend_invalid_since(self):
        result = subprocess.run(
            [sys.executable, AGENT_TELEMETRY, "trend", "--repo", str(self.repo), "--since", "not-a-date"],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertNotEqual(result.returncode, 0)


class TestReportVelocitySummary(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.repo = make_tmp_repo(self.tmp / "repo")
        self.fixtures = make_tmp_telemetry_env(self.tmp, self.repo)
        self.env = {
            **os.environ,
            "AGENTKIT_STATE_DIR": self.fixtures["state_dir"],
        }
        subprocess.run(
            [
                sys.executable, AGENT_TELEMETRY, "ingest",
                "--repo", str(self.repo),
                "--claude-home", self.fixtures["claude_home"],
                "--codex-home", self.fixtures["codex_home"],
                "--events", self.fixtures["events_file"],
            ],
            capture_output=True,
            env=self.env,
            check=True,
        )

    def test_report_has_velocity_summary(self):
        result = subprocess.run(
            [sys.executable, AGENT_TELEMETRY, "report", "--repo", str(self.repo)],
            capture_output=True,
            text=True,
            env=self.env,
        )
        data = json.loads(result.stdout)
        self.assertIn("velocity_summary", data)

    def test_velocity_summary_has_expected_keys(self):
        result = subprocess.run(
            [sys.executable, AGENT_TELEMETRY, "report", "--repo", str(self.repo)],
            capture_output=True,
            text=True,
            env=self.env,
        )
        data = json.loads(result.stdout)
        vs = data["velocity_summary"]
        self.assertIn("tasks_in_window", vs)
        self.assertIn("total_tokens", vs)
        self.assertIn("trend_direction", vs)

    def test_report_since_flag(self):
        result = subprocess.run(
            [
                sys.executable, AGENT_TELEMETRY, "report",
                "--repo", str(self.repo),
                "--since", "2026-01-01",
            ],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data.get("since"), "2026-01-01")


if __name__ == "__main__":
    unittest.main()
