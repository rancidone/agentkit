#!/usr/bin/env python3
"""Shared helpers for agentkit tools."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
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


def detect_runner(env: dict[str, str] | None = None) -> str:
    env_map = os.environ if env is None else env
    override = (env_map.get("AGENTKIT_TELEMETRY_SCOPE") or env_map.get("AGENTKIT_RUNNER") or "").strip().lower()
    if override in {"claude", "codex", "all"}:
        return override

    if any(key.startswith("CODEX_") and env_map.get(key) for key in env_map):
        return "codex"

    claude_markers = (
        "CLAUDECODE",
        "CLAUDE_CODE",
        "CLAUDE_CODE_ENTRYPOINT",
        "CLAUDECODE_ENTRYPOINT",
    )
    if any(env_map.get(key) for key in claude_markers):
        return "claude"

    return "all"


def read_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: str, data: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")


AGENTKIT_CONFIG_SCHEMA: dict[str, Any] = {
    "index": {
        "_type": "object",
        "exclude_paths": {"_type": "list"},
        "max_file_bytes": {"_type": "int"},
    },
    "extract": {
        "_type": "object",
        "enabled": {"_type": "bool"},
        "max_file_bytes": {"_type": "int"},
        "languages": {"_type": "object"},
        "allow_custom_adapters": {"_type": "bool"},
        "adapters": {"_type": "list"},
    },
    "context": {
        "_type": "object",
        "max_snippets_total": {"_type": "int"},
        "max_snippets_per_file": {"_type": "int"},
        "prefer_symbol_blocks": {"_type": "bool"},
        "max_files_per_pack": {"_type": "int"},
        "max_tests_per_pack": {"_type": "int"},
        "default_token_budget": {"_type": "int"},
        "max_read_chunk_lines": {"_type": "int"},
        "synonyms": {"_type": "object"},
    },
    "test_hints": {"_type": "object"},
}

_SCALAR_TYPE_MAP = {"int": int, "bool": bool, "str": str, "object": dict, "list": list}


def validate_repo_config(cfg: dict[str, Any]) -> list[str]:
    """Validate agentkit.json config against schema. Returns list of warning strings."""
    errors: list[str] = []
    if not isinstance(cfg, dict):
        return ["agentkit.json root must be a JSON object"]

    for section, section_schema in AGENTKIT_CONFIG_SCHEMA.items():
        if section not in cfg:
            continue
        val = cfg[section]
        expected_type = section_schema.get("_type", "object")
        py_type = _SCALAR_TYPE_MAP.get(expected_type, dict)
        if not isinstance(val, py_type):
            errors.append(f"agentkit.json: '{section}' should be a {expected_type}, got {type(val).__name__}")
            continue
        if isinstance(val, dict) and isinstance(section_schema, dict):
            for key, key_schema in section_schema.items():
                if key == "_type" or key not in val:
                    continue
                kval = val[key]
                ktype = key_schema.get("_type", "str")
                kpy = _SCALAR_TYPE_MAP.get(ktype, str)
                if not isinstance(kval, kpy):
                    errors.append(
                        f"agentkit.json: '{section}.{key}' should be a {ktype}, got {type(kval).__name__}"
                    )
    return errors


def load_repo_config(repo: str) -> dict[str, Any]:
    candidates = [
        os.path.join(repo, ".claude", "agentkit.json"),
        os.path.join(repo, "agentkit.json"),
    ]
    for cfg_path in candidates:
        if os.path.exists(cfg_path):
            cfg = read_json(cfg_path)
            for warning in validate_repo_config(cfg):
                print(f"[agentkit warning] {warning}", file=sys.stderr)
            return cfg
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
