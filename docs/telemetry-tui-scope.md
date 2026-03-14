# Telemetry TUI Scope

Date: 2026-03-14
Repository: `/home/maddie/repos/agentkit`
Status: Approved scope for initial implementation

## Goal

Define the first shipping scope for a read-only terminal UI that lets an operator inspect telemetry health and recent task activity from one session without reformatting backend data in multiple places.

The first pass is intentionally narrow:

- Read-only only. No lifecycle writes, no event edits, no rebuild/migrate actions from the UI.
- One-process local UI over existing telemetry data for the current repo.
- Backend data should come from structured telemetry surfaces, not from parsing human-oriented CLI text.

## Non-Goals

- Editing TODO items or task lifecycle events.
- Triggering `ingest`, `migrate`, `rebuild`, or git actions from the UI.
- Multi-repo dashboards.
- Background refresh daemons or streaming updates.
- A general widget framework beyond what the telemetry explorer needs.

## Primary Operator Jobs

1. Confirm whether telemetry for this repo is healthy and current.
2. Review a compact report for the current time window.
3. Inspect day-by-day token and task trends.
4. Identify tool hotspots and high-token warnings.
5. Drill into one task run to inspect lifecycle events and artifacts.
6. Confirm whether migration is required before trusting reports.

## Information Architecture

The initial TUI uses four top-level views plus one drill-down panel.

### 1. Summary

Purpose:
- Give a fast repo-health snapshot when the UI opens.

Content:
- Repo path.
- Telemetry DB path.
- Migration-required state.
- Window selector.
- Completed task count.
- Total tokens split by Claude/Codex.
- KPI tokens per completed TODO.
- Attribution confidence summary.
- Velocity summary fields already present in `report`.

### 2. Trends

Purpose:
- Show whether task volume, tokens, or duration are moving in the wrong direction.

Content:
- Day-by-day rows from `trend`.
- Per-day tasks, tokens, average duration, and lines changed.
- A lightweight chart or sparkline is optional; tabular output is required.

### 3. Hotspots

Purpose:
- Surface tools with disproportionate call volume or token cost.

Content:
- Provider.
- Tool name.
- Call count.
- Estimated tokens.
- Average tokens per call.
- Soft warnings returned by the backend.

### 4. Task Runs

Purpose:
- Browse recent task runs and open one task for detail inspection.

Content:
- Recent task sample rows from `report`.
- Task id.
- Session branch.
- Task text.
- Outcome.
- Duration.
- Complexity points.
- Claude/Codex token split.

### 5. Task Detail Drill-Down

Purpose:
- Inspect one selected task run without leaving the TUI session.

Content:
- Run metadata from `task.inspect`.
- Token totals and attribution metadata.
- Artifact summary: commit SHA, files changed, insertions, deletions.
- Ordered lifecycle event timeline.

## Navigation Model

The UI should use a predictable keyboard-first model.

- `1` `2` `3` `4`: switch between Summary, Trends, Hotspots, and Task Runs.
- `Tab` and `Shift-Tab`: move focus between major panes within the active view.
- `Up` `Down`: move row selection in lists and tables.
- `Enter`: open Task Detail from the selected task row.
- `Esc`: close Task Detail and return to the previous view.
- `[` and `]`: shrink or expand the active time window.
- `/`: open filter input.
- `r`: reload all read models from the backend.
- `q`: quit.

Mouse support is optional for the first pass. Keyboard support is required.

## Filters

Filters are global unless noted otherwise. They should update the active view immediately after confirmation.

Required filters:

- Time window:
  - Presets: `1d`, `7d`, `30d`, `90d`
  - Custom `since` date in `YYYY-MM-DD`
- Provider:
  - `all`, `claude`, `codex`
- Outcome:
  - `all`, `completed`, `failed`, `other`
- Text search:
  - Match against `task_id`, `session_branch`, and `task_text`

View-specific filters:

- Hotspots:
  - Minimum calls threshold
  - Warning-only toggle
- Task Runs:
  - Complexity range `1..5`

The first pass does not need compound saved searches or sort customization beyond sensible defaults.

## Read-Only Data Contract

The TUI should consume structured backend payloads and map them into internal read models. The backend surface for the next task should expose these payloads without forcing the UI to duplicate report formatting logic.

### Required datasets

1. `summary`
   - Derived from today’s `telemetry.report` payload.
2. `trends`
   - Derived from today’s `telemetry.trend` payload.
3. `hotspots`
   - Derived from today’s `telemetry.hotspots` payload.
4. `inspect`
   - Derived from today’s `telemetry.inspect` payload.
5. `task_detail`
   - Derived from today’s `task.inspect` payload.

### Summary model

```json
{
  "repo": "/abs/repo",
  "window_days": 7,
  "since": null,
  "completed_tasks": 4,
  "tokens": {
    "total": 12345,
    "claude": 0,
    "codex": 12345,
    "prompt_completion": 11000,
    "cache": 1345
  },
  "kpi_tokens_per_completed_todo": 3086.25,
  "attribution_confidence": {
    "high": 4
  },
  "trend": {
    "slope_tokens_per_task": 0.0,
    "direction_tokens_per_task": "flat"
  },
  "velocity_summary": {
    "tasks_in_window": 4,
    "total_tokens": 12345,
    "mean_duration_seconds": 92.3,
    "trend_direction": "flat"
  },
  "recent_task_samples": []
}
```

### Trends model

```json
{
  "repo": "/abs/repo",
  "window_days": 30,
  "since": null,
  "days": [
    {
      "day": "2026-03-14",
      "tasks": 2,
      "tokens_total": 900,
      "avg_duration_s": 45.5,
      "loc_changed": 120
    }
  ],
  "total_tasks": 2,
  "total_tokens": 900
}
```

### Hotspots model

```json
{
  "repo": "/abs/repo",
  "window_days": 7,
  "since": null,
  "hotspots": [
    {
      "provider": "codex",
      "tool_name": "Read",
      "calls": 12,
      "estimated_tokens": 2400,
      "avg_tokens_per_call": 200.0
    }
  ],
  "soft_warnings": [],
  "suggestion": "tighten allowlist for tools with high avg_tokens_per_call"
}
```

### Inspect model

```json
{
  "repo": "/abs/repo",
  "db_path": "/abs/state/telemetry-xxxx.db",
  "counts": {
    "usage_events": 10,
    "tool_calls": 12,
    "task_events": 8,
    "task_runs": 4,
    "task_artifacts": 4
  },
  "checkpoints": [],
  "migration_required": false,
  "legacy_schema_missing": []
}
```

### Task detail model

```json
{
  "repo": "/abs/repo",
  "task_id": "telemetry-tui-scope",
  "run_count": 1,
  "event_count": 2,
  "latest_run": {},
  "runs": [
    {
      "run_id": 1,
      "task_id": "telemetry-tui-scope",
      "session_branch": "todo/20260314-050636",
      "task_text": "Define the telemetry TUI scope",
      "task_outcome": "completed",
      "started_at": 0,
      "ended_at": 0,
      "duration_seconds": 12.5,
      "complexity_points": 2,
      "token_confidence": "high",
      "attribution_method": "branch_link",
      "tokens": {
        "total": 100,
        "claude": 0,
        "codex": 100,
        "prompt_completion": 90,
        "cache": 10
      },
      "artifact": {
        "commit_sha": "",
        "files_changed": 1,
        "insertions": 10,
        "deletions": 0
      }
    }
  ],
  "events": [
    {
      "event_type": "task_started",
      "session_branch": "todo/20260314-050636",
      "session_id": null,
      "conversation_id": null,
      "worker_branch": null,
      "status": null,
      "task_text": "Define the telemetry TUI scope",
      "complexity_points": 2,
      "task_outcome": null,
      "timestamp": "2026-03-14T00:00:00Z"
    }
  ]
}
```

## Backend Requirements For The Next Task

The next backend task should provide one structured query surface for the TUI so the frontend does not orchestrate five separate command wrappers and then normalize them ad hoc.

Required backend behavior:

- Read-only methods only.
- Accept `repo`, `window_days` or `since`, and filter inputs.
- Return structured JSON using the models above.
- Reuse existing backend computation paths where possible:
  - `report_telemetry`
  - `trend_telemetry`
  - `hotspots_telemetry`
  - `inspect_telemetry`
  - `inspect_task_run`
- Do not reformat into human prose inside the backend method.

Recommended shape:

- A TUI-focused backend adapter with methods like:
  - `tui.summary`
  - `tui.trends`
  - `tui.hotspots`
  - `tui.inspect`
  - `tui.task_detail`
- Or one aggregate call that returns all non-detail datasets in one response:
  - `tui.snapshot`

Either shape is acceptable as long as the responses remain read-only, structured, and derived from the current telemetry backend without duplicated formatting logic.

## State and Refresh Rules

- Load Summary, Inspect, Trends, and Hotspots at startup.
- Load Task Detail only on demand.
- `r` performs a fresh read of the active filter set.
- The UI should treat backend responses as point-in-time snapshots.
- The first pass does not require auto-refresh timers.

## Empty and Error States

Required empty states:

- No telemetry DB yet.
- DB exists but has zero task runs in the selected window.
- Migration required before report data is trustworthy.
- Filter returns no matching tasks or hotspots.

Required error handling:

- Show backend error text in a status/footer region.
- Keep the current view mounted when reload fails.
- Allow retry without restarting the process.

## Acceptance Criteria

This scope is complete when the first TUI implementation can:

1. Open against the current repo and show summary plus health state.
2. Switch between Summary, Trends, Hotspots, and Task Runs without leaving the process.
3. Apply the required filters and reload the views.
4. Open a task detail drill-down from Task Runs.
5. Render migration-required and empty-data states clearly.
6. Avoid any write path other than optional local UI state such as selection and filter memory.
