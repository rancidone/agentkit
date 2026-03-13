"""Tests for the telemetry MCP stdio server."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from tests.test_cli_telemetry import make_tmp_telemetry_env
from tests.conftest import make_tmp_repo

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
                "telemetry.ingest",
                "telemetry.report",
                "telemetry.hotspots",
                "telemetry.trend",
                "telemetry.inspect",
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


if __name__ == "__main__":
    unittest.main()
