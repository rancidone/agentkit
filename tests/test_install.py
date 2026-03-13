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
AGENT_UNINSTALL = str(REPO_ROOT / "agent-uninstall")


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

    def test_legacy_wrapper_install_requires_explicit_flag(self):
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
                [sys.executable, AGENT_INSTALL, "--repo-root", str(REPO_ROOT), "--legacy-bin-dir", str(bin_dir)],
                capture_output=True,
                text=True,
                check=True,
                env=env,
            )
            manifest = json.loads((xdg_data_home / "agentkit" / "install-manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(any(artifact["type"] == "legacy_wrapper_link" for artifact in manifest["artifacts"]))
            self.assertTrue((bin_dir / "agentkit").is_symlink())

    def test_deprecated_global_tools_shim_no_longer_installs_wrappers(self):
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

            result = subprocess.run(
                [str(REPO_ROOT / "agent-install-global-tools"), str(bin_dir)],
                capture_output=True,
                text=True,
                check=True,
                env=env,
            )
            self.assertIn("no longer the default", result.stderr)
            self.assertFalse((bin_dir / "agentkit").exists())
            manifest = json.loads((xdg_data_home / "agentkit" / "install-manifest.json").read_text(encoding="utf-8"))
            self.assertFalse(any(artifact["type"] == "legacy_wrapper_link" for artifact in manifest["artifacts"]))

    def test_uninstall_removes_managed_artifacts_and_manifest_only(self):
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

            subprocess.run(
                [sys.executable, AGENT_INSTALL, "--repo-root", str(REPO_ROOT)],
                capture_output=True,
                text=True,
                check=True,
                env=env,
            )

            telemetry_db = xdg_data_home / "agentkit" / "telemetry.db"
            telemetry_db.parent.mkdir(parents=True, exist_ok=True)
            telemetry_db.write_text("keep", encoding="utf-8")
            events_file = claude_home / "agent-events.jsonl"
            events_file.parent.mkdir(parents=True, exist_ok=True)
            events_file.write_text("keep\n", encoding="utf-8")
            copied_script = codex_home / "copied-script"
            copied_script.write_text("keep", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, AGENT_UNINSTALL, "--repo-root", str(REPO_ROOT)],
                capture_output=True,
                text=True,
                check=True,
                env=env,
            )
            data = json.loads(result.stdout)

            self.assertTrue(data["manifest_found"])
            self.assertTrue(data["manifest_removed"])
            self.assertFalse((xdg_data_home / "agentkit" / "install-manifest.json").exists())
            self.assertFalse((codex_home / "skills" / "agentkit-todo-codex").exists())
            self.assertFalse((claude_home / "skills" / "agentkit-todo-claude").exists())
            self.assertFalse((codex_home / "agentkit" / "mcp-servers.json").exists())
            self.assertFalse((claude_home / "agentkit" / "mcp-servers.json").exists())
            self.assertTrue(telemetry_db.exists())
            self.assertTrue(events_file.exists())
            self.assertTrue(copied_script.exists())

    def test_uninstall_is_idempotent_when_artifacts_are_missing(self):
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

            subprocess.run(
                [sys.executable, AGENT_INSTALL, "--repo-root", str(REPO_ROOT)],
                capture_output=True,
                text=True,
                check=True,
                env=env,
            )

            subprocess.run(
                [sys.executable, AGENT_UNINSTALL, "--repo-root", str(REPO_ROOT)],
                capture_output=True,
                text=True,
                check=True,
                env=env,
            )

            second = subprocess.run(
                [sys.executable, AGENT_UNINSTALL, "--repo-root", str(REPO_ROOT)],
                capture_output=True,
                text=True,
                check=True,
                env=env,
            )
            data = json.loads(second.stdout)
            self.assertFalse(data["manifest_found"])
            self.assertFalse(data["manifest_removed"])
            self.assertEqual(data["removed"], [])

    def test_uninstall_performs_best_effort_legacy_symlink_cleanup_only_for_repo_owned_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            codex_home = tmp_path / "codex"
            claude_home = tmp_path / "claude"
            xdg_data_home = tmp_path / "data"
            legacy_bin_dir = tmp_path / "bin"
            foreign_root = tmp_path / "foreign"
            foreign_root.mkdir()
            env = {
                **os.environ,
                "CODEX_HOME": str(codex_home),
                "CLAUDE_HOME": str(claude_home),
                "XDG_DATA_HOME": str(xdg_data_home),
            }

            legacy_bin_dir.mkdir()
            (codex_home / "skills").mkdir(parents=True)
            repo_owned = legacy_bin_dir / "agentkit"
            repo_owned.symlink_to(REPO_ROOT / "agentkit")
            foreign_wrapper = legacy_bin_dir / "agent-index"
            foreign_target = foreign_root / "agent-index"
            foreign_target.write_text("foreign", encoding="utf-8")
            foreign_wrapper.symlink_to(foreign_target)
            copied_wrapper = legacy_bin_dir / "agent-log"
            copied_wrapper.write_text("copied", encoding="utf-8")
            legacy_skill = codex_home / "skills" / "agentkit-todo-codex"
            legacy_skill.symlink_to(REPO_ROOT / "skills" / "agentkit-todo-codex")

            result = subprocess.run(
                [
                    sys.executable,
                    AGENT_UNINSTALL,
                    "--repo-root",
                    str(REPO_ROOT),
                    "--legacy-bin-dir",
                    str(legacy_bin_dir),
                ],
                capture_output=True,
                text=True,
                check=True,
                env=env,
            )
            data = json.loads(result.stdout)

            self.assertIn(str(repo_owned), data["legacy_removed"])
            self.assertIn(str(legacy_skill), data["legacy_removed"])
            self.assertFalse(repo_owned.exists())
            self.assertFalse(legacy_skill.exists())
            self.assertTrue(foreign_wrapper.is_symlink())
            self.assertTrue(copied_wrapper.exists())


if __name__ == "__main__":
    unittest.main()
