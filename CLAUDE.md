# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Agentkit is a framework-neutral CLI tooling suite for coding-agent workflows. It provides two main subsystems:
- **`agent-index`**: lightweight repo indexing and task-scoped context pack generation (SQLite-backed)
- **`agent-telemetry`**: local telemetry ingestion and KPI reporting from Claude + Codex JSONL logs (SQLite-backed, WAL mode, single-writer lease)

## Common Commands

```bash
just --list                          # show all available recipes
just setup                           # validate docs + full index refresh + telemetry ingest (session start)
just observe                         # telemetry ingest + report + hotspots (session finish)
just validate-command-docs           # validate claude/commands/ and skill markdown for banned patterns
just command-guard "<cmd>"           # check a command shape before running it
just index-refresh-light             # incremental index refresh
just index-refresh-full              # full index rebuild
just telemetry-ingest                # incremental telemetry ingest (non-destructive)
just telemetry-report                # 7-day summary report
just telemetry-hotspots              # 7-day hotspot table (12 rows)
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

**`agentkit`**: High-level orchestrator CLI with three subcommands: `prepare` (index + pack), `observe` (ingest + report), `cycle` (prepare + observe).

## Claude Commands

Portable Claude command markdown lives in `claude/commands/`. These are the skills available as `/skill-name`:
- `/start-todo` — orchestrate TODO.md using tasks-first default (worker-branch only when ≥2 independent medium/high-complexity tasks)
- `/next <task>` — implement a task with lifecycle wrappers
- `/check` — run lint/test/checks and fix all issues
- `/validate` — deep validation of completed implementation
- `/prompt <task>` — synthesize execution prompt
- `/index-refresh` — scoped index refresh
- `/telemetry-report` — ingest and report telemetry

Install commands into `~/.claude/commands/` by symlinking. Install all tools and the Codex skill globally:
```bash
./agent-install-global-tools
```

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
- **Single-writer coordination**: a per-repo file lock serializes concurrent ingest calls.
- Report/hotspots/export use read-mode connections and are available during ingest.
- Full reset: `./agent-telemetry rebuild --repo . --claude-home "$HOME/.claude" --codex-home "$HOME/.codex" --events .claude/agent-events.jsonl`

## Inspecting Agentkit State DBs

The agentkit SQLite databases live in `~/.claude/tools/agentkit/state/`. For ad-hoc inspection, configure `mcp-server-sqlite` in Claude Code's MCP settings pointed at the state dir:

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

## start-todo Execution Model

Default mode is **tasks-first**: execute tasks directly in-session with lifecycle logging. Escalate to worker-branch only when the heuristic passes: at least 2 independent tasks from current phase, each medium or high complexity. In tasks-first mode, only `task-started`/`task-completed`/`task-failed` events are logged — no synthetic worker events. Never merge into `main` or `develop` from `start-todo`.
