---
allowed-tools: Bash
description: Ingest and report telemetry via scoped just recipes
---

1. Validate command docs are safe:

```bash
just validate-command-docs
```

2. Ingest telemetry:

```bash
just telemetry-ingest
```

3. Print report:

```bash
just telemetry-report
```

4. Print hotspots:

```bash
just telemetry-hotspots
```
