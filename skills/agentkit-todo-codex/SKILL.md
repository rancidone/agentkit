---
name: agentkit-todo-codex
description: Run Agentkit TODO.md execution workflows in Codex using strict just/agent wrapper commands, including start-todo, next, check, validate, prompt, index-refresh, and telemetry-report flows.
---

# Agentkit TODO Codex

Use this skill as the supported user-facing orchestration layer for TODO.md execution in `agentkit`. Backend CLIs and wrappers remain implementation details for now.

## Safety Rules

1. Prefer scoped `agent-*` wrappers.
2. Do not use shell chaining, subshell expansion, heredocs, or ad-hoc pipelines.
3. Run `agent-validate-command-docs .` before orchestration and before custom command execution.
4. Never merge directly to `main` or `develop`.
5. During the MCP migration, preserve the repo-local TODO workflow as a compatibility path for this repository's own dogfooding until MCP plus skills reach parity.

## Inputs

- TODO source: `TODO.md`
- Migration contract: `MIGRATION.md`
- Repo config: `agentkit.json` (fallback `.claude/agentkit.json`)
- Event log: `.claude/agent-events.jsonl`
- Required CLIs: `agentkit` toolset on PATH (`agent-*`, `agent-index`, `agent-telemetry`)

## Command: start-todo

ARGS: optional `--max-parallel N` (default `2`, max `3`).

Run setup:

```bash
agent-validate-command-docs .
```

```bash
agent-command-guard "<candidate-command>"
```

```bash
agent-index-refresh-full .
```

```bash
agent-telemetry-ingest . "$HOME/.claude" .claude/agent-events.jsonl
```

In Codex, the ingest wrapper must auto-select Codex logs from the active runner environment instead of ingesting Claude usage logs by default.

```bash
agent-session-branch todo
```

Record session-branch output as `SESSION_BRANCH`.

Task selection and dispatch:

1. Read unchecked `[ ]` items in `TODO.md`.
2. Respect phase order.
3. Select only independent tasks.
4. Default to tasks-first mode.
5. Keep `--max-parallel N` as task concurrency planning, not default worker spawning.
6. Switch to worker mode only when all are true:
   - At least `2` independent tasks are selected.
   - Each selected task is medium/high complexity.
   - Otherwise remain in tasks-first mode.
7. Do not select or execute work that would leave this repo unable to run its own `start-todo`, `next`, `check`, `validate`, `prompt`, `index-refresh`, or `telemetry-report` flow before MCP parity exists.

Per selected task:

```bash
agent-index pack --repo . --task "<exact task text>" --token-budget 2800 --limit 12 --out "/tmp/agentpack-<id>.json"
```

```bash
agent-log-task-started . "<task_id>" "<SESSION_BRANCH>" "<exact task text>"
```

Tasks-first branch (default):

1. Execute task via `/next "<exact task text>"`.
2. If successful, mark TODO item `[x]` and log:

```bash
agent-log-task-complete . "<task_id>" "<SESSION_BRANCH>"
```

3. If failed, log:

```bash
agent-log-task-failed . "<task_id>" "<SESSION_BRANCH>" failed
```

No worker lifecycle events in this branch.

Worker branch (conditional escalation):

**Compact context before spawning workers** to avoid context bleed and redundant re-reads in sub-agents.

1. Log worker start:

```bash
agent-log-worker-spawned . "<task_id>" "<SESSION_BRANCH>"
```

2. Verify merge target is not `main` or `develop`.
3. Run changed-scope checks and policy checks.
4. Merge worker branch into `SESSION_BRANCH`.
5. Mark TODO item `[x]`.

Then log:

```bash
agent-log-worker-merged . "<task_id>" "<SESSION_BRANCH>" merged
```

```bash
agent-log-task-complete . "<task_id>" "<SESSION_BRANCH>"
```

If merge gate fails:

```bash
agent-log-task-failed . "<task_id>" "<SESSION_BRANCH>" failed
```

After each merge, refresh:

```bash
agent-index-refresh-light .
```

```bash
agent-telemetry-ingest . "$HOME/.claude" .claude/agent-events.jsonl
```

Finish:

```bash
agent-telemetry-report . 7
```

```bash
agent-telemetry-hotspots . 7 12
```

## Command: next

Implement: `<task text>`

Branch setup:

```bash
git branch --show-current
```

If not already on `feat/*` or `todo/*`:

```bash
agent-session-branch feat
```

Workflow:

1. Research relevant files before edits.
2. Implement changes directly.
3. Run `check`.
4. Run `validate`.

Completion lifecycle:

```bash
agent-log-task-started . "<task_id>" "<session_branch>" "<task text>"
```

```bash
agent-commit-files --message-file <path-to-message-file>
```

```bash
agent-log-task-complete . "<task_id>" "<session_branch>"
```

Then mark TODO item `[x]`.

## Command: check

1. Run applicable lint/test/build/format/security checks.
2. Fix every issue found.
3. Re-run checks until all pass.

Guardrail:

```bash
agent-validate-command-docs .
```

Success criteria: all applicable checks pass with zero errors.

## Command: validate

Start with this exact sentence:

`Let me ultrathink about this implementation and examine the code closely`

Validation criteria:

1. Task completeness and edge cases.
2. Code quality and boundary error handling.
3. Architecture consistency with existing patterns.
4. Hidden risks: race, security, performance, missing tests.

Response format:

- `Done Well:` specific achievements
- `Issues Found:` problems with severity
- `Verdict:` completion status

If issues exist, fix them immediately.

## Command: prompt

To synthesize a full execution prompt:

1. Use the `Command: next` section in this skill as the base template.
2. Replace `Implement: <task text>` with the user task text.
3. Output the complete prompt in a code block.
4. Preserve lifecycle workflow and scoped wrappers.

## Command: index-refresh

```bash
agent-validate-command-docs .
```

Default:

```bash
agent-index-refresh-light .
```

If arguments include `full`:

```bash
agent-index-refresh-full .
```

## Command: telemetry-report

```bash
agent-validate-command-docs .
```

```bash
agent-telemetry-ingest . "$HOME/.claude" .claude/agent-events.jsonl
```

```bash
agent-telemetry-report . 7
```

```bash
agent-telemetry-hotspots . 7 12
```
