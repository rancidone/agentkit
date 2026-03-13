# agentkit

Framework-neutral CLI tooling for coding-agent workflows.

## Includes

- `agent-index`: lightweight repository indexing and task-scoped context pack generation.
- `agent-telemetry`: local telemetry ingestion/reporting from Claude + Codex JSONL logs.

## Goals

- Token-efficient context packaging for worker agents.
- Task-level telemetry and KPI tracking (`tokens per completed TODO`).
- Policy-aware orchestration support (allowlist + soft warnings).

## Migration Contract

The active migration contract is documented in [MIGRATION.md](/home/maddie/repos/agentkit/MIGRATION.md).

During the MCP transition, this repository must keep using agentkit to execute its own `TODO.md` workflow. Until MCP plus skills reach workflow parity, retain the minimum in-repo compatibility path required for this repo to keep dogfooding `start-todo`, `next`, `check`, `validate`, `prompt`, `index-refresh`, and `telemetry-report`.

## MCP Backend Split

Phase 1 establishes an explicit two-service backend split without removing the existing wrapper-based compatibility path:

- `agentkit-repo-mcp` owns repo, index, context pack, and repo-config operations.
- `agentkit-telemetry-mcp` owns telemetry ingestion/reporting, state handling, and task lifecycle logging.

Bootstrap entrypoints are available now:

```bash
./agentkit-repo-mcp
./agentkit-telemetry-mcp
```

At this stage the current `agent-*` wrappers remain the supported dogfooding path for this repository until the MCP-backed skills reach workflow parity.
The shared backend logic now lives in importable modules, with `agent-index` delegating to `agent_index_cli` over `agent_index_backend`, and `agent-telemetry` delegating to `agent_telemetry_backend`.
Phase 1 keeps the current SQLite state layout and repo config lookup unchanged: DB files still resolve from `agentkit_common.default_state_dir()`, and repo config still loads from `.claude/agentkit.json` first with `agentkit.json` as the fallback.

Current inspect-oriented MCP tools include:

- `index.inspect`
- `config.load`
- `telemetry.inspect`
- `task.inspect`

## Requirements

- Python 3.10+
- Git (for repository detection)

## Quick Start

```bash
./agent-index build --repo . --mode full
./agent-index pack --repo . --task "implement SSE endpoint" --out /tmp/pack.json

./agent-index-refresh-light .
./agent-telemetry-ingest . "$HOME/.claude" .claude/agent-events.jsonl "$HOME/.codex"
./agent-telemetry-report . 7
./agent-telemetry-hotspots . 7 12
./agent-telemetry rebuild --repo . --claude-home "$HOME/.claude" --codex-home "$HOME/.codex" --events .claude/agent-events.jsonl
./agent-telemetry export --repo . --dataset task_kpi --format csv --out .claude/task-kpi.csv
./agent-telemetry-strict --repo . --window-days 7 --enforce
```

## Telemetry Ingest Model

- `agent-telemetry ingest` is incremental and non-destructive.
- Checkpoints are tracked per source log so reruns only process new records.
- Writes are serialized by a per-repo writer lease, allowing concurrent Codex/Claude callers without DB lock races.
- `agent-telemetry rebuild` is the maintenance path for full reset + recompute.
- `agent-telemetry-ingest` auto-detects the active runner environment: Codex ingests Codex logs, Claude ingests Claude logs, and explicit overrides can use `AGENTKIT_TELEMETRY_SCOPE=codex|claude|all`.

## Task Event Logging (KPI Wiring)

`agent-telemetry` and `agent-telemetry-strict` compute `tokens_per_completed_todo` from task lifecycle events.
Record both `task_started` and `task_completed` in the repo event log (`.claude/agent-events.jsonl`).

Required fields:
- `repo`
- `task_id`
- `session_branch`

Optional fields:
- `task_text` (persisted to telemetry DB)
- `complexity_points` (`1..5`)
- `task_outcome` (for custom outcomes on non-standard flows)
- `commit_sha`, `files_changed`, `insertions`, `deletions` (build artifact linking)

Examples:

```bash
./agent-log-task-started . phase4-fw todo/20260308-130742 "Implement SSE endpoint wiring"
./agent-log-task-started . phase4-fw todo/20260308-130742 "Implement SSE endpoint wiring" .claude/agent-events.jsonl 3
./agent-log-task-complete . phase4-fw todo/20260308-130742
```

Agentkit wrappers:

```bash
just task-started phase4-fw todo/20260308-130742 "Implement SSE endpoint wiring"
just task-started phase4-fw todo/20260308-130742 "Implement SSE endpoint wiring" . .claude/agent-events.jsonl 3
just task-completed phase4-fw todo/20260308-130742
just telemetry-ingest
just telemetry-report
just telemetry-hotspots
./agent-weekly-telemetry-gate /path/to/repo 7 "$HOME/.claude" "/path/to/repo/.claude/agent-events.jsonl" "$HOME/.codex"
```


## Backend Utility CLI

Skills are the supported user-facing orchestration layer.
Use `agentkit` only as a backend utility CLI for local debugging, smoke checks, or temporary compatibility flows while the skill migration is in progress.

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

## Legacy Claude Command Markdown

Legacy Claude command markdown still lives in `claude/commands/`, but it is no longer a supported user-facing interface.
Skills are the supported orchestration layer during the migration. The legacy markdown remains in-repo only as a temporary compatibility artifact.

Validate skill markdown, and any legacy command markdown still present in the repo, for banned shell patterns:

```bash
./agent-validate-command-docs .
```

Guard-friendly command patterns:

```bash
# Logging lifecycle events: use repo "." with wrapper-compatible args
./agent-log-worker-merged . phase7-build todo/20260308-151125 merged .claude/agent-events.jsonl
./agent-log-task-complete . phase7-build todo/20260308-151125 .claude/agent-events.jsonl

# Commit flow: write message file, then use scoped commit wrapper
printf '%s\n' "feat: phase 7 build pipeline" "" "- Add build-all.sh and docs updates" > /tmp/commit-msg.txt
./agent-commit-files --message-file /tmp/commit-msg.txt --files firmware/CMakeLists.txt thermometer-ui/vite.config.ts README.md build-all.sh
```

## Codex Integration

An installable Codex skill is included at `skills/agentkit-todo-codex`.
This skill is the supported user-facing orchestration entrypoint for the TODO workflow in Codex.
It mirrors the existing TODO execution workflow (`start-todo`, `next`, `check`, `validate`, `prompt`, `index-refresh`, `telemetry-report`) and now treats MCP tools as the primary repo, telemetry, and task lifecycle interface.
The `start-todo` orchestration defaults to tasks-first execution, and only escalates to worker-branch flow when multiple independent medium/high-complexity tasks justify it.
In tasks-first mode, lifecycle logging stays task-scoped (`task-started`, `task-completed`, `task-failed`) without synthetic worker events.
This skill remains part of the required compatibility path while the repo migrates to MCP-backed orchestration for its own dogfooding workflow.

A parallel Claude-side skill package now lives at `skills/agentkit-todo-claude`.
It carries the same workflow semantics so Codex and Claude can converge on one skills-first orchestration contract during the MCP migration.
The shared MCP-backed workflow reference lives at `skills/shared/agentkit_todo_mcp_workflow.md`, and both skills use MCP tools first for repo, telemetry, and task lifecycle operations.

Install the backend tools plus the supported Codex and Claude skill packages globally:

```bash
./agent-install-global-tools
```

This installs backend tool symlinks into `~/.local/bin`, links the Codex skill into `$CODEX_HOME/skills` (default `~/.codex/skills`), and links the Claude skill into `$CLAUDE_HOME/skills` (default `~/.claude/skills`).
For non-default install location:

```bash
./agent-install-global-tools /custom/bin/dir
```

Validate the Codex skill markdown, plus any retained legacy command markdown, with:

```bash
./agent-validate-command-docs .
```

Ensure the install bin directory is on `PATH` for both your shell and Codex runtime.
Claude command markdown is not a supported install surface anymore.

## License

MIT
