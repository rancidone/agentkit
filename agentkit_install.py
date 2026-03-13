#!/usr/bin/env python3
"""Manifest-managed installer for agentkit MCP services and skills."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def _data_home() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg).expanduser()
    return Path.home() / ".local" / "share"


def install_manifest_path() -> Path:
    return _data_home() / "agentkit" / "install-manifest.json"


def managed_codex_config_path(codex_home: Path) -> Path:
    return codex_home / "agentkit" / "mcp-servers.json"


def managed_claude_config_path(claude_home: Path) -> Path:
    return claude_home / "agentkit" / "mcp-servers.json"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _symlink(target: Path, link_path: Path) -> None:
    link_path.parent.mkdir(parents=True, exist_ok=True)
    if link_path.exists() or link_path.is_symlink():
        link_path.unlink()
    link_path.symlink_to(target)


def build_managed_mcp_config(repo_root: Path) -> dict[str, Any]:
    return {
        "mcpServers": {
            "agentkit-repo-mcp": {
                "command": str(repo_root / "agentkit-repo-mcp"),
                "args": [],
                "transport": "stdio",
            },
            "agentkit-telemetry-mcp": {
                "command": str(repo_root / "agentkit-telemetry-mcp"),
                "args": [],
                "transport": "stdio",
            },
        }
    }


def install_agentkit(
    repo_root: Path,
    codex_home: Path,
    claude_home: Path,
    legacy_bin_dir: Path | None = None,
) -> dict[str, Any]:
    codex_skill = codex_home / "skills" / "agentkit-todo-codex"
    claude_skill = claude_home / "skills" / "agentkit-todo-claude"
    codex_config = managed_codex_config_path(codex_home)
    claude_config = managed_claude_config_path(claude_home)
    manifest_path = install_manifest_path()

    _symlink(repo_root / "skills" / "agentkit-todo-codex", codex_skill)
    _symlink(repo_root / "skills" / "agentkit-todo-claude", claude_skill)

    config_payload = build_managed_mcp_config(repo_root)
    _write_json(codex_config, config_payload)
    _write_json(claude_config, config_payload)

    artifacts: list[dict[str, str]] = [
        {"type": "skill_link", "path": str(codex_skill), "target": str(repo_root / "skills" / "agentkit-todo-codex")},
        {"type": "skill_link", "path": str(claude_skill), "target": str(repo_root / "skills" / "agentkit-todo-claude")},
        {"type": "managed_config", "path": str(codex_config)},
        {"type": "managed_config", "path": str(claude_config)},
    ]

    if legacy_bin_dir is not None:
        legacy_bin_dir.mkdir(parents=True, exist_ok=True)
        tools = [
            "agent-install-global-tools",
            "agentkit",
            "agent-index",
            "agent-index-refresh-light",
            "agent-index-refresh-full",
            "agent-telemetry",
            "agent-telemetry-ingest",
            "agent-telemetry-report",
            "agent-telemetry-hotspots",
            "agent-telemetry-strict",
            "agent-log",
            "agent-log-task-started",
            "agent-log-task-complete",
            "agent-log-task-failed",
            "agent-log-worker-spawned",
            "agent-log-worker-merged",
            "agent-session-branch",
            "agent-command-guard",
            "agent-validate-command-docs",
            "agent-commit-files",
            "agent-weekly-telemetry-gate",
        ]
        for tool in tools:
            target = repo_root / tool
            if not target.exists():
                raise SystemExit(f"missing executable in repo: {tool}")
            link_path = legacy_bin_dir / tool
            _symlink(target, link_path)
            artifacts.append({"type": "legacy_wrapper_link", "path": str(link_path), "target": str(target)})

    manifest = {
        "schema_version": 1,
        "repo_root": str(repo_root),
        "artifacts": artifacts,
    }
    _write_json(manifest_path, manifest)

    return {
        "repo_root": str(repo_root),
        "manifest": str(manifest_path),
        "codex_skill": str(codex_skill),
        "claude_skill": str(claude_skill),
        "codex_mcp_config": str(codex_config),
        "claude_mcp_config": str(claude_config),
        "legacy_bin_dir": str(legacy_bin_dir) if legacy_bin_dir is not None else None,
        "artifacts_recorded": len(artifacts),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install agentkit MCP configs and skill links.")
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parent)
    parser.add_argument("--codex-home", default=os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    parser.add_argument("--claude-home", default=os.environ.get("CLAUDE_HOME", str(Path.home() / ".claude")))
    parser.add_argument("--legacy-bin-dir")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = install_agentkit(
        repo_root=Path(args.repo_root).resolve(),
        codex_home=Path(args.codex_home).expanduser(),
        claude_home=Path(args.claude_home).expanduser(),
        legacy_bin_dir=Path(args.legacy_bin_dir).expanduser() if args.legacy_bin_dir else None,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
