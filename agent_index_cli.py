#!/usr/bin/env python3
"""CLI wrapper for the importable agent index backend."""

from __future__ import annotations

import argparse
import json
from typing import Any

from agent_index_backend import build_index, build_pack, query_by_id, search_candidates
from agentkit_common import repo_root, write_json


def _resolve_task_text(repo: str, args: argparse.Namespace) -> str:
    task_text = args.task
    if args.task_id:
        task_text = query_by_id(repo, args.task_id)
        if task_text is None:
            raise SystemExit(f"task id not found: {args.task_id}")
    if not task_text:
        raise SystemExit("--task or --task-id is required")
    return str(task_text)


def _print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2))


def cmd_build(args: argparse.Namespace) -> int:
    repo = repo_root(args.repo)
    out = build_index(repo, args.mode, allow_custom_adapters=getattr(args, "allow_custom_adapters", False))
    _print_json(out)
    return 0


def cmd_refresh(args: argparse.Namespace) -> int:
    repo = repo_root(args.repo)
    mode = "light" if args.mode == "light" else "full"
    out = build_index(repo, mode, allow_custom_adapters=getattr(args, "allow_custom_adapters", False))
    _print_json(out)
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    repo = repo_root(args.repo)
    task_text = _resolve_task_text(repo, args)
    out = search_candidates(repo, task_text, args.limit)
    _print_json(out)
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    repo = repo_root(args.repo)
    task_text = _resolve_task_text(repo, args)
    pack = build_pack(repo, task_text, args.limit, args.token_budget)
    if args.out:
        write_json(args.out, pack)
        return 0
    _print_json(pack)
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agent-index")
    sp = p.add_subparsers(dest="cmd", required=True)

    p_build = sp.add_parser("build")
    p_build.add_argument("--repo", default=".")
    p_build.add_argument("--mode", choices=["full", "light"], default="full")
    p_build.add_argument("--allow-custom-adapters", action="store_true", default=False)
    p_build.set_defaults(func=cmd_build)

    p_refresh = sp.add_parser("refresh")
    p_refresh.add_argument("--repo", default=".")
    p_refresh.add_argument("--mode", choices=["light", "full"], default="light")
    p_refresh.add_argument("--allow-custom-adapters", action="store_true", default=False)
    p_refresh.set_defaults(func=cmd_refresh)

    p_query = sp.add_parser("query")
    p_query.add_argument("--repo", default=".")
    p_query.add_argument("--task")
    p_query.add_argument("--task-id")
    p_query.add_argument("--limit", type=int, default=20)
    p_query.set_defaults(func=cmd_query)

    p_pack = sp.add_parser("pack")
    p_pack.add_argument("--repo", default=".")
    p_pack.add_argument("--task")
    p_pack.add_argument("--task-id")
    p_pack.add_argument("--limit", type=int, default=12)
    p_pack.add_argument("--token-budget", type=int, default=2800)
    p_pack.add_argument("--out")
    p_pack.set_defaults(func=cmd_pack)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
