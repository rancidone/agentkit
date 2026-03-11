---
allowed-tools: all
description: Orchestrate TODO.md using scoped lifecycle commands and just recipes
---

# TODO Orchestrator v2.0 (Scoped)

ARGS: optional `--max-parallel N` (default `2`, max `3`).

## Inputs

- TODO source: `TODO.md`
- Repo config: `agentkit.json` (fallback `.claude/agentkit.json`)
- Event log: `.claude/agent-events.jsonl`
- Required CLIs: `just`, `agent-index`, `agent-telemetry`, `agent-log`

## Setup

1. Validate command docs and guardrails:

```bash
just validate-command-docs
```

2. Reject unsafe ad-hoc command shapes before running custom commands:

```bash
just command-guard "<candidate-command>"
```

3. Refresh full index baseline:

```bash
just index-refresh-full
```

4. Ingest telemetry baseline:

```bash
just telemetry-ingest
```

5. Create or reuse the session branch:

```bash
just session-branch todo
```

Record this output as `SESSION_BRANCH`.

## Task Selection Rules

- Read unchecked `[ ]` items in `TODO.md`.
- Respect phase order.
- Select only independent tasks.
- Default mode is **tasks-first**. Do not spawn workers unless the worker-switch heuristic is satisfied.
- Keep `--max-parallel N` as a planning limit for independent tasks, not a default worker count.
- Worker-switch heuristic:
  - Require at least `2` independent tasks selected from the current phase.
  - Require each selected task to be medium or high complexity.
  - Otherwise stay in tasks-first mode.

## Tasks-First Branch (Default)

For each selected task, run:

1. Build task context pack:

```bash
just context-pack "<exact task text>" "/tmp/agentpack-<id>.json"
```

2. Log lifecycle start:

```bash
just task-started "<task_id>" "<SESSION_BRANCH>" "<exact task text>"
```

3. Execute directly in-session with lifecycle commands:

```bash
/next "<exact task text>"
```

4. If complete, mark TODO item `[x]` and log completion:

```bash
just task-completed "<task_id>" "<SESSION_BRANCH>"
```

5. If failed, record:

```bash
just task-failed "<task_id>" "<SESSION_BRANCH>" failed
```

## Worker Branch (Conditional Escalation)

Only enter this branch when the worker-switch heuristic passes.

As each worker finishes:

1. Verify merge target is not `main` or `develop`.
2. Run changed-scope checks and policy checks.
3. Merge worker branch into `SESSION_BRANCH`.
4. Mark TODO item `[x]`.
5. Log worker and task completion:

```bash
just worker-merged "<task_id>" "<SESSION_BRANCH>" merged
```

```bash
just task-completed "<task_id>" "<SESSION_BRANCH>"
```

If merge gate fails, record:

```bash
just task-failed "<task_id>" "<SESSION_BRANCH>" failed
```

After each merge, refresh baseline data:

```bash
just index-refresh-light
```

```bash
just telemetry-ingest
```

## Lifecycle Command Requirement

Use lifecycle commands for implementation and validation flow:

- `/next <task>` to execute implementation workflow
- `/check` to fix quality issues
- `/validate` for deep validation
- `/prompt <task>` to synthesize complete execution prompts

## Finish

```bash
just telemetry-report
```

```bash
just telemetry-hotspots
```

Never merge into `main` or `develop` from this command.
