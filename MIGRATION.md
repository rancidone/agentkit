# Migration Bootstrap Contract

This repository must keep using agentkit to execute its own `TODO.md` workflow throughout the MCP migration.

## Non-negotiable Constraint

At no point in the migration may this repository lose the ability to dogfood its own workflow with agentkit-managed orchestration.

Until the MCP-backed workflow reaches parity, this repo must continue to support its own execution of:

- `start-todo`
- `next`
- `check`
- `validate`
- `prompt`
- `index-refresh`
- `telemetry-report`

## Bootstrap Rule

Skills orchestrate MCP-first when the required MCP tool behavior exists.

Until that parity is complete, keep the minimum in-repo compatibility path needed for this repository to continue running the workflow above against this repo's own `TODO.md`.

That compatibility path may include temporary local adapters or shims, but only when they are required to preserve repo self-hosting during the migration.

Do not remove or de-support the repo-local compatibility path until MCP plus skills can replace it for this repository end to end.
