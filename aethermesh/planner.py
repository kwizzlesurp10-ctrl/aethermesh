"""Planner Agent proposal generation informed by Critic tuning hints."""

from __future__ import annotations


def generate_proposal(
    intent: dict,
    tuning_hint: dict | None = None,
    base_overrides: dict | None = None,
) -> dict:
    """Generate a proposedChange payload for modules/s3-static-bucket."""
    proposal = {
        "engine": "opentofu",
        "module": "modules/s3-static-bucket",
        "public_access_block": False,
        "acl": "private",
        "encryption": {"enabled": True, "algorithm": "AES256"},
        "tags": {
            "Environment": intent.get("env", "staging"),
            "Owner": intent.get("owner", "platform-team"),
        },
        "estMonthlyCostUSD": 4.5,
        "blastRadius": "low",
        "reversible": True,
        **(base_overrides or {}),
    }

    actions = " ".join((tuning_hint or {}).get("suggested_actions", [])).lower()
    if "public_access_block=true" in actions:
        proposal["public_access_block"] = True
        proposal["acl"] = "private"
    if "enable encryption" in actions:
        proposal["encryption"] = {"enabled": True, "algorithm": "AES256"}
    if "reduce estmonthlycostusd" in actions and intent.get("maxMonthlyCostUSD"):
        proposal["estMonthlyCostUSD"] = min(
            proposal["estMonthlyCostUSD"],
            float(intent["maxMonthlyCostUSD"]),
        )
    return proposal
