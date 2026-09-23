"""Independent age-proof regression through real export and native admission."""

from enterprise.audit_suite import company_backup_admission as admission
from enterprise.audit_suite import company_backup_criterion as criterion
from enterprise.audit_suite import company_backup_runtime as backup
from enterprise.audit_suite import company_configuration_export as export
from tests.audit_suite.test_company_backup_criterion import lease, setup
from tests.audit_suite.test_company_configuration_export import args
from tests.audit_suite.test_company_configuration_runtime import ready


def test_native_admission_cannot_rejuvenate_old_producer_checkpoint(tmp_path, monkeypatch):
    consumer = tmp_path / "consumer"
    consumer.mkdir(mode=0o700)
    producer = tmp_path / "producer"
    producer.mkdir(mode=0o700)
    initialize = backup.initialize

    def initialize_bytes(*a, **kw):
        # The maintained configuration exporter produces a data-only JSON object,
        # not the backup runtime's separate JSON_RECORDS schema.
        kw["datasets"] = [{"id": "DATA", "format": "BYTES"}]
        return initialize(*a, **kw)

    with monkeypatch.context() as context:
        context.setattr(backup, "initialize", initialize_bytes)
        runtime = setup(consumer)
    source = ready.__wrapped__(producer)
    output = export.export_current(source[0], **args(source))
    with backup.database(source[0]) as db:
        definition = backup.pin(
            db.execute("SELECT * FROM versions WHERE system='configuration_runtime'").fetchone()
        )
    selected = admission.inspect_source(
        source[0], source_pin=output["native_pin"], source_definition_pin=definition
    )
    lease_pin = backup.record_lease(runtime[0], **lease(runtime))["lease_pin"]
    cfg = backup._config(runtime[0], runtime[1])
    admitted = admission.admit_dataset(
        runtime[0],
        expected_runtime_sha256=runtime[1],
        expected_revision=1,
        command_id="admit-old",
        dataset_id="DATA",
        operator_id=cfg["operator_id"],
        event_at="2028-10-02T08:00:00Z",
        source_root=source[0],
        source_store_id=selected["source_store_id"],
        source_pin=output["native_pin"],
        source_definition_pin=definition,
        expected_source_metadata_sha256=selected["metadata_sha256"],
    )
    backup.run_backup(
        runtime[0],
        expected_runtime_sha256=runtime[1],
        expected_revision=2,
        command_id="copy",
        occurrence_id="B0",
        source_pin=admitted["source_pin"],
        lease_pin=lease_pin,
        attempted_at="2028-10-02T08:01:00Z",
        rationale="Copy a retained older producer snapshot",
    )
    result = criterion.evaluate(
        runtime[0], expected_runtime_sha256=runtime[1], as_of="2028-10-02T08:30:00Z"
    )
    data = result["datasets"]["DATA"]
    assert selected["metadata"]["event_at"] == "2027-02-03T00:00:00.000000+00:00"
    assert data["points"][0]["checkpoint_at"] == selected["metadata"]["event_at"]
    assert data["points"][0]["checkpoint_at"] != admitted["event_at"]
    assert data["age_breach_intervals"]
    assert data["intervals"][-1]["status"] == "BREACH"
    assert result["publication_allowance_violations"]
    assert result["whole_period_effectiveness"] == "NOT_ASSESSED"
