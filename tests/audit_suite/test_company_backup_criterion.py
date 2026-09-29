"""Optional local criterion binding and byte-backed logical checkpoint proof."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from enterprise.audit_suite import company_backup_criterion as criterion
from enterprise.audit_suite import company_backup_monitor as monitor
from enterprise.audit_suite import company_backup_runtime as backup
from enterprise.audit_suite.company_operating_period import create_period
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from enterprise.audit_suite.organization import snapshot

ROOT = Path(__file__).resolve().parents[2]


def setup(tmp_path, change=None, enabled=True):
    start = datetime(2028, 10, 2, 8, tzinfo=UTC)

    def stamp(d):
        return d.isoformat(timespec="microseconds")

    org = snapshot(ROOT, as_of="2028-10-02")
    assignment = next(r for r in org["control_assignments"] if r["control_id"] == "SH-BCM-003")
    owner, reviewer = assignment["primary_person_id"], assignment["operating_reviewer_person_id"]
    plan = dict(
        period_id="LOCAL",
        company_id="SH",
        branch_id="local",
        owner_id=owner,
        control_ids=["SH-BCM-002"],
        period_start=stamp(start),
        period_end_exclusive=stamp(start + timedelta(hours=3)),
        declared_at="2028-10-01T11:00:00.000000+00:00",
        inventory=[{"id": "DATA", "description": "Synthetic local records"}],
        local_basis="Prospective simulation only",
        schedule=[],
    )
    for n in range(6):
        t = start + timedelta(minutes=n * 30)
        plan["schedule"].append(
            dict(
                id=f"B{n}",
                control_id="SH-BCM-002",
                inventory_ids=["DATA"],
                depends_on=[],
                window_start=stamp(t),
                window_end_exclusive=stamp(t + timedelta(minutes=30)),
                due_at=stamp(t + timedelta(minutes=5)),
            )
        )
    body = dict(
        format="LOCAL_BACKUP_DATA_LOSS_CRITERION_V1",
        status="LOCAL_SIMULATION_RULE_APPROVED",
        scope={"service_id": "SVC-compute", "dataset_ids": ["DATA"]},
        author_id=owner,
        reviewer_id=reviewer,
        approved_at="2028-10-01T10:00:00.000000+00:00",
        effective_from=plan["period_start"],
        effective_to_exclusive=plan["period_end_exclusive"],
        max_age_seconds=3600,
        checkpoint_interval_seconds=1800,
        publication_allowance_seconds=300,
        retention="RETAIN_ALL_LOCAL_EXERCISE_ORIGINALS_NO_DELETION",
        isolation="PRIVATE_LOCAL_STORE_NOT_PRODUCTION_ISOLATION",
        rationale="Declared local age rule, not enterprise acceptance",
    )
    if change:
        change(body)
    decision = tmp_path / "criterion"
    decision.mkdir(mode=0o700)
    store = CompanyStore(decision)
    store.register_system("SH", "local", criterion.SYSTEM, owner)
    row = store.append_version(
        "SH",
        "local",
        criterion.SYSTEM,
        "RULE",
        expected_version=0,
        command_id="approval",
        content=encoded(body),
        event_at=body["approved_at"],
        available_at=body["approved_at"],
        provenance={"source_reference": "Explicit local decision"},
    )
    with backup.database(decision) as db:
        meta = dict(db.execute("SELECT * FROM versions").fetchone())
        meta.pop("content")
    dependency = {
        "root": str(decision),
        "native": backup.pin(row),
        "metadata_sha256": sha(encoded(meta)),
    }
    ledger = tmp_path / "ledger"
    ledger.mkdir(mode=0o700)
    declaration = create_period(CompanyStore(ledger), repository=ROOT, plan=plan)
    kwargs = dict(
        repository=ROOT,
        declaration_root=ledger,
        declaration_ref=backup.pin(declaration),
        bindings=[
            {"occurrence_id": s["id"], "dataset_id": "DATA", "operation": "BACKUP"}
            for s in plan["schedule"]
        ],
        datasets=[{"id": "DATA", "format": "JSON_RECORDS"}],
    )
    if enabled:
        kwargs["local_data_loss_criterion"] = dependency
    root = tmp_path / "runtime"
    result = backup.initialize(root, **kwargs)
    return root, result["runtime_sha256"], decision, dependency, body


def alter(root, field="imported_at", value="2028-01-01T00:00:00.000000+00:00"):
    with backup.database(root, True) as db:
        for (name,) in db.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='versions'"
        ):
            db.execute('DROP TRIGGER "' + name + '"')
        db.execute("UPDATE versions SET " + field + "=?", (value,))


def lease(rt):
    return dict(
        expected_runtime_sha256=rt[1],
        expected_revision=0,
        command_id="lease",
        operation="BACKUP_WRITE",
        enabled=True,
        valid_from="2028-10-02T08:00:00Z",
        expires_at="2028-10-02T12:00:00Z",
        event_at="2028-10-02T08:00:00Z",
    )


def test_optional_binding_and_exact_replay(tmp_path):
    rt = setup(tmp_path)
    request = lease(rt)
    first = backup.record_lease(rt[0], **request)
    assert backup.record_lease(rt[0], **request) == first
    assert (
        backup.reconcile(rt[0], expected_runtime_sha256=rt[1], as_of="2028-10-02T11:00:00Z")[
            "approved_bia_targets"
        ]
        == "NOT_ESTABLISHED"
    )
    alter(rt[2])
    for read in [
        lambda: backup.record_lease(rt[0], **request),
        lambda: backup.reconcile(
            rt[0], expected_runtime_sha256=rt[1], as_of="2028-10-02T11:00:00Z"
        ),
        lambda: monitor.inspect(rt[0], expected_runtime_sha256=rt[1], as_of="2028-10-02T11:00:00Z"),
    ]:
        with pytest.raises(CompanyStoreError, match="metadata changed"):
            read()


def test_absent_criterion_preserves_definition(tmp_path):
    rt = setup(tmp_path, enabled=False)
    assert "local_data_loss_criterion" not in json.loads((rt[0] / "RUNTIME.json").read_text())
    alter(rt[2])
    backup.record_lease(rt[0], **lease(rt))


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b.update(max_age_seconds=True),
        lambda b: b.update(max_age_seconds=2000),
        lambda b: b.update(status="ENTERPRISE_APPROVED"),
        lambda b: b.update(reviewer_id=b["author_id"]),
        lambda b: b["scope"].update(service_id="WRONG"),
        lambda b: b.update(checkpoint_interval_seconds=1700),
        lambda b: b.update(publication_allowance_seconds=299),
        lambda b: b.update(rationale=" " * 2100 + "x"),
        lambda b: b.update(approved_at="2028-10-01T12:00:00.000000+00:00"),
    ],
)
def test_invalid_criterion_rejected_before_publication(tmp_path, change):
    with pytest.raises(CompanyStoreError):
        setup(tmp_path, change)
    assert not (tmp_path / "runtime").exists()


def test_final_dependency_race_rolls_back_command(tmp_path, monkeypatch):
    rt = setup(tmp_path)
    original = backup._insert

    def race(*a, **kw):
        result = original(*a, **kw)
        alter(rt[2])
        return result

    monkeypatch.setattr(backup, "_insert", race)
    with pytest.raises(CompanyStoreError, match="metadata changed"):
        backup.record_lease(rt[0], **lease(rt))
    with backup.database(rt[0]) as db:
        assert db.execute("SELECT revision FROM backup_runtime_state").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM backup_runtime_commands").fetchone()[0] == 0


def test_oversized_metadata_rejected_before_native(tmp_path, monkeypatch):
    rt = setup(tmp_path)
    alter(rt[2], "provenance", "x" * 20000)
    monkeypatch.setattr(criterion, "native", lambda *a, **k: pytest.fail("oversized row fetched"))
    with pytest.raises(CompanyStoreError, match="Bounded criterion"):
        backup.record_lease(rt[0], **lease(rt))


def test_actual_copy_parse_and_startup_gap(tmp_path):
    rt = setup(tmp_path)
    pin = backup.record_lease(rt[0], **lease(rt))["lease_pin"]
    raw = encoded({"records": [{"id": "ONE", "value": 1}]})
    source = backup.append_dataset(
        rt[0],
        expected_runtime_sha256=rt[1],
        expected_revision=1,
        command_id="data",
        dataset_id="DATA",
        content=raw,
        expected_sha256=sha(raw),
        event_at="2028-10-02T08:00:00Z",
    )["source_pin"]
    result = backup.run_backup(
        rt[0],
        expected_runtime_sha256=rt[1],
        expected_revision=2,
        command_id="copy",
        occurrence_id="B0",
        source_pin=source,
        lease_pin=pin,
        attempted_at="2028-10-02T08:01:00Z",
        rationale="Local byte copy",
    )
    report = criterion.evaluate(rt[0], expected_runtime_sha256=rt[1], as_of="2028-10-02T08:30:00Z")
    data = report["datasets"]["DATA"]
    assert len(data["unestablished_intervals"]) == 1
    assert data["unestablished_intervals"][0]["to"] == "2028-10-02T08:01:00.000000+00:00"
    assert data["points"][0]["object_pin"] == result["object_pin"]
    with backup.database(rt[0]) as db:
        job = json.loads(
            db.execute("SELECT content FROM versions WHERE system='backup_job'").fetchone()[0]
        )
    (rt[0] / job["copy_path"]).write_bytes(b"bad")
    with pytest.raises(CompanyStoreError, match="copied bytes differ"):
        criterion.evaluate(rt[0], expected_runtime_sha256=rt[1], as_of="2028-10-02T08:30:00Z")


def test_freshest_checkpoint_not_latest_publication():
    prefix = "2028-10-02T"
    points = [
        {"checkpoint_at": prefix + "08:00:00+00:00", "published_at": prefix + "08:01:00+00:00"},
        {"checkpoint_at": prefix + "08:30:00+00:00", "published_at": prefix + "08:31:00+00:00"},
        {"checkpoint_at": prefix + "08:00:00+00:00", "published_at": prefix + "08:40:00+00:00"},
        {"checkpoint_at": prefix + "09:30:00+00:00", "published_at": prefix + "09:40:00+00:00"},
    ]
    intervals = criterion.age_intervals(
        points, start=prefix + "08:00:00+00:00", end=prefix + "10:00:00+00:00", maximum=3600
    )
    assert intervals[0]["status"] == "UNESTABLISHED"
    assert max(i["maximum_age_seconds"] or 0 for i in intervals) == 4200
    assert intervals[-2]["checkpoint_at"] == prefix + "08:30:00+00:00"


def test_failed_copy_never_establishes_checkpoint(tmp_path):
    rt = setup(tmp_path)
    request = lease(rt)
    request["enabled"] = False
    pin = backup.record_lease(rt[0], **request)["lease_pin"]
    raw = encoded({"records": [{"id": "ONE"}]})
    source = backup.append_dataset(
        rt[0],
        expected_runtime_sha256=rt[1],
        expected_revision=1,
        command_id="data",
        dataset_id="DATA",
        content=raw,
        expected_sha256=sha(raw),
        event_at="2028-10-02T08:00:00Z",
    )["source_pin"]
    backup.run_backup(
        rt[0],
        expected_runtime_sha256=rt[1],
        expected_revision=2,
        command_id="failure",
        occurrence_id="B0",
        source_pin=source,
        lease_pin=pin,
        attempted_at="2028-10-02T08:01:00Z",
        rationale="Explicit failed local attempt",
    )
    result = criterion.evaluate(rt[0], expected_runtime_sha256=rt[1], as_of="2028-10-02T08:10:00Z")
    assert len(result["failed_attempts"]) == 1
    assert result["datasets"]["DATA"]["points"] == []
    assert result["datasets"]["DATA"]["due_without_success"] == ["B0"]
    assert result["datasets"]["DATA"]["intervals"][0]["status"] == "UNESTABLISHED"


def test_monitor_final_dependency_race(tmp_path, monkeypatch):
    rt = setup(tmp_path)
    original = monitor._capture

    def race(*args, **kwargs):
        result = original(*args, **kwargs)
        alter(rt[2])
        return result

    monkeypatch.setattr(monitor, "_capture", race)
    with pytest.raises(CompanyStoreError, match="metadata changed"):
        monitor.inspect(rt[0], expected_runtime_sha256=rt[1], as_of="2028-10-02T11:00:00Z")


def successful(tmp_path):
    rt = setup(tmp_path)
    pin = backup.record_lease(rt[0], **lease(rt))["lease_pin"]
    raw = encoded({"records": [{"id": "ONE"}]})
    source = backup.append_dataset(
        rt[0],
        expected_runtime_sha256=rt[1],
        expected_revision=1,
        command_id="data",
        dataset_id="DATA",
        content=raw,
        expected_sha256=sha(raw),
        event_at="2028-10-02T08:00:00Z",
    )["source_pin"]
    backup.run_backup(
        rt[0],
        expected_runtime_sha256=rt[1],
        expected_revision=2,
        command_id="copy",
        occurrence_id="B0",
        source_pin=source,
        lease_pin=pin,
        attempted_at="2028-10-02T08:01:00Z",
        rationale="Local proof fixture",
    )
    return rt


def test_native_metadata_race_without_revision_change(tmp_path, monkeypatch):
    rt = successful(tmp_path)
    original = criterion.age_intervals

    def race(*a, **kw):
        result = original(*a, **kw)
        alter(rt[0])
        return result

    monkeypatch.setattr(criterion, "age_intervals", race)
    with pytest.raises(CompanyStoreError, match="Native proof changed"):
        criterion.evaluate(rt[0], expected_runtime_sha256=rt[1], as_of="2028-10-02T08:10:00Z")


@pytest.mark.parametrize(
    "field,value", [("company", "FOREIGN"), ("origin", "IMPORTED"), ("input_digest", "0" * 64)]
)
def test_native_identity_metadata_rejected(tmp_path, field, value):
    rt = successful(tmp_path)
    if field == "company":
        with backup.database(rt[0]) as db:
            rows = [dict(row) for row in db.execute("SELECT * FROM systems")]
        for row in rows:
            CompanyStore(rt[0]).register_system(value, row["branch"], row["system"], row["owner"])
    alter(rt[0], field, value)
    with pytest.raises(CompanyStoreError, match="Native proof"):
        criterion.evaluate(rt[0], expected_runtime_sha256=rt[1], as_of="2028-10-02T08:10:00Z")


def test_object_publication_must_match_job(tmp_path):
    rt = successful(tmp_path)
    with backup.database(rt[0], True) as db:
        for (name,) in db.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='versions'"
        ):
            db.execute('DROP TRIGGER "' + name + '"')
        row = dict(db.execute("SELECT * FROM versions WHERE system='backup_object'").fetchone())
        at = "2028-10-02T08:02:00.000000+00:00"
        fingerprint = sha(
            backup._json(
                [
                    [row[k] for k in ["company", "branch", "system", "record"]],
                    row["version"] - 1,
                    at,
                    at,
                    row["origin"],
                    json.loads(row["provenance"]),
                    row["sha256"],
                ]
            ).encode()
        )
        db.execute(
            "UPDATE versions SET event_at=?,available_at=?,input_digest=? "
            "WHERE system='backup_object'",
            (at, at, fingerprint),
        )
    with pytest.raises(CompanyStoreError, match="Object publication differs"):
        criterion.evaluate(rt[0], expected_runtime_sha256=rt[1], as_of="2028-10-02T08:10:00Z")


def test_breach_threshold_precedes_late_stale_publication_interval():
    def t(time):
        return "2028-10-02T" + time + ":00.000000+00:00"

    points = [
        {"checkpoint_at": t("08:30"), "published_at": t("08:31")},
        {"checkpoint_at": t("08:00"), "published_at": t("09:35")},
    ]
    rows = criterion.age_intervals(points, start=t("08:30"), end=t("09:40"), maximum=3600)
    assert rows[-1]["from"] == t("09:35")
    assert rows[-1]["checkpoint_at"] == t("08:30")
    assert rows[-1]["breach_after"] == t("09:30")
