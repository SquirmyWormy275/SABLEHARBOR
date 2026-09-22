"""Actual data-only lease/session operations from genuine approved source originals."""

from copy import deepcopy

import pytest

from enterprise.audit_suite import company_privileged_runtime as runtime
from enterprise.audit_suite.company_activity import generate_pair
from enterprise.audit_suite.company_backup_runtime import database, pin
from enterprise.audit_suite.company_lifecycle_activity import LifecycleSourceRef, read_inputs
from enterprise.audit_suite.company_operating_period import create_period
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from enterprise.audit_suite.organization import snapshot
from tests.audit_suite.test_company_activity import ROOT, recipe


@pytest.fixture
def prepared(tmp_path):
    source, declaration = tmp_path / "source", tmp_path / "declaration"
    source.mkdir(mode=0o700)
    declaration.mkdir(mode=0o700)
    generate_pair(CompanyStore(source), repository=ROOT, recipe=recipe())
    with database(source) as db:
        rows = db.execute(
            "SELECT * FROM versions WHERE branch='activity-clean' "
            "AND ((system='hr' AND version=3) OR "
            "(system IN ('directory','application') AND version=2))"
        ).fetchall()
    refs = {r["system"]: pin(r) for r in rows}
    _, metadata = read_inputs(source, tuple(LifecycleSourceRef(**r) for r in refs.values()))
    owner = next(
        a
        for a in snapshot(ROOT, as_of="2027-05-01")["control_assignments"]
        if a["control_id"] == "SH-IAM-005"
    )["primary_person_id"]
    plan = {
        "period_id": "LOCAL-PRIVILEGE",
        "company_id": "SH",
        "branch_id": "local-privilege",
        "owner_id": owner,
        "control_ids": ["SH-IAM-005"],
        "declared_at": "2027-04-30T00:00:00Z",
        "period_start": "2027-05-01T00:00:00Z",
        "period_end_exclusive": "2027-05-02T00:00:00Z",
        "inventory": [
            {"id": "P014", "description": "Existing fictional source subject"},
            {"id": "LOCAL-OBJECT", "description": "Nonpersonal inert byte fixture"},
        ],
        "local_basis": "Two explicit local checks, not accepted quarterly enterprise coverage",
        "schedule": [
            {
                "id": name,
                "inventory_ids": ["P014", "LOCAL-OBJECT"],
                "control_id": "SH-IAM-005",
                "depends_on": [],
                "window_start": "2027-05-01T00:00:00Z",
                "window_end_exclusive": "2027-05-02T00:00:00Z",
                "due_at": at,
            }
            for name, at in [("FIRST", "2027-05-01T01:00:00Z"), ("SECOND", "2027-05-01T02:00:00Z")]
        ],
    }
    create_period(CompanyStore(declaration), repository=ROOT, plan=plan)
    with database(declaration) as db:
        declaration_pin = pin(db.execute("SELECT * FROM versions").fetchone())
    args = dict(
        repository=ROOT,
        source_root=source,
        source_pins=refs,
        expected_source_metadata_sha256=metadata,
        declaration_root=declaration,
        declaration_pin=declaration_pin,
        object_id="LOCAL-OBJECT",
        object_bytes=b"nonpersonal local configuration: version=1\n",
        max_lease_seconds=600,
        local_rule_basis="Explicit ten-minute local exercise rule; no corporate policy",
        as_of="2027-05-01T00:00:00Z",
    )
    root = tmp_path / "runtime"
    result = runtime.initialize(root, **args)
    return root, result, args, owner


def issue():
    return {
        "lease_id": "L1",
        "principal_id": "P014",
        "object_id": "LOCAL-OBJECT",
        "right": "coordination-read",
        "purpose": "Inspect local protected fixture",
        "expires_at": "2027-05-01T00:10:00Z",
    }


def call(prepared, command, action, payload, at, *, actor=None, revision=None):
    root, initial, _, owner = prepared
    if revision is None:
        with database(root) as db:
            revision = db.execute("SELECT revision FROM privileged_state").fetchone()[0]
    return dict(
        expected_runtime_sha256=initial["runtime_sha256"],
        expected_revision=revision,
        command_id=command,
        action=action,
        payload=payload,
        actor_id=actor or owner,
        event_at=at,
    )


def records(root):
    with database(root) as db:
        return {
            table: [tuple(row) for row in db.execute("SELECT * FROM " + table + " ORDER BY 1")]
            for table in [
                "versions",
                "privileged_state",
                "privileged_commands",
                "grants",
                "collections",
            ]
        }


def test_real_read_expiry_denial_reconciliation_and_originals_retained(prepared):
    root, initial, args, owner = prepared
    source_bytes = (args["source_root"] / "company.sqlite3").read_bytes()
    runtime.execute(root, **call(prepared, "lease", "ISSUE_LEASE", issue(), "2027-05-01T00:00:00Z"))
    runtime.execute(
        root,
        **call(
            prepared,
            "open",
            "OPEN_SESSION",
            {"session_id": "S1", "lease_id": "L1", "principal_id": "P014"},
            "2027-05-01T00:01:00Z",
            actor="P014",
        ),
    )
    request = call(
        prepared,
        "read",
        "READ_OBJECT",
        {"session_id": "S1", "principal_id": "P014", "object_id": "LOCAL-OBJECT"},
        "2027-05-01T00:02:00Z",
        actor="P014",
    )
    observed = runtime.execute(root, **request)
    assert observed["observation"]["read_sha256"] == sha(args["object_bytes"])
    before = records(root)
    assert runtime.execute(root, **request) == observed and records(root) == before
    denied = runtime.execute(
        root,
        **call(
            prepared,
            "expired-read",
            "READ_OBJECT",
            request["payload"],
            "2027-05-01T00:10:00Z",
            actor="P014",
        ),
    )
    assert denied["observation"]["status"] == "DENIED"
    early = runtime.inspect(
        root, expected_runtime_sha256=initial["runtime_sha256"], as_of="2027-05-01T01:00:00Z"
    )
    assert early["reconciliation"]["expired_unclosed_session_ids"] == ["S1"]
    assert early["reconciliation"]["previously_unrecorded_due_ids"] == ["FIRST"]
    runtime.execute(root, **call(prepared, "expire", "EXPIRE", {}, "2027-05-01T01:01:00Z"))
    runtime.execute(
        root,
        **call(prepared, "review", "RECONCILE", {"occurrence_id": "FIRST"}, "2027-05-01T01:02:00Z"),
    )
    final = runtime.inspect(
        root, expected_runtime_sha256=initial["runtime_sha256"], as_of="2027-05-01T03:00:00Z"
    )
    assert final["reconciliation"]["previously_unrecorded_due_ids"] == ["SECOND"]
    assert not final["reconciliation"]["expired_unclosed_session_ids"]
    assert final["revision"] == 6 and final["state"]["sessions"]["S1"]["status"] == "EXPIRED"
    assert not before["grants"] and not before["collections"]
    assert (args["source_root"] / "company.sqlite3").read_bytes() == source_bytes


def test_revocation_and_wrong_principal_are_recorded_denials(prepared):
    root, *_ = prepared
    runtime.execute(root, **call(prepared, "lease", "ISSUE_LEASE", issue(), "2027-05-01T00:00:00Z"))
    denied = runtime.execute(
        root,
        **call(
            prepared,
            "wrong",
            "OPEN_SESSION",
            {"session_id": "WRONG", "lease_id": "L1", "principal_id": "OTHER"},
            "2027-05-01T00:01:00Z",
            actor="OTHER",
        ),
    )
    assert denied["observation"]["status"] == "DENIED"
    runtime.execute(
        root,
        **call(
            prepared,
            "revoke",
            "REVOKE_LEASE",
            {"lease_id": "L1", "reason": "Local exercise end"},
            "2027-05-01T00:02:00Z",
        ),
    )
    denied = runtime.execute(
        root,
        **call(
            prepared,
            "after",
            "OPEN_SESSION",
            {"session_id": "AFTER", "lease_id": "L1", "principal_id": "P014"},
            "2027-05-01T00:03:00Z",
            actor="P014",
        ),
    )
    assert denied["observation"]["status"] == "DENIED"


@pytest.mark.parametrize(
    "field,value",
    [
        ("right", "admin"),
        ("principal_id", "OTHER"),
        ("object_id", "OTHER"),
        ("expires_at", "2027-05-01T01:00:00Z"),
    ],
)
def test_lease_cannot_expand_source_eligibility_or_local_rule(prepared, field, value):
    root, *_ = prepared
    before = records(root)
    payload = issue()
    payload[field] = value
    with pytest.raises(CompanyStoreError):
        runtime.execute(
            root, **call(prepared, "bad", "ISSUE_LEASE", payload, "2027-05-01T00:00:00Z")
        )
    assert records(root) == before


def test_stale_changed_replay_and_atomic_insert_failure(prepared, monkeypatch):
    root, *_ = prepared
    request = call(prepared, "lease", "ISSUE_LEASE", issue(), "2027-05-01T00:00:00Z")
    runtime.execute(root, **request)
    before = records(root)
    with pytest.raises(CompanyStoreError):
        runtime.execute(root, **{**request, "command_id": "stale"})
    with pytest.raises(CompanyStoreError):
        changed = deepcopy(request)
        changed["payload"]["purpose"] = "Changed rationale"
        runtime.execute(root, **changed)
    original = runtime._insert

    def fail(*args):
        original(*args)
        raise RuntimeError("after native insert before journal")

    monkeypatch.setattr(runtime, "_insert", fail)
    with pytest.raises(RuntimeError):
        runtime.execute(
            root,
            **call(
                prepared,
                "open",
                "OPEN_SESSION",
                {"session_id": "S1", "lease_id": "L1", "principal_id": "P014"},
                "2027-05-01T00:01:00Z",
                actor="P014",
            ),
        )
    assert records(root) == before


def test_future_wrong_pin_and_alias_admission_leave_no_destination(prepared, tmp_path):
    _, _, args, _ = prepared
    for name, changes in [
        ("future", {"as_of": "2027-04-01T00:00:00Z"}),
        ("hash", {"expected_source_metadata_sha256": "0" * 64}),
    ]:
        path = tmp_path / name
        with pytest.raises(CompanyStoreError):
            runtime.initialize(path, **{**args, **changes})
        assert not path.exists()
    alias = tmp_path / "alias"
    alias.symlink_to(args["source_root"], target_is_directory=True)
    with pytest.raises(CompanyStoreError):
        runtime.initialize(tmp_path / "aliased", **{**args, "source_root": alias})


def test_corrupt_native_object_or_state_cannot_replay_success(prepared):
    root, _, _, _ = prepared
    request = call(prepared, "lease", "ISSUE_LEASE", issue(), "2027-05-01T00:00:00Z")
    runtime.execute(root, **request)
    with database(root, True) as db:
        db.execute(
            "UPDATE privileged_state SET state=?",
            (encoded({"leases": {}, "sessions": {}, "reconciled_occurrences": []}).decode(),),
        )
    with pytest.raises(CompanyStoreError, match="Current state differs"):
        runtime.execute(root, **request)


def test_source_supersession_blocks_new_access_but_allows_explicit_revocation(prepared):
    root, initial, args, _ = prepared
    runtime.execute(root, **call(prepared, "lease", "ISSUE_LEASE", issue(), "2027-05-01T00:00:00Z"))
    source = CompanyStore(args["source_root"])
    ref = args["source_pins"]["application"]
    source.append_version(
        ref["company"],
        ref["branch"],
        ref["system"],
        ref["record"],
        expected_version=ref["version"],
        content=encoded({"account_status": "DISABLED"}),
        event_at="2027-05-01T00:01:00Z",
        available_at="2027-05-01T00:01:00Z",
        origin="AUTHORED_TRAINING_SOURCE",
        provenance={"qualification": "local", "source_reference": "explicit-disable"},
        command_id="explicit-upstream-disable",
    )
    with pytest.raises(CompanyStoreError, match="superseded"):
        runtime.execute(
            root,
            **call(
                prepared,
                "open",
                "OPEN_SESSION",
                {"session_id": "S1", "lease_id": "L1", "principal_id": "P014"},
                "2027-05-01T00:02:00Z",
                actor="P014",
            ),
        )
    runtime.execute(
        root,
        **call(
            prepared,
            "revoke",
            "REVOKE_LEASE",
            {"lease_id": "L1", "reason": "Upstream eligibility ended"},
            "2027-05-01T00:03:00Z",
        ),
    )
    view = runtime.inspect(
        root, expected_runtime_sha256=initial["runtime_sha256"], as_of="2027-05-01T00:03:00Z"
    )
    assert view["state"]["leases"]["L1"]["status"] == "REVOKED"


def test_final_source_change_rolls_back_native_and_command(prepared, monkeypatch):
    root, *_ = prepared
    before = records(root)
    original = runtime._source_check
    calls = 0

    def changed(*args, **kwargs):
        nonlocal calls
        calls += 1
        original(*args, **kwargs)
        if calls == 2:
            raise CompanyStoreError("Original eligibility changed at commit boundary")

    monkeypatch.setattr(runtime, "_source_check", changed)
    with pytest.raises(CompanyStoreError, match="commit boundary"):
        runtime.execute(
            root, **call(prepared, "lease", "ISSUE_LEASE", issue(), "2027-05-01T00:00:00Z")
        )
    assert records(root) == before


def test_exact_native_receipt_replay_rejects_false_revision(prepared):
    root, *_ = prepared
    request = call(prepared, "lease", "ISSUE_LEASE", issue(), "2027-05-01T00:00:00Z")
    result = runtime.execute(root, **request)
    with database(root, True) as db:
        db.execute("DROP TRIGGER privileged_no_update")
        db.execute(
            "UPDATE privileged_commands SET receipt=?",
            (encoded({**result, "revision": True}).decode(),),
        )
    with pytest.raises(CompanyStoreError, match="receipt envelope"):
        runtime.execute(root, **request)


def test_native_byte_quota_and_typed_revision_fail_without_mutation(prepared, monkeypatch):
    root, *_ = prepared
    before = records(root)
    request = call(prepared, "lease", "ISSUE_LEASE", issue(), "2027-05-01T00:00:00Z")
    with pytest.raises(CompanyStoreError):
        runtime.execute(root, **{**request, "expected_revision": False})
    monkeypatch.setattr(runtime, "MAX_NATIVE_BYTES", 1)
    with pytest.raises(CompanyStoreError, match="Bounded native history"):
        runtime.execute(root, **request)
    assert records(root) == before


def test_original_byte_tamper_cannot_return_a_successful_replay(prepared):
    root, *_ = prepared
    request = call(prepared, "lease", "ISSUE_LEASE", issue(), "2027-05-01T00:00:00Z")
    runtime.execute(root, **request)
    with database(root, True) as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute("UPDATE versions SET content=? WHERE system='privileged_object'", (b"tampered",))
    with pytest.raises(CompanyStoreError, match="protected bytes"):
        runtime.execute(root, **request)


def test_native_discovery_collection_future_and_revocation_preserve_operations(prepared):
    root, initial, _, _ = prepared
    request = call(prepared, "lease", "ISSUE_LEASE", issue(), "2027-05-01T00:00:00Z")
    result = runtime.execute(root, **request)
    before = records(root)
    store = CompanyStore(root)
    ref = result["operation_pin"]
    args = ("collector", "engagement", ref["company"], ref["branch"], ref["system"], ref["record"])
    store.grant(*args[:5])
    with pytest.raises(CompanyStoreError):
        store.read_version(*args, version=1, as_of="2027-04-30T23:59:59Z")
    original = store.read_version(*args, version=1, as_of="2027-05-01T00:00:00Z")
    assert sha(original["content"]) == ref["sha256"]
    receipt = store.collect(*args, version=1, as_of="2027-05-01T00:00:00Z", command_id="collect")
    assert (
        store.collect(*args, version=1, as_of="2027-05-01T00:00:00Z", command_id="collect")
        == receipt
    )
    store.grant(*args[:5], active=False)
    with pytest.raises(CompanyStoreError):
        store.collect(*args, version=1, as_of="2027-05-01T00:00:00Z", command_id="collect")
    after = records(root)
    for table in ["versions", "privileged_state", "privileged_commands"]:
        assert before[table] == after[table]
    assert (
        runtime.inspect(
            root, expected_runtime_sha256=initial["runtime_sha256"], as_of="2027-05-01T00:00:00Z"
        )["revision"]
        == 1
    )
