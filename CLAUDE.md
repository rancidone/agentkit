# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Agentkit is a framework-neutral CLI tooling suite for coding-agent workflows. It provides two main subsystems:
- **`agent-index`**: lightweight repo indexing and task-scoped context pack generation (SQLite-backed)
- **`agent-telemetry`**: local telemetry ingestion and KPI reporting from Claude + Codex JSONL logs (SQLite-backed, WAL mode, single-writer lease)

## Migration Bootstrap Contract

Follow [MIGRATION.md](/home/maddie/repos/agentkit/MIGRATION.md) during the MCP transition.

This repo must keep using agentkit to execute its own `TODO.md` workflow throughout the migration. The repo-local hard switch is complete: use the MCP-backed skills as the primary path for `start-todo`, `next`, `check`, `validate`, `prompt`, `index-refresh`, and `telemetry-report`, with scoped local helpers retained only where MCP parity is intentionally incomplete.

## Skills-First Workflow

Use the MCP-backed skills as the primary workflow surface for this repository.

- Install the managed global MCP configs with `./agent-install`.
- The default managed config paths are `~/.codex/agentkit/mcp-servers.json` and `~/.claude/agentkit/mcp-servers.json`.
- Run `agentkit-todo-codex` or `agentkit-todo-claude` for `start-todo`, `next`, `check`, `validate`, `prompt`, `index-refresh`, and `telemetry-report`.

## Local Helper Commands

Keep these `just` recipes and wrappers for debugging, narrow helper tasks, and migration gaps. They are not a supported primary install surface.

```bash
just --list                          # show all available recipes
just setup                           # validate docs + full index refresh + telemetry ingest (session start)
just observe                         # telemetry ingest + report + hotspots (session finish)
just validate-command-docs           # validate skill markdown and any legacy command markdown for banned patterns
just command-guard "<cmd>"           # check a command shape before running it
just index-refresh-light             # incremental index refresh
just index-refresh-full              # full index rebuild
just telemetry-ingest                # incremental telemetry ingest (non-destructive)
just telemetry-report                # 7-day summary report
just telemetry-hotspots              # 7-day hotspot table (12 rows)
just telemetry-tui                   # launch the repo-local telemetry UI
just context-pack "<task>" "/tmp/out.json"  # generate task context pack
just session-branch todo             # create/reuse session branch (prints branch name)
```

Task lifecycle logging:
```bash
just task-started "<task_id>" "<session_branch>" "<task_text>"
just task-completed "<task_id>" "<session_branch>"
just task-failed "<task_id>" "<session_branch>" failed
```

Commit helper (required pattern — no heredocs or chaining):
```bash
printf '%s\n' "feat: description" "" "- detail" > /tmp/commit-msg.txt
./agent-commit-files --message-file /tmp/commit-msg.txt --files file1 file2
# or to stage all:
just commit-all /tmp/commit-msg.txt
```

## Architecture

All scripts are Python 3.10+ (shebang `#!/usr/bin/env python3`) or bash. No build step needed.

**Shared library**: `agentkit_common.py` — `repo_root()`, `default_state_dir()`, `load_repo_config()`, `iter_repo_files()`, `infer_role()`, `parse_isoish_timestamp()`.

**State directory**: `~/.claude/tools/agentkit/state/` (or `$AGENTKIT_STATE_DIR`). Contains:
- `index-<repo_id>.db` — file index and symbol/task tables
- `telemetry-<repo_id>.db` — usage events, checkpoints, KPI views
- Writer lease lock files for concurrent-safe ingest

**Repo config**: `.claude/agentkit.json` or `agentkit.json` at repo root. Used to configure extraction adapters.

**`agent_extractors.py`**: Symbol extraction adapters — built-in (`esp-idf-http-routes`, `svelte-live-api`, `typescript-stores`) and custom Python plugins loaded from repo files.

**`agentkit`**: Backend utility CLI with three subcommands: `prepare` (index + pack), `observe` (ingest + report), `cycle` (prepare + observe). It is useful for local debugging and compatibility flows, not as the supported end-user orchestration layer.

## Skills

Skills are the supported user-facing orchestration layer.

The legacy `claude/commands/` markdown remains in-repo temporarily for migration compatibility, but it is not a supported interface and should not be installed as a primary workflow surface.

This repository now carries parallel skill packages for Codex and Claude under `skills/agentkit-todo-codex` and `skills/agentkit-todo-claude`, with the same tasks-first workflow semantics.
Both point at `skills/shared/agentkit_todo_mcp_workflow.md`, which defines the MCP-first workflow contract for repo, telemetry, and task lifecycle operations.

Install the managed MCP config artifacts and both skill packages globally:
```bash
./agent-install
```

For this repository's own dogfood workflow, prefer the managed global install state by default. Use the repo-local MCP examples under `examples/` only when you explicitly need a local override while testing migration behavior in-place.

Remove only agentkit-managed install artifacts with:
```bash
./agent-uninstall
```

Default uninstall removes manifest-managed skill links, MCP config files, and managed legacy launch helpers, plus best-effort cleanup of historical repo-owned symlinks.
It intentionally preserves telemetry DBs, event logs, repo-local data, copied scripts, and other arbitrary user files.

## Command Safety Rules

`agent-command-guard` enforces these bans in workflow commands and command docs:
- No subshell expansion `$(...)`
- No heredocs `<<`
- No command chaining (`&&`, `||`, `;`)
- No pipes `|`
- No `2>&1 | tail` patterns

Always use `just` recipes or `agent-*` wrappers instead of composing shell commands. Use `repo='.'` (not `repo="$(pwd)"`) in lifecycle wrappers.

## Telemetry Model

- Ingest is **incremental and non-destructive** — checkpoints track last-processed position per source log.
- `./agent-telemetry migrate --repo . --claude-home "$HOME/.claude" --codex-home "$HOME/.codex" --events .claude/agent-events.jsonl` upgrades legacy telemetry DBs in place and recomputes derived tables.
- **Single-writer coordination**: a per-repo file lock serializes concurrent ingest calls.
- Report/hotspots/export use read-mode connections and are available during ingest.
- Full reset: `./agent-telemetry rebuild --repo . --claude-home "$HOME/.claude" --codex-home "$HOME/.codex" --events .claude/agent-events.jsonl`
- `./agent-telemetry-ingest` now auto-selects provider logs from the active runner environment. Use `AGENTKIT_TELEMETRY_SCOPE=codex`, `claude`, or `all` only when you need to override the default.
- Legacy repos that error on `report`, `trend`, `hotspots`, or `task` should run `agent-telemetry migrate` first.

## Inspecting Agentkit State DBs

Prefer the repo MCP `index.inspect` / `config.load` tools and the telemetry MCP `telemetry.inspect` / `task.inspect` tools first. Those cover the supported inspection paths without dropping into ad-hoc SQL.

The agentkit SQLite databases still live in `~/.claude/tools/agentkit/state/`. If you need lower-level inspection beyond the MCP surface, configure `mcp-server-sqlite` in Claude Code's MCP settings pointed at the state dir:

```json
{
  "mcpServers": {
    "sqlite": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sqlite", "~/.claude/tools/agentkit/state"]
    }
  }
}
```

This avoids one-off `python3 -c "..."` debug scripts for every query. Without it, use `python3 -c "import sqlite3; ..."` directly against the DB path from `agentkit_common.default_state_dir()`.

## Repo-Local MCP Dogfood Config

While this repository is migrating, keep a repo-local dev path that does not depend on user-home MCP config or state directories.

- Codex example: `examples/codex-mcp-servers.repo-local.example.json`
- Claude example: `examples/claude-mcp-servers.repo-local.example.json`
- Repo-local writable state dir: `.agentkit/state`

Materialize those examples into `.codex/agentkit/mcp-servers.json` and `.claude/agentkit/mcp-servers.json` with `__REPO_ROOT__` replaced by the absolute repo path. Both examples set `AGENTKIT_STATE_DIR` to `$REPO_ROOT/.agentkit/state` so repo and telemetry MCP operations stay writable during dogfooding.

## start-todo Execution Model

Default mode is **tasks-first**: execute tasks directly in-session with lifecycle logging. Escalate to worker-branch only when the heuristic passes: at least 2 independent tasks from current phase, each medium or high complexity. In tasks-first mode, only `task-started`/`task-completed`/`task-failed` events are logged — no synthetic worker events. Never merge into `main` or `develop` from `start-todo`.
The repo-local hard switch is complete for self-dogfooding. Keep temporary local helpers only for workflow gaps that are still intentionally outside the MCP surface.
