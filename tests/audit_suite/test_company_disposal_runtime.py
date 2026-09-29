"""Real unlink of newly created private fixtures; never existing company/audit data."""

import os
from copy import deepcopy

import pytest

from enterprise.audit_suite import company_disposal_runtime as runtime
from enterprise.audit_suite.company_backup_runtime import database, pin
from enterprise.audit_suite.company_operating_period import create_period
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.inference import _json as decode
from enterprise.audit_suite.organization import snapshot
from tests.audit_suite.test_company_activity import ROOT

AT = "2027-05-01T00:00:00Z"
LATER = "2027-05-01T00:01:00Z"
PAYLOAD = b"ONLY NEW NONPERSONAL DISPOSABLE FIXTURE 673791\n"


@pytest.fixture
def prepared(tmp_path):
    declaration = tmp_path / "declaration"
    declaration.mkdir(mode=0o700)
    owner = next(
        a["primary_person_id"]
        for a in snapshot(ROOT, as_of="2027-05-01")["control_assignments"]
        if a["control_id"] == "SH-REC-004"
    )
    plan = {
        "period_id": "LOCAL-DISPOSAL",
        "company_id": "SH",
        "branch_id": "local-disposal",
        "owner_id": owner,
        "control_ids": ["SH-REC-004"],
        "declared_at": "2027-04-30T00:00:00Z",
        "period_start": AT,
        "period_end_exclusive": "2027-05-02T00:00:00Z",
        "inventory": [
            {"id": x, "description": "New nonpersonal local fixture copy"}
            for x in ["ACTIVE1", "BACKUP1"]
        ],
        "local_basis": "Explicit local fixture retention, not corporate policy or legal release",
        "schedule": [
            {
                "id": "CHECK",
                "inventory_ids": ["ACTIVE1", "BACKUP1"],
                "control_id": "SH-REC-004",
                "depends_on": [],
                "window_start": AT,
                "window_end_exclusive": "2027-05-02T00:00:00Z",
                "due_at": "2027-05-01T02:00:00Z",
            }
        ],
    }
    create_period(CompanyStore(declaration), repository=ROOT, plan=plan)
    with database(declaration) as db:
        ref = pin(db.execute("SELECT * FROM versions").fetchone())
    args = dict(
        repository=ROOT,
        declaration_root=declaration,
        declaration_pin=ref,
        copies=[
            {"id": i, "kind": kind, "content": PAYLOAD, "not_before": AT, "holds": []}
            for i, kind in [("ACTIVE1", "ACTIVE"), ("BACKUP1", "BACKUP")]
        ],
        as_of=AT,
    )
    root = tmp_path / "runtime"
    initial = runtime.initialize(root, **args)
    return root, initial, args, owner


def view(p, at=LATER):
    return runtime.inspect(p[0], expected_runtime_sha256=p[1]["runtime_sha256"], as_of=at)


def cfg(p):
    return decode((p[0] / "RUNTIME.json").read_bytes())


def base(p, command, at=AT):
    return dict(
        expected_runtime_sha256=p[1]["runtime_sha256"],
        expected_revision=view(p, at)["revision"],
        command_id=command,
        operator_id=p[3],
        event_at=at,
    )


def authorize(p, ids=None, expires="2027-05-01T01:00:00Z"):
    args = base(p, "authorize")
    runtime.control(
        p[0],
        **args,
        action="AUTHORIZE",
        payload={
            "authorization_id": "AUTH",
            "copy_ids": ids or ["ACTIVE1", "BACKUP1"],
            "expires_at": expires,
            "rationale": "Explicit local fixture-only operator authorization",
        },
    )
    return args


def dispose_args(p, ids=None):
    return base(p, "dispose") | {
        "authorization_id": "AUTH",
        "copy_ids": ids or ["ACTIVE1", "BACKUP1"],
    }


def retry(p, at=LATER):
    current = view(p, at)
    return runtime.retry_pending(
        p[0],
        expected_runtime_sha256=p[1]["runtime_sha256"],
        expected_revision=current["revision"],
        intent_sha256=current["pending"]["intent_sha256"],
        operator_id=p[3],
        retry_at=at,
    )


def hold(p, ident, active, command="hold", at=AT):
    return runtime.control(
        p[0],
        **base(p, command, at),
        action="HOLD",
        payload={
            "copy_id": ident,
            "hold_id": "LOCAL-HOLD",
            "active": active,
            "rationale": "Explicit local fixture hold",
        },
    )


def stop_after_intent(p, monkeypatch, ids=None):
    original = runtime._continue
    monkeypatch.setattr(runtime, "_continue", lambda *a: (_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        runtime.dispose(p[0], **dispose_args(p, ids))
    monkeypatch.setattr(runtime, "_continue", original)
    assert view(p)["pending"] is not None


def test_actual_unlink_all_copies_exact_replay_and_metadata_only(prepared):
    p = prepared
    original = (p[2]["declaration_root"] / "company.sqlite3").read_bytes()
    authorize(p)
    args = dispose_args(p)
    result = runtime.dispose(p[0], **args)
    assert result["copies"] == {
        "ACTIVE1": "UNLINKED_VERIFIED_OWNED_INODE",
        "BACKUP1": "UNLINKED_VERIFIED_OWNED_INODE",
    }
    before = (p[0] / "company.sqlite3").read_bytes()
    assert runtime.dispose(p[0], **args) == result
    assert (p[0] / "company.sqlite3").read_bytes() == before
    observed = view(p)
    assert observed["revision"] == 5 and observed["pending"] is None
    assert observed["retained_internal_files"] == []
    assert observed["secure_erasure"] == "NOT_ASSERTED"
    with database(p[0]) as db:
        rows = db.execute("SELECT * FROM versions").fetchall()
        assert len(rows) == 6
        assert all(PAYLOAD not in r["content"] for r in rows)
        for table in ["grants", "collections", "access_events"]:
            assert db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] == 0
    assert (p[2]["declaration_root"] / "company.sqlite3").read_bytes() == original


def test_active_disposal_does_not_hide_remaining_backup(prepared):
    authorize(prepared, ["ACTIVE1"])
    runtime.dispose(prepared[0], **dispose_args(prepared, ["ACTIVE1"]))
    inventory = {x["id"]: x for x in view(prepared)["inventory"]}
    assert not inventory["ACTIVE1"]["path_present"]
    assert inventory["BACKUP1"]["path_present"] and inventory["BACKUP1"]["kind"] == "BACKUP"
    assert inventory["BACKUP1"]["matches_initial_identity"]


def test_hold_and_expired_authorization_block_before_intent(prepared):
    authorize(prepared)
    hold(prepared, "BACKUP1", True)
    old = view(prepared)
    with pytest.raises(CompanyStoreError, match="hold"):
        runtime.dispose(prepared[0], **dispose_args(prepared))
    assert view(prepared) == old
    hold(prepared, "BACKUP1", False, "unhold")
    with pytest.raises(CompanyStoreError, match="authorization"):
        runtime.dispose(
            prepared[0], **(dispose_args(prepared) | {"event_at": "2027-05-01T01:00:00Z"})
        )
    assert view(prepared)["pending"] is None


def test_retention_date_and_unapproved_subset(prepared):
    p = prepared
    args = deepcopy(p[2])
    args["copies"][0]["not_before"] = LATER
    root = p[0].parent / "later"
    new = runtime.initialize(root, **args)
    other = root, new, args, p[3]
    authorize(other)
    with pytest.raises(CompanyStoreError, match="retention"):
        runtime.dispose(root, **dispose_args(other))
    authorize(p, ["ACTIVE1"])
    with pytest.raises(CompanyStoreError, match="authorization"):
        runtime.dispose(p[0], **dispose_args(p))


def test_interrupted_unlink_records_missing_without_claiming_execution(prepared, monkeypatch):
    p = prepared
    authorize(p)
    append = runtime._append

    def interrupted(*args, **kwargs):
        if args[5] == "PROGRESS":
            raise KeyboardInterrupt()
        return append(*args, **kwargs)

    monkeypatch.setattr(runtime, "_append", interrupted)
    with pytest.raises(KeyboardInterrupt):
        runtime.dispose(p[0], **dispose_args(p))
    monkeypatch.setattr(runtime, "_append", append)
    current = view(p)
    assert current["revision"] == 2
    assert not current["inventory"][0]["path_present"]
    result = retry(p)
    assert result["copies"]["ACTIVE1"] == "MISSING_AFTER_RETAINED_INTENT"
    assert result["status"] == "COMPLETED_WITH_UNATTRIBUTED_MISSING_COPY"
    observed = view(p)
    assert observed["recorded_unattributed_missing_count"] == 1
    assert observed["recorded_unlinked_count"] == 1
    assert observed["inventory"][0]["recorded_status"] == "MISSING_UNATTRIBUTED"
    assert result["copies"]["BACKUP1"] == "UNLINKED_VERIFIED_OWNED_INODE"


def test_current_hold_blocks_remaining_after_partial_unlink(prepared, monkeypatch):
    p = prepared
    authorize(p)
    unlink = runtime._unlink_owned
    count = 0

    def fail_second(*a):
        nonlocal count
        count += 1
        if count == 2:
            raise OSError("Injected local fixture failure")
        return unlink(*a)

    monkeypatch.setattr(runtime, "_unlink_owned", fail_second)
    with pytest.raises(OSError):
        runtime.dispose(p[0], **dispose_args(p))
    monkeypatch.setattr(runtime, "_unlink_owned", unlink)
    assert view(p)["pending"]["completed"] == {"ACTIVE1": "UNLINKED_VERIFIED_OWNED_INODE"}
    hold(p, "BACKUP1", True)
    with pytest.raises(CompanyStoreError, match="hold"):
        retry(p)
    current = view(p)
    assert current["inventory"][1]["path_present"]
    hold(p, "BACKUP1", False, "release-hold", LATER)
    assert retry(p, "2027-05-01T00:02:00Z")["copies"]["ACTIVE1"] == "UNLINKED_VERIFIED_OWNED_INODE"


def test_expiry_after_interruption_never_deletes_remaining(prepared, monkeypatch):
    p = prepared
    authorize(p)
    stop_after_intent(p, monkeypatch)
    with pytest.raises(CompanyStoreError, match="authorization"):
        retry(p, "2027-05-01T01:00:00Z")
    assert all(x["path_present"] for x in view(p, "2027-05-01T01:00:00Z")["inventory"])


def test_replacement_same_bytes_never_adopted_by_old_intent(prepared, monkeypatch):
    p = prepared
    authorize(p)
    stop_after_intent(p, monkeypatch)
    path = p[0] / "copies" / cfg(p)["copies"]["ACTIVE1"]["file"]
    replacement = p[0] / "replacement"
    replacement.write_bytes(PAYLOAD)
    replacement.chmod(0o600)
    assert replacement.stat().st_ino != path.stat().st_ino
    os.replace(replacement, path)
    with pytest.raises(CompanyStoreError, match="identity"):
        retry(p)
    assert path.read_bytes() == PAYLOAD
    assert view(p)["pending"]["completed"] == {}


def test_alias_directory_does_not_delete_external_fixture(prepared, monkeypatch):
    p = prepared
    authorize(p)
    stop_after_intent(p, monkeypatch)
    copies = p[0] / "copies"
    copies.rename(p[0] / "preserved-copies")
    outside = p[0].parent / "external"
    outside.mkdir(mode=0o700)
    name = cfg(p)["copies"]["ACTIVE1"]["file"]
    external = outside / name
    external.write_bytes(PAYLOAD)
    external.chmod(0o600)
    copies.symlink_to(outside, target_is_directory=True)
    with pytest.raises(CompanyStoreError):
        runtime.retry_pending(
            p[0],
            expected_runtime_sha256=p[1]["runtime_sha256"],
            expected_revision=2,
            intent_sha256=decode_pending(p)["intent_sha256"],
            operator_id=p[3],
            retry_at=LATER,
        )
    assert external.read_bytes() == PAYLOAD


def decode_pending(p):
    with database(p[0]) as db:
        return decode(db.execute("SELECT state FROM disposal_state").fetchone()[0])["pending"]


def test_command_identity_cannot_collide_or_restart_aborted_intent(prepared, monkeypatch):
    p = prepared
    authorize(p)
    stop_after_intent(p, monkeypatch)
    with pytest.raises(CompanyStoreError, match="identity"):
        hold(p, "BACKUP1", True, "dispose")
    runtime.control(
        p[0],
        **base(p, "abort"),
        action="ABORT_PENDING",
        payload={"rationale": "Stop pending local operation"},
    )
    with pytest.raises(CompanyStoreError, match="identity"):
        runtime.dispose(p[0], **dispose_args(p))
    assert all(x["path_present"] for x in view(p)["inventory"])


def test_cas_actor_and_changed_completed_replay(prepared):
    p = prepared
    authorize(p)
    args = dispose_args(p)
    for changes in [
        {"operator_id": "AS-P001"},
        {"expected_revision": 0},
        {"expected_revision": True},
    ]:
        with pytest.raises(CompanyStoreError):
            runtime.dispose(p[0], **(args | changes))
    runtime.dispose(p[0], **args)
    with pytest.raises(CompanyStoreError, match="replay"):
        runtime.dispose(p[0], **(args | {"copy_ids": ["ACTIVE1"]}))


def test_code_pin_and_native_metadata_tamper_fail_before_unlink(prepared, monkeypatch):
    p = prepared
    authorize(p)
    args = dispose_args(p)
    original = runtime._code
    monkeypatch.setattr(runtime, "_code", lambda: original() | {"inference.py": "0" * 64})
    with pytest.raises(CompanyStoreError, match="code"):
        runtime.dispose(p[0], **args)
    monkeypatch.setattr(runtime, "_code", original)
    with database(p[0], True) as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute(
            "UPDATE versions SET available_at='2027-05-01T00:00:01Z' "
            "WHERE system='disposal_definition'"
        )
    with pytest.raises(CompanyStoreError, match="metadata"):
        runtime.dispose(p[0], **args)
    assert len(list((p[0] / "copies").iterdir())) == 2


def test_fresh_retry_time_required_and_old_intent_time_not_reused(prepared, monkeypatch):
    p = prepared
    authorize(p)
    stop_after_intent(p, monkeypatch)
    with pytest.raises(CompanyStoreError, match="fresh retry"):
        retry(p, AT)
    assert retry(p)["status"] == "SELECTED_LOCAL_COPIES_UNLINKED"


def test_quarantine_failure_retains_original_and_expiry_stops_retry(prepared, monkeypatch):
    p = prepared
    authorize(p)
    real_unlink = runtime.os.unlink

    def fail_quarantine(path, *args, **kwargs):
        if str(path).startswith("pending-"):
            raise PermissionError("Injected fixture unlink failure")
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(runtime.os, "unlink", fail_quarantine)
    with pytest.raises(PermissionError):
        runtime.dispose(p[0], **dispose_args(p))
    monkeypatch.setattr(runtime.os, "unlink", real_unlink)
    current = view(p)
    assert any(n.startswith("pending-") for n in current["retained_internal_files"])
    assert current["pending"]["completed"] == {}
    with pytest.raises(CompanyStoreError, match="authorization"):
        retry(p, "2027-05-01T01:00:00Z")
    assert any(
        n.startswith("pending-") for n in view(p, "2027-05-01T01:00:00Z")["retained_internal_files"]
    )


def test_fully_repinned_pending_state_cannot_expand_original_intent(prepared, monkeypatch):
    from enterprise.audit_suite.company_store import _json
    from enterprise.audit_suite.operating_source_bridge import encoded, sha

    p = prepared
    authorize(p)
    stop_after_intent(p, monkeypatch, ["ACTIVE1"])
    # Disposable corruption fixture: defeat immutability and recompute every row/hash association.
    with database(p[0], True) as db:
        db.execute("DROP TRIGGER disposal_immutable_update")
        db.execute("DROP TRIGGER no_version_update")
        row = db.execute("SELECT * FROM disposal_events ORDER BY seq DESC LIMIT 1").fetchone()
        body = decode(row["body"])
        pending = body["after"]["pending"]
        pending["request"]["copy_ids"].append("BACKUP1")
        pending["expected"]["BACKUP1"] = cfg(p)["copies"]["BACKUP1"]["identity"]
        pending["intent_sha256"] = sha(
            encoded({k: v for k, v in pending.items() if k != "intent_sha256"})
        )
        ref = decode(row["native_pin"])
        raw = encoded(body)
        ref["sha256"] = sha(raw)
        provenance = runtime._provenance(cfg(p))
        key = [ref[k] for k in runtime.FIELDS[:4]]
        digest = sha(
            _json(
                [
                    key,
                    0,
                    body["event_at"],
                    body["event_at"],
                    "AUTHORED_TRAINING_SOURCE",
                    provenance,
                    sha(raw),
                ]
            ).encode()
        )
        db.execute(
            "UPDATE disposal_events SET body=?,sha256=?,native_pin=? WHERE seq=?",
            (_json(body), sha(raw), _json(ref), row["seq"]),
        )
        db.execute(
            "UPDATE versions SET content=?,sha256=?,input_digest=? WHERE record=?",
            (raw, sha(raw), digest, ref["record"]),
        )
        db.execute("UPDATE disposal_state SET state=?", (_json(body["after"]),))
    with pytest.raises(CompanyStoreError, match="transition"):
        runtime.retry_pending(
            p[0],
            expected_runtime_sha256=p[1]["runtime_sha256"],
            expected_revision=2,
            intent_sha256=pending["intent_sha256"],
            operator_id=p[3],
            retry_at=LATER,
        )
    assert len(list((p[0] / "copies").iterdir())) == 2


def test_public_native_collection_remains_possible_after_actual_unlink(prepared):
    from enterprise.audit_suite.operating_source_bridge import sha

    p = prepared
    authorize(p)
    runtime.dispose(p[0], **dispose_args(p))
    with database(p[0]) as db:
        before = [tuple(r) for r in db.execute("SELECT * FROM versions ORDER BY system,record")]
        row = db.execute("SELECT * FROM versions WHERE record='EVENT-5'").fetchone()
        ref = pin(row)
    store = CompanyStore(p[0])
    args = (
        "collector",
        "technical-engagement",
        ref["company"],
        ref["branch"],
        ref["system"],
        ref["record"],
    )
    store.grant(*args[:5])
    with pytest.raises(CompanyStoreError):
        store.read_version(*args, version=1, as_of="2027-04-30T23:59:59Z")
    original = store.read_version(*args, version=1, as_of=AT)
    assert sha(original["content"]) == ref["sha256"] and PAYLOAD not in original["content"]
    receipt = store.collect(*args, version=1, as_of=AT, command_id="collect")
    assert store.collect(*args, version=1, as_of=AT, command_id="collect") == receipt
    store.grant(*args[:5], active=False)
    with pytest.raises(CompanyStoreError):
        store.collect(*args, version=1, as_of=AT, command_id="collect")
    with database(p[0]) as db:
        assert [
            tuple(r) for r in db.execute("SELECT * FROM versions ORDER BY system,record")
        ] == before
    assert view(p)["revision"] == 5


def test_final_declaration_failure_retains_real_unlink_and_failure_record(prepared, monkeypatch):
    p = prepared
    authorize(p)
    args = dispose_args(p)
    original = runtime._current
    checks = 0

    def changed(*args):
        nonlocal checks
        checks += 1
        original(*args)
        if checks == 3:  # intent, before first copy, after physical unlink before progress commit
            raise CompanyStoreError("Injected declaration publication change")

    monkeypatch.setattr(runtime, "_current", changed)
    with pytest.raises(CompanyStoreError, match="publication change"):
        runtime.dispose(p[0], **args)
    monkeypatch.setattr(runtime, "_current", original)
    current = view(p)
    assert current["revision"] == 3  # authorization + intent + failure; progress rolled back
    assert current["pending"]["completed"] == {}
    assert current["present_declared_paths"] == 1
    assert retry(p)["copies"]["ACTIVE1"] == "MISSING_AFTER_RETAINED_INTENT"


def test_declaration_metadata_changed_blocks_control_replay(prepared):
    p = prepared
    args = authorize(p)
    with database(p[2]["declaration_root"], True) as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute("UPDATE versions SET provenance='{}'")
    with pytest.raises(CompanyStoreError, match="declaration"):
        runtime.control(
            p[0],
            **args,
            action="AUTHORIZE",
            payload={
                "authorization_id": "AUTH",
                "copy_ids": ["ACTIVE1", "BACKUP1"],
                "expires_at": "2027-05-01T01:00:00Z",
                "rationale": "Explicit local fixture-only operator authorization",
            },
        )
    assert len(list((p[0] / "copies").iterdir())) == 2


@pytest.mark.parametrize(
    "table,column,null_column",
    [
        ("versions", "event_at", "version"),
        ("versions", "available_at", None),
        ("versions", "command_id", None),
        ("versions", "input_digest", None),
        ("versions", "record", None),
        ("disposal_events", "native_pin", "body"),
        ("disposal_events", "kind", None),
        ("disposal_events", "command_id", None),
        ("disposal_events", "sha256", None),
        ("disposal_state", "last_at", "state"),
        ("systems", "owner", None),
    ],
)
def test_all_metadata_bounded_before_materialization(prepared, table, column, null_column):
    p = prepared
    authorize(p)
    with database(p[0], True) as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute("DROP TRIGGER disposal_immutable_update")
        db.execute(
            "UPDATE "
            + table
            + " SET "
            + column
            + "=? WHERE rowid=(SELECT min(rowid) FROM "
            + table
            + ")",
            ("x" * (1024 * 1024),),
        )
        if null_column:
            db.execute("UPDATE " + table + " SET " + null_column + "=NULL")
    with pytest.raises(CompanyStoreError, match="Bounded retained table metadata"):
        view(p)
    assert len(list((p[0] / "copies").iterdir())) == 2


def test_state_row_count_bounded_before_materialization(prepared):
    with database(prepared[0], True) as db:
        db.execute("INSERT INTO disposal_state SELECT * FROM disposal_state")
    with pytest.raises(CompanyStoreError, match="Bounded retained table metadata.*disposal_state"):
        view(prepared)


def test_even_repinned_definition_cannot_select_external_path(prepared):
    from enterprise.audit_suite.operating_source_bridge import encoded, sha

    p = prepared
    definition = cfg(p)
    definition["copies"]["ACTIVE1"]["file"] = "../../declaration/company.sqlite3"
    raw = encoded(definition)
    (p[0] / "RUNTIME.json").write_bytes(raw)
    source_before = (p[2]["declaration_root"] / "company.sqlite3").read_bytes()
    with pytest.raises(CompanyStoreError, match="Only generated internal"):
        runtime.inspect(p[0], expected_runtime_sha256=sha(raw), as_of=LATER)
    assert (p[2]["declaration_root"] / "company.sqlite3").read_bytes() == source_before


def test_writer_metadata_overhead_cannot_publish_unreadable_aggregate(prepared):
    from enterprise.audit_suite.company_store import _time

    p = prepared
    before = (p[0] / "company.sqlite3").read_bytes()
    definition = cfg(p)
    # Exercise the maintained atomic insertion primitive at the real 16 MiB limit.
    # Sixty-seven 250KB payloads fit the old content-only quota but not total metadata.
    with pytest.raises(CompanyStoreError, match="Bounded retained table metadata.*versions"):
        with database(p[0], True) as db:
            for i in range(67):
                runtime._insert(db, definition, f"BOUND-{i}", {"padding": "x" * 250000}, _time(AT))
    assert (p[0] / "company.sqlite3").read_bytes() == before
    assert view(p)["revision"] == 0
