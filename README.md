# agentkit

Framework-neutral CLI tooling for coding-agent workflows.

## Includes

- `agent-index`: lightweight repository indexing and task-scoped context pack generation.
- `agent-telemetry`: local telemetry ingestion/reporting from Claude JSONL logs.

## Goals

- Token-efficient context packaging for worker agents.
- Task-level telemetry and KPI tracking (`tokens per completed TODO`).
- Policy-aware orchestration support (allowlist + soft warnings).

## Requirements

- Python 3.10+
- Git (for repository detection)

## Quick Start

```bash
./agent-index build --repo . --mode full
./agent-index pack --repo . --task "implement SSE endpoint" --out /tmp/pack.json

./agent-index-refresh-light .
./agent-telemetry-ingest . "$HOME/.claude" .claude/agent-events.jsonl
./agent-telemetry-report . 7
./agent-telemetry-hotspots . 7 12
./agent-telemetry-strict --repo . --window-days 7 --enforce
```

## Task Event Logging (KPI Wiring)

`agent-telemetry` and `agent-telemetry-strict` compute `tokens_per_completed_todo` from task lifecycle events.
Record both `task_started` and `task_completed` in the repo event log (`.claude/agent-events.jsonl`).

Required fields:
- `repo`
- `task_id`
- `session_branch`

Examples:

```bash
./agent-log-task-started . phase4-fw todo/20260308-130742 "Implement SSE endpoint wiring"
./agent-log-task-complete . phase4-fw todo/20260308-130742
```

Agentkit wrappers:

```bash
just task-started phase4-fw todo/20260308-130742 "Implement SSE endpoint wiring"
just task-completed phase4-fw todo/20260308-130742
just telemetry-ingest
just telemetry-report
just telemetry-hotspots
./agent-weekly-telemetry-gate /path/to/repo 7 "$HOME/.claude" "/path/to/repo/.claude/agent-events.jsonl"
```


## Unified Orchestration CLI

Use `agentkit` as a top-level orchestrator for indexing/context packing and telemetry reporting.

```bash
./agentkit prepare --repo . --task "implement SSE endpoint" --out /tmp/pack.json
./agentkit observe --repo . --window-days 7
./agentkit cycle --repo . --task "implement SSE endpoint" --out /tmp/pack.json
```

## Project-Specific Extraction Adapters

`agent-index` supports adapter plugins so each repo can add domain-specific symbol extraction.

### Built-in adapters

Use adapter names in `agentkit.json`:

- `esp-idf-http-routes`
- `svelte-live-api`
- `typescript-stores`

Example:

```json
{
  "extract": {
    "enabled": true,
    "adapters": [
      {
        "type": "builtin",
        "name": "esp-idf-http-routes",
        "include_ext": ["c", "h"],
        "include_paths": ["components/http_server/"]
      },
      {
        "type": "builtin",
        "name": "svelte-live-api",
        "include_ext": ["ts", "svelte"],
        "include_paths": ["src/lib/api/", "src/lib/stores/"]
      }
    ]
  }
}
```

### Custom python adapters

You can load adapters from repo files (trusted repos only).

```json
{
  "extract": {
    "adapters": [
      {
        "type": "python",
        "name": "custom-c-router",
        "file": "tools/agentkit/custom_adapter.py",
        "function": "extract",
        "include_ext": ["c", "h"],
        "include_paths": ["components/http_server/"]
      }
    ]
  }
}
```

Template: `examples/custom_adapter.py`

## Claude Commands (Portable)

Portable Claude command markdown lives in `claude/commands/`.
These commands invoke scoped wrappers and `just` recipes (no shell composition, no multiline chains).

Validate command docs for banned patterns:

```bash
./agent-validate-command-docs .
```

To use them in Claude Code, copy or symlink the files into your local `~/.claude/commands/` directory.

## Codex Integration

An installable Codex skill is included at `skills/agentkit-todo-codex`.
It mirrors the existing TODO execution workflow (`start-todo`, `next`, `check`, `validate`, `prompt`, `index-refresh`, `telemetry-report`) and uses strict `agent-*` wrappers (no shell composition).

Install agentkit tools and the skill globally:

```bash
./agent-install-global-tools
```

This installs command symlinks into `~/.local/bin` and links the skill into `$CODEX_HOME/skills` (default `~/.codex/skills`).
For non-default install location:

```bash
./agent-install-global-tools /custom/bin/dir
```

Validate both Claude command docs and Codex skill markdown with:

```bash
./agent-validate-command-docs .
```

Ensure the install bin directory is on `PATH` for both your shell and Codex runtime.
Claude command support remains unchanged and fully supported in parallel.

## License

MIT
