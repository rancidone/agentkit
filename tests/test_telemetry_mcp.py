"""Tests for the telemetry MCP stdio server."""

from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from tests.test_cli_telemetry import make_tmp_telemetry_env
from tests.conftest import make_tmp_repo
from agentkit_common import repo_id

REPO_ROOT = pathlib.Path(__file__).parent.parent
AGENTKIT_TELEMETRY_MCP = str(REPO_ROOT / "agentkit-telemetry-mcp")


def _frame(payload: dict[str, object]) -> bytes:
    body = json.dumps(payload).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8") + body


def _parse_frames(data: bytes) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    idx = 0
    while idx < len(data):
        header_end = data.index(b"\r\n\r\n", idx)
        header_blob = data[idx:header_end].decode("utf-8")
        headers = {}
        for line in header_blob.split("\r\n"):
            key, _, value = line.partition(":")
            headers[key.strip().lower()] = value.strip()
        length = int(headers["content-length"])
        body_start = header_end + 4
        body_end = body_start + length
        out.append(json.loads(data[body_start:body_end].decode("utf-8")))
        idx = body_end
    return out


class TestTelemetryMcpServer(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.repo = make_tmp_repo(self.tmp / "repo")
        self.fixtures = make_tmp_telemetry_env(self.tmp, self.repo)
        self.env = {**os.environ, "AGENTKIT_STATE_DIR": self.fixtures["state_dir"]}

    def test_describe_flag_returns_service_contract(self):
        result = subprocess.run(
            [sys.executable, AGENTKIT_TELEMETRY_MCP, "--describe"],
            capture_output=True,
            text=True,
            check=True,
            env=self.env,
        )
        data = json.loads(result.stdout)
        self.assertEqual(data["name"], "agentkit-telemetry-mcp")
        self.assertIn("telemetry.inspect", data["owned_capabilities"])

    def test_stdio_lists_expected_tools(self):
        payload = b"".join(
            [
                _frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
                _frame({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
            ]
        )
        result = subprocess.run(
            [sys.executable, AGENTKIT_TELEMETRY_MCP],
            input=payload,
            capture_output=True,
            check=True,
            env=self.env,
        )
        messages = _parse_frames(result.stdout)
        tool_names = [tool["name"] for tool in messages[1]["result"]["tools"]]
        self.assertEqual(
            tool_names,
            [
                "telemetry.migrate",
                "telemetry.ingest",
                "telemetry.report",
                "telemetry.hotspots",
                "telemetry.trend",
                "telemetry.inspect",
                "task.inspect",
                "task.log_started",
                "task.log_completed",
                "task.log_failed",
                "task.log_worker_spawned",
                "task.log_worker_merged",
            ],
        )

    def test_stdio_can_log_and_inspect(self):
        payload = b"".join(
            [
                _frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
                _frame(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "task.log_started",
                            "arguments": {
                                "repo": str(self.repo),
                                "task_id": "phase2-test",
                                "session_branch": "todo/test",
                                "task_text": "Test telemetry MCP logging",
                                "events": self.fixtures["events_file"],
                            },
                        },
                    }
                ),
                _frame(
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {
                            "name": "telemetry.ingest",
                            "arguments": {
                                "repo": str(self.repo),
                                "claude_home": self.fixtures["claude_home"],
                                "codex_home": self.fixtures["codex_home"],
                                "events": self.fixtures["events_file"],
                            },
                        },
                    }
                ),
                _frame(
                    {
                        "jsonrpc": "2.0",
                        "id": 4,
                        "method": "tools/call",
                        "params": {"name": "telemetry.inspect", "arguments": {"repo": str(self.repo)}},
                    }
                ),
            ]
        )
        result = subprocess.run(
            [sys.executable, AGENTKIT_TELEMETRY_MCP],
            input=payload,
            capture_output=True,
            check=True,
            env=self.env,
        )
        messages = _parse_frames(result.stdout)
        logged = messages[1]["result"]["structuredContent"]
        ingest = messages[2]["result"]["structuredContent"]
        inspect = messages[3]["result"]["structuredContent"]
        self.assertEqual(logged["event_type"], "task_started")
        self.assertEqual(ingest["task_events_ingested"], 1)
        self.assertGreaterEqual(inspect["counts"]["task_events"], 1)

    def test_stdio_can_inspect_task_runs(self):
        payload = b"".join(
            [
                _frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
                _frame(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "task.log_started",
                            "arguments": {
                                "repo": str(self.repo),
                                "task_id": "phase2-inspect",
                                "session_branch": "todo/test",
                                "task_text": "Test telemetry MCP inspect",
                                "events": self.fixtures["events_file"],
                            },
                        },
                    }
                ),
                _frame(
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {
                            "name": "task.log_completed",
                            "arguments": {
                                "repo": str(self.repo),
                                "task_id": "phase2-inspect",
                                "session_branch": "todo/test",
                                "events": self.fixtures["events_file"],
                            },
                        },
                    }
                ),
                _frame(
                    {
                        "jsonrpc": "2.0",
                        "id": 4,
                        "method": "tools/call",
                        "params": {
                            "name": "telemetry.ingest",
                            "arguments": {
                                "repo": str(self.repo),
                                "claude_home": self.fixtures["claude_home"],
                                "codex_home": self.fixtures["codex_home"],
                                "events": self.fixtures["events_file"],
                            },
                        },
                    }
                ),
                _frame(
                    {
                        "jsonrpc": "2.0",
                        "id": 5,
                        "method": "tools/call",
                        "params": {
                            "name": "task.inspect",
                            "arguments": {"repo": str(self.repo), "task_id": "phase2-inspect"},
                        },
                    }
                ),
            ]
        )
        result = subprocess.run(
            [sys.executable, AGENTKIT_TELEMETRY_MCP],
            input=payload,
            capture_output=True,
            check=True,
            env=self.env,
        )
        task_data = _parse_frames(result.stdout)[4]["result"]["structuredContent"]
        self.assertEqual(task_data["task_id"], "phase2-inspect")
        self.assertEqual(task_data["run_count"], 1)
        self.assertEqual(task_data["event_count"], 2)
        self.assertEqual(task_data["latest_run"]["task_id"], "phase2-inspect")

    def test_mcp_ingest_matches_cli_output(self):
        cli = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "agent-telemetry"),
                "ingest",
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
            check=True,
            env=self.env,
        )
        cli_data = json.loads(cli.stdout)
        payload = b"".join(
            [
                _frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
                _frame(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "telemetry.ingest",
                            "arguments": {
                                "repo": str(self.repo),
                                "claude_home": self.fixtures["claude_home"],
                                "codex_home": self.fixtures["codex_home"],
                                "events": self.fixtures["events_file"],
                            },
                        },
                    }
                ),
            ]
        )
        result = subprocess.run(
            [sys.executable, AGENTKIT_TELEMETRY_MCP],
            input=payload,
            capture_output=True,
            check=True,
            env=self.env,
        )
        mcp_data = _parse_frames(result.stdout)[1]["result"]["structuredContent"]
        self.assertEqual(mcp_data, cli_data)

    def test_mcp_migrate_upgrades_legacy_db(self):
        db = pathlib.Path(self.fixtures["state_dir"]) / f"telemetry-{repo_id(str(self.repo))}.db"
        conn = sqlite3.connect(db)
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
        conn.commit()
        conn.close()
        pathlib.Path(self.fixtures["events_file"]).write_text(
            json.dumps(
                {
                    "event_type": "task_completed",
                    "timestamp": "2026-03-14T10:05:00Z",
                    "repo": ".",
                    "session_branch": "todo/test",
                    "task_id": "legacy-mcp",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        payload = b"".join(
            [
                _frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
                _frame(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "telemetry.migrate",
                            "arguments": {
                                "repo": str(self.repo),
                                "claude_home": self.fixtures["claude_home"],
                                "codex_home": self.fixtures["codex_home"],
                                "events": self.fixtures["events_file"],
                            },
                        },
                    }
                ),
                _frame(
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {"name": "telemetry.report", "arguments": {"repo": str(self.repo)}},
                    }
                ),
            ]
        )
        result = subprocess.run(
            [sys.executable, AGENTKIT_TELEMETRY_MCP],
            input=payload,
            capture_output=True,
            check=True,
            env=self.env,
        )
        messages = _parse_frames(result.stdout)
        migrate = messages[1]["result"]["structuredContent"]
        report = messages[2]["result"]["structuredContent"]
        self.assertEqual(migrate["mode"], "migrate")
        self.assertEqual(report["completed_tasks"], 1)

    def test_mcp_report_matches_cli_output(self):
        subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "agent-telemetry"),
                "ingest",
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
            check=True,
            env=self.env,
        )
        cli = subprocess.run(
            [sys.executable, str(REPO_ROOT / "agent-telemetry"), "report", "--repo", str(self.repo)],
            capture_output=True,
            text=True,
            check=True,
            env=self.env,
        )
        cli_data = json.loads(cli.stdout)
        payload = b"".join(
            [
                _frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
                _frame(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {"name": "telemetry.report", "arguments": {"repo": str(self.repo)}},
                    }
                ),
            ]
        )
        result = subprocess.run(
            [sys.executable, AGENTKIT_TELEMETRY_MCP],
            input=payload,
            capture_output=True,
            check=True,
            env=self.env,
        )
        mcp_data = _parse_frames(result.stdout)[1]["result"]["structuredContent"]
        self.assertEqual(mcp_data, cli_data)


if __name__ == "__main__":
    unittest.main()
