import json
from pathlib import Path

import pytest

from enterprise.audit_suite import company_nonhuman_runtime as runtime
from enterprise.audit_suite.company_backup_runtime import database, pin
from enterprise.audit_suite.company_nonhuman_identity_activity import generate_pair
from enterprise.audit_suite.company_operating_period import create_period
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from enterprise.audit_suite.organization import snapshot
from tests.audit_suite.test_company_nonhuman_identity_activity import inputs, versions

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def prepared(tmp_path):
    source, recipe = inputs.__wrapped__(tmp_path)
    original = tmp_path / "prior"
    generate_pair(original, repository=ROOT, source_root=source, recipe=recipe)
    rows = [r for r in versions(original) if r["branch"] == "service-b"]
    refs = [{k: r[k] for k in runtime.FIELDS} for r in rows]
    digest = runtime._sources(
        original, recipe, "service-b", refs, source, "2027-07-01T00:00:00.000000+00:00"
    )[0]
    assignment = next(
        x
        for x in snapshot(ROOT, as_of="2027-07-01")["control_assignments"]
        if x["control_id"] == "SH-IAM-006"
    )
    schedule = []
    for quarter, month, endmonth in [(3, 7, 9), (4, 10, 12)]:
        for kind, date in [
            ("ROTATION", f"2027-{month:02}-15"),
            ("REVIEW", f"2027-{endmonth:02}-30"),
        ]:
            schedule.append(
                {
                    "id": f"{kind}-Q{quarter}",
                    "inventory_ids": [recipe.identity_id],
                    "control_id": "SH-IAM-006",
                    "depends_on": [],
                    "window_start": date + "T00:00:00Z",
                    "window_end_exclusive": date + "T23:59:59Z",
                    "due_at": date + "T12:00:00Z",
                }
            )
    plan = {
        "period_id": "NONHUMAN-H2",
        "company_id": "SH",
        "branch_id": "persistent-service",
        "owner_id": assignment["primary_person_id"],
        "control_ids": ["SH-IAM-006"],
        "declared_at": "2027-07-01T00:00:00Z",
        "period_start": "2027-07-01T00:00:00Z",
        "period_end_exclusive": "2028-01-01T00:00:00Z",
        "inventory": [{"id": recipe.identity_id, "description": "One local inert identity"}],
        "local_basis": "Explicit fictional rotations and scoped reviews; not enterprise policy",
        "schedule": schedule,
    }
    declaration = tmp_path / "declaration"
    declaration.mkdir(mode=0o700)
    record = create_period(CompanyStore(declaration), repository=ROOT, plan=plan)
    kwargs = {
        "repository": ROOT,
        "prior_root": original,
        "prior_recipe": recipe,
        "prior_branch": "service-b",
        "prior_refs": refs,
        "expected_prior_metadata_sha256": digest,
        "backup_source_root": source,
        "declaration_root": declaration,
        "declaration_pin": pin(record),
        "as_of": "2027-07-01T00:00:00Z",
    }
    destination = tmp_path / "runtime"
    receipt = runtime.initialize(destination, **kwargs)
    return destination, receipt, kwargs, assignment


@pytest.mark.parametrize("field,value", [("name", "forged.json"), ("content_type", "text/plain")])
def test_period_document_transport_metadata_is_exact(prepared, tmp_path, field, value):
    _, _, kwargs, _ = prepared
    with database(kwargs["declaration_root"], True) as db:
        db.execute("DROP TRIGGER no_version_update")
        row = db.execute("SELECT provenance FROM versions").fetchone()
        metadata = json.loads(row[0])
        metadata[field] = value
        db.execute("UPDATE versions SET provenance=?", (encoded(metadata).decode(),))
    with pytest.raises(CompanyStoreError, match="Declaration native provenance"):
        runtime.initialize(tmp_path / "refused-transport", **kwargs)


def act(prepared, command, action, payload, at, reviewer=False):
    root, receipt, _, assignment = prepared
    state = runtime.inspect(root, expected_runtime_sha256=receipt["runtime_sha256"], as_of=at)
    return runtime.execute(
        root,
        expected_runtime_sha256=receipt["runtime_sha256"],
        expected_revision=state["revision"],
        expected_state_sha256=state["state_sha256"],
        command_id=command,
        action=action,
        payload=payload,
        actor_id=assignment["operating_reviewer_person_id"]
        if reviewer
        else assignment["primary_person_id"],
        event_at=at,
    )


def test_actual_rotation_denial_copy_and_independent_missing_review(prepared):
    root, receipt, kwargs, _ = prepared
    original = (kwargs["prior_root"] / "company.sqlite3").read_bytes()
    for quarter, month in [(3, 7), (4, 10)]:
        date = f"2027-{month:02}-15"
        act(
            prepared,
            f"rotate{quarter}",
            "ROTATE",
            {"expected_credential_version": quarter - 1, "occurrence_id": f"ROTATION-Q{quarter}"},
            date + "T09:00:00Z",
        )
        copy = {
            "principal_id": kwargs["prior_recipe"].identity_id,
            "source_id": "DATASET-REFERENCE",
            "target_id": kwargs["prior_recipe"].target_id,
        }
        cfg = runtime._config(root, receipt["runtime_sha256"])
        copy["source_id"] = cfg["dataset_id"]
        denied = act(prepared, f"denied{quarter}", "COPY", copy, date + "T09:01:00Z")
        assert (
            denied["observation"]["status"] == "AUTHORIZATION_DENIED" and denied["copy_pin"] is None
        )
        act(
            prepared,
            f"update{quarter}",
            "UPDATE_CONSUMER",
            {"credential_version": quarter},
            date + "T09:02:00Z",
        )
        copied = act(prepared, f"copy{quarter}", "COPY", copy, date + "T09:03:00Z")
        assert copied["copy_pin"]["sha256"] == cfg["dataset_sha256"]
        if quarter == 3:
            act(
                prepared,
                "review3",
                "REVIEW",
                {"occurrence_id": "REVIEW-Q3"},
                "2027-09-30T12:00:00Z",
                True,
            )
    final = runtime.inspect(
        root, expected_runtime_sha256=receipt["runtime_sha256"], as_of="2027-12-31T23:59:59Z"
    )
    assert final["state"]["credential_version"] == final["state"]["consumer_version"] == 4
    assert final["state"]["retired_versions"] == [1, 2, 3]
    assert final["reconciliation"]["missing_due_ids"] == ["REVIEW-Q4"]
    assert len(final["state"]["copy_attempts"]) == 4
    assert original == (kwargs["prior_root"] / "company.sqlite3").read_bytes()
    with database(root) as db:
        copies = db.execute("SELECT content FROM versions WHERE system='copied_dataset'").fetchall()
        source = db.execute(
            "SELECT content FROM versions WHERE system='nonhuman_source'"
        ).fetchone()[0]
        assert len(copies) == 2 and all(r[0] == source for r in copies)
        assert all(
            db.execute("SELECT count(*) FROM " + t).fetchone()[0] == 0
            for t in ("grants", "collections", "access_events")
        )


def test_exact_retry_and_stale_cas_leave_history_unchanged(prepared):
    root, receipt, _, assignment = prepared
    state = runtime.inspect(
        root, expected_runtime_sha256=receipt["runtime_sha256"], as_of="2027-07-15T09:00:00Z"
    )
    command = dict(
        expected_runtime_sha256=receipt["runtime_sha256"],
        expected_revision=0,
        expected_state_sha256=state["state_sha256"],
        command_id="rotate-once",
        action="ROTATE",
        payload={"expected_credential_version": 2, "occurrence_id": "ROTATION-Q3"},
        actor_id=assignment["primary_person_id"],
        event_at="2027-07-15T09:00:00Z",
    )
    result = runtime.execute(root, **command)
    before = (root / "company.sqlite3").read_bytes()
    assert runtime.execute(root, **command) == result
    assert (root / "company.sqlite3").read_bytes() == before
    with pytest.raises(CompanyStoreError, match="Changed command replay"):
        runtime.execute(
            root,
            **{
                **command,
                "payload": {"expected_credential_version": 3, "occurrence_id": "ROTATION-Q3"},
            },
        )
    with pytest.raises(CompanyStoreError, match="Stale state/revision"):
        runtime.execute(root, **{**command, "command_id": "other"})
    assert (root / "company.sqlite3").read_bytes() == before


@pytest.mark.parametrize("version", [True, 2.0])
def test_credential_versions_are_exact_integers(prepared, version):
    with pytest.raises(CompanyStoreError, match="Exact current credential version"):
        act(
            prepared,
            "bad",
            "ROTATE",
            {"expected_credential_version": version, "occurrence_id": "ROTATION-Q3"},
            "2027-07-15T09:00:00Z",
        )


def test_owner_cannot_record_independent_review(prepared):
    with pytest.raises(CompanyStoreError, match="Scoped action actor"):
        act(
            prepared, "bad-review", "REVIEW", {"occurrence_id": "REVIEW-Q3"}, "2027-09-30T12:00:00Z"
        )


def test_wrong_resource_denies_without_copy_original(prepared):
    root, receipt, kwargs, _ = prepared
    result = act(
        prepared,
        "wrong-target",
        "COPY",
        {
            "principal_id": kwargs["prior_recipe"].identity_id,
            "source_id": runtime._config(root, receipt["runtime_sha256"])["dataset_id"],
            "target_id": "UNDECLARED",
        },
        "2027-07-02T00:00:00Z",
    )
    assert result["copy_pin"] is None and result["observation"]["status"] == "AUTHORIZATION_DENIED"
    with database(root) as db:
        assert (
            db.execute("SELECT count(*) FROM versions WHERE system='copied_dataset'").fetchone()[0]
            == 0
        )


@pytest.mark.parametrize(
    "system,field,value",
    [
        ("nonhuman_definition", "origin", "MIGRATED_SYNTHETIC_HISTORY"),
        ("nonhuman_source", "command_id", "forged"),
        ("nonhuman_operation", "available_at", "2027-07-20T00:00:00.000000+00:00"),
        ("copied_dataset", "input_digest", "0" * 64),
        *[
            (system, "imported_at", "2026-01-01T00:00:00.000000+00:00")
            for system in (
                "nonhuman_definition",
                "nonhuman_source",
                "nonhuman_operation",
                "copied_dataset",
            )
        ],
    ],
)
def test_all_native_metadata_is_checked(prepared, system, field, value):
    root, receipt, kwargs, _ = prepared
    cfg = runtime._config(root, receipt["runtime_sha256"])
    act(
        prepared,
        "copy",
        "COPY",
        {
            "principal_id": kwargs["prior_recipe"].identity_id,
            "source_id": cfg["dataset_id"],
            "target_id": cfg["target_id"],
        },
        "2027-07-02T00:00:00Z",
    )
    with database(root, True) as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute("UPDATE versions SET " + field + "=? WHERE system=?", (value, system))
    with pytest.raises(CompanyStoreError):
        runtime.inspect(
            root, expected_runtime_sha256=receipt["runtime_sha256"], as_of="2027-07-03T00:00:00Z"
        )


def test_forged_current_state_does_not_replace_history(prepared):
    root, receipt, _, _ = prepared
    with database(root, True) as db:
        state = json.loads(db.execute("SELECT state FROM nonhuman_state").fetchone()[0])
        state["completed_occurrences"]["REVIEW-Q4"] = {
            "at": "2027-12-30T12:00:00Z",
            "action": "REVIEW",
            "actor_id": "invented",
        }
        db.execute("UPDATE nonhuman_state SET state=?", (json.dumps(state),))
    with pytest.raises(CompanyStoreError, match="Current state differs"):
        runtime.inspect(
            root, expected_runtime_sha256=receipt["runtime_sha256"], as_of="2027-12-31T00:00:00Z"
        )


def test_source_race_rolls_back_operation_and_copied_bytes(prepared, monkeypatch):
    root, receipt, kwargs, assignment = prepared
    cfg = runtime._config(root, receipt["runtime_sha256"])
    real = runtime._source_check
    calls = 0

    def changed(*args, **kw):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise CompanyStoreError("Original source changed")
        return real(*args, **kw)

    monkeypatch.setattr(runtime, "_source_check", changed)
    with pytest.raises(CompanyStoreError, match="Original source changed"):
        runtime.execute(
            root,
            expected_runtime_sha256=receipt["runtime_sha256"],
            expected_revision=0,
            expected_state_sha256=receipt["state_sha256"],
            command_id="copy",
            action="COPY",
            payload={
                "principal_id": kwargs["prior_recipe"].identity_id,
                "source_id": cfg["dataset_id"],
                "target_id": cfg["target_id"],
            },
            actor_id=assignment["primary_person_id"],
            event_at="2027-07-02T00:00:00Z",
        )
    with database(root) as db:
        assert db.execute("SELECT count(*) FROM nonhuman_commands").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM versions").fetchone()[0] == 2
        assert db.execute("SELECT revision FROM nonhuman_state").fetchone()[0] == 0


def test_retained_code_pin_is_required_for_inspect_and_replay(prepared, monkeypatch):
    root, receipt, _, _ = prepared
    code = runtime._code()
    code["company_nonhuman_runtime.py"] = "0" * 64
    monkeypatch.setattr(runtime, "_code", lambda: code)
    with pytest.raises(CompanyStoreError, match="Retained implementation"):
        runtime.inspect(
            root, expected_runtime_sha256=receipt["runtime_sha256"], as_of="2027-07-02T00:00:00Z"
        )


def test_reader_quota_precedes_command_receipt_decode(prepared, monkeypatch):
    root, receipt, _, _ = prepared
    with database(root, True) as db:
        db.execute(
            "INSERT INTO nonhuman_commands VALUES(?,?,?)",
            ("oversized", "0" * 64, "x" * (runtime.MAX_ROW_BYTES + 1)),
        )
    real = runtime.decode

    def no_large_decode(value):
        assert len(value) <= runtime.MAX_ROW_BYTES
        return real(value)

    monkeypatch.setattr(runtime, "decode", no_large_decode)
    with pytest.raises(CompanyStoreError, match="Bounded native history"):
        runtime.inspect(
            root, expected_runtime_sha256=receipt["runtime_sha256"], as_of="2027-07-02T00:00:00Z"
        )


def test_repinned_prior_credential_cannot_invent_terminal_state(prepared, tmp_path):
    _, _, kwargs, _ = prepared
    root = kwargs["prior_root"]
    with database(root, True) as db:
        db.execute("DROP TRIGGER no_version_update")
        row = dict(
            db.execute(
                "SELECT * FROM versions WHERE branch='service-b' "
                "AND system='credential_metadata' AND version=2"
            ).fetchone()
        )
        body = json.loads(row["content"])
        body["version"] = 3
        raw = encoded(body)
        digest = sha(raw)
        db.execute(
            "UPDATE versions SET content=?,sha256=? WHERE company=? AND branch=? "
            "AND system=? AND record=? AND version=?",
            (raw, digest, *[row[k] for k in runtime.FIELDS[:-1]]),
        )
    refs = [
        {**r, "sha256": digest} if r["system"] == "credential_metadata" and r["version"] == 2 else r
        for r in kwargs["prior_refs"]
    ]
    with pytest.raises(CompanyStoreError, match="does not reperform"):
        runtime.initialize(tmp_path / "bad", **{**kwargs, "prior_refs": refs})
    assert not (tmp_path / "bad").exists()


@pytest.mark.parametrize("source", ["prior_root", "backup_source_root"])
def test_original_import_time_pinned_separately_from_recipe_digest(prepared, source):
    root, receipt, kwargs, _ = prepared
    with database(kwargs[source], True) as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute("UPDATE versions SET imported_at='2026-01-01T00:00:00.000000+00:00'")
    with pytest.raises(CompanyStoreError, match="Original source/declaration changed"):
        runtime.inspect(
            root, expected_runtime_sha256=receipt["runtime_sha256"], as_of="2027-07-02T00:00:00Z"
        )


def test_independent_declaration_cannot_hide_a_quarterly_review(prepared, tmp_path):
    root, receipt, kwargs, _ = prepared
    cfg = runtime._config(root, receipt["runtime_sha256"])
    plan = {
        **cfg["plan"],
        "schedule": [s for s in cfg["plan"]["schedule"] if s["id"] != "REVIEW-Q4"],
    }
    destination = tmp_path / "incomplete-declaration"
    destination.mkdir(mode=0o700)
    record = create_period(CompanyStore(destination), repository=ROOT, plan=plan)
    with pytest.raises(CompanyStoreError, match="one independent review due slot"):
        runtime.initialize(
            tmp_path / "bad",
            **{**kwargs, "declaration_root": destination, "declaration_pin": pin(record)},
        )
    assert not (tmp_path / "bad").exists()


def test_writer_bounds_combined_native_metadata_before_insert(prepared, monkeypatch):
    root, receipt, _, _ = prepared
    cfg = runtime._config(root, receipt["runtime_sha256"])
    # Provenance alone fits16KiB, but the complete native scalar metadata exceeds it.
    monkeypatch.setattr(runtime, "_provenance", lambda cfg: {"padding": "x" * 16300})
    with database(root, True) as db:
        before = db.execute("SELECT count(*) FROM versions").fetchone()[0]
        with pytest.raises(CompanyStoreError, match="Native writer quota exceeded"):
            runtime._insert(
                db,
                cfg,
                "nonhuman_operation",
                "oversized-metadata",
                b"{}",
                "2027-07-02T00:00:00.000000+00:00",
                "oversized",
                cfg["initialized_imported_at"],
            )
        assert db.execute("SELECT count(*) FROM versions").fetchone()[0] == before
