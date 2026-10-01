"""Neutral company lifetime and actual supported audit commands, never audit answers."""

import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from enterprise.audit_suite.company_collection import discover as engine_discover
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError, _json
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.persistent_company_journey import (
    CompanyOperator,
    PersistentAudit,
    PersistentCompany,
    native_rows,
    write,
)
from enterprise.audit_suite.source_library_audit import (
    LIBRARY_MANIFEST_SCHEMA,
    LIBRARY_REVIEW_SCHEMA,
    LIBRARY_REVIEW_VERDICT,
    AcceptedLibrary,
    BusinessRoute,
    file_sha,
    quiescent_read,
)

REPO = Path(__file__).resolve().parents[2]


def source(root):
    root.mkdir(mode=0o700)
    store = CompanyStore(root)
    for branch in ("ALPHA", "BETA"):
        store.register_system("NEUTRAL-COMPANY", branch, "operations.events", "neutral-owner")
        store.append_version(
            "NEUTRAL-COMPANY",
            branch,
            "operations.events",
            "event-one",
            expected_version=0,
            command_id=f"initial-{branch}",
            event_at="2027-01-02T00:00:00Z",
            available_at="2027-01-02T01:00:00Z",
            content=json.dumps({"engineering_neutral_fixture": True, "revision": 1}).encode(),
            provenance={
                "source_reference": "neutral-engineering-fixture-only",
                "name": "event.json",
                "content_type": "application/json",
            },
        )
    database = root / "company.sqlite3"
    manifest, review = root / "MANIFEST.json", root / "REVIEW.json"
    write(
        manifest,
        {"schema": LIBRARY_MANIFEST_SCHEMA, "files": {"company.sqlite3": file_sha(database)}},
    )
    write(
        review,
        {
            "schema": LIBRARY_REVIEW_SCHEMA,
            "verdict": LIBRARY_REVIEW_VERDICT,
            "source_quality_accepted_for_final_learner_audit": True,
            "library_pins": {
                "company.sqlite3": file_sha(database),
                "MANIFEST.json": file_sha(manifest),
            },
            "native_versions": 2,
            "engineering_neutral_test_fixture_not_actual_independent_acceptance": True,
        },
    )
    return AcceptedLibrary(
        database, file_sha(database), manifest, file_sha(manifest), review, file_sha(review), 2
    )


@pytest.fixture
def world(tmp_path):
    tmp_path.chmod(0o700)
    accepted = source(tmp_path / "accepted-neutral-fixture")
    return PersistentCompany.initialize(
        accepted,
        tmp_path / "company-lifetime",
        operator_id="COMPANY-OPERATOR-NEUTRAL",
        engineering_only=True,
    )


def cmd(session, actor, kind, payload):
    state = session.engine.store.get(actor, session.engagement)
    return session.engine.command(
        actor,
        session.engagement,
        {
            "command_id": f"neutral-{kind}-{state['revision']}",
            "kind": kind,
            "expected_revision": state["revision"],
            "payload": payload,
        },
    )


def create(world, root, *, branch="ALPHA"):
    session = PersistentAudit(
        world,
        [BusinessRoute("NEUTRAL-COMPANY", branch, "operations.events", "operations", "events")],
    )
    engine, state, ids = session.create(
        repository=REPO,
        audit_root=root,
        payload={
            "command_id": "neutral-fresh-create",
            "title": "Neutral persistent company investigation",
            "discipline": "IT",
            "mode": "CLEAN",
            "configuration": {"selections": []},
            "scope": {
                "programs": ["SOC2"],
                "report_type": "Type 2",
                "period_start": "2027-01-01",
                "period_end": "2027-12-31",
                "fieldwork_start": "2027-01-03",
                "timezone": "UTC",
                "boundaries": ["corporate"],
                "control_ids": ["SH-SEC-003"],
            },
        },
    )
    cmd(session, ids["operator"], "company.activate", {})
    cmd(session, ids["auditor"], "kickoff.start", {})
    session.authorize(**session.identities, engagement=session.engagement)
    return session, ids


def request(session):
    actor = session.identities["auditor"]
    state = cmd(
        session,
        actor,
        "pbc.create",
        {
            "title": "Neutral original event",
            "purpose": "Direct company original collection",
            "control_id": "SH-SEC-003",
            "person_id": "AS-P007",
            "boundary_id": "corporate",
        },
    )
    rid = state["requests"][-1]["id"]
    cmd(session, actor, "pbc.issue", {"request_id": rid})
    return rid


def discover(session, **kwargs):
    return session.discover(
        session.engine, session.identities["auditor"], session.engagement, **kwargs
    )[0]


def correction(world, *, branch="ALPHA"):
    content = json.dumps(
        {
            "engineering_neutral_fixture": True,
            "revision": 2,
            "company_correction": "Ordinary corrected event detail",
        }
    ).encode()
    operation = {
        "company": "NEUTRAL-COMPANY",
        "branch": branch,
        "system": "operations.events",
        "record": "event-one",
        "expected_version": 1,
        "command_id": "correction-" + branch,
        "event_at": "2027-01-10T00:00:00Z",
        "available_at": "2027-01-11T00:00:00Z",
        "content_sha256": hashlib.sha256(content).hexdigest(),
        "provenance": {
            "source_reference": "neutral-company-correction-original",
            "name": "event.json",
            "content_type": "application/json",
        },
        "origin": "AUTHORED_TRAINING_SOURCE",
    }
    return operation, content


def journey(world, root):
    first, first_ids = create(world, root / "first-audit")
    old_row = discover(first)[0]
    old = first.collect(
        first.engine,
        first_ids["auditor"],
        first.engagement,
        request(first),
        old_row,
        command_id="first-original",
    )
    original_artifact = first.engine.store.get(first_ids["auditor"], first.engagement)["artifacts"][
        0
    ]
    original_bytes = first.engine.artifacts.read(original_artifact)
    update = world.append(world.operator, *correction(world))
    # The second engagement exists concurrently with the first and shares actual journals.
    second, second_ids = create(world, root / "second-audit")
    assert not any(second_ids["zero_workroom_counts"].values())
    assert first.database == second.database == world.database
    assert first.engagement != second.engagement
    assert [r["version"] for r in discover(first)] == [1]
    assert [r["version"] for r in discover(second)] == [1]
    for session in (first, second):
        with pytest.raises(ProcedureError, match="simulated clock"):
            discover(session, as_of="2027-01-12T09:00:00Z")
    with ThreadPoolExecutor(max_workers=2) as pool:
        concurrent = list(pool.map(discover, (first, second)))
    assert all([r["version"] for r in rows] == [1] for rows in concurrent)
    advanced = cmd(
        second,
        second_ids["auditor"],
        "clock.advance",
        {"mode": "TARGET_DATE", "target": "2027-01-12T09:00:00Z"},
    )
    assert advanced["simulated_at"].startswith("2027-01-12")
    later = discover(second)
    assert [r["version"] for r in later] == [1, 2]
    new = second.collect(
        second.engine,
        second_ids["auditor"],
        second.engagement,
        request(second),
        later[-1],
        command_id="second-correction",
    )
    assert original_bytes == first.engine.artifacts.read(original_artifact)
    assert new["source"]["sha256"] != old["source"]["sha256"]
    assert not second.engine.store.get(second_ids["auditor"], second.engagement)["reviews"]
    first.authorize(**first.identities, engagement=first.engagement, active=False)
    second.authorize(**second.identities, engagement=second.engagement, active=False)
    assert world.verify()["native_versions"] == 3
    with quiescent_read(world.database) as db:
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM access_events").fetchone()[0] == 4
        assert db.execute("SELECT COUNT(*) FROM grants WHERE active!=0").fetchone()[0] == 0
    return first, first_ids, second, second_ids, old, new, update


def test_actual_two_empty_engagements_shared_company_correction_clock_and_immutable_old_artifact(
    world,
):
    baseline = native_rows(world.accepted.database)
    initial_checkpoint, initial_pin = world.checkpoint, world.checkpoint_sha256
    journey(world, world.root.parent)
    current = native_rows(world.database)
    assert all(current[key] == value for key, value in baseline.items())
    before = file_sha(world.database)
    reopened = PersistentCompany(
        world.accepted, world.root, world.checkpoint, world.checkpoint_sha256, read_only=True
    )
    assert reopened.verify()["native_versions"] == 3
    assert reopened.store is None and file_sha(world.database) == before
    with pytest.raises(ProcedureError, match="Unreceipted"):
        PersistentCompany(
            world.accepted, world.root, initial_checkpoint, initial_pin, read_only=True
        )


def test_company_operator_and_normal_append_cannot_be_impersonated_by_auditor(world):
    operation, content = correction(world)
    with pytest.raises(ProcedureError, match="operator capability"):
        world.append(CompanyOperator(world.operator.principal), operation, content)
    with pytest.raises(ProcedureError, match="approved append"):
        world.store.append_version("NEUTRAL-COMPANY", "ALPHA", "operations.events", "event-one")
    operation["content_sha256"] = "0" * 64
    with pytest.raises(ProcedureError, match="fields/bytes"):
        world.append(world.operator, operation, content)
    assert world.verify()["native_versions"] == 2


def test_wrong_predecessor_and_bad_typed_bytes_do_not_modify_company(world):
    operation, content = correction(world)
    operation["expected_version"] = 0
    with pytest.raises(ProcedureError, match="predecessor"):
        world.append(world.operator, operation, content)
    operation["expected_version"] = 1
    operation["provenance"]["name"] = "wrong.txt"
    with pytest.raises(ProcedureError, match="filename/type"):
        world.append(world.operator, operation, content)
    assert world.verify()["native_versions"] == 2


def test_branch_and_reserved_reviewer_isolation_in_shared_store(world):
    first, ids = create(world, world.root.parent / "alpha-audit")
    beta, _ = create(world, world.root.parent / "beta-audit", branch="BETA")
    foreign = discover(beta)[0]
    with pytest.raises(ProcedureError, match="engagement branch"):
        first.collect(
            first.engine,
            ids["auditor"],
            first.engagement,
            request(first),
            foreign,
            command_id="forbidden-foreign",
        )
    with pytest.raises(ProcedureError, match="audit performer"):
        first.discover(first.engine, ids["reviewer"], first.engagement)
    with pytest.raises(CompanyStoreError, match="unauthorized"):
        world.store.read_version(
            ids["auditor"],
            first.engagement,
            "NEUTRAL-COMPANY",
            "BETA",
            "operations.events",
            "event-one",
            version=1,
            as_of="2027-01-03T09:00:00Z",
        )
    assert not first.engine.store.get(ids["auditor"], first.engagement)["artifacts"]


def test_held_open_wal_shadow_is_rejected_and_not_checkpointed_or_deleted(world):
    session, ids = create(world, world.root.parent / "wal-audit")
    writer = sqlite3.connect(world.database)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("DROP TRIGGER no_version_update")
        writer.execute(
            "UPDATE versions SET content=?,sha256=? WHERE branch='ALPHA'",
            (b'{"replacement":true}', hashlib.sha256(b'{"replacement":true}').hexdigest()),
        )
        writer.commit()
        sidecar = Path(str(world.database) + "-wal")
        pin = file_sha(sidecar)
        with pytest.raises(ProcedureError, match="sidecars"):
            world.verify()
        with pytest.raises(ProcedureError, match="sidecars"):
            discover(session)
        with pytest.raises(ProcedureError, match="sidecars"):
            engine_discover(session.engine, ids["auditor"], session.engagement, "operations.events")
        assert sidecar.exists() and file_sha(sidecar) == pin
        assert not session.engine.store.get(ids["auditor"], session.engagement)["artifacts"]
    finally:
        writer.close()
    with pytest.raises(ProcedureError, match="schema|history"):
        world.verify()


def test_resealed_receipt_and_checkpoint_fail_against_external_current_pin(world):
    update = world.append(world.operator, *correction(world))
    path = Path(update["receipt"])
    receipt = json.loads(path.read_bytes())
    receipt["operator_id"] = "UNAUTHORIZED-OPERATOR"
    path.write_bytes((_json(receipt) + "\n").encode())
    checkpoint = json.loads(world.checkpoint.read_bytes())
    checkpoint["operations"][0]["sha256"] = file_sha(path)
    world.checkpoint.write_bytes((_json(checkpoint) + "\n").encode())
    with pytest.raises(ProcedureError, match="externally pinned|Externally pinned"):
        world.verify()


def test_neutral_mode_cannot_admit_real_company_bodies_or_later_corrections(world):
    operation, content = correction(world)
    operation["company"] = "SABLE-HARBOR-REFERENCE"
    with pytest.raises(ProcedureError, match="actual company history"):
        world.append(world.operator, operation, content)
    world.initialization["engineering_only"] = False
    # Verification restores the pinned initializer rather than trusting an in-memory flag.
    world.require_runtime()
    assert world.initialization["engineering_only"] is True


def test_frozen_adapter_gate_cannot_authorize_persistent_company(world):
    path = world.root.parent / "old-adapter-gate.json"
    write(
        path,
        {
            "schema": "SH_ROOT_SOURCE_LIBRARY_ADAPTER_INDEPENDENT_REVIEW_V2",
            "verdict": "PASS_QUIESCENT_ENGINE_BOUND_ADAPTER",
            "source_execution_authorized": True,
            "runtime_module_sha256": file_sha(
                REPO / "enterprise/audit_suite/persistent_company_journey.py"
            ),
            "accepted_baseline_pins": world.pins,
        },
    )
    with pytest.raises(ProcedureError, match="Separate independent"):
        world.accept_runtime(path, file_sha(path))


def test_registered_owner_changes_and_unreceipted_versions_fail_closed(world):
    with sqlite3.connect(world.database) as db:
        db.execute("UPDATE systems SET owner='substituted-owner' WHERE branch='ALPHA'")
    with pytest.raises(ProcedureError, match="baseline/schema"):
        world.verify()


def test_an_unreceipted_raw_operator_append_is_quarantined_not_autoaccepted(world):
    operation, content = correction(world)
    CompanyStore(world.root).append_version(
        operation["company"],
        operation["branch"],
        operation["system"],
        operation["record"],
        expected_version=operation["expected_version"],
        command_id=operation["command_id"],
        event_at=operation["event_at"],
        available_at=operation["available_at"],
        content=content,
        provenance=operation["provenance"],
        origin=operation["origin"],
    )
    with pytest.raises(ProcedureError, match="Unreceipted"):
        world.verify()


def test_persistent_gate_requires_exact_passed_baseline_not_just_matching_module(world):
    from enterprise.audit_suite.persistent_company_journey import RUNTIME_SCHEMA, RUNTIME_VERDICT

    production = PersistentCompany.initialize(
        world.accepted,
        world.root.parent / "unactivated-production-contract-fixture",
        operator_id="COMPANY-OPERATOR-CONTRACT-TEST",
    )
    with pytest.raises(ProcedureError, match="runtime review"):
        production.require_runtime()
    path = world.root.parent / "hypothetical-runtime-contract-fixture.json"
    gate = {
        "schema": RUNTIME_SCHEMA,
        "verdict": RUNTIME_VERDICT,
        "source_execution_authorized": True,
        "runtime_module_sha256": file_sha(
            REPO / "enterprise/audit_suite/persistent_company_journey.py"
        ),
        "adapter_module_sha256": file_sha(REPO / "enterprise/audit_suite/source_library_audit.py"),
        "accepted_baseline_pins": {**production.pins, "version_count": 999},
        "engineering_fixture_not_actual_independent_review": True,
    }
    write(path, gate)
    with pytest.raises(ProcedureError, match="exact baseline pins"):
        production.accept_runtime(path, file_sha(path))
    gate["accepted_baseline_pins"] = production.pins
    path.unlink()
    write(path, gate)
    production.accept_runtime(path, file_sha(path))
    # Mutating a process flag cannot turn production into unreviewed neutral mode.
    production.initialization["engineering_only"] = True
    production.require_runtime()
    assert production.initialization["engineering_only"] is False
    assert not any((production.root / "operations").iterdir())


def test_exact_source_operation_approval_cannot_be_reused_for_other_bytes(world):
    from enterprise.audit_suite.persistent_company_journey import (
        OPERATION_SCHEMA,
        OPERATION_VERDICT,
    )

    operation, content = correction(world)
    path = world.root.parent / "hypothetical-operation-contract-fixture.json"
    gate = {
        "schema": OPERATION_SCHEMA,
        "verdict": OPERATION_VERDICT,
        "accepted_baseline_pins": world.pins,
        "operation_sha256": hashlib.sha256(_json(operation).encode()).hexdigest(),
        "company_operator_id": world.operator.principal,
        "engineering_fixture_not_actual_independent_review": True,
    }
    write(path, gate)
    assert world.operation_approval(operation, world.operator.principal, path, file_sha(path))[
        "sha256"
    ] == file_sha(path)
    operation["available_at"] = "2027-01-12T00:00:00Z"
    with pytest.raises(ProcedureError, match="exact company-owned"):
        world.operation_approval(operation, world.operator.principal, path, file_sha(path))
    assert world.verify()["native_versions"] == 2
