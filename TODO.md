# Agentkit — Implementation TODO

---

## Phase 1: Tighten Approval Workflow

- [ ] Add focused wrapper scripts for common `agent-log` and telemetry actions so commands avoid broad patterns (`$(...)`, pipes, mixed reads) that trigger wide approval prompts
- [ ] Update command docs/examples to use only those wrappers in normal operation
- [ ] Add a small validation check that rejects unsafe command shapes before execution and suggests the narrow wrapper alternative
- [ ] Split post-batch refresh into dedicated wrappers (e.g., `agent-index-refresh-light`, `agent-telemetry-ingest`) so callers do not use multiline commands, `2>&1`, or `| tail`
- [ ] Import task lifecycle command definitions from `~/.claude/commands` (`next.md`, `validate.md`/`check.md`, `prompt.md`) into repo-local `claude/commands/` with scoped argument interfaces and no shell composition requirements
- [ ] Update orchestration prompts (`claude/commands/*.md`) to require lifecycle commands instead of inline multi-step shell snippets
