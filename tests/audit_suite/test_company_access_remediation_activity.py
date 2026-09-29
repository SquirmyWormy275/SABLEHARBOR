# Fixture imported for pytest discovery.
# ruff: noqa: F811
import json
import sqlite3
from dataclasses import replace

import pytest

from enterprise.audit_suite.company_access_remediation_activity import (
    AccessRemediationRecipe,
    AccessRemediationSourceRef,
    CompanyStoreError,
    LocalEntitlements,
    generate_pair,
)
from tests.audit_suite.test_company_access_remediation_operator import ROOT, prepared  # noqa: F401


def typed(value):
    return AccessRemediationRecipe(
        **{
            **value,
            "branch_ids": tuple(value["branch_ids"]),
            "source_refs": tuple(AccessRemediationSourceRef(**r) for r in value["source_refs"]),
        }
    )


def test_actual_state_drives_distinct_probes_and_preserves_originals(tmp_path, prepared):
    source, value = prepared
    original = (source / "company/company.sqlite3").read_bytes()
    out = tmp_path / "continuation"
    receipt = generate_pair(
        out, repository=ROOT, source_root=source / "company", recipe=typed(value)
    )
    assert len(receipt["records"]) == 22
    assert (source / "company/company.sqlite3").read_bytes() == original
    with sqlite3.connect(out / "company.sqlite3") as db:

        def body(branch, system, record, version):
            return json.loads(
                db.execute(
                    "SELECT content FROM versions WHERE branch=? AND system=? "
                    "AND record=? AND version=?",
                    (branch, system, record, version),
                ).fetchone()[0]
            )

        for branch, excess in [("removal-a", []), ("removal-b", ["billing-admin"])]:
            initial = body(branch, "validation_probes", "VALIDATION", 1)
            assert initial["excess_rights"] == excess
            assert initial["removed_permission_probes"]["billing-admin"] == (
                "ALLOW" if excess else "DENY"
            )
            assert initial["recorded_unresolved_population_ids"] == ["P014"]
            assert initial["independent_assurance"] == "NOT_PERFORMED"
            assert body(branch, "validation_probes", "VALIDATION", 2)["excess_rights"] == []
        assert body("removal-b", "execution_attempts", "EXECUTION", 1)[
            "unresolved_permissions"
        ] == ["billing-admin"]
        assert body("removal-b", "entitlement_state", "APPLICATION", 2)["rights"] == [
            "billing-admin",
            "inventory-admin",
        ]
        assert body("removal-b", "entitlement_state", "APPLICATION", 3)["rights"] == [
            "inventory-admin"
        ]
        for table in ("grants", "collections", "access_events"):
            assert db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
    with pytest.raises(CompanyStoreError):
        generate_pair(out, repository=ROOT, source_root=source / "company", recipe=typed(value))


@pytest.mark.parametrize(
    "actor,subject,requested,mapping",
    [
        ("other", "person", ["old"], {"old": "old"}),
        ("owner", "other", ["old"], {"old": "old"}),
        ("owner", "person", ["current"], {"current": "current"}),
        ("owner", "person", ["old"], {"old": "current"}),
    ],
)
def test_execution_cannot_broaden_owner_decision(actor, subject, requested, mapping):
    state = LocalEntitlements("person", "owner", "reviewer", ["old", "current"], ["old"])
    with pytest.raises(CompanyStoreError):
        state.execute(actor, subject, requested, mapping)
    assert state.rights == {"old", "current"}
    with pytest.raises(CompanyStoreError):
        state.verify("owner", ["current"])


def test_failed_mapping_does_not_remove_permission_and_repeat_is_idempotent():
    state = LocalEntitlements("person", "owner", "reviewer", ["old", "current"], ["old"])
    assert state.execute("owner", "person", ["old"], {})["removed_rights"] == []
    assert state.verify("reviewer", ["current"])["removed_permission_probes"] == {"old": "ALLOW"}
    assert state.execute("owner", "person", ["old"], {"old": "old"})["removed_rights"] == ["old"]
    assert state.execute("owner", "person", ["old"], {"old": "old"})["removed_rights"] == []
    assert state.verify("reviewer", ["current"])["removed_permission_probes"] == {"old": "DENY"}


@pytest.mark.parametrize(
    "change",
    [
        {"source_versions_sha256": "0" * 64},
        {"subject_person_id": "P014"},
        {"branch_ids": ("activity-messy", "other")},
        {"execute_at": "2027-07-01T09:00:00Z"},
    ],
)
def test_invalid_binding_or_chronology_publishes_nothing(tmp_path, prepared, change):
    source, value = prepared
    out = tmp_path / "invalid"
    with pytest.raises(CompanyStoreError):
        generate_pair(
            out,
            repository=ROOT,
            source_root=source / "company",
            recipe=replace(typed(value), **change),
        )
    assert not out.exists()
