"""Behavioral contracts for current business economics and institutional boundaries."""

import copy
import json
from collections import defaultdict
from decimal import Decimal as D

import pytest

from enterprise.business import advisory, boundaries, validation
from enterprise.business.model import BusinessModel, check_inputs, fingerprint, load_inputs


@pytest.fixture(scope="module")
def model():
    return BusinessModel().build()


@pytest.mark.parametrize(
    ("achievement", "payout"),
    [("0.49", "0"), ("0.50", "0.25"), ("0.625", "0.425"), ("1", "1"), ("2", "1.5")],
)
def test_value_curve_is_contractual_and_capped(achievement, payout):
    assert advisory.payout_factor(achievement, load_inputs()["policy"]["value_payout_curve"]) == D(
        payout
    )


@pytest.mark.parametrize("role", ["acceptance_principal", "independent_reviewer", "value_officer"])
def test_originator_cannot_self_accept_review_or_certify(role):
    e = copy.deepcopy(load_inputs()["engagements"][0])
    e["roles"][role] = e["roles"]["originator"]
    with pytest.raises(ValueError):
        advisory.check_matter(e)


def test_decision_matters_are_fixed_and_atlas_fee_is_separate():
    e = copy.deepcopy(load_inputs()["engagements"][0])
    e["matter_class"] = "DECISION"
    with pytest.raises(ValueError, match="contingent"):
        advisory.check_matter(e)
    e["committed_fraction"] = "1"
    e["atlas_fee_included"] = True
    with pytest.raises(ValueError, match="separate"):
        advisory.check_matter(e)


def test_client_transfer_cannot_export_professional_plane():
    transfer = copy.deepcopy(load_inputs()["engagements"][0]["transfer"])
    transfer["components"][0]["plane"] = "professional"
    with pytest.raises(ValueError, match="cannot transfer"):
        advisory.check_transfer(transfer)


def test_source_lineage_accounting_and_staff_reconcile(model):
    checks = validation.business(model)
    assert checks["source_events"] > 10000
    assert len(model.roster) == 591
    assert sum(r["occupied"] for r in model.roster) == 506
    advisory_staff = [r for r in model.tables["workforce_assignments"] if r["unit"] == "advisory"]
    assert {r["home_group"] for r in advisory_staff} == {"advisory", "willow"}
    capacity = [r for r in model.tables["capacity"] if r["unit"] == "advisory"]
    assert len(capacity) == 180
    assert all(D(r["capacity_hours"]) == D("2953.6") for r in capacity)


def test_declined_matters_generate_no_work_or_revenue(model):
    declined = {
        e["engagement_id"]
        for e in model.inputs["engagements"]
        if e.get("acceptance_status") == "DECLINE"
    }
    assert len(declined) == 5
    for event in model.tables["events"]:
        if event["kind"] in {"DELIVERY_WORK", "VALUE_CERTIFIED", "OUTCOME_ACCEPTED"}:
            assert event.get("engagement_id", event["source_id"]) not in declined
    for invoice in model.tables["invoices"]:
        assert not any(eid in invoice["source_id"] for eid in declined)


def test_baseline_approved_before_delivery_is_reused_for_certification(model):
    approved = {
        (r["scenario"], r["source_id"]): r
        for r in model.tables["events"]
        if r["kind"] == "VALUE_BASELINE_APPROVED"
    }
    for r in model.tables["value_certifications"]:
        first = approved[r["scenario"], r["engagement_id"]]
        assert first["baseline_sha256"] == r["baseline_sha256"]
        assert first["period"] < r["period"]
        if r["matter_class"] == "DECISION":
            assert D(r["variable_fee_usd"]) == 0
        if r["scenario"] == "downside" and r["matter_class"] == "MEASURABLE_VALUE":
            assert D(r["variable_fee_usd"]) == 0


def test_acceptance_delays_revenue_but_does_not_multiply_committed_fee(model):
    first = "ADV-2027-01"
    earned = defaultdict(D)
    dates = {}
    for e in model.tables["events"]:
        if e["kind"] == "OUTCOME_ACCEPTED" and e.get("engagement_id") == first:
            earned[e["scenario"]] += D(e["committed_recognition_usd"])
            dates.setdefault(e["scenario"], []).append(e["period"])
    assert earned["base"] == D("288000")
    assert earned["downside"] == D("259200")  # Explicit 90% scenario price; no time/rework billing.
    assert min(dates["downside"]) > min(dates["base"])
    first_roll = next(
        r
        for r in model.tables["subledger_rollforward"]
        if r["scenario"] == "base" and r["unit"] == "advisory"
    )
    assert D(first_roll["deferred_revenue_usd"]) > 0


def test_recovery_mass_and_acceptance_boundaries(model):
    runs = [r for r in model.tables["events"] if r["kind"] == "RECOVERY_RUN"]
    for r in runs:
        assert 0 <= D(r["recovered_kg"]) <= D(r["contained_kg"])
        if r["bypass"]:
            assert D(r["recovered_kg"]) == 0
    assert any(r["bypass"] for r in runs)
    for lot in model.tables["recovery_lots"]:
        assert lot["accept_month"] > lot["capture_month"]
        acceptance = [
            e
            for e in model.tables["events"]
            if e["kind"] == "DOWNSTREAM_ACCEPTANCE"
            and e["scenario"] == lot["scenario"]
            and e["source_id"] == lot["lot_id"]
        ]
        if acceptance:
            assert acceptance[0]["month_index"] == lot["accept_month"]
    for r in model.tables["events"]:
        if r["kind"] == "HOST_SETTLEMENT_REQUEST":
            collection = next(
                e
                for e in model.tables["events"]
                if e["scenario"] == r["scenario"]
                and e["kind"] == "COLLECTION"
                and e["source_id"] == r["source_id"]
            )
            assert r["month_index"] > collection["month_index"]


def test_transfer_preserves_basis_and_creates_no_income(model):
    events = {
        e["event_id"] for e in model.tables["events"] if e["kind"] == "QUALIFIED_ASSET_TRANSFER"
    }
    assert events
    rows = [r for r in model.tables["journal"] if r["source_id"] in events]
    assert all(r["account_type"] not in {"revenue", "expense"} for r in rows)
    assert not validation.total(rows, ["scenario", "source_id", "account"])


def test_input_identity_changes_without_rewriting_original():
    source = load_inputs()
    old = fingerprint(source)
    changed = copy.deepcopy(source)
    changed["contracts"][0]["monthly_subscription_usd"] += 1
    assert fingerprint(changed) != old and fingerprint(source) == old


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(
            principal_tenant="A",
            source_tenant="B",
            plane="client",
            source_right=True,
            purpose_right=True,
        ),
        dict(
            principal_tenant="A",
            source_tenant="A",
            plane="professional",
            source_right=True,
            purpose_right=True,
        ),
        dict(
            principal_tenant="A",
            source_tenant="A",
            plane="client",
            source_right=True,
            purpose_right=False,
        ),
    ],
)
def test_cross_tenant_or_ungranted_material_is_denied(kwargs):
    assert not boundaries.source_access(**kwargs)


def test_hiring_carry_and_orientation_have_separate_gates():
    assert boundaries.advisory_application(serving_j2=True) == "DENIED_SERVING_J2"
    assert (
        boundaries.advisory_application(
            serving_j2=False,
            service_end="2026-01-01",
            application_date="2026-01-02",
            initiated_by_person=True,
        )
        == "PERMITTED_POST_SERVICE_APPLICATION"
    )
    assert (
        boundaries.carry_eligibility(
            profession="judgment", judgment_years=5, operating_line_years=0
        )
        == "INELIGIBLE_SERVICE_GATE"
    )
    assert (
        boundaries.carry_eligibility(
            profession="orientation", full_orientation_tour=True, qualifying_fellowship=True
        )
        == "ELIGIBLE_NO_ALLOCATION"
    )
    assert boundaries.carry_eligibility(profession="education") == "OPEN_GATE_NOT_INFERRED"
    assert not boundaries.orientation_role(former_orientation=True, has_line_authority=True)


def test_manifest_rejects_tampering_and_unmanifested_files(tmp_path):
    from enterprise.business.exports import file_hash

    data = tmp_path / "data.txt"
    data.write_text("evidence")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"artifacts": {"data.txt": file_hash(data)}}))
    (tmp_path / "SHA256SUMS.txt").write_text(
        f"{file_hash(data)}  data.txt\n{file_hash(manifest)}  manifest.json\n"
    )
    validation.verify_files(tmp_path)
    data.write_text("tampered")
    with pytest.raises(ValueError, match="hash mismatch"):
        validation.verify_files(tmp_path)
    data.write_text("evidence")
    (tmp_path / "unexpected.txt").write_text("extra")
    with pytest.raises(ValueError, match="unmanifested"):
        validation.verify_files(tmp_path)


def test_finite_treasury_does_not_hide_unfunded_equipment_or_reclassify_it_as_operating():
    from industrial.planning.enterprise import Books, member_funding

    policy = json.loads(
        __import__("pathlib").Path("industrial/planning/source/enterprise.json").read_text()
    )
    policy["scenarios"]["downside"]["member_equity_annual_limit_usd"] = 0
    policy["core"]["minimum_cash_usd"] = 0
    policy["core"]["payment_deferral_accounts"] = {
        "OPERATING": "CORE_UNPAID",
        "INVESTING": "BIZ_CAPITAL_UNPAID",
        "FINANCING": "BIZ_DEBT_UNPAID",
    }
    types = {
        "1000": "asset",
        "3000": "equity",
        "BIZ_PPE": "asset",
        "BIZ_PAYROLL": "expense",
        "CORE_UNPAID": "liability",
        "BIZ_CAPITAL_UNPAID": "liability",
        "BIZ_DEBT_UNPAID": "liability",
    }
    books = Books("downside", policy, types)
    books.post(
        "SHI",
        2027,
        1,
        [("BIZ_PPE", 100), ("1000", -100, "INVESTING")],
        "equipment",
        "received equipment",
        kind="BUSINESS_DRIVEN_FORECAST",
    )
    funding = []
    used = {"core": D(0), "subsidiary": D(0)}
    member_funding(books, 2027, 1, D(0), used, D(0), funding)
    assert books.balances["SHI"]["1000"] == 0
    assert books.balances["SHI"]["BIZ_CAPITAL_UNPAID"] == -100
    assert books.balances["SHI"]["CORE_UNPAID"] == 0
    assert funding[0]["feasibility"] == "FUNDING_GAP"
    assert all(r["cash_flow"] == "INVESTING" for r in books.rows if r["account"] == "1000")
    books.post(
        "SHI",
        2027,
        2,
        [("1000", 100, "FINANCING"), ("3000", -100)],
        "new-cash",
        "explicit additional cash",
    )
    member_funding(books, 2027, 2, D(0), used, D(0), funding)
    assert books.balances["SHI"]["BIZ_CAPITAL_UNPAID"] == 0
    assert funding[-1]["arrears_paid_usd"] == "100.0000"
    assert books.rows[-1]["cash_flow"] == "INVESTING"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("scenario", "other", "scenario"),
        ("unit", "willow", "unit scope"),
        ("unexpected_secret", "value", "column"),
    ],
)
def test_export_rejects_unexpected_scope_or_schema(field, value, message):
    from pathlib import Path
    from enterprise.business.exports import validate_population

    schema = json.loads(Path("enterprise/business/export_schema.json").read_text())["foundry-field"]
    tables = {k: [] for k in schema}
    row = {"scenario": "base", "unit": "foundry-field"}
    row[field] = value
    tables["journal"] = [row]
    with pytest.raises(ValueError, match=message):
        validate_population(tables, "foundry-field", {"scenarios": ["base"], "run_id": "test"})


@pytest.mark.parametrize(
    ("key", "value"), [("price_factor", "-1"), ("mineral_recovery", "1.01"), ("churn_modulus", 0)]
)
def test_invalid_scenario_drivers_are_rejected(key, value):
    source = load_inputs()
    source["policy"]["cases"]["base"][key] = value
    with pytest.raises(ValueError):
        check_inputs(source)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [("entity", "OTHER", "legal entity"), ("segment", "OTHER", "reporting segment")],
)
def test_export_rejects_unexpected_legal_or_segment_scope(field, value, message):
    from pathlib import Path
    from enterprise.business.exports import validate_population

    schema = json.loads(Path("enterprise/business/export_schema.json").read_text())["foundry-field"]
    tables = {k: [] for k in schema}
    tables["journal"] = [{"unit": "foundry-field", field: value}]
    with pytest.raises(ValueError, match=message):
        validate_population(tables, "foundry-field", {"scenarios": ["base"]})


def test_export_rejects_unregistered_business_site():
    from pathlib import Path
    from enterprise.business.exports import validate_population

    schema = json.loads(Path("enterprise/business/export_schema.json").read_text())[
        "project-cradle"
    ]
    tables = {k: [] for k in schema}
    tables["events"] = [{"unit": "project-cradle", "site": "OTHER"}]
    with pytest.raises(ValueError, match="business site"):
        validate_population(tables, "project-cradle", {"scenarios": ["base"]})


def test_matter_does_not_grant_an_atlas_license():
    transfer = copy.deepcopy(load_inputs()["engagements"][0]["transfer"])
    assert all(c["classification"] == "CLIENT_OWNED" for c in transfer["components"])
    transfer["components"].append(
        {"id": "atlas-runtime", "plane": "client", "classification": "LICENSED_PRODUCT"}
    )
    with pytest.raises(ValueError, match="contract-rights"):
        advisory.check_transfer(transfer)
    with pytest.raises(ValueError, match="contract-rights"):
        advisory.check_transfer(transfer, license_validator=lambda c: False)
    advisory.check_transfer(transfer, license_validator=lambda c: c["id"] == "atlas-runtime")
