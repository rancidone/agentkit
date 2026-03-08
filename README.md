# agentkit

Framework-neutral CLI tooling for coding-agent workflows.

## Includes

- `agent-index`: lightweight repository indexing and task-scoped context pack generation.
- `agent-telemetry`: local telemetry ingestion/reporting from Claude JSONL logs.

## Goals

- Token-efficient context packaging for worker agents.
- Task-level telemetry and KPI tracking (`tokens per completed TODO`).
- Policy-aware orchestration support (allowlist + soft warnings).

## Requirements

- Python 3.10+
- Git (for repository detection)

## Quick Start

```bash
./agent-index build --repo . --mode full
./agent-index pack --repo . --task "implement SSE endpoint" --out /tmp/pack.json

./agent-telemetry ingest --repo . --claude-home ~/.claude --events ./.claude/agent-events.jsonl
./agent-telemetry report --repo . --window-days 7
./agent-telemetry hotspots --repo . --window-days 7 --limit 12
```

## License

MIT
