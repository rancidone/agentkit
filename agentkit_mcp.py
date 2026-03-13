"""MCP service split definitions for the agentkit migration bootstrap."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ServiceDefinition:
    name: str
    purpose: str
    compatibility_path_required: bool
    owned_capabilities: tuple[str, ...]
    deferred_capabilities: tuple[str, ...]


REPO_SERVICE = ServiceDefinition(
    name="agentkit-repo-mcp",
    purpose="Owns repo, index, context, and repo-config operations.",
    compatibility_path_required=True,
    owned_capabilities=(
        "index.build",
        "index.refresh",
        "index.query",
        "index.pack",
        "index.inspect",
        "config.load",
    ),
    deferred_capabilities=(),
)

TELEMETRY_SERVICE = ServiceDefinition(
    name="agentkit-telemetry-mcp",
    purpose="Owns telemetry ingestion, state management, and task lifecycle operations.",
    compatibility_path_required=True,
    owned_capabilities=(
        "telemetry.ingest",
        "telemetry.report",
        "telemetry.hotspots",
        "telemetry.trend",
        "telemetry.inspect",
        "task.log_started",
        "task.log_completed",
        "task.log_failed",
        "task.log_worker_spawned",
        "task.log_worker_merged",
    ),
    deferred_capabilities=(),
)


def service_definitions() -> list[ServiceDefinition]:
    return [REPO_SERVICE, TELEMETRY_SERVICE]


def describe_service(name: str) -> dict[str, object]:
    for service in service_definitions():
        if service.name == name:
            return asdict(service)
    raise SystemExit(f"unknown service: {name}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Describe the agentkit MCP bootstrap services.")
    parser.add_argument("service_name")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    print(json.dumps(describe_service(args.service_name), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
