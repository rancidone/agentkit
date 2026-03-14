"""Terminal UI for exploring repo telemetry."""

from __future__ import annotations

import argparse
import curses
import os
from dataclasses import dataclass
from typing import Any

from agent_telemetry_backend import tui_snapshot, tui_task_detail
from agentkit_common import repo_root


WINDOW_CHOICES = [1, 7, 30, 90]
TABS = ["Summary", "Trends", "Hotspots", "Tasks"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Explore repo telemetry in a terminal UI.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--window-days", type=int, default=7)
    parser.add_argument("--since", default=None)
    parser.add_argument("--task-limit", type=int, default=50)
    parser.add_argument("--hotspot-limit", type=int, default=12)
    return parser.parse_args(argv)


@dataclass
class Filters:
    provider: str | None = None
    task_outcome: str | None = None
    search_text: str | None = None


class TelemetryTui:
    def __init__(self, args: argparse.Namespace):
        self.repo = repo_root(args.repo)
        self.window_days = args.window_days
        self.since = args.since
        self.task_limit = args.task_limit
        self.hotspot_limit = args.hotspot_limit
        self.filters = Filters()
        self.tab = 0
        self.selected_row = 0
        self.snapshot: dict[str, Any] | None = None
        self.detail: dict[str, Any] | None = None
        self.status = ""
        self.error = ""

    def ensure_state_dir(self) -> None:
        if "AGENTKIT_STATE_DIR" in os.environ:
            return
        repo_state = os.path.join(self.repo, ".agentkit", "state")
        if os.path.isdir(repo_state):
            os.environ["AGENTKIT_STATE_DIR"] = repo_state

    def load_snapshot(self) -> None:
        self.ensure_state_dir()
        self.snapshot = tui_snapshot(
            self.repo,
            self.window_days,
            self.since,
            hotspot_limit=self.hotspot_limit,
            task_limit=self.task_limit,
            provider=self.filters.provider,
            task_outcome=self.filters.task_outcome,
            search_text=self.filters.search_text,
        )
        self.selected_row = 0
        self.status = f"Loaded telemetry for {self.repo}"
        self.error = ""

    def load_detail(self, task_id: str) -> None:
        self.ensure_state_dir()
        self.detail = tui_task_detail(self.repo, task_id)
        self.status = f"Opened task detail for {task_id}"
        self.error = ""

    def run(self, stdscr: Any) -> None:
        curses.curs_set(0)
        stdscr.keypad(True)
        self.load_snapshot()
        while True:
            self.draw(stdscr)
            ch = stdscr.getch()
            if not self.handle_key(stdscr, ch):
                break

    def handle_key(self, stdscr: Any, ch: int) -> bool:
        if ch in (ord("q"), ord("Q")):
            return False
        if ch == -1:
            return True

        if self.detail is not None:
            if ch in (27, curses.KEY_EXIT, curses.KEY_BACKSPACE):
                self.detail = None
                self.status = "Closed task detail"
            return True

        if ch in (ord("1"), ord("2"), ord("3"), ord("4")):
            self.tab = int(chr(ch)) - 1
            self.selected_row = 0
            return True
        if ch == ord("r"):
            try:
                self.load_snapshot()
            except Exception as exc:  # pragma: no cover - interactive fallback
                self.error = str(exc)
            return True
        if ch == ord("["):
            self.bump_window(-1)
            return True
        if ch == ord("]"):
            self.bump_window(1)
            return True
        if ch == curses.KEY_UP:
            self.selected_row = max(self.selected_row - 1, 0)
            return True
        if ch == curses.KEY_DOWN:
            self.selected_row = min(self.selected_row + 1, max(self.current_rows() - 1, 0))
            return True
        if ch in (10, 13, curses.KEY_ENTER) and self.tab == 3:
            rows = self.current_task_rows()
            if rows:
                try:
                    self.load_detail(rows[self.selected_row]["task_id"])
                except Exception as exc:  # pragma: no cover - interactive fallback
                    self.error = str(exc)
            return True
        if ch == ord("/") and self.tab == 3:
            self.filters.search_text = self.prompt(stdscr, "Task search", self.filters.search_text or "")
            self.reload_with_feedback()
            return True
        if ch == ord("o") and self.tab == 3:
            outcomes = [None, "completed", "failed", "other"]
            idx = outcomes.index(self.filters.task_outcome) if self.filters.task_outcome in outcomes else 0
            self.filters.task_outcome = outcomes[(idx + 1) % len(outcomes)]
            self.reload_with_feedback()
            return True
        if ch == ord("p") and self.tab == 2:
            providers = [None, "claude", "codex"]
            idx = providers.index(self.filters.provider) if self.filters.provider in providers else 0
            self.filters.provider = providers[(idx + 1) % len(providers)]
            self.reload_with_feedback()
            return True
        if ch == ord("0"):
            self.filters = Filters()
            self.reload_with_feedback()
            return True
        return True

    def reload_with_feedback(self) -> None:
        try:
            self.load_snapshot()
        except Exception as exc:  # pragma: no cover - interactive fallback
            self.error = str(exc)

    def bump_window(self, direction: int) -> None:
        if self.window_days not in WINDOW_CHOICES:
            self.window_days = 7
        idx = WINDOW_CHOICES.index(self.window_days)
        idx = min(max(idx + direction, 0), len(WINDOW_CHOICES) - 1)
        self.window_days = WINDOW_CHOICES[idx]
        self.reload_with_feedback()

    def current_rows(self) -> int:
        if self.snapshot is None:
            return 0
        if self.tab == 1:
            return len(self.snapshot["trends"]["days"])
        if self.tab == 2:
            return len(self.snapshot["hotspots"]["hotspots"])
        if self.tab == 3:
            return len(self.current_task_rows())
        return 0

    def current_task_rows(self) -> list[dict[str, Any]]:
        if self.snapshot is None:
            return []
        return self.snapshot["task_runs"]["task_runs"]

    def draw(self, stdscr: Any) -> None:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        self.draw_header(stdscr, width)
        if self.detail is not None:
            self.draw_detail(stdscr, height, width)
        elif self.snapshot is None:
            self.add_line(stdscr, 3, 0, "No telemetry snapshot loaded.")
        elif self.tab == 0:
            self.draw_summary(stdscr, height, width)
        elif self.tab == 1:
            self.draw_trends(stdscr, height, width)
        elif self.tab == 2:
            self.draw_hotspots(stdscr, height, width)
        else:
            self.draw_tasks(stdscr, height, width)
        self.draw_footer(stdscr, height, width)
        stdscr.refresh()

    def draw_header(self, stdscr: Any, width: int) -> None:
        title = f"agent-telemetry-tui  repo={self.repo}  window={self.window_days}d"
        self.add_line(stdscr, 0, 0, title[:width - 1], curses.A_BOLD)
        filters = f"filters provider={self.filters.provider or 'all'} outcome={self.filters.task_outcome or 'all'} search={self.filters.search_text or '-'}"
        self.add_line(stdscr, 1, 0, filters[:width - 1])
        tab_line = "  ".join(
            f"[{index + 1}] {name}" if index != self.tab else f"[{index + 1}] {name}*"
            for index, name in enumerate(TABS)
        )
        self.add_line(stdscr, 2, 0, tab_line[:width - 1])

    def draw_summary(self, stdscr: Any, height: int, width: int) -> None:
        summary = self.snapshot["summary"]
        inspect = self.snapshot["inspect"]
        lines = [
            f"Migration required: {inspect['migration_required']}",
            f"Telemetry DB: {inspect['db_path']}",
            f"Completed tasks: {summary['completed_tasks']}",
            f"Total tokens: {summary['tokens']['total']}",
            f"Claude/Codex: {summary['tokens']['claude']} / {summary['tokens']['codex']}",
            f"KPI tokens per completed TODO: {summary['kpi_tokens_per_completed_todo']}",
            f"Trend direction: {summary['velocity_summary']['trend_direction']}",
            f"Mean duration seconds: {summary['velocity_summary']['mean_duration_seconds']}",
            f"Task runs tracked: {inspect['counts']['task_runs']}",
            "",
            "Recent task samples:",
        ]
        row = 4
        for line in lines:
            self.add_line(stdscr, row, 0, line[:width - 1])
            row += 1
        for item in summary["recent_task_samples"][: max(height - row - 2, 0)]:
            text = f"- {item['task_id']} [{item['task_outcome']}] {item['task_text']}"
            self.add_line(stdscr, row, 0, text[:width - 1])
            row += 1

    def draw_trends(self, stdscr: Any, height: int, width: int) -> None:
        self.add_line(stdscr, 4, 0, "Day         Tasks   Tokens   AvgSec   LOC")
        for index, day in enumerate(self.snapshot["trends"]["days"][: max(height - 6, 0)]):
            attrs = curses.A_REVERSE if index == self.selected_row else 0
            line = f"{day['day']:<10} {day['tasks']:>5} {day['tokens_total']:>8} {day['avg_duration_s']:>8} {day['loc_changed']:>6}"
            self.add_line(stdscr, 5 + index, 0, line[:width - 1], attrs)

    def draw_hotspots(self, stdscr: Any, height: int, width: int) -> None:
        self.add_line(stdscr, 4, 0, "Provider Tool                 Calls   EstTokens   AvgTokens")
        rows = self.snapshot["hotspots"]["hotspots"][: max(height - 6, 0)]
        for index, item in enumerate(rows):
            attrs = curses.A_REVERSE if index == self.selected_row else 0
            line = (
                f"{item['provider']:<8} {item['tool_name'][:20]:<20} {item['calls']:>5} "
                f"{item['estimated_tokens']:>11} {item['avg_tokens_per_call']:>11}"
            )
            self.add_line(stdscr, 5 + index, 0, line[:width - 1], attrs)

    def draw_tasks(self, stdscr: Any, height: int, width: int) -> None:
        self.add_line(stdscr, 4, 0, "Task ID                Outcome     Duration   Tokens   Text")
        rows = self.current_task_rows()[: max(height - 6, 0)]
        for index, item in enumerate(rows):
            attrs = curses.A_REVERSE if index == self.selected_row else 0
            line = (
                f"{item['task_id'][:20]:<20} {str(item['task_outcome'] or 'other')[:10]:<10} "
                f"{item['duration_seconds']:>8} {item['tokens']['total']:>8} {item['task_text'] or ''}"
            )
            self.add_line(stdscr, 5 + index, 0, line[:width - 1], attrs)

    def draw_detail(self, stdscr: Any, height: int, width: int) -> None:
        latest = self.detail["latest_run"]
        lines = [
            f"Task detail: {self.detail['task_id']}",
            f"Session branch: {latest['session_branch']}",
            f"Outcome: {latest['task_outcome']}",
            f"Duration seconds: {latest['duration_seconds']}",
            f"Tokens total: {latest['tokens']['total']}",
            f"Artifact commit/files: {latest['artifact']['commit_sha']} / {latest['artifact']['files_changed']}",
            "",
            "Events:",
        ]
        row = 4
        for line in lines:
            self.add_line(stdscr, row, 0, line[:width - 1], curses.A_BOLD if row == 4 else 0)
            row += 1
        for event in self.detail["events"][: max(height - row - 2, 0)]:
            text = f"- {event['event_type']} @ {event['timestamp']} branch={event['session_branch']}"
            self.add_line(stdscr, row, 0, text[:width - 1])
            row += 1

    def draw_footer(self, stdscr: Any, height: int, width: int) -> None:
        keys = "1-4 tabs  Up/Down move  Enter detail  Esc back  [ ] window  r reload  / search(tasks)  o outcome(tasks)  p provider(hotspots)  0 clear  q quit"
        self.add_line(stdscr, height - 2, 0, keys[:width - 1], curses.A_DIM)
        status = self.error or self.status
        self.add_line(stdscr, height - 1, 0, status[:width - 1], curses.A_DIM)

    def prompt(self, stdscr: Any, label: str, initial: str) -> str | None:
        height, width = stdscr.getmaxyx()
        prompt = f"{label}: "
        stdscr.move(height - 1, 0)
        stdscr.clrtoeol()
        self.add_line(stdscr, height - 1, 0, prompt[:width - 1], curses.A_BOLD)
        curses.curs_set(1)
        curses.echo()
        stdscr.refresh()
        try:
            raw = stdscr.getstr(height - 1, min(len(prompt), width - 1), max(width - len(prompt) - 1, 1))
            value = raw.decode("utf-8").strip()
            return value or None
        finally:
            curses.noecho()
            curses.curs_set(0)

    @staticmethod
    def add_line(stdscr: Any, y: int, x: int, text: str, attrs: int = 0) -> None:
        height, width = stdscr.getmaxyx()
        if 0 <= y < height:
            stdscr.addnstr(y, x, text, max(width - x - 1, 0), attrs)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    app = TelemetryTui(args)
    curses.wrapper(app.run)
    return 0
