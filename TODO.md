# TODO Plan: Tasks-First Claude Command Orchestration

## Plan
- [ ] Update `/start-todo` in [`claude/commands/start-todo.md`](/home/maddie/repos/agentkit/claude/commands/start-todo.md) to make tasks-first the default flow.
- [ ] Keep `--max-parallel N`, but document it as task concurrency planning, not default worker spawning.
- [ ] Add conservative worker auto-switch heuristic.
- [ ] Require `>=2` independent tasks.
- [ ] Require each selected task to be medium/high complexity.
- [ ] Otherwise remain in tasks-first mode.
- [ ] Split `/start-todo` flow into explicit branches.
- [ ] Tasks-first branch: `task-started` -> `/next` -> `task-completed` or `task-failed`.
- [ ] Worker branch: `worker-spawned` -> merge gate -> `worker-merged` -> `task-completed`/`task-failed`.
- [ ] Define lifecycle logging policy.
- [ ] Tasks-first path logs only `task_started`, `task_completed`, `task_failed`.
- [ ] No synthetic worker events when workers are not used.
- [ ] Align skill docs in [`skills/agentkit-todo-codex/SKILL.md`](/home/maddie/repos/agentkit/skills/agentkit-todo-codex/SKILL.md) with the same default, heuristic, and branching behavior.
- [ ] Update [`README.md`](/home/maddie/repos/agentkit/README.md) to state tasks-first default and worker flow as conditional escalation only.
- [ ] Validate command docs with `agent-validate-command-docs .`.
- [ ] Run consistency checks (`rg`) so worker-first/default wording is removed from command + skill + README docs.
- [ ] Verify doc scenarios are covered.
- [ ] Simple single-file edit -> tasks-first, no worker events.
- [ ] Multi-task medium/high complexity -> worker branch allowed.
- [ ] Task failure in tasks-first -> `task-failed` without worker logs.

## Assumptions
- [ ] Scope is documentation/workflow guidance only (no runtime scheduler implementation changes in this pass).
- [ ] Complexity classification remains operator-judgment based in docs.

# Plan 2: Build Cross-Agent Planning Skill (Phased TODOs)

## Phase 1: Define Output Contract
- [ ] Require final output to be a single fenced `md` block.
- [ ] Specify that TODOs must be machine-parseable by Claude and Codex.
- [ ] Prohibit extra prose outside the TODO block in strict mode.

## Phase 2: Define Standard Task Schema
- [ ] Set required fields: `id`, `slug`, `title`, `status`, `priority`, `deps`, `acceptance_criteria`, `verification`.
- [ ] Enforce ID format as sequential (`T001`, `T002`, ...).
- [ ] Store slug on every task (paired directly with ID).
- [ ] Enforce status set: `todo|in_progress|blocked|done`.

## Phase 3: Define Formatting Rules
- [ ] Lock fixed field order for every task.
- [ ] Add explicit delimiter rules between tasks.
- [ ] Define dependency syntax referencing task IDs only.
- [ ] Document uniqueness requirements for `id` and `slug`.

## Phase 4: Provide Canonical Example
- [ ] Add one complete sample TODO block using the exact schema.
- [ ] Include at least one dependency chain.
- [ ] Include at least one `blocked` and one `in_progress` task.
- [ ] Ensure sample is copy-paste ready for both Claude and Codex skills.

## Phase 5: Validation Criteria
- [ ] Add checklist for required-field completeness.
- [ ] Add checks for sequential IDs and unique slugs.
- [ ] Add checks for valid status vocabulary.
- [ ] Add checks that all `deps` reference existing IDs.
- [ ] Add check that output remains exactly one fenced `md` block.

## Assumptions
- Primary key is `id`; secondary lookup key is `slug`.
- The skill text remains platform-agnostic Markdown.
- Wrapping into Claude/Codex-specific skill packaging is done afterward without changing schema semantics.
