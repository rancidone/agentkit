---
allowed-tools: all
description: Synthesize a complete execution prompt from local next.md
---

# Prompt Synthesizer (Scoped)

Create a complete prompt by combining:

1. `claude/commands/next.md`
2. User task: `$ARGUMENTS`

## Task

1. Read `claude/commands/next.md`.
2. Replace `Implement: $ARGUMENTS` with the user task.
3. Output the complete prompt in a code block.

## Requirements

- Preserve lifecycle workflow and scoped wrappers.
- Keep branch setup, quality checks, and completion requirements.
