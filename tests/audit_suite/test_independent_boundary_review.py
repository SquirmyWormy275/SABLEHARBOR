"""Neutral independent regressions for source, temporal and recovery boundaries."""

from types import SimpleNamespace

import pytest

from enterprise.audit_suite import evidence_transform, private_review_export, recovery
from enterprise.audit_suite.artifacts import Artifacts
from enterprise.audit_suite.generation import private_json, run_directory
from enterprise.audit_suite.store import DomainError, Store
from enterprise.audit_suite.temporal_workflow import current


def test_date_only_temporal_scope_uses_declared_timezone():
    state = {
        "scope": {
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "timezone": "America/Denver",
            "boundaries": ["neutral-unit"],
        },
        "controls": [{"id": "C1", "owner_ids": ["P1"], "implementation_version": "v1"}],
    }
    from datetime import datetime

    effective = current(state)["versions"][0]["effective"]
    assert datetime.fromisoformat(effective["start"]).timestamp() == datetime.fromisoformat(
        "2027-01-01T07:00:00+00:00"
    ).timestamp()
    assert datetime.fromisoformat(effective["end"]).timestamp() == datetime.fromisoformat(
        "2028-01-01T07:00:00+00:00"
    ).timestamp()


@pytest.mark.parametrize("other", ["Approved by NeutralReviewer", {"actor": "NeutralReviewer"}])
def test_project_rejects_removed_native_value_embedded_in_other_fields(other):
    source = {
        "recipe": {
            "format": "json",
            "title": "Neutral decision",
            "columns": ["id", "reviewer", "comment"],
            "rows": [{"id": "R1", "reviewer": "NeutralReviewer", "comment": other}],
        }
    }
    contract = {
        "kind": "REDACT_FIELDS",
        "recovery_route": "ACTUAL_SOURCE_RELEASE",
        "runtime_binding": {"target_fields": ["reviewer"]},
    }
    with pytest.raises(DomainError, match="leak"):
        evidence_transform.project(source, contract)


def test_private_reviewer_export_rejects_changed_frozen_plan(tmp_path):
    store = Store(tmp_path)
    actor = store.provision("Neutral instructor", ["instructor"])
    state = store.create(actor["id"], {"title": "Review", "scope": {}, "artifacts": []}, "new")
    engine = SimpleNamespace(store=store, artifacts=Artifacts(tmp_path))
    directory = run_directory(engine, state["id"])
    private_json(
        directory / "unit-00000.json",
        {
            "plan_integrity_version": 1,
            "plan_sha256": "0" * 64,
            "requests": [{"title": "Changed source after freeze"}],
        },
    )
    with pytest.raises(DomainError):
        private_review_export.build(engine, state, actor["id"])


def test_backup_rejects_replay_hash_not_matching_immutable_command(tmp_path):
    tmp_path.chmod(0o700)
    store = Store(tmp_path / "state")
    actor = store.provision("Neutral instructor", ["instructor"])
    store.create(actor["id"], {"title": "Recovery", "artifacts": []}, "new")
    # Model an inconsistent imported/corrupted SQLite checkpoint. Application
    # commands cannot perform this mutation; recovery must detect it independently.
    with store.connect() as db:
        db.execute("DROP TRIGGER events_no_update")
        db.execute("UPDATE events SET request_hash=?", ("0" * 64,))
    with pytest.raises(DomainError, match="integrity"):
        recovery.backup(store, tmp_path / "backup")


def test_private_export_rejects_run_directory_alias_to_another_engagement(tmp_path):
    store = Store(tmp_path)
    actor = store.provision("Scoped reviewer", ["reviewer"])
    owner = store.provision("Owner", ["instructor"])
    first = store.create(owner["id"], {"title": "First", "scope": {}, "artifacts": []}, "one")
    other = store.create(owner["id"], {"title": "Other", "scope": {}, "artifacts": []}, "two")
    store.grant(first["id"], actor["id"], "review")
    engine = SimpleNamespace(store=store, artifacts=Artifacts(tmp_path))
    other_dir = run_directory(engine, other["id"])
    private_json(other_dir / "world.json", {"private_answer": "OTHER_ENGAGEMENT_ONLY"})
    (tmp_path / "worlds" / first["id"]).symlink_to(other_dir, target_is_directory=True)
    with pytest.raises(DomainError):
        private_review_export.build(engine, first, actor["id"])


def test_draft_substitution_requires_actual_draft_condition():
    original = {
        "source_identity": "CURRENT",
        "recipe": {
            "format": "json",
            "title": "Approved record",
            "columns": ["id", "approval_state"],
            "rows": [{"id": "R1", "approval_state": "APPROVED"}],
        },
    }
    alternate = {
        **original,
        "source_identity": "OTHER_APPROVED_COPY",
    }
    contract = {
        "kind": "SUBSTITUTE_DRAFT",
        "recovery_route": "ACTUAL_SOURCE_RELEASE",
        "runtime_binding": {
            "required_fields": ["approval_state"],
            "alternate_source_role": "draft",
            "alternate_required_values": {"approval_state": "DRAFT"},
        },
    }
    with pytest.raises(DomainError):
        evidence_transform.project(original, contract, alternates={"draft": alternate})


def test_recovery_preserves_company_source_integrity_sidecar(tmp_path):
    tmp_path.chmod(0o700)
    store = Store(tmp_path / "state")
    actor = store.provision("Neutral instructor", ["instructor"])
    state = store.create(actor["id"], {"title": "Sources", "artifacts": []}, "new")
    folder = store.root / "worlds" / state["id"] / "parent-support"
    folder.mkdir(parents=True, mode=0o700)
    source = b'{"source_id":"neutral-frozen-source"}'
    import hashlib

    (folder / "source.json").write_bytes(source)
    (folder / "source.json").chmod(0o600)
    lock = (hashlib.sha256(source).hexdigest() + "\n").encode()
    (folder / "source.sha256").write_bytes(lock)
    (folder / "source.sha256").chmod(0o600)
    recovery.backup(store, tmp_path / "backup")
    recovery.restore(tmp_path / "backup", tmp_path / "restored")
    relative = folder.relative_to(store.root) / "source.sha256"
    assert (tmp_path / "restored" / relative).read_bytes() == lock


def test_redaction_does_not_compare_python_repr_of_embedded_native_values():
    secret = "Neutral\nReviewer"
    source = {
        "recipe": {
            "format": "json",
            "title": "Neutral record",
            "columns": ["reviewer", "comment"],
            "rows": [{"reviewer": secret, "comment": "Signed by " + secret}],
        }
    }
    contract = {
        "kind": "REDACT_FIELDS",
        "recovery_route": "ACTUAL_SOURCE_RELEASE",
        "runtime_binding": {"target_fields": ["reviewer"]},
    }
    with pytest.raises(DomainError, match="leak"):
        evidence_transform.project(source, contract)


def test_portable_demonstration_cannot_release_before_its_actual_source_date():
    from enterprise.audit_suite.portable_composition import compose

    source = {
        "name": "historical.csv",
        "available_by": "2027-12-31",
        "recipe": {
            "format": "csv",
            "title": "Historical record",
            "columns": ["id"],
            "rows": [{"id": "HISTORICAL"}],
        },
    }
    demo = {
        "name": "current-demo.csv",
        "source_role": "demo",
        "artifact_kind": "CURRENT_ACTION_DEMONSTRATION",
        "available_by": "2028-06-01",
        "recipe": {
            "format": "csv",
            "title": "Current demonstration",
            "columns": ["id", "performed_at"],
            "rows": [{"id": "DEMO", "performed_at": "2028-06-01"}],
        },
    }
    contract = {
        "kind": "DEMONSTRATE_ONLY",
        "recovery_route": "SUPPORTED_LIMITATION",
        "delay_business_days": 1,
        "initial_response": "Demonstration source offered.",
        "followup_response": "Historical operation still requires its own source.",
        "runtime_binding": {"alternate_source_role": "demo"},
    }
    try:
        plan = compose(
            {"requests": [{"id": "R1", "artifact_recipes": [source, demo]}]},
            {"definition": {"id": "NEUTRAL", "binding_contract": {
                "portable_evidence_transform": contract,
            }}},
            {"id": "C1", "assignment": {
                "primary_person_id": "P1", "custodian_person_id": "P2",
            }},
            {"boundary_id": "unit", "period_start": "2027-01-01", "period_end": "2027-12-31"},
            {"P1": "Neutral owner", "P2": "Neutral custodian"},
        )
    except DomainError:
        return  # A future/out-of-scope demonstration may instead fail closed.
    transformed = next(
        row for row in plan["requests"][0]["artifact_recipes"]
        if row["name"].startswith("initial-")
    )
    assert transformed["available_by"] >= demo["available_by"]
