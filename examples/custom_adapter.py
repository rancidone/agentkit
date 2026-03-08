#!/usr/bin/env python3
"""Example custom adapter for agentkit.

Config snippet (agentkit.json):

{
  "extract": {
    "adapters": [
      {
        "type": "python",
        "name": "custom-c-router",
        "file": "tools/agentkit/custom_adapter.py",
        "function": "extract",
        "include_ext": ["c", "h"],
        "include_paths": ["components/http_server/"]
      }
    ]
  }
}
"""

from __future__ import annotations

import re
from typing import Any


def extract(
    path: str,
    rel_path: str,
    ext: str,
    lines: list[str],
    text: str,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return symbol blocks for custom project patterns.

    Must return list of dicts with keys:
      - symbol
      - kind
      - start_line
      - end_line
    """
    out: list[dict[str, Any]] = []
    route_re = re.compile(r"\bhandle_[A-Za-z_]\w*\b")

    for i, line in enumerate(lines, start=1):
        m = route_re.search(line)
        if not m:
            continue
        out.append(
            {
                "symbol": m.group(0),
                "kind": "handler",
                "start_line": i,
                "end_line": min(len(lines), i + 20),
            }
        )
    return out
