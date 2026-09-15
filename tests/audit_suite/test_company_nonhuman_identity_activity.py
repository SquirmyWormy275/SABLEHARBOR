import json
from dataclasses import replace
from pathlib import Path

import pytest

from enterprise.audit_suite.company_backup_activity import generate_backup_pair
from enterprise.audit_suite.company_nonhuman_identity_activity import (
    FIELDS,
    LocalCopyIdentity,
    NonhumanIdentityRecipe,
    NonhumanSourceRef,
    generate_pair,
    read_inputs,
)
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from tests.audit_suite.test_company_backup_activity import recipe as backup_recipe

ROOT = Path(__file__).resolve().parents[2]


def versions(root):
    store = CompanyStore(root)
    with store._db() as db:
        return [
            dict(r)
            for r in db.execute("SELECT * FROM versions ORDER BY branch,system,record,version")
        ]


@pytest.fixture
def inputs(tmp_path):
    tmp_path.chmod(0o700)
    source = tmp_path / "source"
    source.mkdir(mode=0o700)
    store = CompanyStore(source)
    generate_backup_pair(store, repository=ROOT, recipe=backup_recipe())
    selected = [
        r
        for r in versions(source)
        if r["branch"] == "backup-messy"
        and (r["system"], r["version"])
        in {("inventory", 1), ("source_dataset", 2), ("credential_event", 2), ("backup_job", 2)}
    ]
    refs = tuple(NonhumanSourceRef(**{k: r[k] for k in FIELDS}) for r in selected)
    _, pin = read_inputs(source, refs)
    recipe = NonhumanIdentityRecipe(
        "SH",
        "backup-originals",
        refs,
        pin,
        ("service-a", "service-b"),
        "EXERCISE-SVC-BACKUP-COPY",
        "LOCAL-COPY",
        "LOCAL-ISOLATED-TARGET",
        "2027-04-01T00:00:00Z",
        "2027-05-01T09:00:00Z",
        "2027-05-01T09:10:00Z",
        "2027-05-01T10:00:00Z",
        "2027-06-30T12:00:00Z",
        "2027-07-01T00:00:00Z",
        (
            "Explicit local rule: least-privilege dataset copy, rotation and dependency review, "
            "quarter-end checkpoint"
        ),
    )
    return source, recipe


def test_paired_actual_authentication_copy_and_immutable_failure(tmp_path, inputs):
    source, recipe = inputs
    before = (source / "company.sqlite3").read_bytes()
    result = generate_pair(tmp_path / "out", repository=ROOT, source_root=source, recipe=recipe)
    rows = versions(tmp_path / "out")
    assert len(rows) == 35
    indexed = {(r["branch"], r["record"], r["version"]): r for r in rows}
    for record, version in [
        ("IDENTITY", 1),
        ("CREDENTIAL", 1),
        ("CONSUMER", 1),
        ("BASELINE", 1),
        ("CREDENTIAL", 2),
    ]:
        assert (
            indexed["service-a", record, version]["content"]
            == indexed["service-b", record, version]["content"]
        )
    assert ("service-b", "AFTER-ROTATION-OUTPUT", 1) not in indexed
    failed = json.loads(indexed["service-b", "AFTER-ROTATION", 1]["content"])
    assert failed["status"] == "AUTHORIZATION_DENIED" and failed["copied_bytes"] == 0
    assert failed["output_ref"] is None and failed["output_sha256"] is None
    assert failed["configured_version"] == 1 and failed["current_credential_version"] == 2
    dataset = next(
        r for r in read_inputs(source, recipe.source_refs)[0] if r["system"] == "source_dataset"
    )
    for row in rows:
        assert sha(row["content"]) == row["sha256"]
        if row["system"] == "copied_dataset":
            assert row["content"] == dataset["content"]
            payload = json.loads(row["content"])
            provenance = json.loads(row["provenance"])
            assert payload["source_period_start"].startswith("2027-03-01")
            assert row["event_at"] >= "2027-04-01"
            assert payload["classification"] == "FICTIONAL_REFERENCE_EXERCISE_NOT_DEPLOYMENT"
            assert provenance["original_payload_unchanged"] is True
            assert provenance["control_ids"] == ["SH-IAM-006"]
        else:
            for ref in json.loads(row["content"])["previous_events"]:
                previous = indexed[row["branch"], ref["record"], ref["version"]]
                assert (
                    previous["sha256"] == ref["sha256"]
                    and previous["available_at"] <= row["available_at"]
                )
    for branch in recipe.branch_ids:
        assert json.loads(indexed[branch, "AFTER-CORRECTION", 1]["content"])["status"] == "COPIED"
        assert (
            json.loads(indexed[branch, "RETIRED-VERSION-PROBE", 1]["content"])["authorization"]
            == "DENY"
        )
        assert (
            json.loads(indexed[branch, "UNDECLARED-OPERATION-PROBE", 1]["content"])["authorization"]
            == "DENY"
        )
        review = json.loads(indexed[branch, "QUARTER-END-REVIEW", 1]["content"])
        assert review["mismatched_dependency_ids"] == [] and review["ownership_changes"] == []
        assert review["owner_by_identity"][recipe.identity_id] == "AS-P007"
    assert sha(encoded(result["source_metadata"])) == recipe.source_versions_sha256
    assert (source / "company.sqlite3").read_bytes() == before
    for path, pin in result["upstream_files"].items():
        assert sha((tmp_path / "out" / path).read_bytes()) == pin
    historical = [
        json.loads(r["content"])
        for r in read_inputs(source, recipe.source_refs)[0]
        if r["system"] == "credential_event"
    ][0]
    assert historical["principal"] == "AS-P007" and historical["principal"] != recipe.identity_id
    store = CompanyStore(tmp_path / "out")
    with store._db() as db:
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
    with pytest.raises(CompanyStoreError):
        generate_pair(tmp_path / "out", repository=ROOT, source_root=source, recipe=recipe)
    assert versions(tmp_path / "out") == rows


def test_permissions_identity_retired_versions_and_copy_bytes():
    identity = LocalCopyIdentity("EXERCISE-SVC-ONE", "DATA", "TARGET")
    raw = b"original\x00native\xffbytes"
    assert identity.copy(identity.identity_id, 1, raw, "DATA", "TARGET")["output"] == raw
    for who, version, source, target in [
        ("OTHER", 1, "DATA", "TARGET"),
        (identity.identity_id, True, "DATA", "TARGET"),
        (identity.identity_id, 1, "OTHER", "TARGET"),
        (identity.identity_id, 1, "DATA", "OTHER"),
    ]:
        result = identity.copy(who, version, raw, source, target)
        assert result["output"] is None and result["copied_bytes"] == 0
    identity.rotate()
    assert (
        identity.copy(identity.identity_id, 1, raw, "DATA", "TARGET")["status"]
        == "AUTHORIZATION_DENIED"
    )
    assert identity.copy(identity.identity_id, 2, raw, "DATA", "TARGET")["output"] == raw
    assert not identity.authorize(identity.identity_id, 2, "DELETE_SOURCE", "DATA")
    assert not identity.authorize(identity.identity_id, 2, "WRITE_ISOLATED_TARGET", "DATA")


@pytest.mark.parametrize(
    "fault",
    [
        "hash",
        "quarter",
        "future",
        "samebranches",
        "identity",
        "order",
        "duplicate",
        "nested",
        "alias",
    ],
)
def test_invalid_source_and_bounds_rejected_before_output(tmp_path, inputs, fault):
    source, recipe = inputs
    target = tmp_path / "out"
    if fault == "hash":
        recipe = replace(recipe, source_versions_sha256="0" * 64)
    elif fault == "quarter":
        recipe = replace(recipe, review_at="2027-06-29T12:00:00Z")
    elif fault == "future":
        recipe = replace(
            recipe,
            period_start="2027-01-01T00:00:00Z",
            rotation_at="2027-02-01T00:00:00Z",
            reconcile_at="2027-02-01T00:01:00Z",
            correction_at="2027-02-01T00:02:00Z",
            review_at="2027-03-31T12:00:00Z",
            period_end_exclusive="2027-04-01T00:00:00Z",
        )
    elif fault == "samebranches":
        recipe = replace(recipe, branch_ids=("same", "same"))
    elif fault == "identity":
        recipe = replace(recipe, identity_id="AS-P007")
    elif fault == "order":
        recipe = replace(recipe, reconcile_at=recipe.rotation_at)
    elif fault == "duplicate":
        recipe = replace(recipe, source_refs=(recipe.source_refs[0],) * 4)
    elif fault == "nested":
        target = source / "out"
    else:
        alias = tmp_path / "alias"
        alias.symlink_to(source)
        source = alias
    with pytest.raises(CompanyStoreError):
        generate_pair(target, repository=ROOT, source_root=source, recipe=recipe)
    assert not target.exists()


def test_historical_job_must_pin_selected_dataset_not_just_matching_labels(tmp_path, inputs):
    source, recipe = inputs
    row = next(
        r
        for r in versions(source)
        if r["branch"] == "backup-messy" and r["system"] == "backup_job" and r["version"] == 1
    )
    refs = tuple(
        NonhumanSourceRef(**{k: row[k] for k in FIELDS}) if ref.system == "backup_job" else ref
        for ref in recipe.source_refs
    )
    _, pin = read_inputs(source, refs)
    with pytest.raises(CompanyStoreError, match="Correlated original dataset"):
        generate_pair(
            tmp_path / "out",
            repository=ROOT,
            source_root=source,
            recipe=replace(recipe, source_refs=refs, source_versions_sha256=pin),
        )
    assert not (tmp_path / "out").exists()


def test_source_privacy_change_before_publish_leaves_no_new_store(tmp_path, inputs, monkeypatch):
    from enterprise.audit_suite import company_nonhuman_identity_activity as module

    source, recipe = inputs
    native = module.read_inputs
    calls = 0

    def changed(root, refs):
        nonlocal calls
        calls += 1
        if calls == 2:
            (source / "company.sqlite3").chmod(0o644)
        return native(root, refs)

    monkeypatch.setattr(module, "read_inputs", changed)
    with pytest.raises(CompanyStoreError):
        module.generate_pair(tmp_path / "out", repository=ROOT, source_root=source, recipe=recipe)
    assert not (tmp_path / "out").exists()
