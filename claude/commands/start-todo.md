---
allowed-tools: all
description: Orchestrate TODO.md with bounded parallelism, context packs, telemetry, and soft tool governance
---

# TODO Orchestrator v1.2 (Portable)

ARGS: optional `--max-parallel N` (default `2`, max `3`).

## Inputs

- TODO source: `TODO.md`
- Repo config: `agentkit.json` (fallback `.claude/agentkit.json`)
- Event log: `.claude/agent-events.jsonl`
- Required CLIs on `PATH`: `agent-index`, `agent-telemetry`, `agent-log`

## Setup

1. Verify required CLIs are available:

```bash
command -v agent-index agent-telemetry agent-log
```

2. Determine parallelism from args:
- If missing, use `2`
- Clamp to `1..3`

3. Refresh metadata index before planning:

```bash
agent-index refresh --repo . --mode full
```

4. Start telemetry ingestion baseline:

```bash
agent-telemetry ingest --repo . --claude-home ~/.claude --events ./.claude/agent-events.jsonl
```

5. Create a unique session branch (unless already on `todo/*`):

```bash
git branch --show-current
git checkout -b todo/$(date +%Y%m%d-%H%M%S)
```

Record this as `SESSION_BRANCH`.

## Task Selection Rules

- Read unchecked `[ ]` items in TODO.md.
- Respect phase order (no later phase before earlier unfinished phase).
- Only select independent tasks (no shared primary files, no direct dependency chain).
- Always keep up to `N` active workers while eligible tasks remain.

## Per-Task Dispatch

For each selected task:

1. Create a context pack:

```bash
agent-index pack --repo . --task "<exact task text>" --token-budget 2800 --out /tmp/agentpack-<id>.json
```

2. Append `task_started` event:

```bash
agent-log --events .claude/agent-events.jsonl \
  --event-type task_started \
  --field repo="$(pwd)" \
  --field session_branch=<SESSION_BRANCH> \
  --field task_id=<task_id> \
  --field "task_text=<exact task text>"
```

3. Spawn worker agent in `isolation: "worktree"`.

Also append `worker_spawned` event:

```bash
agent-log --events .claude/agent-events.jsonl \
  --event-type worker_spawned \
  --field repo="$(pwd)" \
  --field task_id=<task_id> \
  --field session_branch=<SESSION_BRANCH>
```

## Merge Gate (Balanced)

As each worker finishes (do not wait for full batch):

1. Verify merge target is not `main` or `develop`.
2. Run changed-scope checks (based on changed files + `agentkit.json` hints).
3. Run policy checks:
- no banned broad-scan patterns used in worker notes
- no unbounded-output command usage
4. Merge worker branch into `SESSION_BRANCH`.
5. Resolve conflicts and commit if needed.
6. Mark TODO item `[x]` and commit TODO update.
7. Append events:

```bash
agent-log --events .claude/agent-events.jsonl \
  --event-type worker_merged \
  --field repo="$(pwd)" \
  --field task_id=<task_id> \
  --field session_branch=<SESSION_BRANCH>

agent-log --events .claude/agent-events.jsonl \
  --event-type task_completed \
  --field repo="$(pwd)" \
  --field session_branch=<SESSION_BRANCH> \
  --field task_id=<task_id>
# Use task_failed instead of task_completed if gate fails
```

After each merge, run light refresh + telemetry ingest:

```bash
agent-index refresh --repo . --mode light
agent-telemetry ingest --repo . --claude-home ~/.claude --events ./.claude/agent-events.jsonl
```

## Finish

When no unchecked TODO items remain:

```bash
agent-telemetry report --repo . --window-days 7
agent-telemetry hotspots --repo . --window-days 7 --limit 12
```

Never merge into `main` or `develop` from this command.
