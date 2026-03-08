#!/usr/bin/env python3
"""Symbol/block extraction helpers and pluggable project adapters."""

from __future__ import annotations

import importlib.util
import os
import re
from dataclasses import dataclass
from typing import Any, Callable


ExtractFn = Callable[[str, str, str, list[str], dict[str, Any]], list[dict[str, Any]]]


@dataclass
class Adapter:
    name: str
    include_ext: set[str]
    include_path_patterns: list[re.Pattern[str]]
    fn: ExtractFn


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


def _default_extract(ext: str, layer: str, lines: list[str]) -> list[dict[str, Any]]:
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


def _decorate(symbols: list[dict[str, Any]], extractor_name: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for s in symbols:
        item = dict(s)
        item.setdefault("kind", "function")
        item["extractor"] = extractor_name
        out.append(item)
    return out


def _builtin_adapter_fn(name: str) -> ExtractFn:
    def esp_idf_http_routes(path: str, rel_path: str, ext: str, lines: list[str], cfg: dict[str, Any]) -> list[dict[str, Any]]:
        syms = extract_c_like(lines)
        out = []
        for s in syms:
            nm = s["symbol"].lower()
            if nm.startswith("handle_") or "route" in nm or "events" in nm:
                out.append(s)
        return out

    def svelte_live(path: str, rel_path: str, ext: str, lines: list[str], cfg: dict[str, Any]) -> list[dict[str, Any]]:
        syms = extract_ts_js(lines)
        out = []
        for s in syms:
            nm = s["symbol"].lower()
            if any(k in nm for k in ("live", "event", "stream", "start", "stop", "subscribe")):
                out.append(s)
        return out

    def ts_store(path: str, rel_path: str, ext: str, lines: list[str], cfg: dict[str, Any]) -> list[dict[str, Any]]:
        syms = extract_ts_js(lines)
        out = []
        for s in syms:
            nm = s["symbol"].lower()
            if any(k in nm for k in ("store", "set", "update", "start", "stop", "subscribe")):
                out.append(s)
        return out

    mapping: dict[str, ExtractFn] = {
        "esp-idf-http-routes": esp_idf_http_routes,
        "svelte-live-api": svelte_live,
        "typescript-stores": ts_store,
    }
    if name not in mapping:
        raise ValueError(f"unknown builtin adapter: {name}")
    return mapping[name]


def _load_custom_adapter(repo: str, spec: dict[str, Any]) -> ExtractFn:
    file_path = spec.get("file")
    if not file_path:
        raise ValueError("custom adapter requires 'file'")
    abs_file = file_path if os.path.isabs(file_path) else os.path.join(repo, file_path)
    func_name = spec.get("function", "extract")

    module_name = f"agentkit_adapter_{abs(hash(abs_file))}"
    module_spec = importlib.util.spec_from_file_location(module_name, abs_file)
    if module_spec is None or module_spec.loader is None:
        raise ValueError(f"failed loading adapter module: {abs_file}")
    mod = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(mod)

    fn = getattr(mod, func_name, None)
    if not callable(fn):
        raise ValueError(f"adapter function not found/callable: {func_name}")

    def _wrapper(path: str, rel_path: str, ext: str, lines: list[str], cfg: dict[str, Any]) -> list[dict[str, Any]]:
        text = "\n".join(lines)
        try:
            return fn(path=path, rel_path=rel_path, ext=ext, lines=lines, text=text, config=cfg) or []
        except TypeError:
            try:
                return fn(path, rel_path, ext, lines, text, cfg) or []
            except TypeError:
                return fn(path, text) or []

    return _wrapper


def _compile_patterns(raw_patterns: list[str]) -> list[re.Pattern[str]]:
    out = []
    for p in raw_patterns:
        try:
            out.append(re.compile(p))
        except re.error:
            continue
    return out


def load_adapters(repo: str, cfg: dict[str, Any]) -> list[Adapter]:
    out: list[Adapter] = []
    adapters_cfg = cfg.get("extract", {}).get("adapters", [])
    if not isinstance(adapters_cfg, list):
        return out

    for item in adapters_cfg:
        if isinstance(item, str):
            item = {"type": "builtin", "name": item}
        if not isinstance(item, dict):
            continue

        ad_type = item.get("type", "builtin")
        name = item.get("name", "unnamed-adapter")
        include_ext = {f".{e.lstrip('.').lower()}" for e in item.get("include_ext", [])}
        include_path_patterns = _compile_patterns(item.get("include_paths", []))

        try:
            if ad_type == "builtin":
                fn = _builtin_adapter_fn(name)
            elif ad_type == "python":
                fn = _load_custom_adapter(repo, item)
            else:
                continue
        except Exception:
            continue

        out.append(
            Adapter(
                name=name,
                include_ext=include_ext,
                include_path_patterns=include_path_patterns,
                fn=fn,
            )
        )

    return out


def _adapter_matches(adapter: Adapter, rel_path: str, ext: str) -> bool:
    if adapter.include_ext and ext not in adapter.include_ext:
        return False
    if adapter.include_path_patterns:
        return any(p.search(rel_path) for p in adapter.include_path_patterns)
    return True


def extract_symbols(
    path: str,
    ext: str,
    layer: str,
    rel_path: str | None = None,
    adapters: list[Adapter] | None = None,
    cfg: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    lines = _safe_read_lines(path)
    if not lines:
        return []

    cfg = cfg or {}
    rel = rel_path or path
    seen: set[tuple[str, int, int]] = set()
    out: list[dict[str, Any]] = []

    default_symbols = _decorate(_default_extract(ext, layer, lines), layer or "auto")
    for s in default_symbols:
        key = (str(s.get("symbol", "")), int(s.get("start_line", 0)), int(s.get("end_line", 0)))
        if key in seen:
            continue
        seen.add(key)
        out.append(s)

    for adapter in adapters or []:
        if not _adapter_matches(adapter, rel, ext):
            continue
        try:
            adapter_symbols = _decorate(adapter.fn(path, rel, ext, lines, cfg), adapter.name)
        except Exception:
            continue
        for s in adapter_symbols:
            key = (str(s.get("symbol", "")), int(s.get("start_line", 0)), int(s.get("end_line", 0)))
            if key in seen:
                continue
            seen.add(key)
            out.append(s)

    return out


def snippet_preview(path: str, start: int, end: int, max_lines: int = 40) -> str:
    lines = _safe_read_lines(path)
    if not lines:
        return ""
    s = max(1, start)
    e = min(len(lines), end, s + max_lines - 1)
    return "\n".join(lines[s - 1 : e])
