set shell := ["bash", "-euo", "pipefail", "-c"]

default:
  @just --list

validate-command-docs:
  ./agent-validate-command-docs .

command-guard cmd:
  ./agent-command-guard "{{cmd}}"

index-refresh-light:
  ./agent-index-refresh-light .

index-refresh-full:
  ./agent-index-refresh-full .

telemetry-ingest repo='.' claude_home="$HOME/.claude" events='.claude/agent-events.jsonl' codex_home="$HOME/.codex":
  ./agent-telemetry-ingest "{{repo}}" "{{claude_home}}" "{{events}}" "{{codex_home}}"

telemetry-report repo='.' window_days='7':
  ./agent-telemetry-report "{{repo}}" "{{window_days}}"

telemetry-hotspots repo='.' window_days='7' limit='12':
  ./agent-telemetry-hotspots "{{repo}}" "{{window_days}}" "{{limit}}"

telemetry-trend repo='.' window_days='30':
  ./agent-telemetry-trend "{{repo}}" "{{window_days}}"

telemetry-tui repo='.' window_days='7':
  AGENTKIT_STATE_DIR="$PWD/.agentkit/state" ./agent-telemetry-tui --repo "{{repo}}" --window-days "{{window_days}}"

context-pack task out token_budget='2800' limit='12' repo='.':
  ./agent-index pack --repo "{{repo}}" --task "{{task}}" --token-budget "{{token_budget}}" --limit "{{limit}}" --out "{{out}}"

task-started task_id session_branch task_text repo='.' events='.claude/agent-events.jsonl' complexity_points='':
  if [ -n "{{complexity_points}}" ]; then \
    ./agent-log-task-started "{{repo}}" "{{task_id}}" "{{session_branch}}" "{{task_text}}" "{{events}}" "{{complexity_points}}"; \
  else \
    ./agent-log-task-started "{{repo}}" "{{task_id}}" "{{session_branch}}" "{{task_text}}" "{{events}}"; \
  fi

worker-spawned task_id session_branch repo='.' events='.claude/agent-events.jsonl':
  ./agent-log-worker-spawned "{{repo}}" "{{task_id}}" "{{session_branch}}" "{{events}}"

worker-merged task_id session_branch status='merged' repo='.' events='.claude/agent-events.jsonl':
  ./agent-log-worker-merged "{{repo}}" "{{task_id}}" "{{session_branch}}" "{{status}}" "{{events}}"

task-completed task_id session_branch repo='.' events='.claude/agent-events.jsonl':
  ./agent-log-task-complete "{{repo}}" "{{task_id}}" "{{session_branch}}" "{{events}}"

task-failed task_id session_branch status='failed' repo='.' events='.claude/agent-events.jsonl':
  ./agent-log-task-failed "{{repo}}" "{{task_id}}" "{{session_branch}}" "{{status}}" "{{events}}"

session-branch prefix='todo':
  ./agent-session-branch "{{prefix}}"

commit-all message_file:
  ./agent-commit-files --message-file "{{message_file}}"

commit-files message_file +files:
  ./agent-commit-files --message-file "{{message_file}}" --files {{files}}

# Composite: run all three telemetry steps in one invocation
observe repo='.' window_days='7':
  ./agent-telemetry-ingest "{{repo}}" "$HOME/.claude" ".claude/agent-events.jsonl" "$HOME/.codex"
  ./agent-telemetry-report "{{repo}}" "{{window_days}}"
  ./agent-telemetry-hotspots "{{repo}}" "{{window_days}}" "12"

test:
  python3 -m unittest discover -s tests/ -p "test_*.py" -v

# Composite: validate docs + full index refresh + telemetry ingest (session setup)
setup:
  ./agent-validate-command-docs .
  ./agent-index-refresh-full .
  ./agent-telemetry-ingest "." "$HOME/.claude" ".claude/agent-events.jsonl" "$HOME/.codex"
