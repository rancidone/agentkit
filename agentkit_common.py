#!/usr/bin/env python3
"""Shared helpers for agentkit tools."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
from typing import Any


DEFAULT_EXCLUDES = {
    ".git",
    ".idea",
    ".vscode",
    "node_modules",
    "dist",
    "build",
    ".cache",
    ".next",
    ".venv",
    "venv",
    "__pycache__",
    ".claude/worktrees",
}


def run(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def repo_root(start: str | None = None) -> str:
    start_dir = os.path.abspath(start or os.getcwd())
    code, out, _ = run(["git", "rev-parse", "--show-toplevel"], cwd=start_dir)
    if code == 0:
        return out.strip()
    return start_dir


def slug_for_path(path: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", path.strip("/"))


def repo_id(path: str) -> str:
    digest = hashlib.sha256(path.encode("utf-8")).hexdigest()
    return digest[:16]


def default_state_dir() -> str:
    override = os.environ.get("AGENTKIT_STATE_DIR")
    if override:
        os.makedirs(override, exist_ok=True)
        return override
    home = os.path.expanduser("~")
    base = os.path.join(home, ".claude", "tools", "agentkit", "state")
    try:
        os.makedirs(base, exist_ok=True)
        return base
    except PermissionError:
        fallback = os.path.join("/tmp", f"agentkit-state-{os.getuid()}")
        os.makedirs(fallback, exist_ok=True)
        return fallback


def read_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: str, data: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")


def load_repo_config(repo: str) -> dict[str, Any]:
    candidates = [
        os.path.join(repo, ".claude", "agentkit.json"),
        os.path.join(repo, "agentkit.json"),
    ]
    for cfg_path in candidates:
        if os.path.exists(cfg_path):
            return read_json(cfg_path)
    return {}


def should_skip(rel_path: str, excludes: set[str]) -> bool:
    rel = rel_path.replace("\\", "/")
    if rel.startswith("./"):
        rel = rel[2:]
    for ex in excludes:
        norm_ex = ex.replace("\\", "/")
        if norm_ex in rel:
            return True
    return False


def iter_repo_files(repo: str, excludes: set[str] | None = None) -> list[str]:
    excludes = excludes or set()
    files: list[str] = []
    repo_path = pathlib.Path(repo)
    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(repo_path))
        if should_skip(rel, excludes):
            continue
        files.append(rel)
    return files


def infer_role(path: str) -> str:
    p = path.lower()
    if p.endswith((".md", ".txt", ".rst")):
        return "docs"
    if p.endswith((".test.ts", ".spec.ts", "_test.py", "_test.c", ".test.js")):
        return "test"
    if "/tests/" in p or p.startswith("tests/"):
        return "test"
    if p.endswith((".json", ".toml", ".yaml", ".yml", ".ini")):
        return "config"
    if "/api/" in p or "routes_" in p:
        return "api"
    if "/stores/" in p or "/model" in p or "types.ts" in p:
        return "model"
    if p.endswith(".svelte") or "/views/" in p or "/components/" in p:
        return "view"
    if p.endswith((".c", ".h", ".cc", ".cpp", ".rs", ".go", ".py", ".ts", ".js")):
        return "code"
    return "asset"


def parse_isoish_timestamp(ts: str | None) -> float | None:
    if not ts:
        return None
    try:
        # Handles "2026-03-08T16:46:48.716Z"
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        import datetime as _dt

        return _dt.datetime.fromisoformat(ts).timestamp()
    except Exception:
        return None
