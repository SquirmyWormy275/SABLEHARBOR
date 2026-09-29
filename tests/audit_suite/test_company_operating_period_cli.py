"""Actual local CLI boundaries: no audit, no overwrite, immutable report inputs."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.operating_source_bridge import sha
from enterprise.audit_suite.store import DomainError
from tools.audit_suite.company_operating_period import create, record, report

REPO = Path(__file__).resolve().parents[2]


def plan():
    return {
        "period_id": "PER-2027",
        "company_id": "SH",
        "branch_id": "local-reference",
        "owner_id": "AS-P007",
        "control_ids": ["SH-IAM-007"],
        "period_start": "2027-01-01T00:00:00Z",
        "period_end_exclusive": "2028-01-01T00:00:00Z",
        "declared_at": "2026-12-31T12:00:00Z",
        "inventory": [{"id": "LOCAL-ACCOUNT", "description": "Explicit local exercise account"}],
        "local_basis": "Operator-declared local exercise only; no corporate cadence inferred",
        "schedule": [
            {
                "id": "REVIEW-Q1",
                "inventory_ids": ["LOCAL-ACCOUNT"],
                "control_id": "SH-IAM-007",
                "window_start": "2027-01-01T00:00:00Z",
                "window_end_exclusive": "2027-04-01T00:00:00Z",
                "due_at": "2027-04-01T00:00:00Z",
                "depends_on": [],
            }
        ],
    }


def private_json(path, value):
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    return path


def test_actual_cli_creates_empty_schedule_then_readonly_due_report(tmp_path):
    source = private_json(tmp_path / "plan.json", plan())
    root = tmp_path / "company"
    command = [sys.executable, "-m", "tools.audit_suite.company_operating_period"]
    created = subprocess.run(
        [
            *command,
            "create",
            "--plan",
            str(source),
            "--destination",
            str(root),
            "--repository",
            str(REPO),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "PYTHONPATH": str(REPO)},
    )
    assert json.loads(created.stdout) == {
        "status": "COMPLETE",
        "action": "create",
        "audit_created": False,
    }
    native = root / "company.sqlite3"
    before = native.read_bytes()
    out = tmp_path / "report"
    subprocess.run(
        [
            *command,
            "report",
            "--store",
            str(root),
            "--period-id",
            "PER-2027",
            "--as-of",
            "2027-04-02T00:00:00Z",
            "--destination",
            str(out),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "PYTHONPATH": str(REPO)},
    )
    assert native.read_bytes() == before
    manifest = json.loads((out / "MANIFEST.json").read_bytes())
    assert manifest["files"]["REPORT.json"] == sha((out / "REPORT.json").read_bytes())
    assert manifest["operation_executed_by_report"] is False
    assert {
        "enterprise/audit_suite/company_operating_period.py",
        "tools/audit_suite/company_operating_period.py",
    } <= manifest["analysis_modules_sha256"].keys()
    assert not list(tmp_path.rglob("engagements.sqlite3"))
    assert all(not p.stat().st_mode & 0o077 for p in [root, native, out, *out.iterdir()])


def test_record_skip_replay_and_report_preserve_history(tmp_path):
    root = tmp_path / "company"
    create(private_json(tmp_path / "plan.json", plan()), root, REPO)
    action = {
        "period_id": "PER-2027",
        "occurrence_id": "REVIEW-Q1",
        "expected_version": 0,
        "command_id": "SKIP-Q1",
        "recorded_at": "2027-04-02T00:00:00Z",
        "disposition": "SKIPPED",
        "sources": [],
        "reason": "Explicit local exercise occurrence was not performed",
        "predecessor_refs": [],
    }
    path = private_json(tmp_path / "action.json", action)
    first = record(root, path)
    assert record(root, path) == first
    store = CompanyStore(root)
    with store._db() as db:
        assert db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 2
        for table in ["grants", "collections", "access_events"]:
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    report(root, "PER-2027", "2027-04-03T00:00:00Z", tmp_path / "report")


@pytest.mark.parametrize("raw", ['{"period_id":"A","period_id":"B"}', '{"number":1e999}'])
def test_strict_plan_rejected_before_destination_creation(tmp_path, raw):
    path = tmp_path / "plan.json"
    path.write_text(raw)
    path.chmod(0o600)
    with pytest.raises(DomainError, match="Strict finite"):
        create(path, tmp_path / "company", REPO)
    assert not (tmp_path / "company").exists()


def test_existing_destination_and_report_inside_source_rejected(tmp_path):
    path = private_json(tmp_path / "plan.json", plan())
    root = tmp_path / "company"
    create(path, root, REPO)
    before = (root / "company.sqlite3").read_bytes()
    with pytest.raises(DomainError, match="New destination"):
        create(path, root, REPO)
    with pytest.raises(DomainError, match="outside"):
        report(root, "PER-2027", "2027-04-03T00:00:00Z", root / "report")
    assert (root / "company.sqlite3").read_bytes() == before


def test_report_and_record_do_not_initialize_missing_database(tmp_path):
    root = tmp_path / "company"
    root.mkdir(mode=0o700)
    action = private_json(
        tmp_path / "action.json",
        {
            k: None
            for k in (
                "period_id",
                "occurrence_id",
                "expected_version",
                "command_id",
                "recorded_at",
                "disposition",
                "sources",
                "reason",
                "predecessor_refs",
            )
        },
    )
    with pytest.raises(FileNotFoundError):
        record(root, action)
    with pytest.raises(FileNotFoundError):
        report(root, "PER-2027", "2027-04-03T00:00:00Z", tmp_path / "report")
    assert not list(root.iterdir())


def test_changed_report_helper_pin_prevents_publication(tmp_path, monkeypatch):
    from tools.audit_suite import company_operating_period as cli

    root = tmp_path / "company"
    create(private_json(tmp_path / "plan.json", plan()), root, REPO)
    before = (root / "company.sqlite3").read_bytes()
    original = cli.report_code_pins
    reads = 0

    def changed_pin():
        nonlocal reads
        reads += 1
        pins = original()
        if reads > 1:
            pins["enterprise/audit_suite/inference.py"] = "0" * 64
        return pins

    monkeypatch.setattr(cli, "report_code_pins", changed_pin)
    with pytest.raises(DomainError, match="code changed"):
        report(root, "PER-2027", "2027-04-03T00:00:00Z", tmp_path / "report")
    assert not (tmp_path / "report").exists()
    assert not list(tmp_path.glob(".operating-period-report-*"))
    assert (root / "company.sqlite3").read_bytes() == before
