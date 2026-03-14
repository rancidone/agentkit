# TODO

## Done

- [x] Dogfood the repo-local MCP-first TODO workflow in this checkout.
- [x] Add `agent-telemetry migrate` for legacy DB upgrade and relative-path event recovery.
- [x] Lock migration behavior with CLI and MCP tests.

## Next

- [ ] Enforce test-first changes for behavior-affecting work in this repo. For any non-trivial logic change, write or update failing tests first, then implement the code, then rerun the relevant test scope before closing the task.
- [ ] Audit current automated coverage for install, MCP, telemetry, index, and skill workflow behavior. Identify which user-facing contracts are only documented or manually exercised and which ones are protected by fixture-backed tests.
- [ ] Turn the coverage audit into a concrete gap list with priorities. Call out missing tests for installer/runtime integration, skill contract assumptions, migration paths, and any logic that previously relied on unverified environment assumptions.
- [x] Fresh `agent-install` is not sufficient for the shipped TODO skills: the install flow no longer exposes helper commands on `PATH`, but `agentkit-todo-codex` and `agentkit-todo-claude` still require bare-command access to `agent-validate-command-docs`, `agent-session-branch`, and `agent-commit-files`. Fix the install/runtime contract so a default install can actually execute the documented workflow.
- [x] Choose and implement a compatibility path for helper command resolution. Either install a managed helper bin dir and surface it clearly to Codex/Claude runtime environments, or update the skills/workflow/docs to invoke repo-rooted helpers explicitly instead of assuming global command availability.
- [x] Add install coverage for helper-command availability after `agent-install`. Tests should fail if a fresh install produces MCP config and skill links but leaves the required compatibility helpers unreachable from the runtime the skills expect.
- [x] Define the telemetry TUI scope: views, navigation model, filters, and read-only data contract.
- [x] Add a backend surface for the TUI to query report, trend, hotspots, and task-run detail without duplicating CLI formatting.
- [x] Build an initial terminal UI for exploring task runs, token trends, hotspots, and migration status from one session.
- [x] Add fixture-backed tests for TUI data loading and core interactions.
- [x] Document the TUI workflow and operator entrypoints once the interface is stable.
- [ ] MCP silent failure: when `agentkit-repo-mcp` or `agentkit-telemetry-mcp` are not loaded/reachable, the skill proceeds silently with degraded behavior. Should emit a clear warning on first MCP call failure so operators know to check `.claude/agentkit/mcp-servers.json` registration.
- [ ] `agent-install` writes MCP config to `~/.claude/agentkit/mcp-servers.json` but Claude Code loads servers from `~/.claude/mcp.json` (global) or `.mcp.json` (project root) — the agentkit path is never auto-loaded. Fix `agent-install` to merge agentkit servers into `~/.claude/mcp.json` (with backup) so the MCP tools are actually available after install, and update `agent-uninstall` to remove them cleanly.
- [ ] Missing repo-id lookup: initializing a new repo required manually computing the SHA256 repo-id to verify state DB presence. Add `agent-index list-repos` (or `agent-index status`) that maps each state DB to its resolved repo path and shows index freshness.
- [ ] Define a prompt-attribution telemetry model that explains high token usage without breaking current reports. Decide what to persist per usage event or per prompt fingerprint, which raw prompt fields are safe to retain, and how Claude/Codex records map onto one shared schema.
- [ ] Add backward-compatible prompt telemetry storage and migration. Prefer additive tables or nullable columns plus `agent-telemetry migrate`/`rebuild` support so existing DBs, reports, and MCP consumers keep working until prompt attribution data is present.
- [ ] Extend ingest to capture prompt metadata from raw logs when available. Start with prompt fingerprints, role/source, size metrics, and optional redacted preview fields so large-token sessions can be grouped by repeated prompt patterns without requiring full prompt-body retention.
- [ ] Add prompt cost analysis surfaces to CLI/MCP/TUI. Operators should be able to see top prompt fingerprints by total tokens, average tokens per invocation, and recent high-cost outliers, with clear confidence labels when attribution is inferred rather than exact.
- [ ] Document retention, privacy, and rollout rules for deeper telemetry. Include defaults for redaction/off-by-default raw prompt capture, the migration path for older telemetry DBs, and how operators should enable and interpret the new prompt-level views.
