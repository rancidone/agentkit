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


## Project-Specific Extraction Adapters

`agent-index` supports adapter plugins so each repo can add domain-specific symbol extraction.

### Built-in adapters

Use adapter names in `agentkit.json`:

- `esp-idf-http-routes`
- `svelte-live-api`
- `typescript-stores`

Example:

```json
{
  "extract": {
    "enabled": true,
    "adapters": [
      {
        "type": "builtin",
        "name": "esp-idf-http-routes",
        "include_ext": ["c", "h"],
        "include_paths": ["components/http_server/"]
      },
      {
        "type": "builtin",
        "name": "svelte-live-api",
        "include_ext": ["ts", "svelte"],
        "include_paths": ["src/lib/api/", "src/lib/stores/"]
      }
    ]
  }
}
```

### Custom python adapters

You can load adapters from repo files (trusted repos only).

```json
{
  "extract": {
    "adapters": [
      {
        "type": "python",
        "name": "custom-c-router",
        "file": "tools/agentkit/custom_adapter.py",
        "function": "extract",
        "include_ext": ["c", "h"],
        "include_paths": ["components/http_server/"]
      }
    ]
  }
}
```

Template: `examples/custom_adapter.py`

## License

MIT
