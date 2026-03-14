"""CLI smoke tests for agent-telemetry ingest and report subcommands."""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from agentkit_common import repo_id
from tests.conftest import make_tmp_repo

REPO_ROOT = pathlib.Path(__file__).parent.parent
AGENT_TELEMETRY = str(REPO_ROOT / "agent-telemetry")
AGENT_TELEMETRY_INGEST = str(REPO_ROOT / "agent-telemetry-ingest")


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


def write_usage_log(root: pathlib.Path, filename: str, repo: pathlib.Path, input_tokens: int) -> None:
    log_dir = root / "projects" / "session"
    log_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "cwd": str(repo),
        "sessionId": "sess-1",
        "conversationId": "conv-1",
        "timestamp": "2026-03-13T12:00:00Z",
        "message": {
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": 5,
            },
            "content": [
                {
                    "type": "tool_use",
                    "name": "Read",
                    "input": {"file_path": str(repo / "main.py"), "offset": 0, "limit": 20},
                }
            ],
        },
    }
    (log_dir / filename).write_text(json.dumps(entry) + "\n", encoding="utf-8")


def write_legacy_telemetry_db(state_dir: pathlib.Path, repo: pathlib.Path) -> pathlib.Path:
    db = state_dir / f"telemetry-{repo_id(str(repo))}.db"
    conn = sqlite3.connect(db)
    conn.execute(
        """
        CREATE TABLE usage_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          repo TEXT NOT NULL,
          session_id TEXT,
          branch TEXT,
          message_uuid TEXT,
          timestamp REAL,
          model TEXT,
          input_tokens INTEGER NOT NULL DEFAULT 0,
          output_tokens INTEGER NOT NULL DEFAULT 0,
          cache_read_tokens INTEGER NOT NULL DEFAULT 0,
          cache_create_tokens INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE tool_calls (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          repo TEXT NOT NULL,
          session_id TEXT,
          message_uuid TEXT,
          timestamp REAL,
          tool_name TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE task_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          repo TEXT NOT NULL,
          task_id TEXT NOT NULL,
          event_type TEXT NOT NULL,
          session_branch TEXT,
          worker_branch TEXT,
          status TEXT,
          timestamp REAL NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()
    return db


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


class TestTelemetryIngestWrapper(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.repo = make_tmp_repo(self.tmp / "repo")
        self.fixtures = make_tmp_telemetry_env(self.tmp, self.repo)
        self.env = {
            **os.environ,
            "AGENTKIT_STATE_DIR": self.fixtures["state_dir"],
        }
        write_usage_log(pathlib.Path(self.fixtures["claude_home"]), "claude.jsonl", self.repo, 11)
        write_usage_log(pathlib.Path(self.fixtures["codex_home"]), "codex.jsonl", self.repo, 22)

    def test_wrapper_auto_detects_codex_and_skips_claude_logs(self):
        env = {
            **self.env,
            "CODEX_CI": "1",
        }
        result = subprocess.run(
            [
                AGENT_TELEMETRY_INGEST,
                str(self.repo),
                self.fixtures["claude_home"],
                self.fixtures["events_file"],
                self.fixtures["codex_home"],
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["usage_events_by_provider"]["claude"], 0)
        self.assertEqual(data["usage_events_by_provider"]["codex"], 1)
        self.assertEqual(data["files_scanned_by_provider"]["claude"], 0)
        self.assertEqual(data["files_scanned_by_provider"]["codex"], 1)

    def test_wrapper_override_can_force_claude_only(self):
        env = {
            **self.env,
            "AGENTKIT_TELEMETRY_SCOPE": "claude",
        }
        result = subprocess.run(
            [
                AGENT_TELEMETRY_INGEST,
                str(self.repo),
                self.fixtures["claude_home"],
                self.fixtures["events_file"],
                self.fixtures["codex_home"],
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["usage_events_by_provider"]["claude"], 1)
        self.assertEqual(data["usage_events_by_provider"]["codex"], 0)


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


class TestAgentTelemetryMigrate(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.repo = make_tmp_repo(self.tmp / "repo")
        self.fixtures = make_tmp_telemetry_env(self.tmp, self.repo)
        self.env = {
            **os.environ,
            "AGENTKIT_STATE_DIR": self.fixtures["state_dir"],
        }
        write_legacy_telemetry_db(pathlib.Path(self.fixtures["state_dir"]), self.repo)
        pathlib.Path(self.fixtures["events_file"]).write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "event_type": "task_started",
                            "timestamp": "2026-03-14T10:00:00Z",
                            "repo": ".",
                            "session_branch": "todo/test",
                            "task_id": "legacy-task",
                            "task_text": "Migrate a legacy telemetry DB",
                        }
                    ),
                    json.dumps(
                        {
                            "event_type": "task_completed",
                            "timestamp": "2026-03-14T10:05:00Z",
                            "repo": ".",
                            "session_branch": "todo/test",
                            "task_id": "legacy-task",
                        }
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def test_report_on_legacy_db_returns_migration_hint(self):
        result = subprocess.run(
            [sys.executable, AGENT_TELEMETRY, "report", "--repo", str(self.repo)],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("legacy telemetry DB", result.stderr)
        self.assertIn("agent-telemetry migrate", result.stderr)

    def test_migrate_upgrades_legacy_db_and_recovers_relative_repo_events(self):
        result = subprocess.run(
            [
                sys.executable,
                AGENT_TELEMETRY,
                "migrate",
                "--repo",
                str(self.repo),
                "--claude-home",
                self.fixtures["claude_home"],
                "--codex-home",
                self.fixtures["codex_home"],
                "--events",
                self.fixtures["events_file"],
            ],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["mode"], "migrate")
        self.assertIn("task_runs", data["legacy_schema_missing_before"])

        report = subprocess.run(
            [sys.executable, AGENT_TELEMETRY, "report", "--repo", str(self.repo)],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(report.returncode, 0, msg=report.stderr)
        report_data = json.loads(report.stdout)
        self.assertEqual(report_data["completed_tasks"], 1)

        inspect = subprocess.run(
            [sys.executable, AGENT_TELEMETRY, "task", "legacy-task", "--repo", str(self.repo)],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(inspect.returncode, 0, msg=inspect.stderr)
        task_data = json.loads(inspect.stdout)
        self.assertEqual(task_data["runs"][0]["task_id"], "legacy-task")


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
