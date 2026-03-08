---
allowed-tools: Bash
description: Ingest Claude logs and print token telemetry reports
---

1. Verify CLI availability:

```bash
command -v agent-telemetry
```

2. Ingest latest logs and task events:

```bash
agent-telemetry ingest --repo . --claude-home ~/.claude --events ./.claude/agent-events.jsonl
```

3. Print summary:

```bash
agent-telemetry report --repo . --window-days 7
```

4. Print hotspots:

```bash
agent-telemetry hotspots --repo . --window-days 7 --limit 12
```
