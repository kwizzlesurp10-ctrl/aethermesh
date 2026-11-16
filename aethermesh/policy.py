"""Policy evaluation, risk scoring, and Critic veto logic."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path


def run_opa(contract: dict, rego_path: str | Path = "policies/s3.rego") -> list[dict]:
    """Evaluate the JSON-RPC contract against OPA Rego rules."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=True) as tmp:
        tmp.write(json.dumps(contract))
        tmp.flush()
        result = subprocess.run(
            [
                "opa",
                "eval",
                "--input",
                tmp.name,
                "--data",
                str(rego_path),
                "data.aethermesh.s3.deny",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    opa_out = json.loads(result.stdout)
    denials = (
        opa_out.get("result", [{}])[0]
        .get("expressions", [{}])[0]
        .get("value", [])
    )
    if denials:
        return [{"policy": d, "passed": False} for d in denials]
    return [{"policy": "all", "passed": True}]


def score_risk(
    proposed: dict,
    env: str,
    all_passed: bool,
    cost_delta_pct: float = 0.0,
) -> int:
    """Compute a 0-100 risk score for a proposed infrastructure change."""
    blast = proposed.get("blastRadius", "medium")
    reversible = proposed.get("reversible", True)
    public = proposed.get("acl", "private") != "private" or not proposed.get("public_access_block", False)
    prod = env == "production"

    score = {"low": 5, "medium": 25, "high": 45}.get(blast, 30)
    score += min(20, int(max(0.0, cost_delta_pct) * 0.5))
    score += 0 if reversible else 25
    score += 20 if public else 0
    score += 15 if prod else 0
    if not all_passed:
        score = max(score, 70)
    return min(100, score)


def critic_veto(
    risk: int,
    policies: list[dict],
    env: str,
    reversible: bool,
) -> tuple[bool, str]:
    """Return (veto, reason) enforcing OPA, risk, production, and reversibility gates."""
    if any(not p.get("passed", False) for p in policies):
        return True, "OPA policy failure"
    if risk >= 70:
        return True, "risk >= 70 (hard block)"
    if env == "production" and risk >= 30:
        return True, "production requires human approval"
    if not reversible:
        return True, "non-reversible change requires human approval"
    return False, "no veto"
