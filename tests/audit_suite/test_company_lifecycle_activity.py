import json
import os
from dataclasses import replace
from pathlib import Path

import pytest

from enterprise.audit_suite.company_activity import generate_pair as mover_pair
from enterprise.audit_suite.company_lifecycle_activity import (
    CHANNELS,
    FIELDS,
    LifecycleRecipe,
    LifecycleSourceRef,
    LocalIdentity,
    generate_pair,
    read_inputs,
)
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import sha
from tests.audit_suite.test_company_activity import recipe as mover_recipe

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def inputs(tmp_path):
    tmp_path.chmod(0o700)
    root = tmp_path / "source"
    root.mkdir(mode=0o700)
    store = CompanyStore(root)
    mover_pair(store, repository=ROOT, recipe=mover_recipe())
    with store._db() as db:
        rows = [
            dict(r)
            for r in db.execute(
                "SELECT * FROM versions WHERE branch='activity-clean' "
                "AND ((system='hr' AND version=3) OR (system='directory' AND version=2) "
                "OR (system='application' AND version=2)) ORDER BY system"
            )
        ]
    refs = tuple(LifecycleSourceRef(**{k: r[k] for k in FIELDS}) for r in rows)
    _, pin = read_inputs(root, refs)
    recipe = LifecycleRecipe(
        "SH",
        "identity-originals",
        refs,
        pin,
        ("lifecycle-a", "lifecycle-b"),
        "EXERCISE-WORKER-001",
        "P014",
        "2027-05-01T09:00:00Z",
        "2027-05-02T09:00:00Z",
        "2027-05-03T09:00:00Z",
        "2027-05-03T09:10:00Z",
        "2027-05-03T10:00:00Z",
        "Explicit fictional read-only role, all six local handles revoked at test contract expiry",
    )
    return root, recipe


def rows(root):
    store = CompanyStore(root)
    with store._db() as db:
        return [dict(r) for r in db.execute("SELECT * FROM versions ORDER BY branch,system,record")]


def test_actual_transition_pair_preserves_sources_shared_inputs_and_chronology(tmp_path, inputs):
    source, recipe = inputs
    source_bytes = (source / "company.sqlite3").read_bytes()
    result = generate_pair(
        tmp_path / "lifecycle", repository=ROOT, source_root=source, recipe=recipe
    )
    native = rows(tmp_path / "lifecycle")
    assert len(native) == 24
    indexed = {(r["branch"], r["record"]): r for r in native}
    for record in [
        "REQUEST",
        "LOCAL-CATALOG",
        "APPROVAL",
        "CREATE",
        "PROVISION",
        "INITIAL-PROBES",
        "CONTRACT-EXPIRED",
    ]:
        assert (
            indexed["lifecycle-a", record]["content"] == indexed["lifecycle-b", record]["content"]
        )
    for branch in recipe.branch_ids:
        checkpoint = json.loads(indexed[branch, "CHECKPOINT"]["content"])
        assert checkpoint["active_channels"] == (
            [] if branch == "lifecycle-a" else ["application_session"]
        )
        assert checkpoint["probes"]["directory_account"] == "DENY"
        assert json.loads(indexed[branch, "FINAL-PROBES"]["content"])["active_channels"] == []
        for row in [r for r in native if r["branch"] == branch]:
            assert sha(row["content"]) == row["sha256"]
            for ref in json.loads(row["content"])["previous_events"]:
                previous = indexed[branch, ref["record"]]
                assert (
                    ref["sha256"] == previous["sha256"]
                    and previous["available_at"] <= row["available_at"]
                )
    assert (source / "company.sqlite3").read_bytes() == source_bytes
    for name, pin in result["upstream_files"].items():
        assert sha((tmp_path / "lifecycle" / name).read_bytes()) == pin
    store = CompanyStore(tmp_path / "lifecycle")
    with store._db() as db:
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
    with pytest.raises(CompanyStoreError):
        generate_pair(tmp_path / "lifecycle", repository=ROOT, source_root=source, recipe=recipe)
    assert rows(tmp_path / "lifecycle") == native


def test_local_approval_gate_unique_identity_and_actual_cached_session():
    state = LocalIdentity()
    request = {
        "request_id": "R",
        "subject_id": "EXERCISE-ONE",
        "sponsor_person_id": "SPONSOR",
        "approved": False,
        "proofing_check": "LOCAL_CORRELATION_ONLY",
    }
    with pytest.raises(CompanyStoreError):
        state.create(request)
    assert state.subject is None
    request["approved"] = True
    state.create(request)
    with pytest.raises(CompanyStoreError):
        state.create(request)
    approval = {
        "subject_id": "EXERCISE-ONE",
        "approved": True,
        "business_need": "Read test records",
        "rights": ["local.records.admin"],
        "reviewer_id": "REVIEWER",
        "provisioner_id": "OPERATOR",
        "conflict_check": "NO_CONFLICT_IN_DECLARED_CATALOG",
    }
    with pytest.raises(CompanyStoreError):
        state.provision(approval)
    assert state.rights == set()
    approval["rights"] = ["local.records.read"]
    state.provision(approval)
    state.revoke([c for c in CHANNELS if c != "application_session"])
    assert (
        state.probe()["application_session"] == "ALLOW"
        and state.probe()["directory_account"] == "DENY"
    )
    state.revoke(["application_session"])
    assert set(state.probe().values()) == {"DENY"}


@pytest.mark.parametrize(
    "fault",
    [
        "hash",
        "future",
        "sponsor",
        "subject",
        "samebranches",
        "order",
        "duplicate",
        "public",
        "hardlink",
        "nested",
    ],
)
def test_rejects_changed_unavailable_or_unsafe_inputs_without_output(tmp_path, inputs, fault):
    source, recipe = inputs
    target = tmp_path / "out"
    if fault == "hash":
        recipe = replace(
            recipe,
            source_refs=(replace(recipe.source_refs[0], sha256="0" * 64), *recipe.source_refs[1:]),
        )
    elif fault == "future":
        recipe = replace(recipe, request_at="2027-04-01T00:00:00Z")
    elif fault == "sponsor":
        recipe = replace(recipe, sponsor_person_id="P015")
    elif fault == "subject":
        recipe = replace(recipe, exercise_subject_id="P014")
    elif fault == "samebranches":
        recipe = replace(recipe, branch_ids=("same", "same"))
    elif fault == "order":
        recipe = replace(recipe, correction_at=recipe.start_at)
    elif fault == "duplicate":
        recipe = replace(recipe, source_refs=(recipe.source_refs[0], recipe.source_refs[0]))
    elif fault == "public":
        (source / "company.sqlite3").chmod(0o644)
    elif fault == "hardlink":
        os.link(source / "company.sqlite3", tmp_path / "alias.sqlite3")
    else:
        target = source / "nested"
    with pytest.raises(CompanyStoreError):
        generate_pair(target, repository=ROOT, source_root=source, recipe=recipe)
    assert not target.exists()


def test_source_changes_during_generation_fail_without_publication(tmp_path, inputs, monkeypatch):
    from enterprise.audit_suite import company_lifecycle_activity as module

    source, recipe = inputs
    original = module.read_inputs
    calls = 0

    def changed(root, refs):
        nonlocal calls
        calls += 1
        if calls == 2:
            store = CompanyStore(source)
            with store._db() as db:
                # Explicit malicious-file simulation in this test's disposable source only.
                db.execute("DROP TRIGGER no_version_update")
                db.execute(
                    "UPDATE versions SET content=? WHERE branch=? AND system='directory'",
                    (b"changed original bytes", "activity-clean"),
                )
        return original(root, refs)

    monkeypatch.setattr(module, "read_inputs", changed)
    with pytest.raises(CompanyStoreError, match="pin mismatch"):
        module.generate_pair(tmp_path / "out", repository=ROOT, source_root=source, recipe=recipe)
    assert not (tmp_path / "out").exists()


def test_exact_selected_inputs_exclude_other_people_and_preserve_metadata(tmp_path, inputs):
    source, recipe = inputs
    selected, pin = read_inputs(source, recipe.source_refs)
    assert len(selected) == 3 and all(
        json.loads(r["content"])["person_id"] == "P014" for r in selected
    )
    assert {r["system"] for r in selected} == {"hr", "directory", "application"}
    from enterprise.audit_suite.operating_source_bridge import encoded

    receipt = generate_pair(tmp_path / "out", repository=ROOT, source_root=source, recipe=recipe)
    assert sha(encoded(receipt["source_metadata"])) == pin
    assert len(list((tmp_path / "out/upstream").iterdir())) == 3


@pytest.mark.parametrize("fault", ["mode", "replacement"])
def test_read_rechecks_private_file_identity_after_transaction(
    tmp_path, inputs, monkeypatch, fault
):
    from enterprise.audit_suite import company_lifecycle_activity as module

    source, recipe = inputs
    original = module.sqlite3.connect
    path = source / "company.sqlite3"

    def changed(*a, **k):
        connection = original(*a, **k)
        if fault == "mode":
            path.chmod(0o644)
        else:
            original_bytes = path.read_bytes()
            path.rename(source / "preserved.sqlite3")
            path.write_bytes(original_bytes)
            path.chmod(0o600)
        return connection

    monkeypatch.setattr(module.sqlite3, "connect", changed)
    with pytest.raises(CompanyStoreError):
        read_inputs(source, recipe.source_refs)


def test_source_quota_counts_utf8_bytes(tmp_path, inputs, monkeypatch):
    from enterprise.audit_suite import company_lifecycle_activity as module

    source, recipe = inputs
    store = CompanyStore(source)
    with store._db() as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute(
            "UPDATE versions SET provenance=? WHERE branch='activity-clean' AND system='directory'",
            ("界" * 500,),
        )
    selected, _ = read_inputs(source, recipe.source_refs)
    codepoints = sum(len(r["content"]) + len(r["provenance"]) for r in selected)
    monkeypatch.setattr(module, "MAX_INPUT", codepoints + 100)
    with pytest.raises(CompanyStoreError, match="quota"):
        read_inputs(source, recipe.source_refs)
