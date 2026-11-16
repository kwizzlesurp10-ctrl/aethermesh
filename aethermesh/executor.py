"""Conservative Executor apply path with pre-apply safety guards."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def apply_if_approved(
    decision: dict,
    plan_file: str,
    dry_run: bool = True,
    allow_real_aws: bool = False,
) -> dict:
    """Apply an OpenTofu plan only when auto_approved, low-risk, reversible, and safe."""
    if decision.get("status") != "auto_approved" or decision.get("veto", True):
        return {"applied": False, "reason": f"blocked: status={decision.get('status')}"}
    if decision.get("risk", 100) >= 30:
        return {"applied": False, "reason": "blocked: risk >= 30"}
    if not decision.get("proposedChange", {}).get("reversible", False):
        return {"applied": False, "reason": "blocked: reversible=false"}
    if dry_run:
        return {
            "applied": False,
            "dry_run": True,
            "would_run": f"tofu apply -input=false {plan_file}",
        }
    if not allow_real_aws and not os.getenv("LOCALSTACK_ENDPOINT"):
        return {
            "applied": False,
            "reason": "blocked: LOCALSTACK_ENDPOINT not set (real AWS guard)",
        }

    plan_path = Path(plan_file)
    if not plan_path.exists():
        return {"applied": False, "reason": f"blocked: missing plan {plan_file}"}

    res = subprocess.run(
        ["tofu", f"-chdir={plan_path.parent}", "apply", "-input=false", plan_path.name],
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "applied": res.returncode == 0,
        "returncode": res.returncode,
        "stdout": res.stdout[-1000:],
        "stderr": res.stderr[-1000:],
    }
