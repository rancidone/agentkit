"""Minimal JSON-RPC stdio server utilities for MCP-style tools."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, Callable


JsonDict = dict[str, Any]
ToolHandler = Callable[[JsonDict], JsonDict]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: JsonDict
    handler: ToolHandler


class JsonRpcError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _read_message(stdin: Any) -> JsonDict | None:
    headers: dict[str, str] = {}
    while True:
        line = stdin.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        key, _, value = line.decode("utf-8").partition(":")
        headers[key.strip().lower()] = value.strip()

    content_length = int(headers.get("content-length", "0"))
    if content_length <= 0:
        raise JsonRpcError(-32700, "missing Content-Length header")
    body = stdin.read(content_length)
    if len(body) != content_length:
        raise JsonRpcError(-32700, "incomplete message body")
    return json.loads(body.decode("utf-8"))


def _write_message(stdout: Any, payload: JsonDict) -> None:
    body = json.dumps(payload).encode("utf-8")
    stdout.write(f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8"))
    stdout.write(body)
    stdout.flush()


def _success(request_id: Any, result: JsonDict) -> JsonDict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> JsonDict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def run_stdio_server(server_name: str, server_version: str, tools: list[ToolDefinition]) -> int:
    tool_map = {tool.name: tool for tool in tools}
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer

    while True:
        try:
            request = _read_message(stdin)
            if request is None:
                return 0
            request_id = request.get("id")
            method = request.get("method")
            params = request.get("params") or {}

            if method == "initialize":
                result = {
                    "protocolVersion": "2025-11-05",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": server_name, "version": server_version},
                }
                if request_id is not None:
                    _write_message(stdout, _success(request_id, result))
                continue

            if method == "notifications/initialized":
                continue

            if method == "tools/list":
                result = {
                    "tools": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.input_schema,
                        }
                        for tool in tools
                    ]
                }
                if request_id is not None:
                    _write_message(stdout, _success(request_id, result))
                continue

            if method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments") or {}
                if tool_name not in tool_map:
                    raise JsonRpcError(-32602, f"unknown tool: {tool_name}")
                structured = tool_map[tool_name].handler(arguments)
                result = {
                    "content": [{"type": "text", "text": json.dumps(structured, indent=2)}],
                    "structuredContent": structured,
                    "isError": False,
                }
                if request_id is not None:
                    _write_message(stdout, _success(request_id, result))
                continue

            raise JsonRpcError(-32601, f"method not found: {method}")
        except JsonRpcError as exc:
            _write_message(stdout, _error(request.get("id") if "request" in locals() else None, exc.code, exc.message))
        except json.JSONDecodeError as exc:
            _write_message(stdout, _error(request.get("id") if "request" in locals() else None, -32700, f"invalid JSON: {exc}"))
        except SystemExit as exc:
            message = str(exc) or "tool execution failed"
            _write_message(stdout, _success(request.get("id"), {"content": [{"type": "text", "text": message}], "structuredContent": {"error": message}, "isError": True}))
        except Exception as exc:  # pragma: no cover - last-resort protocol safety
            _write_message(stdout, _error(request.get("id") if "request" in locals() else None, -32000, str(exc)))
