# Agentkit — Implementation TODO

---

## Phase 1: Tighten Approval Workflow

- [ ] Add focused wrapper scripts for common `agent-log` and telemetry actions so commands avoid broad patterns (`$(...)`, pipes, mixed reads) that trigger wide approval prompts
- [ ] Update command docs/examples to use only those wrappers in normal operation
- [ ] Add a small validation check that rejects unsafe command shapes before execution and suggests the narrow wrapper alternative
- [ ] Split post-batch refresh into dedicated wrappers (e.g., `agent-index-refresh-light`, `agent-telemetry-ingest`) so callers do not use multiline commands, `2>&1`, or `| tail`
- [ ] Import task lifecycle command definitions from `~/.claude/commands` (`next.md`, `validate.md`/`check.md`, `prompt.md`) into repo-local `claude/commands/` with scoped argument interfaces and no shell composition requirements
- [ ] Update orchestration prompts (`claude/commands/*.md`) to require lifecycle commands instead of inline multi-step shell snippets
- [ ] Add a narrow commit helper (e.g., `agent-commit-files --message-file`) and update prompts to avoid `$(...)`, heredocs, and chained `git add && git commit` one-liners

## Phase 2: Orchestration Migration (Hybrid + just)

- [ ] Add a `justfile` with scoped orchestration recipes (`index-refresh-light/full`, `telemetry-ingest/report/hotspots`, task lifecycle event recipes) to replace inline shell snippets in prompts/docs
- [ ] Refactor `agent-log` to use safe JSON encoding (no manual string concatenation) and preserve current CLI args
- [ ] Normalize helper defaults to repo-local `.claude/agent-events.jsonl` (remove toolkit-local default fallbacks)
- [ ] Import/adapt global Claude lifecycle commands (`next`, `validate`/`check`, `prompt`) into repo-local `claude/commands/`
- [ ] Update `claude/commands/start-todo.md`, `index-refresh.md`, and `telemetry-report.md` to invoke only single-purpose `just` recipes
- [ ] Add a guard check that fails if command docs reintroduce disallowed shell patterns (`$(...)`, heredocs, multiline chains, `2>&1 | tail`)
