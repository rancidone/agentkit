"""Fixture-backed tests for the telemetry TUI."""

from __future__ import annotations

import os
import pathlib
import tempfile
import unittest

from agent_telemetry_backend import append_event, ingest_telemetry
from agent_telemetry_tui import TelemetryTui, parse_args
from tests.conftest import make_tmp_repo
from tests.test_cli_telemetry import make_tmp_telemetry_env, write_usage_log


class PromptingTelemetryTui(TelemetryTui):
    def __init__(self, args, prompt_value: str | None):
        super().__init__(args)
        self.prompt_value = prompt_value

    def prompt(self, stdscr, label: str, initial: str) -> str | None:
        return self.prompt_value


class TestTelemetryTui(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.repo = make_tmp_repo(self.tmp / "repo")
        self.fixtures = make_tmp_telemetry_env(self.tmp, self.repo)
        self.previous_state_dir = os.environ.get("AGENTKIT_STATE_DIR")
        os.environ["AGENTKIT_STATE_DIR"] = self.fixtures["state_dir"]

        write_usage_log(pathlib.Path(self.fixtures["codex_home"]), "codex.jsonl", self.repo, 22)
        append_event(
            self.fixtures["events_file"],
            "task_started",
            {
                "repo": str(self.repo),
                "task_id": "phase2-tui-tests",
                "session_branch": "todo/test",
                "task_text": "Build telemetry TUI tests",
                "complexity_points": 3,
            },
        )
        append_event(
            self.fixtures["events_file"],
            "task_completed",
            {
                "repo": str(self.repo),
                "task_id": "phase2-tui-tests",
                "session_branch": "todo/test",
            },
        )
        ingest_telemetry(
            str(self.repo),
            self.fixtures["claude_home"],
            self.fixtures["codex_home"],
            self.fixtures["events_file"],
        )

    def tearDown(self):
        if self.previous_state_dir is None:
            os.environ.pop("AGENTKIT_STATE_DIR", None)
        else:
            os.environ["AGENTKIT_STATE_DIR"] = self.previous_state_dir

    def test_load_snapshot_populates_summary_and_task_rows(self):
        app = TelemetryTui(parse_args(["--repo", str(self.repo)]))
        app.load_snapshot()
        self.assertEqual(app.snapshot["summary"]["completed_tasks"], 1)
        self.assertEqual(app.current_task_rows()[0]["task_id"], "phase2-tui-tests")

    def test_enter_opens_task_detail_from_tasks_tab(self):
        app = TelemetryTui(parse_args(["--repo", str(self.repo)]))
        app.load_snapshot()
        app.tab = 3
        handled = app.handle_key(None, 10)
        self.assertTrue(handled)
        self.assertEqual(app.detail["task_id"], "phase2-tui-tests")

    def test_search_prompt_updates_filter_and_reloads(self):
        app = PromptingTelemetryTui(parse_args(["--repo", str(self.repo)]), "phase2")
        app.load_snapshot()
        app.tab = 3
        handled = app.handle_key(None, ord("/"))
        self.assertTrue(handled)
        self.assertEqual(app.filters.search_text, "phase2")
        self.assertEqual(app.snapshot["task_runs"]["total_runs"], 1)

    def test_window_shortcuts_change_active_window(self):
        app = TelemetryTui(parse_args(["--repo", str(self.repo), "--window-days", "7"]))
        app.load_snapshot()
        handled = app.handle_key(None, ord("]"))
        self.assertTrue(handled)
        self.assertEqual(app.window_days, 30)
