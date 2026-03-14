"""Tests for repo-local MCP dogfood config examples."""
from __future__ import annotations

import json
import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).parent.parent


class TestRepoLocalDevConfigs(unittest.TestCase):
    def test_repo_local_mcp_examples_define_both_services_and_repo_state_dir(self):
        for name in (
            "codex-mcp-servers.repo-local.example.json",
            "claude-mcp-servers.repo-local.example.json",
        ):
            payload = json.loads((REPO_ROOT / "examples" / name).read_text(encoding="utf-8"))
            self.assertEqual(
                set(payload["mcpServers"]),
                {"agentkit-repo-mcp", "agentkit-telemetry-mcp"},
            )
            for server in payload["mcpServers"].values():
                self.assertEqual(server["transport"], "stdio")
                self.assertEqual(server["args"], [])
                self.assertEqual(server["env"]["AGENTKIT_STATE_DIR"], "__REPO_ROOT__/.agentkit/state")
                self.assertTrue(server["command"].startswith("__REPO_ROOT__/agentkit-"))

    def test_repo_local_state_dir_is_gitignored_but_kept_present(self):
        text = (REPO_ROOT / ".agentkit" / ".gitignore").read_text(encoding="utf-8")
        self.assertEqual(text.strip().splitlines(), ["*", "!.gitignore"])

    def test_docs_present_skills_first_and_fallback_path(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("Repo-Local Skills-First Dogfooding", readme)
        self.assertIn("Local Helper Fallbacks", readme)
        self.assertIn("agentkit-todo-codex start-todo", readme)
        self.assertIn("Skills-First Workflow", claude)
        self.assertIn("Local Helper Commands", claude)

    def test_docs_record_hard_switch_and_no_supported_legacy_wrapper_install(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("hard switch is now complete", readme)
        self.assertIn("hard switch is complete", claude)
        self.assertNotIn("./agent-install --legacy-bin-dir", readme)


if __name__ == "__main__":
    unittest.main()
