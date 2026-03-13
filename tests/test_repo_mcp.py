"""Tests for the repo MCP stdio server."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from tests.conftest import make_tmp_repo

REPO_ROOT = pathlib.Path(__file__).parent.parent
AGENTKIT_REPO_MCP = str(REPO_ROOT / "agentkit-repo-mcp")


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


class TestRepoMcpServer(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.repo = make_tmp_repo(self.tmp / "repo")
        self.state_dir = self.tmp / "state"
        self.state_dir.mkdir()
        self.env = {**os.environ, "AGENTKIT_STATE_DIR": str(self.state_dir)}

    def test_describe_flag_returns_service_contract(self):
        result = subprocess.run(
            [sys.executable, AGENTKIT_REPO_MCP, "--describe"],
            capture_output=True,
            text=True,
            check=True,
            env=self.env,
        )
        data = json.loads(result.stdout)
        self.assertEqual(data["name"], "agentkit-repo-mcp")
        self.assertIn("index.inspect", data["owned_capabilities"])

    def test_stdio_lists_expected_tools(self):
        payload = b"".join(
            [
                _frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
                _frame({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
            ]
        )
        result = subprocess.run(
            [sys.executable, AGENTKIT_REPO_MCP],
            input=payload,
            capture_output=True,
            check=True,
            env=self.env,
        )
        messages = _parse_frames(result.stdout)
        tool_names = [tool["name"] for tool in messages[1]["result"]["tools"]]
        self.assertEqual(tool_names, ["index.build", "index.refresh", "index.query", "index.pack", "index.inspect"])

    def test_stdio_can_call_build_and_inspect(self):
        payload = b"".join(
            [
                _frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
                _frame(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {"name": "index.build", "arguments": {"repo": str(self.repo), "mode": "full"}},
                    }
                ),
                _frame(
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {"name": "index.inspect", "arguments": {"repo": str(self.repo)}},
                    }
                ),
            ]
        )
        result = subprocess.run(
            [sys.executable, AGENTKIT_REPO_MCP],
            input=payload,
            capture_output=True,
            check=True,
            env=self.env,
        )
        messages = _parse_frames(result.stdout)
        build = messages[1]["result"]["structuredContent"]
        inspect = messages[2]["result"]["structuredContent"]
        self.assertGreater(build["files_indexed"], 0)
        self.assertEqual(inspect["repo"], str(self.repo))
        self.assertIn("db_path", inspect)
        self.assertGreater(inspect["counts"]["tasks"], 0)

    def test_mcp_build_matches_cli_output(self):
        cli = subprocess.run(
            [sys.executable, str(REPO_ROOT / "agent-index"), "build", "--repo", str(self.repo), "--mode", "full"],
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
                        "params": {"name": "index.build", "arguments": {"repo": str(self.repo), "mode": "full"}},
                    }
                ),
            ]
        )
        result = subprocess.run(
            [sys.executable, AGENTKIT_REPO_MCP],
            input=payload,
            capture_output=True,
            check=True,
            env=self.env,
        )
        mcp_data = _parse_frames(result.stdout)[1]["result"]["structuredContent"]
        self.assertEqual(mcp_data, cli_data)

    def test_mcp_pack_matches_cli_output(self):
        subprocess.run(
            [sys.executable, str(REPO_ROOT / "agent-index"), "build", "--repo", str(self.repo)],
            capture_output=True,
            check=True,
            env=self.env,
        )
        cli = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "agent-index"),
                "pack",
                "--repo",
                str(self.repo),
                "--task",
                "test task one",
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
                            "name": "index.pack",
                            "arguments": {"repo": str(self.repo), "task": "test task one"},
                        },
                    }
                ),
            ]
        )
        result = subprocess.run(
            [sys.executable, AGENTKIT_REPO_MCP],
            input=payload,
            capture_output=True,
            check=True,
            env=self.env,
        )
        mcp_data = _parse_frames(result.stdout)[1]["result"]["structuredContent"]
        self.assertEqual(mcp_data, cli_data)

    def test_mcp_pack_has_no_file_output_side_effect(self):
        out_path = self.tmp / "pack.json"
        subprocess.run(
            [sys.executable, str(REPO_ROOT / "agent-index"), "build", "--repo", str(self.repo)],
            capture_output=True,
            check=True,
            env=self.env,
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
                            "name": "index.pack",
                            "arguments": {
                                "repo": str(self.repo),
                                "task": "test task one",
                                "out": str(out_path),
                            },
                        },
                    }
                ),
            ]
        )
        subprocess.run(
            [sys.executable, AGENTKIT_REPO_MCP],
            input=payload,
            capture_output=True,
            check=True,
            env=self.env,
        )
        self.assertFalse(out_path.exists())


if __name__ == "__main__":
    unittest.main()
