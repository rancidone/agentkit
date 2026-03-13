# Agentkit TODO MCP Workflow

This reference defines the shared tasks-first workflow contract for the Codex and Claude Agentkit TODO skills.

Temporary local helpers remain allowed only where MCP parity is incomplete. All repo, telemetry, and task lifecycle operations should use MCP tools first.

## start-todo

Setup:

1. Run `agent-validate-command-docs .`.
2. Use the repo MCP tool `index.refresh` with `{"repo": ".", "mode": "full"}`.
3. Use the telemetry MCP tool `telemetry.ingest` with the repo and event-log inputs.
4. Use the temporary compatibility helper `agent-session-branch todo` to create or reuse the session branch until branch/session state is served via MCP.

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

1. Use repo MCP `index.pack` with `repo`, `task`, `token_budget`, and `limit`.
2. Use telemetry MCP `task.log_started`.

Tasks-first branch:

1. Execute the implementation workflow via the skill `next` contract.
2. If successful, mark the TODO item `[x]` and use telemetry MCP `task.log_completed`.
3. If failed, use telemetry MCP `task.log_failed`.

Worker branch:

1. Use telemetry MCP `task.log_worker_spawned`.
2. Verify merge target is not `main` or `develop`.
3. Run changed-scope checks and policy checks.
4. Merge the worker branch into the session branch.
5. Mark the TODO item `[x]`.
6. Use telemetry MCP `task.log_worker_merged` and `task.log_completed`.
7. If merge gate fails, use telemetry MCP `task.log_failed`.

After each merge:

1. Use repo MCP `index.refresh` with `mode` `light`.
2. Use telemetry MCP `telemetry.ingest`.

Finish:

1. Use telemetry MCP `telemetry.report`.
2. Use telemetry MCP `telemetry.hotspots`.

## next

1. Confirm the current branch with `git branch --show-current`.
2. If not already on `feat/*` or `todo/*`, use the temporary compatibility helper `agent-session-branch feat`.
3. Research relevant files before edits.
4. Use repo MCP `index.pack` for task context gathering.
5. Implement changes directly.
6. Run the skill `check` contract.
7. Run the skill `validate` contract.
8. Use telemetry MCP `task.log_started` and `task.log_completed` for lifecycle events.
9. Use `agent-commit-files --message-file ...` for commit creation until commit operations are served via MCP.
10. Mark the TODO item `[x]`.

## check

1. Run `agent-validate-command-docs .`.
2. Use repo MCP `config.load` and `index.inspect` to confirm repo config and index state before selecting checks.
3. Run applicable lint, test, build, format, and security checks with repo-local tooling.
4. Fix every issue found.
5. Re-run checks until all pass with zero errors.

## validate

Start with this exact sentence:

`Let me ultrathink about this implementation and examine the code closely`

Validation criteria:

1. Task completeness and edge cases.
2. Code quality and boundary error handling.
3. Architecture consistency with existing patterns.
4. Hidden risks: race, security, performance, missing tests.

Use MCP inspection surfaces to ground the review:

1. Repo MCP `index.inspect`
2. Repo MCP `config.load`
3. Telemetry MCP `telemetry.inspect`
4. Telemetry MCP `task.inspect` when validating a task-specific execution path

Response format:

- `Done Well:` specific achievements
- `Issues Found:` problems with severity
- `Verdict:` completion status

If issues exist, fix them immediately.

## prompt

1. Use the `next` contract in this reference as the base template.
2. Replace the task placeholder with the user task text.
3. Use repo MCP `index.pack` to enrich the prompt with task-scoped context.
4. Output the complete prompt in a code block.
5. Preserve lifecycle workflow and temporary compatibility helpers where MCP parity is incomplete.

## index-refresh

1. Run `agent-validate-command-docs .`.
2. Default to repo MCP `index.refresh` with `{"repo": ".", "mode": "light"}`.
3. If arguments include `full`, use repo MCP `index.refresh` with `{"repo": ".", "mode": "full"}`.

## telemetry-report

1. Run `agent-validate-command-docs .`.
2. Use telemetry MCP `telemetry.ingest`.
3. Use telemetry MCP `telemetry.report`.
4. Use telemetry MCP `telemetry.hotspots`.
