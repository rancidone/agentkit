---
allowed-tools: Bash
description: Refresh agent index via scoped just recipes
---

Run a guarded index refresh.

1. Validate command docs are safe:

```bash
just validate-command-docs
```

2. Default refresh mode:

```bash
just index-refresh-light
```

3. If arguments include `full`, run:

```bash
just index-refresh-full
```
