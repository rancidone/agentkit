"""Tests for shared MCP-backed skill workflow documentation."""
from __future__ import annotations

import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).parent.parent


class TestSkillWorkflowDocs(unittest.TestCase):
    def test_shared_workflow_reference_lists_core_mcp_tools(self):
        text = (REPO_ROOT / "skills" / "shared" / "agentkit_todo_mcp_workflow.md").read_text(encoding="utf-8")
        for token in (
            "index.refresh",
            "index.pack",
            "config.load",
            "telemetry.ingest",
            "telemetry.report",
            "telemetry.hotspots",
            "task.log_started",
            "task.log_completed",
            "task.inspect",
        ):
            self.assertIn(token, text)

    def test_shared_workflow_preserves_tasks_first_dogfooding_semantics(self):
        text = (REPO_ROOT / "skills" / "shared" / "agentkit_todo_mcp_workflow.md").read_text(encoding="utf-8")
        for expected in (
            "Tasks-first remains the default execution mode",
            "Task lifecycle logging remains available for repo self-use",
            "Index refresh and telemetry refresh/report steps remain part of the repo's own TODO execution flow",
            "write or update the relevant automated test first",
            "Do not emit worker lifecycle events in tasks-first mode",
            "task.log_failed",
            "task.log_completed",
            "telemetry.report",
            "telemetry.hotspots",
        ):
            self.assertIn(expected, text)

    def test_start_todo_spec_keeps_repo_self_dogfooding_rollout_requirements(self):
        text = (REPO_ROOT / "skills" / "shared" / "agentkit_todo_mcp_workflow.md").read_text(encoding="utf-8")
        for expected in (
            "`start-todo` must operate against this repository's own `TODO.md`",
            "The repo-local event log remains `.claude/agent-events.jsonl` during rollout",
            "The session branch remains a `todo/*` branch",
            "The flow must stay capable of implementing this repository's own TODO items end to end throughout rollout",
        ):
            self.assertIn(expected, text)

    def test_client_skills_reference_shared_mcp_workflow(self):
        for skill_name in ("agentkit-todo-codex", "agentkit-todo-claude"):
            text = (REPO_ROOT / "skills" / skill_name / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("../shared/agentkit_todo_mcp_workflow.md", text)
            self.assertIn("Prefer MCP tools", text)

    def test_codex_skill_no_longer_relies_on_wrapper_based_index_or_telemetry_steps(self):
        text = (REPO_ROOT / "skills" / "agentkit-todo-codex" / "SKILL.md").read_text(encoding="utf-8")
        for legacy in (
            "agent-index-refresh-full",
            "agent-index-refresh-light",
            "agent-telemetry-report",
            "agent-index pack",
            "agent-log-task-started",
            "agent-log-task-complete",
        ):
            self.assertNotIn(legacy, text)


if __name__ == "__main__":
    unittest.main()
