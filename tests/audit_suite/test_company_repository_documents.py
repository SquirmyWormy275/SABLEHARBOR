import copy
import subprocess

import pytest

from enterprise.audit_suite.company_repository_documents import (
    plan_repository_documents as plan,
)
from enterprise.audit_suite.company_repository_documents import (
    sync_repository_documents as sync,
)
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError


@pytest.fixture
def fixture(tmp_path):
    tmp_path.chmod(0o700)
    repo = tmp_path / "repo"
    repo.mkdir()
    path = repo / "docs/governance/charter.md"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"# Charter\nState: PROPOSED\n")

    def git(*args):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)

    git("init")
    git("config", "user.name", "Test")
    git("config", "user.email", "test@example.invalid")
    git("add", ".")
    git("commit", "-m", "source")
    snapshot = {
        "control_assignments": [
            {
                "control_id": "SH-GOV-001",
                "primary_person_id": "P1",
                "status": "PROPOSED_CURRENT_ASSIGNMENT",
            }
        ]
    }
    entry = dict(
        document_id="DOC1",
        path="docs/governance/charter.md",
        expected_version=0,
        control_ids=["SH-GOV-001"],
        owner_id="P1",
        source_authority="PROPOSED",
        source_version="1",
        effective_date="2020-01-01",
        revision_date=None,
        supersedes=[],
        mapping_rationale="Explicit charter design relationship",
    )
    manifest = dict(company="SH", branch="docs", documents=[entry])
    root = tmp_path / "store"
    root.mkdir(mode=0o700)
    return repo, path, git, snapshot, manifest, CompanyStore(root)


def test_original_retry_correction_and_conservative_availability(fixture):
    repo, path, git, snapshot, manifest, store = fixture
    first = plan(repo, manifest=manifest, organization_snapshot=snapshot)

    def run(p, command):
        return sync(
            store, repository=repo, plan=p, organization_snapshot=snapshot, command_id=command
        )

    receipt = run(first, "first")
    assert run(first, "first") == receipt
    original = path.read_bytes()
    path.write_bytes(b"# Corrected charter\nState: PROPOSED\n")
    git("add", ".")
    git("commit", "-m", "dated correction")
    manifest["documents"][0].update(expected_version=1, source_version="2", supersedes=["DOC1:v1"])
    second = plan(repo, manifest=manifest, organization_snapshot=snapshot)
    run(second, "second")
    with store._db() as db:
        rows = db.execute("SELECT * FROM versions ORDER BY version").fetchall()
        assert len(rows) == 2 and rows[0]["content"] == original
        assert rows[1]["content"] == path.read_bytes()
        assert all(r["event_at"] is None and r["available_at"] >= "2026" for r in rows)
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
    store.grant("reader", "E1", "SH", "docs", rows[0]["system"])
    with pytest.raises(CompanyStoreError):
        store.read_version(
            "reader",
            "E1",
            "SH",
            "docs",
            rows[0]["system"],
            "DOC1",
            version=1,
            as_of="2020-01-02T00:00:00Z",
        )
    assert "PROPOSED" in rows[1]["provenance"]


@pytest.mark.parametrize("change", ["bytes", "owner", "plan", "untracked", "finance", "symlink"])
def test_stale_or_unsafe_sources_fail_before_import(fixture, change):
    repo, path, git, snapshot, manifest, store = fixture
    pinned = plan(repo, manifest=manifest, organization_snapshot=snapshot)
    if change == "bytes":
        path.write_text("changed")
    elif change == "owner":
        snapshot["control_assignments"][0]["primary_person_id"] = "P2"
    elif change == "plan":
        pinned["documents"][0]["source_authority"] = "LOCKED"
    elif change == "symlink":
        original = path.read_bytes()
        path.unlink()
        target = repo / "outside.md"
        target.write_bytes(original)
        path.symlink_to(target)
    else:
        entry = manifest["documents"][0]
        entry["path"] = "docs/finance/file.md" if change == "finance" else "docs/governance/new.md"
        target = repo / entry["path"]
        target.parent.mkdir(exist_ok=True)
        target.write_text("untracked")
        with pytest.raises(CompanyStoreError):
            plan(repo, manifest=manifest, organization_snapshot=snapshot)
        return
    with pytest.raises(CompanyStoreError):
        sync(store, repository=repo, plan=pinned, organization_snapshot=snapshot, command_id="bad")
    with store._db() as db:
        assert db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 0


def test_no_inferred_owner_or_duplicate_identity(fixture):
    repo, _, _, snapshot, manifest, _ = fixture
    manifest["documents"].append(copy.deepcopy(manifest["documents"][0]))
    with pytest.raises(CompanyStoreError, match="Duplicate"):
        plan(repo, manifest=manifest, organization_snapshot=snapshot)
    manifest["documents"].pop()
    manifest["documents"][0]["owner_id"] = "OTHER"
    with pytest.raises(CompanyStoreError, match="custody"):
        plan(repo, manifest=manifest, organization_snapshot=snapshot)


def test_partial_import_retries_without_duplicate_or_clock_rewrite(fixture, monkeypatch):
    repo, _, _, snapshot, manifest, store = fixture
    second = copy.deepcopy(manifest["documents"][0])
    second["document_id"] = "DOC2"
    manifest["documents"].append(second)
    pinned = plan(repo, manifest=manifest, organization_snapshot=snapshot)
    original_append = store.append_version
    calls = 0

    def interrupt(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("isolated simulated interruption")
        return original_append(*args, **kwargs)

    monkeypatch.setattr(store, "append_version", interrupt)
    with pytest.raises(OSError):
        sync(
            store, repository=repo, plan=pinned, organization_snapshot=snapshot, command_id="batch"
        )
    with store._db() as db:
        before = dict(db.execute("SELECT * FROM versions").fetchone())
    monkeypatch.setattr(store, "append_version", original_append)
    sync(store, repository=repo, plan=pinned, organization_snapshot=snapshot, command_id="batch")
    with store._db() as db:
        assert db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 2
        assert (
            dict(db.execute("SELECT * FROM versions WHERE record=?", ("DOC1",)).fetchone())
            == before
        )


def test_changed_custody_cannot_fork_existing_document(fixture):
    repo, _, _, snapshot, manifest, store = fixture
    first = plan(repo, manifest=manifest, organization_snapshot=snapshot)
    sync(store, repository=repo, plan=first, organization_snapshot=snapshot, command_id="one")
    snapshot["control_assignments"][0]["primary_person_id"] = "P2"
    manifest["documents"][0].update(owner_id="P2", expected_version=1)
    second = plan(repo, manifest=manifest, organization_snapshot=snapshot)
    with pytest.raises(CompanyStoreError, match="registration conflict"):
        sync(store, repository=repo, plan=second, organization_snapshot=snapshot, command_id="two")
    with store._db() as db:
        assert db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 1


def test_original_markdown_collection_and_authorized_persona(fixture, tmp_path):
    from enterprise.audit_suite.company_persona import sources
    from enterprise.audit_suite.engine import COLLECTIONS, Engine
    from enterprise.audit_suite.review import extract

    repo, path, _, snapshot, manifest, store = fixture
    pinned = plan(repo, manifest=manifest, organization_snapshot=snapshot)
    sync(store, repository=repo, plan=pinned, organization_snapshot=snapshot, command_id="one")
    engine = Engine(tmp_path / "audit", company_root=store.path.parent)
    actor = engine.store.provision("Auditor", ["learner"])["id"]
    state = {k: [] for k in COLLECTIONS}
    state.update(
        title="Documentary",
        phase="ACTIVE",
        discipline="IT",
        mode="CLEAN",
        evidence_acquisition="COMPANY_SOURCE_COLLECTION",
        simulated_at="2030-01-01T00:00:00Z",
        people=[{"id": "P1"}],
        scope={
            "boundaries": ["corporate"],
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "timezone": "UTC",
        },
        configuration={"selections": []},
    )
    state["requests"] = [{"id": "R1", "status": "ISSUED", "artifact_ids": []}]
    state = engine.store.create(actor, state, "create")
    engine.company_bindings[state["id"]] = {"company": "SH", "branch": "docs"}
    with store._db() as db:
        system = db.execute("SELECT system FROM systems").fetchone()[0]
    store.grant(actor, state["id"], "SH", "docs", system)
    context = sources(engine, actor, state, "P1")
    assert "Charter" in str(context) and "PROVISIONAL_DOCUMENTARY_CUSTODY" in str(context)
    out = engine.command(
        actor,
        state["id"],
        {
            "command_id": "collect",
            "expected_revision": state["revision"],
            "kind": "company.collect",
            "payload": {"system_id": system, "record_id": "DOC1", "version": 1, "request_id": "R1"},
        },
    )
    artifact = out["artifacts"][0]
    data = engine.artifacts.read(artifact)
    assert data == path.read_bytes() and artifact["name"] == "charter.md"
    parsed = extract(artifact, data)
    assert "Charter" in str(parsed)
    store.grant(actor, state["id"], "SH", "docs", system, active=False)
    assert "Charter" not in str(sources(engine, actor, state, "P1"))


def test_markdown_embedded_code_remains_inert_text(tmp_path):
    import hashlib

    from enterprise.audit_suite.parser_sandbox import parse

    marker = tmp_path / "must-not-exist"
    payload = (
        '# Original\n<script>fetch("https://example.invalid/")</script>\n'
        f'```python\nopen({str(marker)!r}, "w").write("executed")\n```\n'
    ).encode()
    metadata = {
        "id": "DOC",
        "name": "original.md",
        "status": "AVAILABLE",
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    inspected = parse("inspect", metadata, payload)
    assert inspected["status"] == "AVAILABLE" and inspected["mime"] == "text/plain"
    extracted = parse("extract", metadata, payload)
    assert extracted["status"] == "EXTRACTED"
    assert "<script>" in str(extracted) and "open(" in str(extracted)
    assert not marker.exists()
    invalid = parse("inspect", metadata, b"\x00binary")
    assert invalid["status"] == "QUARANTINED"
