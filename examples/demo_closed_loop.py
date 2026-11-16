# Run: python3 examples/demo_closed_loop.py
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aethermesh import (
    apply_if_approved,
    init_db,
    recent_vetoes,
    record_decision,
    run_closed_loop,
    summarize_vetoes,
)


def main() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        conn = sqlite3.connect(tmp.name)
        init_db(conn)

        bad_contract = {
            "params": {
                "proposedChange": {
                    "public_access_block": False,
                    "tags": {"Environment": "staging", "Owner": "platform"},
                }
            }
        }
        for i in range(3):
            record_decision(
                conn,
                "modules/s3-static-bucket",
                "staging",
                {
                    "risk": 70,
                    "veto": True,
                    "status": "hard_block",
                    "reason": "OPA: public_access_block must be true",
                },
                bad_contract,
                trace_id=f"seed-{i}",
            )

        intent = {
            "actor": "planner",
            "goal": "static site",
            "env": "staging",
            "owner": "platform",
            "maxMonthlyCostUSD": 50,
        }
        with patch(
            "aethermesh.orchestrator.run_opa",
            return_value=[{"policy": "all", "passed": True}],
        ):
            decision = run_closed_loop(conn, intent)
        print("DECISION:", json.dumps(decision, indent=2))

        apply_res = apply_if_approved(decision, "tfplan.bin", dry_run=True)
        print("DRY_RUN_APPLY:", json.dumps(apply_res, indent=2))

        heatmap = summarize_vetoes(
            recent_vetoes(conn, "modules/s3-static-bucket", limit=20)
        )
        print("HEATMAP:", json.dumps(heatmap, indent=2))


if __name__ == "__main__":
    main()
