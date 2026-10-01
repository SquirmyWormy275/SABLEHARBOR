import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pytest

from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.source_library_audit import (
    LIBRARY_MANIFEST_SCHEMA,
    LIBRARY_REVIEW_SCHEMA,
    LIBRARY_REVIEW_VERDICT,
    AcceptedLibrary,
    BusinessRoute,
    LibraryAudit,
    exact_projected_reference,
    file_sha,
    private_file,
    typed_content,
)


def write(path, value):
    path.write_bytes(json.dumps(value).encode())
    path.chmod(0o600)


@pytest.fixture
def library(tmp_path):
    tmp_path.chmod(0o700)
    source = tmp_path / "source"
    source.mkdir(mode=0o700)
    store = CompanyStore(source)
    store.register_system("EXAMPLE", "operating", "operations.events", owner_id="security")
    for version, available in ((1, "2027-01-02T00:00:00Z"), (2, "2027-01-04T00:00:00Z")):
        store.append_version(
            "EXAMPLE",
            "operating",
            "operations.events",
            "event-one",
            content=json.dumps({"revision": version}).encode(),
            event_at="2027-01-01T00:00:00Z",
            available_at=available,
            origin="AUTHORED_TRAINING_SOURCE",
            provenance={
                "source_reference": "test-only",
                "name": "event.json",
                "content_type": "application/json",
            },
            expected_version=version - 1,
            command_id=f"test-import-{version}",
        )
    store.append_version(
        "EXAMPLE",
        "operating",
        "operations.events",
        "object-one",
        content=b"Exact ordinary UTF-8 original\n",
        event_at="2027-01-10T00:00:00Z",
        available_at="2027-01-11T00:00:00Z",
        expected_version=0,
        command_id="text-object",
        provenance={
            "source_reference": "test-only",
            "name": "original.txt",
            "content_type": "text/plain; charset=utf-8",
        },
    )
    database = source / "company.sqlite3"
    pin = file_sha(database)
    manifest, review = tmp_path / "MANIFEST.json", tmp_path / "REVIEW.json"
    write(manifest, {"schema": LIBRARY_MANIFEST_SCHEMA, "files": {"company.sqlite3": pin}})
    write(
        review,
        {
            "schema": LIBRARY_REVIEW_SCHEMA,
            "verdict": LIBRARY_REVIEW_VERDICT,
            "source_quality_accepted_for_final_learner_audit": True,
            "library_pins": {"company.sqlite3": pin, "MANIFEST.json": file_sha(manifest)},
            "native_versions": 3,
        },
    )
    accepted = AcceptedLibrary(
        database, pin, manifest, file_sha(manifest), review, file_sha(review), 3
    )
    route = BusinessRoute("EXAMPLE", "operating", "operations.events", "security", "event_history")
    return accepted, route


def command(session, actor, kind, payload):
    engine, engagement = session.engine, session.engagement
    current = engine.store.get(actor, engagement)
    return engine.command(
        actor,
        engagement,
        {
            "command_id": f"test-{kind}-{current['revision']}",
            "expected_revision": current["revision"],
            "kind": kind,
            "payload": payload,
        },
    )


def create_session(session, *, start="2027-01-05"):
    engine, state, identities = session.create(
        repository=Path(__file__).resolve().parents[2],
        audit_root=session.database.parent.parent / "audit",
        payload={
            "command_id": "fresh-test-create",
            "title": "Neutral source-library mechanics test",
            "discipline": "IT",
            "mode": "CLEAN",
            "configuration": {"selections": []},
            "scope": {
                "programs": ["SOC2"],
                "report_type": "Type 2",
                "period_start": "2027-01-01",
                "period_end": "2027-12-31",
                "fieldwork_start": start,
                "timezone": "UTC",
                "boundaries": ["corporate"],
                "control_ids": ["SH-SEC-003"],
            },
        },
    )
    command(session, identities["operator"], "company.activate", {})
    return engine, state, identities


def authorize(session, *, active=True):
    if session.engine is None:
        create_session(session)
    session.authorize(**session.identities, engagement=session.engagement, active=active)


def discover(session, cutoff):
    return session.discover(
        session.engine, session.identities["auditor"], session.engagement, as_of=cutoff
    )


def test_acceptance_and_original_source_pins_required_before_staging(library, tmp_path):
    accepted, route = library
    write(accepted.review, {"verdict": "PENDING", "database_sha256": accepted.database_sha256})
    changed = AcceptedLibrary(
        accepted.database,
        accepted.database_sha256,
        accepted.manifest,
        accepted.manifest_sha256,
        accepted.review,
        file_sha(accepted.review),
        2,
    )
    with pytest.raises(ProcedureError, match="acceptance"):
        LibraryAudit(changed, tmp_path / "forbidden", [route])
    assert not (tmp_path / "forbidden").exists()


def test_discovery_preserves_projected_identity_and_available_version_clock(library, tmp_path):
    accepted, route = library
    session = LibraryAudit(accepted, tmp_path / "ordinary-copy", [route])
    authorize(session)
    rows, pages = discover(session, "2027-01-03T00:00:00Z")
    assert [r["version"] for r in rows] == [1]
    assert rows[0]["system"] == "operations.events"
    assert rows[0]["logical_system"] == "event_history"
    assert rows[0]["logical_family"] == "security"
    assert rows[0]["sha256"] == hashlib.sha256(rows[0]["content"]).hexdigest()
    assert pages[0]["records"][0]["available_at"].startswith("2027-01-02")
    later, _ = discover(session, "2027-01-05T00:00:00Z")
    assert [r["version"] for r in later] == [1, 2]
    assert file_sha(accepted.database) == accepted.database_sha256
    authorize(session, active=False)
    with pytest.raises(ProcedureError, match="not granted"):
        discover(session, "2027-01-05T00:00:00Z")


@pytest.mark.parametrize(
    "changes",
    [
        {"verdict": "PASS_BOUNDED_RAW_SOURCE_ONLY"},
        {"source_quality_accepted_for_final_learner_audit": False},
        {"schema": "SH_GENERIC_SOURCE_REVIEW_V1"},
        {"native_versions": 2},
        {"library_pins": {"company.sqlite3": "0" * 64, "MANIFEST.json": "0" * 64}},
    ],
)
def test_other_pass_or_false_quality_reviews_do_not_authorize_audit_creation(
    library, tmp_path, changes
):
    accepted, route = library
    review = json.loads(accepted.review.read_bytes())
    review.update(changes)
    write(accepted.review, review)
    changed = AcceptedLibrary(
        accepted.database,
        accepted.database_sha256,
        accepted.manifest,
        accepted.manifest_sha256,
        accepted.review,
        file_sha(accepted.review),
        accepted.version_count,
    )
    with pytest.raises(ProcedureError):
        LibraryAudit(changed, tmp_path / "forbidden", [route])
    assert not (tmp_path / "forbidden").exists()


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_source_sidecars_fail_closed_without_copying_or_deleting_them(library, tmp_path, suffix):
    accepted, route = library
    sidecar = Path(str(accepted.database) + suffix)
    sidecar.write_bytes(b"preserved-sidecar")
    sidecar.chmod(0o600)
    with pytest.raises(ProcedureError, match="sidecars"):
        LibraryAudit(accepted, tmp_path / "forbidden", [route])
    assert not (tmp_path / "forbidden").exists()
    assert sidecar.read_bytes() == b"preserved-sidecar"


def test_private_file_rejects_symlink_ancestor(library, tmp_path):
    accepted, _ = library
    alias = tmp_path / "source-alias"
    alias.symlink_to(accepted.database.parent, target_is_directory=True)
    with pytest.raises(ProcedureError, match="aliases"):
        private_file(alias / accepted.database.name)


def test_rejected_v2_manifest_cannot_be_resealed_as_final_v2_1_acceptance(library, tmp_path):
    accepted, route = library
    manifest = json.loads(accepted.manifest.read_bytes())
    manifest["schema"] = "SH_COMPANY_OPERATIONAL_PROJECTION_V2"
    write(accepted.manifest, manifest)
    review = json.loads(accepted.review.read_bytes())
    review["library_pins"]["MANIFEST.json"] = file_sha(accepted.manifest)
    write(accepted.review, review)
    resealed = AcceptedLibrary(
        accepted.database,
        accepted.database_sha256,
        accepted.manifest,
        file_sha(accepted.manifest),
        accepted.review,
        file_sha(accepted.review),
        accepted.version_count,
    )
    with pytest.raises(ProcedureError, match="Manifest"):
        LibraryAudit(resealed, tmp_path / "forbidden", [route])
    assert not (tmp_path / "forbidden").exists()


def test_branch_membership_and_reviewer_separation_are_not_inferred(library, tmp_path):
    accepted, route = library
    session = LibraryAudit(accepted, tmp_path / "copy", [route])
    with pytest.raises(ProcedureError, match="Separate"):
        session.authorize(
            operator="operator", auditor="same-person", reviewer="same-person", engagement="new"
        )
    authorize(session)
    session.engine.company_bindings[session.engagement] = {"company": "EXAMPLE", "branch": "other"}
    with pytest.raises(ProcedureError, match="branch binding"):
        discover(session, "2027-01-05T00:00:00Z")
    session.engine.company_bindings[session.engagement] = {
        "company": "EXAMPLE",
        "branch": "operating",
    }
    with pytest.raises(ProcedureError, match="audit performer"):
        session.discover(session.engine, session.identities["reviewer"], session.engagement)
    with pytest.raises(CompanyStoreError, match="unauthorized"):
        session.store.read_version(
            session.identities["reviewer"],
            session.engagement,
            "EXAMPLE",
            "operating",
            "operations.events",
            "event-one",
            version=1,
            as_of="2027-01-05T00:00:00Z",
        )


def test_original_changes_after_staging_fail_closed(library, tmp_path):
    accepted, route = library
    session = LibraryAudit(accepted, tmp_path / "copy", [route])
    store = CompanyStore(accepted.database.parent)
    store.register_system("EXAMPLE", "operating", "new-system", owner_id="security")
    with pytest.raises(ProcedureError, match="pin changed"):
        authorize(session)


def test_removing_collection_immutability_on_disposable_copy_fails_closed(library, tmp_path):
    accepted, route = library
    session = LibraryAudit(accepted, tmp_path / "copy", [route])
    with sqlite3.connect(session.database) as db:
        db.execute("DROP TRIGGER no_collection_update")
    with pytest.raises(ProcedureError, match="schema changed"):
        authorize(session)


def test_held_open_wal_shadow_is_rejected_before_normal_source_access(library, tmp_path):
    accepted, route = library
    session = LibraryAudit(accepted, tmp_path / "copy", [route])
    authorize(session)
    shadow = sqlite3.connect(session.database)
    try:
        assert shadow.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        shadow.execute("DROP TRIGGER no_version_update")
        replacement = b'{"revision":"unaccepted WAL replacement"}'
        shadow.execute(
            "UPDATE versions SET content=?,sha256=? WHERE record='event-one' AND version=1",
            (replacement, hashlib.sha256(replacement).hexdigest()),
        )
        shadow.commit()
        assert Path(str(session.database) + "-wal").is_file()
        with pytest.raises(ProcedureError, match="sidecars"):
            session.check_unchanged()
        with pytest.raises(ProcedureError, match="sidecars"):
            authorize(session)
        with pytest.raises(ProcedureError, match="sidecars"):
            discover(session, "2027-01-03T00:00:00Z")
        # Engine and direct normal CompanyStore calls share the same boundary.
        with pytest.raises(ProcedureError, match="sidecars"):
            session.engine.company_store.read_version(
                session.identities["auditor"],
                session.engagement,
                "EXAMPLE",
                "operating",
                "operations.events",
                "event-one",
                version=1,
                as_of="2027-01-03T00:00:00Z",
            )
        assert file_sha(accepted.database) == accepted.database_sha256
        assert Path(str(session.database) + "-wal").is_file()
    finally:
        shadow.close()


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
@pytest.mark.parametrize("alias", [False, True])
def test_staged_sidecars_and_dangling_aliases_block_immutable_and_normal_api_reads(
    library, tmp_path, suffix, alias
):
    accepted, route = library
    session = LibraryAudit(accepted, tmp_path / "copy", [route])
    authorize(session)
    sidecar = Path(str(session.database) + suffix)
    if alias:
        sidecar.symlink_to(tmp_path / "nonexistent-preserved-target")
    else:
        sidecar.write_bytes(b"preserved staged journal")
        sidecar.chmod(0o600)
    with pytest.raises(ProcedureError, match="sidecars"):
        session.check_unchanged()
    with pytest.raises(ProcedureError, match="sidecars"):
        session.store.list_systems(
            session.identities["auditor"], session.engagement, "EXAMPLE", "operating"
        )
    assert sidecar.is_symlink() if alias else sidecar.read_bytes() == b"preserved staged journal"
    assert file_sha(accepted.database) == accepted.database_sha256


def test_normal_api_checks_quiescence_after_the_connection_closes(library, tmp_path, monkeypatch):
    accepted, route = library
    session = LibraryAudit(accepted, tmp_path / "copy", [route])
    authorize(session)
    original_db = CompanyStore._db
    sidecar = Path(str(session.database) + "-journal")

    @contextmanager
    def journal_after_connection(store):
        with original_db(store) as db:
            yield db
        sidecar.write_bytes(b"concurrent journal appeared after the read")
        sidecar.chmod(0o600)

    monkeypatch.setattr(CompanyStore, "_db", journal_after_connection)
    with pytest.raises(ProcedureError, match="sidecars"):
        session.store.list_systems(
            session.identities["auditor"], session.engagement, "EXAMPLE", "operating"
        )
    assert sidecar.read_bytes() == b"concurrent journal appeared after the read"


def test_discovery_rejects_future_clock_then_allows_explicit_clock_advance(library, tmp_path):
    accepted, route = library
    session = LibraryAudit(accepted, tmp_path / "copy", [route])
    _, _, identities = create_session(session, start="2027-01-03")
    authorize(session)
    command(session, identities["auditor"], "kickoff.start", {})
    original_state = session.engine.store.get(identities["auditor"], session.engagement)
    assert original_state["simulated_at"].startswith("2027-01-03")
    with pytest.raises(ProcedureError, match="simulated clock"):
        discover(session, "2027-01-12T00:00:00Z")
    assert session.engine.store.get(identities["auditor"], session.engagement) == original_state
    early, _ = discover(session, "2027-01-03T00:00:00Z")
    assert [(row["record"], row["version"]) for row in early] == [("event-one", 1)]
    advanced = command(
        session,
        identities["auditor"],
        "clock.advance",
        {"mode": "TARGET_DATE", "target": "2027-01-12T00:00:00Z"},
    )
    assert advanced["simulated_at"].startswith("2027-01-12")
    later, _ = session.discover(session.engine, identities["auditor"], session.engagement)
    assert {(row["record"], row["version"]) for row in later} == {
        ("event-one", 1),
        ("event-one", 2),
        ("object-one", 1),
    }
    historical, _ = discover(session, "2027-01-03T00:00:00Z")
    assert [(row["record"], row["version"]) for row in historical] == [("event-one", 1)]


def test_discovery_requires_actual_created_and_activated_engine_context(library, tmp_path):
    accepted, route = library
    session = LibraryAudit(accepted, tmp_path / "copy", [route])
    with pytest.raises(ProcedureError, match="bound Engine"):
        session.discover(None, "arbitrary-auditor", "arbitrary-engagement", as_of="2027-01-03")
    engine, _, identities = create_session(session)
    authorize(session)
    for wrong_engine, actor, engagement in (
        (object(), identities["auditor"], session.engagement),
        (engine, identities["reviewer"], session.engagement),
        (engine, identities["auditor"], "unbound-engagement"),
    ):
        with pytest.raises(ProcedureError, match="bound Engine"):
            session.discover(wrong_engine, actor, engagement)


def test_projected_pointer_requires_exact_native_system_version_hash_and_clocks(library, tmp_path):
    accepted, route = library
    session = LibraryAudit(accepted, tmp_path / "copy", [route])
    authorize(session)
    rows, _ = discover(session, "2027-01-05T00:00:00Z")
    reference = {
        key: rows[0][key]
        for key in (
            "company",
            "branch",
            "system",
            "record",
            "version",
            "sha256",
            "event_at",
            "available_at",
            "imported_at",
        )
    }
    assert exact_projected_reference(reference, rows) == rows[0]
    assert (
        exact_projected_reference(
            {key: value for key, value in reference.items() if key != "imported_at"}, rows
        )
        == rows[0]
    )
    with pytest.raises(ProcedureError, match="not uniquely discovered"):
        exact_projected_reference({**reference, "system": rows[0]["logical_system"]}, rows)
    with pytest.raises(ProcedureError, match="hash or clocks"):
        exact_projected_reference({**reference, "sha256": "0" * 64}, rows)
    with pytest.raises(ProcedureError, match="clocks required"):
        exact_projected_reference(
            {key: value for key, value in reference.items() if key != "available_at"}, rows
        )


def test_supported_zero_evidence_creation_and_normal_text_collection(library, tmp_path):
    accepted, route = library
    session = LibraryAudit(accepted, tmp_path / "source-copy", [route])
    assert session.database.is_file()
    engine, state, identities = session.create(
        repository=Path(__file__).resolve().parents[2],
        audit_root=tmp_path / "audit",
        payload={
            "command_id": "fresh-test-create",
            "title": "Neutral source-library mechanics test",
            "discipline": "IT",
            "mode": "CLEAN",
            "configuration": {"selections": []},
            "scope": {
                "programs": ["SOC2"],
                "report_type": "Type 2",
                "period_start": "2027-01-01",
                "period_end": "2027-12-31",
                "fieldwork_start": "2028-01-03",
                "timezone": "UTC",
                "boundaries": ["corporate"],
                "control_ids": ["SH-SEC-003"],
            },
        },
    )
    assert not any(identities["zero_workroom_counts"].values())
    assert len({identities[k] for k in ("operator", "auditor", "reviewer")}) == 3
    engagement = state["id"]

    def command(actor, kind, payload):
        current = engine.store.get(actor, engagement)
        return engine.command(
            actor,
            engagement,
            {
                "command_id": "test-" + kind,
                "expected_revision": current["revision"],
                "kind": kind,
                "payload": payload,
            },
        )

    command(identities["operator"], "company.activate", {})
    command(identities["auditor"], "kickoff.start", {})
    state = command(
        identities["auditor"],
        "pbc.create",
        {
            "title": "Native operational original",
            "purpose": "Exact selected source collection",
            "control_id": "SH-SEC-003",
            "person_id": "AS-P008",
            "boundary_id": "corporate",
        },
    )
    request = state["requests"][-1]["id"]
    command(identities["auditor"], "pbc.issue", {"request_id": request})
    session.authorize(
        operator=identities["operator"],
        auditor=identities["auditor"],
        reviewer=identities["reviewer"],
        engagement=engagement,
    )
    rows, _ = session.discover(
        engine, identities["auditor"], engagement, as_of=state["simulated_at"]
    )
    original = next(row for row in rows if row["record"] == "object-one")
    retained = session.collect(
        engine,
        identities["auditor"],
        engagement,
        request,
        original,
        command_id="typed-source-collect",
    )
    final = engine.store.get(identities["auditor"], engagement)
    artifact = next(a for a in final["artifacts"] if a["id"] == retained["artifact_id"])
    assert artifact["name"] == "original.txt" and artifact["mime"] == "text/plain"
    assert retained["source"]["system"] == "operations.events"
    assert retained["logical_system"] == "event_history"
    assert retained["document"].encode() == original["content"] == engine.artifacts.read(artifact)
    assert not final["reviews"] and not final["workpapers"]
    assert all(
        t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN" for t in final["tasks"]
    )
    assert file_sha(accepted.database) == accepted.database_sha256
    assert engine.company_store is session.store
    assert not any(
        Path(str(session.database) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")
    )


def test_missing_unavailable_predecessor_is_not_assumed_from_latest_version(tmp_path):
    tmp_path.chmod(0o700)
    (tmp_path / "source").mkdir(mode=0o700)
    store = CompanyStore(tmp_path / "source")
    store.register_system("EXAMPLE", "operating", "history", owner_id="security")
    for number, available in ((1, "2027-01-06T00:00:00Z"), (2, "2027-01-04T00:00:00Z")):
        store.append_version(
            "EXAMPLE",
            "operating",
            "history",
            "event",
            content=b'{"business":"record"}',
            event_at="2027-01-01T00:00:00Z",
            available_at=available,
            origin="AUTHORED_TRAINING_SOURCE",
            provenance={
                "source_reference": "test-only",
                "name": "record.json",
                "content_type": "application/json",
            },
            expected_version=number - 1,
            command_id=f"version-{number}",
        )
    database = store.path
    pin = file_sha(database)
    manifest, review = tmp_path / "MANIFEST.json", tmp_path / "REVIEW.json"
    write(manifest, {"schema": LIBRARY_MANIFEST_SCHEMA, "files": {"company.sqlite3": pin}})
    write(
        review,
        {
            "schema": LIBRARY_REVIEW_SCHEMA,
            "verdict": LIBRARY_REVIEW_VERDICT,
            "source_quality_accepted_for_final_learner_audit": True,
            "library_pins": {"company.sqlite3": pin, "MANIFEST.json": file_sha(manifest)},
            "native_versions": 2,
        },
    )
    accepted = AcceptedLibrary(
        database, pin, manifest, file_sha(manifest), review, file_sha(review), 2
    )
    session = LibraryAudit(
        accepted,
        tmp_path / "copy",
        [BusinessRoute("EXAMPLE", "operating", "history", "security", "history")],
    )
    authorize(session)
    with pytest.raises(ProcedureError, match="Incomplete visible"):
        discover(session, "2027-01-05T00:00:00Z")


@pytest.mark.parametrize(
    "content_type,name,raw",
    [
        ("application/json", "wrong.txt", b"{}"),
        ("text/plain", "wrong.json", b"exact original UTF-8"),
        ("application/json", "malformed.json", b"not JSON"),
        ("text/plain", "nonutf8.txt", b"\xff"),
        ("application/pdf", "unsupported.pdf", b"%PDF"),
    ],
)
def test_declared_evidence_types_fail_closed(content_type, name, raw):
    row = {
        "content": raw,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "provenance": {"content_type": content_type, "name": name},
    }
    with pytest.raises(ProcedureError):
        typed_content(row)


def test_text_original_keeps_exact_bytes_and_explicit_txt_type():
    raw = "Ordinary exact UTF-8 company original: café\n".encode()
    row = {
        "content": raw,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "provenance": {"content_type": "text/plain", "name": "original.txt"},
    }
    document, content_type = typed_content(row)
    assert document.encode() == raw
    assert content_type == "text/plain"
