import json
from dataclasses import replace

import pytest

from enterprise.audit_suite.company_activity_period import PeriodRecipe, generate_period
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from tests.audit_suite.test_company_activity import ROOT
from tests.audit_suite.test_company_activity import recipe as mover_recipe


def recipe():
    one = replace(
        mover_recipe(),
        event_id="MOVE-Q1",
        effective_at="2027-02-10T09:00:00Z",
        old_right="billing-admin",
        new_right="inventory-admin",
    )
    two = replace(one, event_id="MOVE-Q2", employee_id="P015", effective_at="2027-05-10T09:00:00Z")
    return PeriodRecipe(
        "SH",
        "activity-clean",
        "activity-messy",
        "2027-01-01T00:00:00Z",
        "2027-07-01T00:00:00Z",
        (one, two),
        "P014",
        "Scenario administration rights; no corporate entitlement classification asserted",
    )


def test_period_population_reconciles_real_sources_and_keeps_incomplete_export(tmp_path):
    tmp_path.chmod(0o700)
    store = CompanyStore(tmp_path)
    result = generate_period(store, repository=ROOT, recipe=recipe())
    assert result["quarters"] == 2 and result["source_versions"] == 52
    assert generate_period(store, repository=ROOT, recipe=recipe()) == result
    with store._db() as db:
        all_rows = [dict(r) for r in db.execute("SELECT * FROM versions")]
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
    by_key = {(r["branch"], r["system"], r["record"], r["version"]): r for r in all_rows}
    for quarter, expected in [("PRIV-2027-Q1", 1), ("PRIV-2027-Q2", 2)]:
        clean = json.loads(by_key["activity-clean", "review_population", quarter, 1]["content"])
        messy = json.loads(by_key["activity-messy", "review_population", quarter, 1]["content"])
        assert len(clean["members"]) == expected and len(messy["members"]) == expected - 1
        recon = json.loads(by_key["activity-messy", "review_reconciliation", quarter, 1]["content"])
        assert recon["missing_person_ids"] == ["P014"] and recon["status"] == "REEXPORT_REQUESTED"
        for member in clean["members"]:
            source = by_key["activity-clean", "application", member["record"], member["version"]]
            assert source["sha256"] == member["sha256"]
            assert source["available_at"] < clean["query"]["as_of_exclusive"]
        assert (
            by_key["activity-clean", "review_population", quarter, 1]["available_at"]
            > clean["period_end_exclusive"]
        )
    # Later quarter retains the prior employee, not merely this quarter's mover events.
    q2 = json.loads(by_key["activity-clean", "review_population", "PRIV-2027-Q2", 1]["content"])
    assert {m["person_id"] for m in q2["members"]} == {"P014", "P015"}
    assert any("Retention" in gap for gap in result["gaps"])


@pytest.mark.parametrize(
    "fault", ["bad_later_employee", "duplicate_person", "partial_quarter", "missing_target"]
)
def test_entire_period_plan_validated_before_target_mutation(tmp_path, fault):
    tmp_path.chmod(0o700)
    store = CompanyStore(tmp_path)
    r = recipe()
    if fault == "bad_later_employee":
        r = replace(r, movers=(r.movers[0], replace(r.movers[1], employee_id="UNKNOWN")))
    elif fault == "duplicate_person":
        r = replace(r, movers=(r.movers[0], replace(r.movers[1], employee_id="P014")))
    elif fault == "partial_quarter":
        r = replace(r, period_start="2027-01-02T00:00:00Z")
    else:
        r = replace(r, omitted_population_employee="UNKNOWN")
    with pytest.raises(CompanyStoreError):
        generate_period(store, repository=ROOT, recipe=r)
    with store._db() as db:
        assert db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM systems").fetchone()[0] == 0
