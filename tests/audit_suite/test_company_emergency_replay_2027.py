"""Selected replay source retains causal history and fails closed on tampering."""

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_emergency_replay_2027 as source
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE_REPOSITORY = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


def test_selected_replay_preserves_denials_and_upstream_open_gates(tmp_path):
    tmp_path.chmod(0o700)
    run = tmp_path / "source"
    assert source.create(run, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY) == (
        source.verify(run, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)
    )
    receipt = json.loads((run / "RECEIPT.json").read_text())
    assert receipt["native_version_counts"] == {"CLEAN": 8, "MESSY": 15}
    assert receipt["local_open_exception_counts"] == {"CLEAN": 0, "MESSY": 1}
    assert receipt["selected_population_count"] == 1
    assert receipt["source_complete"] is receipt["audit_task_credit"] is False
    assert receipt["actual_phi_processing"] is receipt["deployed_recovery_proven"] is False
    assert receipt["external_bytes_or_packets"] == 0
    refs = receipt["upstream_original_refs"]["MESSY"]
    assert refs["bcm_open_closure"]["record"] == "KEY-AND-CAPACITY"
    assert refs["iam_open_exception"]["record"] == "EXC-IAM005-EMERGENCY-STATUS-01"
    assert refs["sec005_open_exception"]["record"] == "EXC-SEC005-Q4-01"
    assert refs["phi_ba_open_exception"]["record"] == "EXC-01"
    assert all(set(ref) == set(source.ORIGINAL_FIELDS) for ref in refs.values())
    context = source._context(REPOSITORY, PRIVATE_REPOSITORY)
    rows = [json.loads(row["content"]) for row in source._rows(context, "MESSY")]
    assert [row["decision"] for row in rows[:5]] == [
        "SELECTED_ONLY",
        "PENDING_AUTHORITY",
        "INVALID_REQUEST",
        "DENY_NO_REPLAY",
        "OPEN",
    ]
    assert rows[-1]["decision"] == "OPEN"
    assert rows[-1]["upstream_exception_status"] == {
        "bcm_capacity_bia": "OPEN",
        "iam_coverage": "OPEN",
        "sec005_telemetry": "OPEN",
        "phi_ba_flowdown": "OPEN",
    }
    expected_hash = hashlib.sha256(source.iam.MARKER_BYTES).hexdigest()
    observed = {row["decision"]: row["observed_checkpoint_sha256"] for row in rows}
    assert observed["HASH_MISMATCH_NO_BYTES_SENT"] != expected_hash
    assert observed["HASH_MATCH_NO_BYTES_SENT"] == expected_hash
    for earlier, later in zip(rows, rows[1:], strict=False):
        assert earlier["event_at"] < later["event_at"]
        assert (
            later["previous_native_content"]["sha256"]
            == hashlib.sha256(
                json.dumps(earlier, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
        )
    with sqlite3.connect(
        (run / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        assert [
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections", "access_events")
        ] == [0, 0, 0]


def test_unreviewed_attachment_fails_closed(tmp_path):
    tmp_path.chmod(0o700)
    run = tmp_path / "source"
    source.create(run, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)
    attachment = run / "unreviewed.txt"
    attachment.write_text("extra")
    attachment.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="Exact three-file"):
        source.verify(run, repository=REPOSITORY, private_repository=PRIVATE_REPOSITORY)
