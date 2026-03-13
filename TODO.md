# TODO

## Active

### Phase 1: Bootstrap MCP Without Breaking Dogfooding

- [x] Add a migration constraint to the implementation and docs: this repo must keep using agentkit to execute its own `TODO.md` workflow throughout the migration
- [x] Define the bootstrap rule: until MCP plus skills reach workflow parity, keep the minimum in-repo compatibility path needed for this repo to continue dogfooding `start-todo`, `next`, `check`, `validate`, `prompt`, `index-refresh`, and `telemetry-report`
- [x] Split the backend into two MCP services:
  `agentkit-repo-mcp` for index, context, and config operations
  `agentkit-telemetry-mcp` for telemetry, state, and task lifecycle operations
- [x] Refactor current script logic into importable Python modules so both MCP services and temporary compatibility shims call the same code
- [x] Decide and document the bootstrap execution path for this repo itself:
  skills orchestrate MCP first when available
  temporary local adapters are allowed only where needed to keep this repo operational during the migration
- [ ] Keep current SQLite state and repo config behavior unchanged during this phase

### Phase 2: Expose Core MCP Tool Surface

- [ ] Implement `agentkit-repo-mcp` stdio server with these tools:
  `index.build`
  `index.refresh`
  `index.query`
  `index.pack`
  `index.inspect`
- [ ] Implement `agentkit-telemetry-mcp` stdio server with these tools:
  `telemetry.ingest`
  `telemetry.report`
  `telemetry.hotspots`
  `telemetry.trend`
  `telemetry.inspect`
  `task.log_started`
  `task.log_completed`
  `task.log_failed`
  `task.log_worker_spawned`
  `task.log_worker_merged`
- [ ] Keep MCP outputs structurally aligned with current JSON-producing CLI behavior to minimize orchestration churn
- [ ] Remove CLI-only concerns from shared logic where they do not belong in MCP, especially file-output behavior for `index.pack`
- [ ] Add first-class inspect tools so the current introspection gaps are solved in the MCP surface instead of as more ad-hoc scripts

### Phase 3: Replace Commands With Skills

- [ ] Retire Claude command markdown as a supported interface
- [ ] Rework agentkit skills so skills are the only user-facing orchestration layer
- [ ] Update the Codex skill and add or align Claude-side skill packaging so both clients orchestrate the same MCP-backed workflow semantics
- [ ] Rewrite workflow logic so skills call MCP tools instead of local wrapper scripts for:
  `start-todo`
  `next`
  `check`
  `validate`
  `prompt`
  `index-refresh`
  `telemetry-report`
- [ ] Preserve current dogfooding workflow semantics during migration:
  tasks-first default remains intact unless explicitly changed later
  task lifecycle logging remains available for repo self-use
  index and telemetry refresh steps still work for this repo's own TODO execution
- [ ] Update `start-todo` spec so the repo can continue implementing its own TODOs via the new MCP-backed skills during rollout

### Phase 4: Install And Uninstall Redesign

- [ ] Replace `agent-install-global-tools` with an install flow centered on:
  MCP service registration and config
  skill installation and linking
  manifest recording of every installed artifact
- [ ] Stop installing the current `agent-*` wrapper fleet into `~/.local/bin`
- [ ] Add `agent-uninstall` with default behavior: remove only agentkit-managed install artifacts
- [ ] For new installs, uninstall must remove:
  installed skill artifacts
  agentkit-owned MCP config entries or generated config files
  any managed launch helpers
  the install manifest
- [ ] For legacy installs, add best-effort cleanup that removes only:
  historical symlinks created by `agent-install-global-tools` that still point to this repo
  the legacy Codex skill symlink if it still points to this repo
- [ ] Default uninstall must not remove:
  telemetry DBs
  event logs
  repo-local data
  arbitrary user-created files or copied scripts
- [ ] Make uninstall idempotent and safe if paths moved or artifacts are already missing

### Phase 5: Repo Migration And Dogfood Cutover

- [ ] Add repo-local client config and examples so this repository itself can run against the two MCP services while developing the migration
- [ ] Convert this repo's own documented development workflow to use the MCP-backed skills first
- [ ] Keep a clearly documented temporary fallback path only until this repo can complete TODO work entirely through MCP-backed skills
- [ ] Declare the hard switch complete only when this repository can dogfood the new architecture end-to-end for its own TODO execution
- [ ] After successful dogfood cutover, deprecate remaining compatibility shims and remove them from the supported install surface

## Acceptance Criteria

- This repository can execute its own TODO workflow using agentkit skills backed by MCP services, without requiring globally installed `agent-*` wrappers
- `start-todo`, `next`, `check`, `validate`, `prompt`, `index-refresh`, and `telemetry-report` all work through skills as orchestrators over MCP
- Repo and index operations are served by `agentkit-repo-mcp`, and telemetry and state operations by `agentkit-telemetry-mcp`
- The new install flow sets up MCP services and skills, and records managed artifacts in a manifest
- Default uninstall removes managed install artifacts and legacy repo-owned symlinks, while preserving state DBs and logs
- This repo can continue dogfooding agentkit throughout the migration, with no period where its own TODO workflow is unsupported

## Test Plan

- Add unit tests for shared backend modules extracted from current scripts
- Add MCP server tests covering tool input validation and stable JSON outputs for both services
- Add workflow-level tests for MCP-backed skills covering current TODO execution flows
- Add install and uninstall tests for manifest-managed installs and legacy symlink cleanup
- Add dogfood smoke tests proving this repo can:
  build and refresh index
  pack task context
  log task lifecycle
  ingest and report telemetry
  drive TODO execution through skills

## Assumptions

- MCP is the execution and data provider layer; skills are the only supported user-facing orchestrators
- The backend split is exactly two MCP services
- Existing SQLite-backed state and repo config stay in place during the migration
- Command markdown is retired rather than migrated
- Default uninstall is conservative and preserves user and state data
