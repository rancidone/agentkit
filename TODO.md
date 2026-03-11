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

## Phase 1: Automated Test Suite

Add pytest coverage for the pure-function and CLI surface so future changes have a
regression safety net. Tests live in a new `tests/` directory.

- [x] Create `tests/` directory with `__init__.py` and `conftest.py`; add `pytest` to a new `requirements-dev.txt`
- [x] Write unit tests for `agentkit_common.py`: `should_skip`, `infer_role`, `repo_id`, and `parse_isoish_timestamp` with edge cases
- [x] Write unit tests for `agent_extractors.py`: `extract_python`, `extract_ts_js`, `extract_c_like` against synthetic multi-function source strings
- [x] Write unit tests for `_tokenize` and `_score_candidates` in `agent-index`: verify synonym expansion, token deduplication, and score ordering against a mock DB
- [x] Write unit tests for `parse_tasks_from_todo` in `agent-index`: verify phase extraction, done/undone detection, and task_id generation
- [x] Write CLI smoke test for `agent-index build` and `agent-index pack` against a temp repo fixture
- [x] Write CLI smoke test for `agent-telemetry ingest` and `agent-telemetry report` against synthetic JSONL fixture
- [x] Add `just test` recipe running `python3 -m unittest discover tests/ -v`

## Phase 2: Context Scoring Improvements

Fix two concrete scoring defects: path-only scoring misses files where task keywords appear
only in content, and symbol scoring uses hardcoded domain terms instead of task tokens.

- [ ] Add `synonyms` key to the `context` section of `agentkit.json`; merge repo-defined synonyms with built-in set in `_tokenize`
- [ ] In `_score_candidates`, add content-grep pass for top-30 path-scored candidates: read first 300 lines, add `+1.0` per task token match, capped at `+4.0` per file
- [ ] In `_pick_snippets`, replace hardcoded symbol keyword list with task token matching using `_tokenize` output
- [ ] Add `score_debug` field to `agent-index query` subcommand output with path/content/symbol score breakdown
- [ ] Write unit tests for updated `_tokenize` with repo-supplied synonyms and content-grep scoring path

## Phase 3: Security Hardening

Add JSON schema validation for `agentkit.json` and a trust gate for Python adapter loading.

- [ ] Define JSON schema for `agentkit.json` as a Python dict constant in `agentkit_common.py` covering all config sections
- [ ] Add `validate_repo_config(cfg) -> list[str]` to `agentkit_common.py`; call from `load_repo_config` with stderr warnings (non-fatal)
- [ ] Add `allow_custom_adapters` boolean key (default `false`) to `extract` schema; skip python-type adapters with clear stderr error when absent or false
- [ ] Add `--allow-custom-adapters` CLI flag to `agent-index build` and `agent-index refresh`
- [ ] Write unit tests for `validate_repo_config` schema violations and adapter trust gate behavior

## Phase 4: Telemetry Trend Exposure

Surface the `v_trends` view that already exists in the telemetry DB but is never displayed.

- [ ] Add `trend` subcommand to `agent-telemetry` rendering `v_trends` as a day table (day, tasks, tokens_total, avg_duration_s, loc_changed); default 30-day window
- [ ] Add `--since YYYY-MM-DD` flag to `agent-telemetry report`, `hotspots`, and `trend` as alternative to `--window-days`
- [ ] Add `just telemetry-trend` recipe following existing wrapper pattern in justfile
- [ ] Extend `agent-telemetry report` with one-line velocity summary (tasks in window, total tokens, mean duration, trend direction)
- [ ] Write unit tests for `trend` subcommand output format and `--since` date parsing against a synthetic DB
