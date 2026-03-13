---
name: agentkit-todo-claude
description: Run Agentkit TODO.md execution workflows in Claude using strict just/agent wrapper commands, matching the Codex skill's tasks-first semantics during MCP migration.
---

# Agentkit TODO Claude

Use this skill as the supported user-facing orchestration layer for TODO.md execution in `agentkit` from Claude. It shares the same tasks-first workflow contract as the Codex-side `agentkit-todo-codex` skill while backend CLIs and wrappers remain implementation details for now.

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

## Workflow Contract

This skill intentionally matches the Codex skill semantics:

1. `start-todo` defaults to tasks-first execution.
2. Worker-branch flow is used only when multiple independent medium/high-complexity tasks justify it.
3. Lifecycle logging remains task-scoped in tasks-first mode.
4. The repo-local compatibility path stays intact until MCP-backed skills reach parity.

Use [skills/agentkit-todo-codex/SKILL.md](/home/maddie/repos/agentkit/skills/agentkit-todo-codex/SKILL.md) as the authoritative step-by-step workflow contract until the shared MCP-backed implementation replaces the wrapper-based compatibility path.
