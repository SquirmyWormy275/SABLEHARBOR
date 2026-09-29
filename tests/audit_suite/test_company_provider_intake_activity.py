import json
from dataclasses import replace
from pathlib import Path

import pytest

from enterprise.audit_suite.company_provider_intake_activity import (
    REQUIREMENTS,
    SITES_PATH,
    ProviderIntakeRecipe,
    generate_pair,
    import_inventory,
    reconcile,
    tier,
)
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import sha

ROOT = Path(__file__).resolve().parents[2]


def recipe():
    return ProviderIntakeRecipe(
        "SABLEHARBOR",
        "provider-complete",
        "provider-omission",
        "LOCAL-2027-Q1",
        sha((ROOT / SITES_PATH).read_bytes()),
        "2027-01-01T00:00:00Z",
        "2027-03-31T00:00:00Z",
        "2027-04-05T00:00:00Z",
        "Local provisional quarterly review; not accepted corporate cadence",
    )


def records(store):
    with store._db() as db:
        return {
            (r["branch"], r["system"], r["record"], r["version"]): json.loads(r["content"])
            for r in db.execute("SELECT * FROM versions")
        }


def test_paired_omission_backfill_preserves_source_states_and_absent_support(tmp_path):
    tmp_path.chmod(0o700)
    before = (ROOT / SITES_PATH).read_bytes()
    result = generate_pair(tmp_path / "company", repository=ROOT, recipe=recipe())
    store = CompanyStore(tmp_path / "company")
    data = records(store)
    assert {a["primary_person_id"] for a in result["assignments"]} == {"AS-P013"}
    assert {a["operating_reviewer_person_id"] for a in result["assignments"]} == {"AS-P002"}
    assert (
        data["provider-complete", "planned_dependency_inventory", "DEPENDENCIES", 1]
        == data["provider-omission", "planned_dependency_inventory", "DEPENDENCIES", 1]
    )
    a = data["provider-complete", "coverage_reconciliation", "COVERAGE-INITIAL", 1]
    b = data["provider-omission", "coverage_reconciliation", "COVERAGE-INITIAL", 1]
    assert a["missing_provider_ids"] == [] and b["missing_provider_ids"] == ["CP-IDACORE"]
    assert b["missing_due_review_provider_ids"] == ["CP-IDACORE"]
    assert len(b["missing_diligence_work_items"]) == len(REQUIREMENTS) == 4
    later = data["provider-omission", "coverage_reconciliation", "COVERAGE-BACKFILL", 1]
    assert (
        later["missing_provider_ids"] == [] and later["third_party_evidence_gaps_closed"] is False
    )
    assert later["diligence_support_obtained"] == 0
    assert (
        data["provider-omission", "review_schedule", "CP-IDACORE-REVIEW-DUE", 1]["schedule_status"]
        == "OVERDUE_AT_REGISTRATION"
    )
    review = data["provider-omission", "monitoring_reviews", "CP-IDACORE-REVIEW", 1]
    assert (
        review["late_seconds"] > 0 and review["performance_data"] == "NOT_APPLICABLE_NOT_OPERATING"
    )
    for (_branch, system, _record, _version), value in data.items():
        if system == "vendor_register":
            p = value["provider"]
            assert (
                p["contract_status"] == "DRAFT"
                and not p["contract_executed"]
                and not p["operating"]
            )
            assert p["provider_legal_name"] is None
            if p["provider_id"] == "CP-IDACORE":
                assert p["independence_verified"] is False and p["independence_evidence"] == []
        if system == "diligence_work_items":
            assert (
                value["support_status"] == "NOT_OBTAINED"
                and value["external_request_status"] == "NOT_SENT_LOCAL_WORK_ITEM_ONLY"
            )
            assert (
                value["received_document_sha256"] is None
                and value["report_scope"] is None
                and value["report_period"] is None
            )
    with store._db() as db:
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
    assert before == (ROOT / SITES_PATH).read_bytes()
    with pytest.raises(CompanyStoreError):
        generate_pair(tmp_path / "company", repository=ROOT, recipe=recipe())


@pytest.mark.parametrize("mutation", ["pin", "dates", "branches"])
def test_invalid_recipe_never_publishes(tmp_path, mutation):
    tmp_path.chmod(0o700)
    r = recipe()
    if mutation == "pin":
        r = replace(r, source_sites_sha256="0" * 64)
    elif mutation == "dates":
        r = replace(r, review_due_at=r.start_at)
    else:
        r = replace(r, omission_branch=r.complete_branch)
    with pytest.raises(CompanyStoreError):
        generate_pair(tmp_path / "bad", repository=ROOT, recipe=r)
    assert not (tmp_path / "bad").exists()


def test_actual_filter_and_duplicate_queue_detection():
    dependencies = [
        {
            "provider_id": "P",
            "planned_dependency_role": "PRIMARY",
            "dependency_id": "D1",
            "operating": False,
        },
        {
            "provider_id": "R",
            "planned_dependency_role": "RECOVERY",
            "dependency_id": "D2",
            "operating": False,
        },
    ]
    assert [
        r["provider_id"] for r in import_inventory(dependencies, included_roles=["PRIMARY"])
    ] == ["P"]
    assert tier(dependencies[1])["accepted_enterprise_tier"] is False
    with pytest.raises(CompanyStoreError):
        import_inventory(dependencies, included_roles=["PRIMARY", "PRIMARY"])
    work = [{"provider_id": "P", "requirement_id": REQUIREMENTS[0]}] * 2
    with pytest.raises(CompanyStoreError, match="Duplicate diligence"):
        reconcile(dependencies, dependencies, work, [])
