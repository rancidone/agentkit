---
allowed-tools: Bash
description: Refresh agent index for current repo (light by default)
---

Run:

```bash
command -v agent-index
agent-index refresh --repo . --mode light
```

If arguments include `full`, run:

```bash
agent-index refresh --repo . --mode full
```
