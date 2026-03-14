# Telemetry TUI Workflow

Date: 2026-03-14
Repository: `/home/maddie/repos/agentkit`

## Purpose

`agent-telemetry-tui` is the read-only terminal UI for inspecting repo telemetry from one session.

Use it to review:

- summary and migration state
- day-by-day token and task trends
- tool hotspots
- recent task runs
- task drill-down details

## Entry Points

Direct script:

```bash
./agent-telemetry-tui --repo .
```

Repo-local helper recipe:

```bash
just telemetry-tui
just telemetry-tui . 30
```

The `just` recipe pins `AGENTKIT_STATE_DIR` to `.agentkit/state` inside the current repo so dogfooding does not depend on a writable home-directory state path.

## Recommended Session Flow

1. Refresh telemetry:

```bash
just telemetry-ingest
```

2. Launch the UI:

```bash
just telemetry-tui
```

3. Check the Summary view for migration state, DB path, completed-task count, token totals, and trend direction.

4. Move through Trends, Hotspots, and Tasks to inspect current behavior.

5. Open task detail from the Tasks view when you need run-level context.

## Keyboard Controls

- `1` `2` `3` `4`: switch between Summary, Trends, Hotspots, and Tasks
- `Up` `Down`: move row selection
- `Enter`: open task detail from the Tasks view
- `Esc`: close task detail
- `[` `]`: shrink or expand the active window preset
- `r`: reload telemetry data
- `/`: set a task search filter in the Tasks view
- `o`: cycle task outcome filters in the Tasks view
- `p`: cycle provider filters in the Hotspots view
- `0`: clear filters
- `q`: quit

## Notes

- The initial UI uses Python's standard-library `curses` module. No extra UI dependency is required.
- The UI reads structured data from the telemetry read models and MCP-aligned surfaces (`tui.snapshot`, `tui.task_detail`).
- If telemetry is missing or stale, rerun `just telemetry-ingest` and reload with `r`.
