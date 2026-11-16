import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from aethermesh import (
    apply_if_approved,
    init_db,
    record_decision,
    run_closed_loop,
)


@pytest.fixture
def sqlite_conn():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    yield conn
    conn.close()


def test_closed_loop_learns_from_historical_vetoes(sqlite_conn):
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
            sqlite_conn,
            "modules/s3-static-bucket",
            "staging",
            {"risk": 70, "veto": True, "status": "hard_block", "reason": "OPA policy failure"},
            bad_contract,
            trace_id=f"seed-{i}",
        )

    intent = {
        "actor": "planner",
        "goal": "provision static site",
        "env": "staging",
        "owner": "platform-team",
        "maxMonthlyCostUSD": 50,
    }
    with patch(
        "aethermesh.orchestrator.run_opa",
        return_value=[{"policy": "all", "passed": True}],
    ):
        result = run_closed_loop(sqlite_conn, intent)

    assert result["status"] == "auto_approved"
    assert result["proposedChange"]["public_access_block"] is True
    assert result["veto"] is False


def test_executor_dry_run_never_applies():
    decision = {
        "status": "auto_approved",
        "veto": False,
        "risk": 5,
        "proposedChange": {"reversible": True},
    }
    result = apply_if_approved(decision, "dummy.tfplan", dry_run=True)
    assert result["applied"] is False
    assert result["dry_run"] is True
    assert "tofu apply" in result["would_run"]


def test_executor_blocks_high_risk():
    decision = {
        "status": "auto_approved",
        "veto": False,
        "risk": 45,
        "proposedChange": {"reversible": True},
    }
    result = apply_if_approved(decision, "dummy.tfplan", dry_run=False)
    assert result["applied"] is False
    assert "risk >= 30" in result["reason"]


def test_executor_blocks_real_aws_without_flag(monkeypatch):
    monkeypatch.delenv("LOCALSTACK_ENDPOINT", raising=False)
    decision = {
        "status": "auto_approved",
        "veto": False,
        "risk": 5,
        "proposedChange": {"reversible": True},
    }
    result = apply_if_approved(
        decision, "dummy.tfplan", dry_run=False, allow_real_aws=False
    )
    assert result["applied"] is False
    assert "LOCALSTACK_ENDPOINT" in result["reason"]


def test_executor_happy_path_localstack(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
    plan = tmp_path / "tfplan.bin"
    plan.write_text("fake-plan")
    decision = {
        "status": "auto_approved",
        "veto": False,
        "risk": 5,
        "proposedChange": {"reversible": True},
    }

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Apply complete", stderr="")
        result = apply_if_approved(
            decision, str(plan), dry_run=False, allow_real_aws=False
        )

    assert result["applied"] is True
    assert result["returncode"] == 0
    mock_run.assert_called_once()
