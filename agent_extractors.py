#!/usr/bin/env python3
"""Symbol/block extraction helpers for context-minimized packs."""

from __future__ import annotations

import re
from typing import Any


def _safe_read_lines(path: str) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read().splitlines()
    except OSError:
        return []


def extract_c_like(lines: list[str]) -> list[dict[str, Any]]:
    symbols: list[dict[str, Any]] = []
    sig = re.compile(
        r"^\s*(?:[A-Za-z_][\w\s\*]*\s+)+([A-Za-z_]\w*)\s*\([^;]*\)\s*\{\s*$"
    )

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        m = sig.match(line)
        if not m:
            i += 1
            continue

        name = m.group(1)
        start = i + 1
        depth = line.count("{") - line.count("}")
        j = i + 1
        while j < n and depth > 0:
            depth += lines[j].count("{") - lines[j].count("}")
            j += 1

        end = j if j > i + 1 else i + 1
        symbols.append(
            {
                "symbol": name,
                "kind": "function",
                "start_line": start,
                "end_line": end,
            }
        )
        i = max(j, i + 1)
    return symbols


def extract_ts_js(lines: list[str]) -> list[dict[str, Any]]:
    symbols: list[dict[str, Any]] = []
    blocked = {"if", "for", "while", "switch", "catch", "else", "return"}
    pats = [
        re.compile(r"^\s*function\s+([A-Za-z_]\w*)\s*\("),
        re.compile(r"^\s*(?:const|let|var)\s+([A-Za-z_]\w*)\s*=\s*\([^)]*\)\s*=>\s*\{"),
        re.compile(r"^\s*([A-Za-z_]\w*)\s*\([^)]*\)\s*\{\s*$"),
    ]

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        name = None
        for p in pats:
            m = p.match(line)
            if m:
                name = m.group(1)
                break
        if not name or name in blocked:
            i += 1
            continue

        start = i + 1
        depth = line.count("{") - line.count("}")
        j = i + 1
        while j < n and depth > 0:
            depth += lines[j].count("{") - lines[j].count("}")
            j += 1
        end = j if j > i + 1 else i + 1
        symbols.append(
            {
                "symbol": name,
                "kind": "function",
                "start_line": start,
                "end_line": end,
            }
        )
        i = max(j, i + 1)
    return symbols


def extract_python(lines: list[str]) -> list[dict[str, Any]]:
    symbols: list[dict[str, Any]] = []
    sig = re.compile(r"^(\s*)def\s+([A-Za-z_]\w*)\s*\(")

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        m = sig.match(line)
        if not m:
            i += 1
            continue

        indent = len(m.group(1).replace("\t", "    "))
        name = m.group(2)
        start = i + 1
        j = i + 1
        while j < n:
            nxt = lines[j]
            if not nxt.strip():
                j += 1
                continue
            nxt_indent = len(nxt) - len(nxt.lstrip(" \t"))
            if nxt_indent <= indent and not nxt.lstrip().startswith("#"):
                break
            j += 1

        end = j if j > i + 1 else i + 1
        symbols.append(
            {
                "symbol": name,
                "kind": "function",
                "start_line": start,
                "end_line": end,
            }
        )
        i = max(j, i + 1)
    return symbols


def extract_symbols(path: str, ext: str, layer: str) -> list[dict[str, Any]]:
    lines = _safe_read_lines(path)
    if not lines:
        return []

    if layer == "regex-c":
        return extract_c_like(lines)
    if layer == "regex-ts":
        return extract_ts_js(lines)
    if layer == "regex-py":
        return extract_python(lines)

    if ext in {".c", ".h", ".cc", ".cpp", ".hpp"}:
        return extract_c_like(lines)
    if ext in {".ts", ".js", ".tsx", ".jsx", ".svelte"}:
        return extract_ts_js(lines)
    if ext == ".py":
        return extract_python(lines)
    return []


def snippet_preview(path: str, start: int, end: int, max_lines: int = 40) -> str:
    lines = _safe_read_lines(path)
    if not lines:
        return ""
    s = max(1, start)
    e = min(len(lines), end, s + max_lines - 1)
    return "\n".join(lines[s - 1 : e])
