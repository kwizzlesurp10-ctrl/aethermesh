"""Closed-loop orchestrator: vetoes -> summarize -> plan -> OPA -> risk -> critic -> persist."""

from __future__ import annotations

import sqlite3
from typing import Any

from aethermesh.planner import generate_proposal
from aethermesh.policy import critic_veto, run_opa, score_risk
from aethermesh.store import recent_vetoes, record_decision, summarize_vetoes


def run_closed_loop(
    conn: sqlite3.Connection,
    intent: dict,
    module: str = "modules/s3-static-bucket",
    env: str | None = None,
    rego_path: str = "policies/s3.rego",
) -> dict[str, Any]:
    """Execute the full AetherMesh closed control loop and persist the decision."""
    target_env = env or intent.get("env", "staging")

    vetoes = recent_vetoes(conn, module, limit=20)
    summary = summarize_vetoes(vetoes)
    tuning_hint = summary["tuning_hint"]

    proposed = generate_proposal(intent, tuning_hint)
    contract = {
        "jsonrpc": "2.0",
        "id": f"loop-{intent.get('goal', 'unknown')}",
        "method": "aethermesh.propose_change",
        "params": {
            "intent": intent,
            "proposedChange": proposed,
        },
    }

    policies = run_opa(contract, rego_path)
    all_passed = all(p.get("passed", False) for p in policies)
    risk = score_risk(proposed, target_env, all_passed)
    veto, reason = critic_veto(
        risk,
        policies,
        target_env,
        proposed.get("reversible", True),
    )

    decision: dict[str, Any] = {
        "risk": risk,
        "veto": veto,
        "reason": reason,
        "status": "hard_block" if veto else ("auto_approved" if risk < 30 else "human_required"),
        "policies": policies,
        "tuning_hint_used": tuning_hint,
        "proposedChange": proposed,
    }

    try:
        record_decision(
            conn,
            module=module,
            env=target_env,
            decision=decision,
            contract=contract,
            trace_id=None,
        )
    except Exception as exc:
        decision["persist_error"] = str(exc)

    return decision
