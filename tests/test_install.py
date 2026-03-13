"""Tests for the manifest-managed install flow."""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).parent.parent
AGENT_INSTALL = str(REPO_ROOT / "agent-install")


class TestAgentInstall(unittest.TestCase):
    def test_install_writes_manifest_skills_and_managed_configs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            codex_home = tmp_path / "codex"
            claude_home = tmp_path / "claude"
            xdg_data_home = tmp_path / "data"
            env = {
                **os.environ,
                "CODEX_HOME": str(codex_home),
                "CLAUDE_HOME": str(claude_home),
                "XDG_DATA_HOME": str(xdg_data_home),
            }

            result = subprocess.run(
                [sys.executable, AGENT_INSTALL, "--repo-root", str(REPO_ROOT)],
                capture_output=True,
                text=True,
                check=True,
                env=env,
            )
            data = json.loads(result.stdout)

            manifest_path = xdg_data_home / "agentkit" / "install-manifest.json"
            self.assertEqual(pathlib.Path(data["manifest"]), manifest_path)
            self.assertTrue(manifest_path.exists())

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], 1)
            artifact_types = {artifact["type"] for artifact in manifest["artifacts"]}
            self.assertIn("skill_link", artifact_types)
            self.assertIn("managed_config", artifact_types)

            codex_skill = codex_home / "skills" / "agentkit-todo-codex"
            claude_skill = claude_home / "skills" / "agentkit-todo-claude"
            self.assertTrue(codex_skill.is_symlink())
            self.assertTrue(claude_skill.is_symlink())
            self.assertEqual(codex_skill.resolve(), REPO_ROOT / "skills" / "agentkit-todo-codex")
            self.assertEqual(claude_skill.resolve(), REPO_ROOT / "skills" / "agentkit-todo-claude")

            codex_config = codex_home / "agentkit" / "mcp-servers.json"
            claude_config = claude_home / "agentkit" / "mcp-servers.json"
            self.assertTrue(codex_config.exists())
            self.assertTrue(claude_config.exists())
            codex_payload = json.loads(codex_config.read_text(encoding="utf-8"))
            self.assertIn("agentkit-repo-mcp", codex_payload["mcpServers"])
            self.assertIn("agentkit-telemetry-mcp", codex_payload["mcpServers"])

    def test_legacy_install_shim_records_wrapper_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            codex_home = tmp_path / "codex"
            claude_home = tmp_path / "claude"
            xdg_data_home = tmp_path / "data"
            bin_dir = tmp_path / "bin"
            env = {
                **os.environ,
                "CODEX_HOME": str(codex_home),
                "CLAUDE_HOME": str(claude_home),
                "XDG_DATA_HOME": str(xdg_data_home),
            }

            subprocess.run(
                [str(REPO_ROOT / "agent-install-global-tools"), str(bin_dir)],
                capture_output=True,
                text=True,
                check=True,
                env=env,
            )
            manifest = json.loads((xdg_data_home / "agentkit" / "install-manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(any(artifact["type"] == "legacy_wrapper_link" for artifact in manifest["artifacts"]))
            self.assertTrue((bin_dir / "agentkit").is_symlink())


if __name__ == "__main__":
    unittest.main()
