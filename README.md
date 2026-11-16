# AetherMesh v1

**Autonomous GitOps & IaC control plane** where AI agents propose infrastructure changes governed by OPA/Rego policy gates, `0–100` risk scoring, Critic vetoes, SQLite/PostgreSQL veto heatmaps, and conservative `tofu apply` execution.

## Architecture

```text
recent_vetoes (SQLite/Postgres)
  │
  ▼
summarize_vetoes ──▶ tuning_hint
  │
  ▼
Planner (generate_proposal)
  │
  ▼
OPA Rego (policies/s3.rego) + score_risk + critic_veto
  │
  ├─ veto / risk >= 70 ──────────▶ hard_block (persisted to gate_decisions)
  ├─ env == prod && risk >= 30 ───▶ human_required
  └─ auto_approved (risk < 30) ───▶ apply_if_approved (dry-run by default)
```

## Quick Start

```bash
pip install -e .
python3 examples/demo_closed_loop.py
pytest -v
```

### CLI

```bash
aethermesh --db local.db propose --intent intent.json > decision.json
aethermesh --db local.db apply --decision decision.json --plan tfplan.bin
aethermesh --db local.db vetoes --module modules/s3-static-bucket
```

### MCP Server (optional)

```bash
pip install -e ".[mcp]"
aethermesh-mcp
```

Exposes tools `aethermesh.propose`, `aethermesh.apply`, `aethermesh.vetoes` and resources `aethermesh://decisions/{module}`, `aethermesh://heatmap/{module}`.
