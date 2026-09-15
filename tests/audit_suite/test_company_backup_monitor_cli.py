"""Actual trusted CLI inspection, scan, replay and continued backup operations."""

import json
import subprocess
import sys

from enterprise.audit_suite import company_backup_runtime as backup
from enterprise.audit_suite.operating_source_bridge import sha
from tests.audit_suite.test_company_backup_runtime import runtime as runtime_fixture
from tests.audit_suite.test_company_backup_runtime_cli import (
    ROOT,
    action,
    private_json,
    run_cli,
)


def test_monitor_cli_exact_inspection_replay_and_shared_runtime(tmp_path):
    rt = runtime_fixture.__wrapped__(tmp_path)
    output = tmp_path / "inspection"
    before = (rt[0] / "company.sqlite3").read_bytes()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.audit_suite.company_backup_runtime",
            "monitor-inspect",
            "--runtime",
            str(rt[0]),
            "--runtime-sha256",
            rt[1],
            "--as-of",
            "2027-01-04T12:00:00Z",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads((output / "RESULT.json").read_text())
    assert (rt[0] / "company.sqlite3").read_bytes() == before
    assert result["runtime_revision"] == 0
    request = action(
        tmp_path,
        rt,
        "MONITOR",
        0,
        "monitor-one",
        expected_jobs_sha256=result["jobs_sha256"],
        as_of="2027-01-04T12:00:00Z",
        recorded_at="2027-01-04T13:00:00Z",
        operator_id=backup._config(rt[0], rt[1])["operator_id"],
        rationale="Explicit scan of four locally declared due occurrences.",
    )
    _, recorded = run_cli(rt, request, tmp_path / "scan")
    _, replay = run_cli(rt, request, tmp_path / "replay")
    assert replay == recorded
    with backup.database(rt[0]) as db:
        assert db.execute("select revision from backup_runtime_state").fetchone()[0] == 1
        assert (
            db.execute("select count(*) from versions where system='monitor_ticket'").fetchone()[0]
            == 4
        )
    content = private_json(tmp_path / "dataset.json", {"records": [{"id": "ONE", "value": 1}]})
    _, continued = run_cli(
        rt,
        action(
            tmp_path,
            rt,
            "DATASET",
            1,
            "continued-data",
            dataset_id="DATA",
            content_path=str(content),
            expected_sha256=sha(content.read_bytes()),
            event_at="2027-01-04T14:00:00Z",
        ),
        tmp_path / "continued",
    )
    assert continued
    with backup.database(rt[0]) as db:
        assert db.execute("select revision from backup_runtime_state").fetchone()[0] == 2
