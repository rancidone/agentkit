"""Tests for the Phase 1 MCP backend split."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from agentkit_mcp import REPO_SERVICE, TELEMETRY_SERVICE, service_definitions

REPO_ROOT = pathlib.Path(__file__).parent.parent
AGENTKIT_REPO_MCP = str(REPO_ROOT / "agentkit-repo-mcp")
AGENTKIT_TELEMETRY_MCP = str(REPO_ROOT / "agentkit-telemetry-mcp")


class TestServiceDefinitions(unittest.TestCase):
    def test_split_is_exactly_two_services(self):
        services = service_definitions()
        self.assertEqual([service.name for service in services], [REPO_SERVICE.name, TELEMETRY_SERVICE.name])

    def test_repo_service_owns_repo_and_index_capabilities(self):
        self.assertIn("index.build", REPO_SERVICE.owned_capabilities)
        self.assertIn("index.pack", REPO_SERVICE.owned_capabilities)
        self.assertIn("config.load", REPO_SERVICE.owned_capabilities)
        self.assertEqual(REPO_SERVICE.backend_module, "agent_index_backend")
        self.assertNotIn("telemetry.ingest", REPO_SERVICE.owned_capabilities)

    def test_telemetry_service_owns_telemetry_and_task_capabilities(self):
        self.assertIn("telemetry.ingest", TELEMETRY_SERVICE.owned_capabilities)
        self.assertIn("task.log_completed", TELEMETRY_SERVICE.owned_capabilities)
        self.assertEqual(TELEMETRY_SERVICE.backend_module, "agent_telemetry_backend")
        self.assertNotIn("index.query", TELEMETRY_SERVICE.owned_capabilities)


class TestServiceEntrypoints(unittest.TestCase):
    def test_repo_entrypoint_describes_repo_service(self):
        result = subprocess.run(
            [sys.executable, AGENTKIT_REPO_MCP],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        self.assertEqual(data["name"], REPO_SERVICE.name)
        self.assertEqual(data["owned_capabilities"], list(REPO_SERVICE.owned_capabilities))

    def test_telemetry_entrypoint_describes_telemetry_service(self):
        result = subprocess.run(
            [sys.executable, AGENTKIT_TELEMETRY_MCP],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        self.assertEqual(data["name"], TELEMETRY_SERVICE.name)
        self.assertEqual(data["owned_capabilities"], list(TELEMETRY_SERVICE.owned_capabilities))


if __name__ == "__main__":
    unittest.main()
