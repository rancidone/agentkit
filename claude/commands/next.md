---
allowed-tools: all
description: Execute production implementation with scoped lifecycle wrappers
---

# Production Implementation (Scoped)

Implement: $ARGUMENTS

## Branch Setup

1. Check current branch:

```bash
git branch --show-current
```

2. If not already on `feat/*` or `todo/*`, create feature branch:

```bash
just session-branch feat
```

## Workflow

1. Research relevant files before edits.
2. Implement changes directly.
3. Run quality validation with `/check`.
4. Run deep validation with `/validate`.

## Standards

- Replace old code paths directly; no versioned forks.
- Keep error handling at real boundaries.
- Add comments only for non-obvious logic.

## Completion

1. Mark task lifecycle start at implementation begin:

```bash
just task-started "<task_id>" "<session_branch>" "$ARGUMENTS"
```

2. Commit using scoped helper:

```bash
agent-commit-files --message-file <path-to-message-file>
```

3. Mark completion after verification:

```bash
just task-completed "<task_id>" "<session_branch>"
```

4. Mark TODO item `[x]`.
