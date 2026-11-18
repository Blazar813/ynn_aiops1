"""Standard MCP stdio server for the Hermes Agentic AIOps demo.

Hermes launches this process from its normal ``mcp_servers`` configuration.
The server deliberately contains no model code: Hermes remains the agent.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("hermes-aiops")

_logs = [
    {"timestamp": (datetime.now(UTC) - timedelta(minutes=4)).isoformat(), "service": "payment-service", "level": "INFO", "message": "Transaction tx_1092 processed successfully in 45ms."},
    {"timestamp": (datetime.now(UTC) - timedelta(minutes=2)).isoformat(), "service": "payment-service", "level": "ERROR", "message": "Connection pool exhausted. Database timeout after 30000ms upstream postgres-cluster."},
    {"timestamp": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(), "service": "payment-service", "level": "CRITICAL", "message": "Deadlocks detected on transaction table. Service degraded."},
]


@mcp.tool()
def get_incident_context(service_name: str, alert: str) -> dict[str, Any]:
    """Return an incident envelope and safe investigation scope for an alert."""
    return {
        "incident_id": f"demo-{service_name}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        "service_name": service_name,
        "alert": alert,
        "environment": "demo",
        "allowed_actions": ["restart_service", "scale_replicas", "clear_cache"],
        "mutation_mode": "enabled" if os.getenv("AIOPS_ALLOW_MUTATIONS", "false").lower() == "true" else "dry-run",
    }


@mcp.tool()
def search_logs(service_name: str, level: str = "", limit: int = 20) -> dict[str, Any]:
    """Search recent service logs. Read-only operation."""
    limit = max(1, min(limit, 100))
    rows = [row for row in _logs if row["service"] == service_name and (not level or row["level"] == level.upper())]
    return {"status": "success", "service_name": service_name, "count": min(len(rows), limit), "logs": rows[:limit]}


@mcp.tool()
def get_service_health(service_name: str) -> dict[str, Any]:
    """Return the current health summary for a service."""
    degraded = any(row["service"] == service_name and row["level"] in {"ERROR", "CRITICAL"} for row in _logs)
    return {"service_name": service_name, "status": "degraded" if degraded else "healthy", "checked_at": datetime.now(UTC).isoformat()}


@mcp.tool()
def execute_remediation(service_name: str, action: str, approval_token: str = "") -> dict[str, Any]:
    """Execute or simulate a bounded remediation action.

    Mutations are blocked unless both the explicit environment switch and the
    approval token are present. This makes accidental model-generated changes
    fail closed in local development.
    """
    allowed = {"restart_service", "scale_replicas", "clear_cache"}
    if action not in allowed:
        return {"status": "rejected", "reason": "unsupported_action", "allowed_actions": sorted(allowed)}
    if os.getenv("AIOPS_ALLOW_MUTATIONS", "false").lower() != "true":
        return {"status": "dry-run", "service_name": service_name, "action": action, "message": "Mutation disabled; no external change was made."}
    if approval_token != os.getenv("AIOPS_APPROVAL_TOKEN", "") or not approval_token:
        return {"status": "rejected", "reason": "approval_required", "message": "A valid approval token is required."}
    return {"status": "executed", "service_name": service_name, "action": action, "executed_at": datetime.now(UTC).isoformat(), "message": "Demo mutation completed."}


if __name__ == "__main__":
    mcp.run(transport="stdio")
