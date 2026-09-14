"""Organization bridges preserve canon, financial model boundaries and independence."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from enterprise.audit_suite import organization


@pytest.fixture(scope="module")
def current():
    return organization.snapshot()


def test_full_control_and_source_account_coverage(current):
    assert current["validation"]["control_count"] == 166
    assert current["validation"]["resolved_current_proposal_count"] == 166
    assert current["validation"]["financial_account_count"] == 54
    assert current["reconciliation"]["accepted_named_employee_count"] == 44
    assert current["reconciliation"]["accepted_nonemployee_directors"] == 7
    assert len(current["proposed_people"]) == 15
    assert all(
        a["primary_person_id"] and a["reviewer_person_id"] for a in current["control_assignments"]
    )
    assert (
        current["repository_acceptance_status"] == "DELEGATED_IMPLEMENTATION_PENDING_ACCEPTED_MERGE"
    )


def test_snapshot_does_not_change_source_files_or_pinned_assets(current):
    root = Path(organization.ROOT)
    paths = [
        organization.CHART,
        organization.POPULATION,
        "docs/finance/CANON_SOURCE_LOCK.json",
        "docs/organization/assets/current/Sable-Harbor-Organization-Charts.pdf",
    ]
    before = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}
    organization.snapshot()
    assert before == {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}
    assert all(
        hashlib.sha256((root / p).read_bytes()).hexdigest() == value
        for p, value in current["source_sha256"].items()
    )


def test_names_do_not_create_payroll_or_occupied_seats(current):
    r = current["reconciliation"]
    assert r["actual_enterprise_headcount"] is r["actual_2026_payroll_delta_usd"] is None
    assert r["current_seat_occupancy_delta"] is None
    assert r["assigned_new_physical_seats"] == 0
    assert r["j2_authorized_billets"] == 237 and r["j2_incremental_billets"] == 0
    for group in r["forecast_groups"]:
        assert group["occupied_before"] == group["occupied_after"]
        assert group["authorized_before"] == group["authorized_after"]
        assert group["incremental_forecast_fte"] == 0
        assert group["incremental_forecast_payroll_usd"] == "0.00"
    assert all(
        p["workplace_assignment"] is None and p["employment_start"] is None
        for p in current["proposed_people"]
    )


def test_historical_snapshot_never_backdates_new_assignments():
    old = organization.snapshot(as_of="2025-12-31")
    assert old["validation"]["historical_unresolved_count"] == 166
    assert all(a["primary_person_id"] is None for a in old["control_assignments"])


def overlay(**changes):
    value = dict(
        control_id="SH-ENG-002",
        primary_person_id="P005",
        custodian_person_id="P017",
        reviewer_person_id="P006",
        effective_from="2026-01-01",
        effective_to=None,
        rationale="Explicit historical training-role assumption; not a canonical appointment",
    )
    value.update(changes)
    return {"assignments": [value]}


def test_historical_overlay_is_explicit_and_does_not_mutate_canon():
    changes = overlay()
    before = copy.deepcopy(changes)
    value = organization.snapshot(as_of="2026-04-01", scenario_overlay=changes)
    row = next(a for a in value["control_assignments"] if a["control_id"] == "SH-ENG-002")
    assert row["status"] == "SCENARIO_ONLY_ASSIGNMENT" and row["primary_person_id"] == "P005"
    assert value["validation"]["resolved_current_proposal_count"] == 1
    assert changes == before
    assert all(p["effective_from"] is None for p in value["canonical_people"])


@pytest.mark.parametrize(
    "change,error",
    [
        ({"primary_person_id": "AS-P007"}, "Future"),
        ({"primary_person_id": "P008"}, "unavailable"),
        ({"primary_person_id": "P999"}, "Unknown"),
        ({"reviewer_person_id": "P005"}, "Reviewer"),
        ({"reviewer_person_id": "P068"}, "J2"),
        ({"primary_person_id": "P018", "effective_from": "2024-01-01"}, "predates"),
        ({"effective_to": "2025-12-31"}, "interval"),
        ({"rationale": ""}, "rationale"),
    ],
)
def test_invalid_historical_or_independence_overlay(change, error):
    with pytest.raises(ValueError, match=error):
        organization.snapshot(as_of="2026-04-01", scenario_overlay=overlay(**change))


def test_internal_audit_cannot_be_transferred_to_management():
    with pytest.raises(ValueError, match="separate function"):
        organization.snapshot(
            scenario_overlay=overlay(
                control_id="SH-ASS-003",
                effective_from="2026-09-13",
                primary_person_id="AS-P005",
                custodian_person_id="AS-P014",
                reviewer_person_id="P044",
            )
        )


def test_lost_control_and_invented_assertion_are_rejected(current):
    bad = copy.deepcopy(current)
    bad["control_assignments"].pop()
    with pytest.raises(ValueError, match="incomplete"):
        organization.validate(bad)
    bad = copy.deepcopy(current)
    bad["financial_model"]["accounts"][0]["candidate_assertions"] = ["AUTOMATIC_EFFECTIVE"]
    with pytest.raises(ValueError, match="assertion"):
        organization.validate(bad)


def test_financial_model_separates_sources_and_preserves_scoping(current):
    model = current["financial_model"]
    assert model["selected_professional_basis"] is None
    assert model["selected_reporting_basis"] is None
    cash = [a for a in model["accounts"] if a["account_code"] == "1000"]
    assert len(cash) == 2 and len({a["id"] for a in cash}) == 2
    revenue = next(a for a in model["accounts"] if a["account_code"] == "BIZ_REVENUE")
    assert "rights_obligations" not in revenue["candidate_assertions"]
    processes = {p["id"]: p for p in model["processes"]}
    assert all(a["id"] in processes[a["process_id"]]["account_ids"] for a in model["accounts"])
    assert all(not p["deployed_system_ids"] for p in processes.values())
    assert all(p["candidate_control_ids"] for p in processes.values())


def test_management_review_route_is_separate_from_independent_audit(current):
    for assignment in current["control_assignments"]:
        operating = assignment["operating_reviewer_person_id"]
        assert operating != "AS-P009"
        assert operating != assignment["reviewer_person_id"]
        assert operating not in {assignment["primary_person_id"], assignment["custodian_person_id"]}
        assert assignment["reviewer_purpose"] == "INDEPENDENT_ASSURANCE_ONLY"
    bad = copy.deepcopy(current)
    bad["control_assignments"][0]["operating_reviewer_person_id"] = "AS-P009"
    with pytest.raises(ValueError, match="Internal Audit|Assurance reviewer"):
        organization.validate(bad)
    bad["control_assignments"][0]["operating_reviewer_person_id"] = bad["control_assignments"][0][
        "primary_person_id"
    ]
    with pytest.raises(ValueError, match="distinct"):
        organization.validate(bad)


def test_dated_current_source_has_no_duplicate_person_or_backdated_join(current):
    assert current["reconciliation"]["branch_current_named_employees"] == 59
    ids = [p["person_id"] for p in current["canonical_people"] + current["proposed_people"]]
    assert len(ids) == len(set(ids))
    assert all(p["joined_year"] is None for p in current["proposed_people"])


def test_workforce_bridge_reperforms_retained_history_without_incremental_payroll():
    from enterprise.business.identity_bridge import build

    result = build()
    assert result["validation"]["retained_2027_base_rows_matched"] == 7092
    assert result["validation"]["retained_rows"] == 7092
    assert len(result["aliases"]) == 15
    assert {r["period"][:4] for r in result["monthly_reconciliation"]} == {
        "2027",
        "2028",
        "2029",
        "2030",
        "2031",
    }
    assert result["preserved_workforce_events"]
    for row in result["monthly_reconciliation"]:
        assert row["occupied_before"] == row["occupied_after"]
        assert row["authorized_before"] == row["authorized_after"]
        assert (
            row["loaded_cost_before_usd"]
            == row["loaded_cost_after_usd"]
            == row["allocation_total_usd"]
        )
    assert all(
        r["employment_start"] is r["workplace_assignment"] is None
        for r in result["monthly_alias_rows"]
    )


def test_vector_successor_preserves_predecessor_and_j2_cards():
    root = organization.ROOT
    old = json.loads((root / "docs/organization/history/v1.1.0/chartbook.json").read_text())
    current = json.loads((root / organization.CHART).read_text())
    previous = {n["id"]: n for n in old["nodes"]}
    after = {n["id"]: n for n in current["nodes"]}
    assert {key: after[key] for key in previous} == previous
    assert set(after) - set(previous) == {f"AS-P{i:03d}" for i in range(1, 16)}
    for chart in old["charts"]:
        if chart["slug"] != "people-enterprise":
            assert chart == next(c for c in current["charts"] if c["id"] == chart["id"])
    manifest = json.loads((root / "docs/organization/history/v1.1.0/manifest.json").read_text())
    for artifact in manifest["artifacts"]:
        assert (
            hashlib.sha256((root / artifact["preserved_path"]).read_bytes()).hexdigest()
            == artifact["sha256"]
        )
    assert (
        old["visual_master_sha256"]
        == "352dfa4f1247f6089d340b19940f75758a666dce14f239fb38b1c2a300aaa38b"
    )


def test_historical_name_exclusion_requires_exact_preserved_source(tmp_path):
    from scripts.organization_history import ARCHIVED_SOURCES, current_text

    path = "docs/organization/history/v1.1.0/chartbook.json"
    payload = (organization.ROOT / path).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == ARCHIVED_SOURCES[path]
    assert "Leah Moravec" not in current_text(organization.ROOT, path, payload.decode())
    target = tmp_path / path
    target.parent.mkdir(parents=True)
    target.write_bytes(payload + b" ")
    with pytest.raises(ValueError, match="checksum drift"):
        current_text(tmp_path, path, target.read_text())
