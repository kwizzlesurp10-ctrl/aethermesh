"""SQLite/PostgreSQL-compatible decision persistence and veto heatmap summarizer."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS gate_decisions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT    NOT NULL,
    module        TEXT    NOT NULL,
    env           TEXT    NOT NULL,
    risk_score    INTEGER NOT NULL,
    veto          BOOLEAN NOT NULL,
    status        TEXT    NOT NULL,
    reason        TEXT,
    otel_trace_id TEXT,
    contract_json TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_gate_decisions_module_veto
    ON gate_decisions (module, veto, created_at DESC);
"""


def init_db(conn: sqlite3.Connection) -> None:
    """Initialize the gate_decisions table and index."""
    conn.executescript(SCHEMA)
    conn.commit()


def record_decision(
    conn: sqlite3.Connection,
    module: str,
    env: str,
    decision: dict,
    contract: dict,
    trace_id: str | None = None,
) -> None:
    """Persist a single gate decision row."""
    init_db(conn)
    sql = (
        "INSERT INTO gate_decisions "
        "(created_at, module, env, risk_score, veto, status, reason, otel_trace_id, contract_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    conn.execute(
        sql,
        (
            datetime.now(timezone.utc).isoformat(),
            module,
            env,
            decision["risk"],
            bool(decision["veto"]),
            decision["status"],
            decision.get("reason"),
            trace_id,
            json.dumps(contract),
        ),
    )
    conn.commit()


def recent_vetoes(
    conn: sqlite3.Connection,
    module: str,
    limit: int = 20,
) -> list[dict]:
    """Fetch the most recent vetoed decisions for a module."""
    init_db(conn)
    cur = conn.execute(
        "SELECT created_at, env, risk_score, reason, otel_trace_id, contract_json "
        "FROM gate_decisions WHERE module = ? AND veto = 1 "
        "ORDER BY created_at DESC LIMIT ?",
        (module, limit),
    )
    cols = ["created_at", "env", "risk_score", "reason", "otel_trace_id", "contract_json"]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def summarize_vetoes(vetoes: list[dict]) -> dict:
    """Summarize recent vetoes into a failure_heatmap and Planner tuning_hint."""
    if not vetoes:
        return {
            "failure_heatmap": {
                "total_vetoes": 0,
                "by_reason": {},
                "by_risk_bucket": {},
                "frequent_missing_attributes": {},
                "policy_failure_count": 0,
            },
            "tuning_hint": {
                "priority": "low",
                "message": "No recent vetoes.",
                "suggested_actions": [],
                "heatmap_summary": {"top_reason": "none", "hard_block_pct": 0.0},
            },
        }

    reason_counts: Counter[str] = Counter()
    risk_buckets: Counter[str] = Counter()
    missing_attrs: Counter[str] = Counter()
    policy_failures = 0

    for v in vetoes:
        reason = v.get("reason") or "unknown"
        reason_counts[reason] += 1
        bucket = "hard_block" if v.get("risk_score", 0) >= 70 else "human_required"
        risk_buckets[bucket] += 1
        if "OPA" in reason:
            policy_failures += 1
        try:
            contract = json.loads(v.get("contract_json", "{}"))
            pc = contract.get("params", {}).get("proposedChange", {})
            if not pc.get("public_access_block"):
                missing_attrs["public_access_block"] += 1
            if not pc.get("encryption", {}).get("enabled"):
                missing_attrs["encryption"] += 1
            tags = pc.get("tags", {})
            if "Environment" not in tags:
                missing_attrs["tag.Environment"] += 1
            if "Owner" not in tags:
                missing_attrs["tag.Owner"] += 1
        except Exception:
            pass

    top_reason = reason_counts.most_common(1)[0][0]
    actions: list[str] = []
    if missing_attrs.get("public_access_block", 0) >= 2:
        actions.append("Planner must always set public_access_block=true")
    if missing_attrs.get("encryption", 0) >= 2:
        actions.append("Planner must always enable encryption")
    if "cost" in top_reason.lower():
        actions.append("Reduce estMonthlyCostUSD or raise intent.maxMonthlyCostUSD")
    if not actions:
        actions.append("Review top veto reason and adjust Planner defaults")

    return {
        "failure_heatmap": {
            "total_vetoes": len(vetoes),
            "by_reason": dict(reason_counts.most_common()),
            "by_risk_bucket": dict(risk_buckets),
            "frequent_missing_attributes": dict(missing_attrs.most_common(5)),
            "policy_failure_count": policy_failures,
        },
        "tuning_hint": {
            "priority": "high" if len(vetoes) >= 5 else "medium",
            "message": f"{len(vetoes)} recent vetoes. Dominant reason: {top_reason}.",
            "suggested_actions": actions,
            "heatmap_summary": {
                "top_reason": top_reason,
                "hard_block_pct": round(100 * risk_buckets["hard_block"] / len(vetoes), 1),
            },
        },
    }
