---
name: agentkit-todo-claude
description: Run Agentkit TODO.md execution workflows in Claude using MCP-backed repo and telemetry tools, matching the Codex skill's tasks-first semantics during MCP migration.
---

# Agentkit TODO Claude

Use this skill as the supported user-facing orchestration layer for TODO.md execution in `agentkit` from Claude. It shares the same tasks-first workflow contract as the Codex-side `agentkit-todo-codex` skill while backend CLIs and wrappers remain temporary implementation details where MCP parity is incomplete.

## Safety Rules

1. Prefer MCP tools for repo, telemetry, and task lifecycle operations.
2. Use scoped local helpers only for gaps that are not yet exposed via MCP, such as session-branch creation, commit helpers, and direct test execution.
3. Do not use shell chaining, subshell expansion, heredocs, or ad-hoc pipelines.
4. Run `agent-validate-command-docs .` before orchestration and before custom command execution.
5. Never merge directly to `main` or `develop`.
6. During the MCP migration, preserve the repo-local TODO workflow as a compatibility path for this repository's own dogfooding until MCP plus skills reach parity.

## Inputs

- TODO source: `TODO.md`
- Migration contract: `MIGRATION.md`
- Repo config: `agentkit.json` (fallback `.claude/agentkit.json`)
- Event log: `.claude/agent-events.jsonl`
- Required MCP services:
  - `agentkit-repo-mcp`
  - `agentkit-telemetry-mcp`
- Temporary local helpers still allowed:
  - `agent-validate-command-docs`
  - `agent-command-guard`
  - `agent-session-branch`
  - `agent-commit-files`
  - repo-local test or lint commands

## Command Map

- `start-todo`: see `../shared/agentkit_todo_mcp_workflow.md#start-todo`
- `next`: see `../shared/agentkit_todo_mcp_workflow.md#next`
- `check`: see `../shared/agentkit_todo_mcp_workflow.md#check`
- `validate`: see `../shared/agentkit_todo_mcp_workflow.md#validate`
- `prompt`: see `../shared/agentkit_todo_mcp_workflow.md#prompt`
- `index-refresh`: see `../shared/agentkit_todo_mcp_workflow.md#index-refresh`
- `telemetry-report`: see `../shared/agentkit_todo_mcp_workflow.md#telemetry-report`

## Claude Note

When calling the telemetry workflow in Claude, keep the existing runner-aware behavior: ingest should select Claude usage logs by default and only broaden scope when explicitly required.
