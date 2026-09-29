"""A parsed restored-copy read is distinct from byte equality and audit acceptance."""

import json

import pytest

from enterprise.audit_suite import company_backup_runtime as backup
from enterprise.audit_suite import company_backup_use_probe as use_probe
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from tests.audit_suite.test_company_backup_runtime import call, prepared
from tests.audit_suite.test_company_backup_runtime import runtime as runtime
from tools.audit_suite import company_backup_runtime as cli


def _before(rt):
    with backup.database(rt[0]) as db:
        return (
            db.execute("SELECT revision FROM backup_runtime_state").fetchone()[0],
            db.execute("SELECT COUNT(*) FROM versions").fetchone()[0],
            db.execute("SELECT COUNT(*) FROM backup_runtime_commands").fetchone()[0],
        )


def _restored(rt, *, expected=1, contract_before=True):
    source, backup_lease, restore_lease = prepared(rt)
    reader = {
        "kind": "JSON_RECORD_FIELD_EQUALS",
        "record_id": "ONE",
        "field": "value",
        "expected": expected,
    }
    if contract_before:
        contract = call(
            rt,
            use_probe.record_use_contract,
            3,
            "use-contract",
            occurrence_id="R1",
            source_pin=source,
            reader=reader,
            rationale="Read record ONE through the isolated restored JSON dataset",
            event_at="2027-01-01T09:02:00Z",
        )
        revision = 4
    else:
        contract = None
        revision = 3
    copied = call(
        rt,
        backup.run_backup,
        revision,
        "backup-for-use",
        occurrence_id="B1",
        source_pin=source,
        lease_pin=backup_lease,
        attempted_at="2027-01-01T10:00:00Z",
    )
    restored = call(
        rt,
        backup.run_restore,
        revision + 1,
        "restore-for-use",
        occurrence_id="R1",
        backup_pin=copied["object_pin"],
        comparison_source_pin=source,
        lease_pin=restore_lease,
        attempted_at="2027-01-02T11:00:00Z",
    )
    if contract is None:
        contract = call(
            rt,
            use_probe.record_use_contract,
            revision + 2,
            "late-use-contract",
            occurrence_id="R1",
            source_pin=source,
            reader=reader,
            rationale="Attempt to define expected use after seeing restored bytes",
            event_at="2027-01-02T11:00:00Z",
        )
        revision += 1
    return contract, restored, revision + 2


@pytest.mark.parametrize(
    "expected,status", [(1, "PASS_LOCAL_PARSED_READ"), (2, "FAIL_LOCAL_PARSED_READ")]
)
def test_native_parsed_restored_copy_probe_is_collectable_and_replay_safe(
    runtime, expected, status
):
    contract, restored, revision = _restored(runtime, expected=expected)
    request = dict(
        contract_pin=contract["contract_pin"],
        restore_job_pin=restored["job_pin"],
        restored_dataset_pin=restored["object_pin"],
        event_at="2027-01-02T11:01:00Z",
    )
    result = call(runtime, use_probe.run_restore_use_probe, revision, "probe", **request)
    assert result["status"] == status
    with backup.database(runtime[0]) as db:
        row = backup.native(db, result["probe_pin"])
        body = json.loads(row["content"])
        assert body["read_status"] == "READ" and body["actual"] == 1
        assert body["copy_sha256"] == restored["object_pin"]["sha256"]
        assert body["contract_pin"] == contract["contract_pin"]
        assert body["restored_dataset_pin"] == restored["object_pin"]
        assert body["performed_by"] != body["recorded_review_contact"]
        assert body["review_performed"] is False
        assert body["not_application_or_data_usability_acceptance"] is True
    before = _before(runtime)
    assert call(runtime, use_probe.run_restore_use_probe, revision, "probe", **request) == result
    assert _before(runtime) == before
    cfg = json.loads((runtime[0] / "RUNTIME.json").read_text())
    store = CompanyStore(runtime[0])
    company, branch = cfg["plan"]["company_id"], cfg["plan"]["branch_id"]
    store.grant("AUDITOR", "ENGAGEMENT", company, branch, "restore_use_probe")
    read = store.read_version(
        "AUDITOR",
        "ENGAGEMENT",
        company,
        branch,
        "restore_use_probe",
        "R1",
        version=1,
        as_of="2027-01-02T11:02:00Z",
    )
    assert read["content"] == row["content"]
    assert sha(read["content"]) == result["probe_pin"]["sha256"]
    collection = store.collect(
        "AUDITOR",
        "ENGAGEMENT",
        company,
        branch,
        "restore_use_probe",
        "R1",
        version=1,
        as_of="2027-01-02T11:02:00Z",
        command_id="COLLECT-USE-PROBE",
    )
    assert collection["source"]["sha256"] == result["probe_pin"]["sha256"]


def test_posthoc_contract_and_changed_copy_fail_without_native_probe(runtime):
    contract, restored, revision = _restored(runtime, contract_before=False)
    request = dict(
        contract_pin=contract["contract_pin"],
        restore_job_pin=restored["job_pin"],
        restored_dataset_pin=restored["object_pin"],
        event_at="2027-01-02T11:02:00Z",
    )
    before = _before(runtime)
    with pytest.raises(CompanyStoreError, match="precede restore"):
        call(runtime, use_probe.run_restore_use_probe, revision, "late-probe", **request)
    assert _before(runtime) == before


def test_tampered_persisted_copy_cannot_be_probed(runtime):
    contract, restored, revision = _restored(runtime)
    with backup.database(runtime[0]) as db:
        job = json.loads(backup.native(db, restored["job_pin"])["content"])
    copy_path = runtime[0] / job["copy_path"]
    copy_path.write_bytes(b'{"records":[{"id":"ONE","value":2}]}')
    before = _before(runtime)
    with pytest.raises(CompanyStoreError, match="Restored copy bytes changed"):
        call(
            runtime,
            use_probe.run_restore_use_probe,
            revision,
            "tampered-probe",
            contract_pin=contract["contract_pin"],
            restore_job_pin=restored["job_pin"],
            restored_dataset_pin=restored["object_pin"],
            event_at="2027-01-02T11:01:00Z",
        )
    assert _before(runtime) == before


def test_unsupported_read_contract_rejected_before_mutation(runtime):
    source, _, _ = prepared(runtime)
    before = _before(runtime)
    with pytest.raises(CompanyStoreError, match="Supported parsed read path"):
        call(
            runtime,
            use_probe.record_use_contract,
            3,
            "invalid-contract",
            occurrence_id="R1",
            source_pin=source,
            reader={"kind": "HASH_EQUALS", "field": "value", "expected": 1},
            rationale="A hash alone cannot prove restored use",
            event_at="2027-01-01T09:02:00Z",
        )
    assert _before(runtime) == before


def test_operator_cli_publishes_exact_probe_receipt(runtime, tmp_path):
    contract, restored, revision = _restored(runtime)
    action = {
        "kind": "USE_PROBE",
        "parameters": {
            "expected_runtime_sha256": runtime[1],
            "expected_revision": revision,
            "command_id": "cli-use-probe",
            "contract_pin": contract["contract_pin"],
            "restore_job_pin": restored["job_pin"],
            "restored_dataset_pin": restored["object_pin"],
            "event_at": "2027-01-02T11:01:00Z",
        },
    }
    action_path = tmp_path / "probe-action.json"
    action_path.write_bytes(encoded(action))
    action_path.chmod(0o600)
    receipt = tmp_path / "probe-receipt"
    result = cli.operate(runtime[0], action_path, receipt)
    assert result["status"] == "PASS_LOCAL_PARSED_READ"
    manifest = json.loads((receipt / "MANIFEST.json").read_bytes())
    assert manifest["audit_created"] is False
    for name, expected_hash in manifest["files"].items():
        assert sha((receipt / name).read_bytes()) == expected_hash
    assert json.loads((receipt / "RESULT.json").read_bytes()) == result
