# TODO

## Bugs

- [x] Fix `sqlite3.IntegrityError: UNIQUE constraint failed: idx_task_runs_unique` in `_build_task_runs` — ingest crashes when event log contains multiple `task_started` events for the same (task_id, session_branch). Use `INSERT OR REPLACE` or pre-deduplicate before insert.
- [x] Reduce per-command Bash approval prompts during orchestration — added `just setup` (validate+index+ingest) and `just observe` (ingest+report+hotspots) composite recipes.
- [x] Evaluate adding `mcp-server-sqlite` (from `@modelcontextprotocol/server-sqlite`) to the Claude Code MCP config for direct DB inspection of agentkit state — documented setup in CLAUDE.md.
- [x] Document (and enforce in skill/command docs) that context must be compacted before spawning subagent workers to avoid context bleed and redundant re-reads.

## Plan: SQLite Single-Writer Telemetry + Incremental Ingest

## Plan
- [x] Add SQLite storage hardening in `agent-telemetry` (`WAL`, `busy_timeout`, deterministic write transactions, bounded lock retry).
- [x] Centralize DB connection creation into explicit read/write modes.
- [x] Add single-writer coordination lock in state dir so concurrent ingest calls serialize.
- [x] Replace destructive ingest with incremental ingest using per-source checkpoints.
- [x] Add checkpoint schema/table and stable source keys for Claude usage logs, Codex usage logs, and task event logs.
- [x] Keep existing uniqueness indexes as idempotency backstop for duplicate events.
- [x] Add explicit maintenance command for full rebuild/reset; keep normal ingest non-destructive.
- [x] Ensure report/hotspots/export use read-mode connections and remain available during ingest activity.
- [x] Update telemetry documentation in `README.md` to reflect incremental behavior, single-writer model, and rebuild semantics.
- [x] Run command doc validation plus targeted telemetry regression checks.

## Acceptance Criteria
- [x] Two concurrent `agent-telemetry ingest` runs complete without lock errors or data loss.
- [x] Re-running ingest without new input leaves totals stable (no duplicate inflation).
- [x] Interrupted ingest resumes from checkpoints without dropping or double-counting events.
- [x] Rebuild/reset command fully recomputes repo telemetry from source logs when explicitly invoked.
- [x] Existing report outputs continue to include correct provider splits and task KPI fields.

## Assumptions
- [x] Backend remains SQLite only (no Postgres in this pass).
- [x] Scope is telemetry datastore concurrency/durability; repo code-edit conflicts are out of scope.
