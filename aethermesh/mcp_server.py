"""MCP server exposing AetherMesh tools and resources over stdio."""

from __future__ import annotations

import json
import sqlite3

from mcp.server.fastmcp import FastMCP

from aethermesh.executor import apply_if_approved
from aethermesh.orchestrator import run_closed_loop
from aethermesh.store import recent_vetoes, summarize_vetoes

mcp = FastMCP("aethermesh")


@mcp.tool(name="aethermesh.propose")
def propose(
    intent: dict,
    module: str = "modules/s3-static-bucket",
    db: str = "aethermesh.db",
) -> dict:
    """Run the closed-loop planner -> OPA -> critic and return the decision."""
    with sqlite3.connect(db) as conn:
        return run_closed_loop(conn, intent, module=module)


@mcp.tool(name="aethermesh.apply")
def apply(
    decision: dict,
    plan: str,
    execute: bool = False,
    allow_real_aws: bool = False,
) -> dict:
    """Apply an auto_approved decision (defaults to dry-run)."""
    return apply_if_approved(
        decision,
        plan,
        dry_run=not execute,
        allow_real_aws=allow_real_aws,
    )


@mcp.tool(name="aethermesh.vetoes")
def vetoes(
    module: str = "modules/s3-static-bucket",
    db: str = "aethermesh.db",
) -> dict:
    """Return the last 20 vetoes and failure heatmap for a module."""
    with sqlite3.connect(db) as conn:
        return summarize_vetoes(recent_vetoes(conn, module, limit=20))


@mcp.resource("aethermesh://decisions/{module}")
def decisions_resource(module: str) -> str:
    """Return the last 50 gate decisions for a module."""
    with sqlite3.connect("aethermesh.db") as conn:
        cur = conn.execute(
            "SELECT created_at, env, risk_score, veto, status, reason "
            "FROM gate_decisions WHERE module = ? ORDER BY created_at DESC LIMIT 50",
            (module,),
        )
        cols = ["created_at", "env", "risk_score", "veto", "status", "reason"]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return json.dumps(rows, indent=2)


@mcp.resource("aethermesh://heatmap/{module}")
def heatmap_resource(module: str) -> str:
    """Return the failure heatmap and tuning hint for a module."""
    with sqlite3.connect("aethermesh.db") as conn:
        return json.dumps(
            summarize_vetoes(recent_vetoes(conn, module, limit=20)),
            indent=2,
        )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
