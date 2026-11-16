"""Installable CLI entry point for AetherMesh."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from aethermesh.executor import apply_if_approved
from aethermesh.orchestrator import run_closed_loop
from aethermesh.store import recent_vetoes, summarize_vetoes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aethermesh")
    parser.add_argument("--db", default="aethermesh.db")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("propose", help="Run closed-loop planner -> OPA -> critic")
    sp.add_argument("--intent", required=True)
    sp.add_argument("--module", default="modules/s3-static-bucket")

    sa = sub.add_parser("apply", help="Apply an auto_approved decision (dry-run by default)")
    sa.add_argument("--decision", required=True)
    sa.add_argument("--plan", required=True)
    sa.add_argument("--execute", action="store_true", help="Disable dry-run")
    sa.add_argument("--allow-real-aws", action="store_true")

    sv = sub.add_parser("vetoes", help="Show last 20 vetoes and failure heatmap")
    sv.add_argument("--module", default="modules/s3-static-bucket")

    args = parser.parse_args(argv)
    with sqlite3.connect(args.db) as conn:
        if args.cmd == "propose":
            intent = json.loads(Path(args.intent).read_text())
            decision = run_closed_loop(conn, intent, module=args.module)
            print(json.dumps(decision, indent=2))
            return 1 if decision.get("veto") else 0

        if args.cmd == "apply":
            decision = json.loads(Path(args.decision).read_text())
            res = apply_if_approved(
                decision,
                args.plan,
                dry_run=not args.execute,
                allow_real_aws=args.allow_real_aws,
            )
            print(json.dumps(res, indent=2))
            return 0 if res.get("applied") or res.get("dry_run") else 1

        if args.cmd == "vetoes":
            summary = summarize_vetoes(recent_vetoes(conn, args.module, limit=20))
            print(json.dumps(summary, indent=2))
            return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
