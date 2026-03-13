---
name: agentkit-todo-codex
description: Run Agentkit TODO.md execution workflows in Codex using MCP-backed repo and telemetry tools, with temporary local helpers only where MCP parity is not complete.
---

# Agentkit TODO Codex

Use this skill as the supported user-facing orchestration layer for TODO.md execution in `agentkit`. It shares the same tasks-first workflow contract as the Claude-side `agentkit-todo-claude` skill while backend CLIs and wrappers remain temporary implementation details where MCP parity is incomplete.

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

## Codex Note

When calling the telemetry workflow in Codex, keep the existing runner-aware behavior: ingest should select Codex usage logs by default and only broaden scope when explicitly required.
