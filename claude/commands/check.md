---
allowed-tools: all
description: Run quality checks and fix issues until clean
---

# Code Quality Check (Scoped)

Fix all issues found during verification. Do not only report problems.

## Workflow

1. Run applicable lint/test/build/format/security checks.
2. Fix every issue found.
3. Re-run checks until all pass.

## Guardrails

1. Validate command docs first:

```bash
just validate-command-docs
```

2. Prefer scoped recipes/wrappers over chained shell commands.

## Success Criteria

All applicable checks pass with zero errors.
