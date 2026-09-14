import pytest

from enterprise.audit_suite.scope import control_projection, validate_scope
from enterprise.audit_suite.store import DomainError


def scope(**changes):
    return {
        "programs": ["SOC2", "HIPAA"],
        "report_type": "Type 2",
        "period_start": "2027-01-01",
        "period_end": "2027-12-31",
        "boundaries": ["corporate"],
        **changes,
    }


def test_soc1_requires_financial_reporting_service_and_risk_selected_controls():
    chosen = scope(programs=["SOC1"])
    with pytest.raises(DomainError, match="service description"):
        validate_scope(chosen, "IT")
    chosen.update(
        service_description="Payroll processing service",
        user_entity_financial_reporting="Payroll expense and accrued liabilities",
        service_control_objectives=["Authorized payroll inputs are processed accurately."],
    )
    with pytest.raises(DomainError, match="Select the controls"):
        validate_scope(chosen, "IT")
    chosen["control_ids"] = ["SH-PAY-002"]
    normalized = validate_scope(chosen, "IT")
    controls = control_projection(normalized)
    assert [c["id"] for c in controls] == ["SH-PAY-002"]
    assert controls[0]["service_control_objectives"] == chosen["service_control_objectives"]
    assert controls[0]["requirement_links"] == []


def test_c5_type1_is_a_date_but_iso_does_not_inherit_soc_terminology():
    chosen = scope(
        programs=["C5"], report_type="Type 1", period_end="2027-01-01", c5_early_adoption=True
    )
    assert validate_scope(chosen, "IT")["temporal_basis"] == "POINT_IN_TIME"
    with pytest.raises(DomainError, match="SOC or C5"):
        validate_scope({**chosen, "programs": ["ISO27001"]}, "IT")


def test_c5_transition_does_not_mix_criteria_editions():
    with pytest.raises(DomainError, match="crosses the C5 transition"):
        validate_scope(scope(programs=["C5"], c5_early_adoption=True), "IT")
    valid = validate_scope(scope(programs=["C5"], period_start="2027-06-01"), "IT")
    assert valid["program_versions"]["C5"].startswith("2026")
    with pytest.raises(DomainError, match="early adoption"):
        validate_scope(scope(programs=["C5"], period_end="2027-05-31"), "IT")


def test_financial_accounts_preserve_model_identity_and_explicit_jurisdiction():
    chosen = scope(
        programs=["FINANCIAL"],
        report_type="Financial statement audit",
        reporting_basis="US GAAP",
        materiality_rationale="Exercise-specific planning judgment",
        financial_audit_jurisdiction="United States nonissuer, selected AU-C methodology",
        accounts=[
            {
                "id": "enterprise_successor:1000",
                "name": "Cash",
                "assertions": ["existence_occurrence", "completeness"],
                "risk_rationale": "Unrecorded accounts or unsupported cash balances",
                "planned_procedures": "Reconcile the ledger and inspect bank confirmation support.",
            }
        ],
    )
    assert validate_scope(chosen, "FINANCIAL")["accounts"][0]["id"] == "enterprise_successor:1000"
    with pytest.raises(DomainError, match="Financial track"):
        validate_scope(chosen, "IT")
    with pytest.raises(DomainError, match="jurisdiction"):
        validate_scope({**chosen, "financial_audit_jurisdiction": ""}, "FINANCIAL")
    chosen["accounts"][0]["id"] = "1000"
    with pytest.raises(DomainError, match="source model"):
        validate_scope(chosen, "FINANCIAL")


def test_ism_scope_keeps_requirement_work_distinct_from_supporting_controls(monkeypatch):
    from enterprise.audit_suite import programs

    monkeypatch.setattr(
        programs,
        "ism_catalog",
        lambda _: {
            "requirements": [{"id": "ism-test", "title": "Example", "statement": "Test only"}],
            "source_url": "https://example.test",
            "attribution": "Test",
            "license": "CC-BY-4.0",
        },
    )
    chosen = scope(
        programs=["IRAP"],
        report_type="Internal assessment",
        control_ids=["SH-PAY-002"],
        ism_requirement_ids=["ism-test"],
        ism_classification="NON_CLASSIFIED",
        ism_system_description="Bounded synthetic payroll environment",
        ism_tailoring_rationale="Exercise-specific system boundary",
    )
    normalized = validate_scope(chosen, "IT")
    assert control_projection(normalized)[0]["requirement_links"] == []
    tasks = programs.ism_tasks(normalized, programs.Path("."))
    assert tasks[0]["mapping_status"] == "UNMAPPED_REQUIRES_SCOPED_REVIEW"
    assert tasks[0]["conclusion"] == "NOT_RUN"
    with pytest.raises(DomainError, match="distinct requirements"):
        validate_scope({**chosen, "ism_requirement_ids": ["invented"]}, "IT")
    with pytest.raises(DomainError, match="non-classified"):
        validate_scope({**chosen, "ism_classification": "SECRET"}, "IT")


def test_fieldwork_date_is_independent_of_operating_period():
    assert validate_scope(scope(), "IT")["fieldwork_start"] == "2028-01-01"
    assert validate_scope(scope(fieldwork_start="2027-06-01"), "IT")["period_end"] == "2027-12-31"
    with pytest.raises(DomainError, match="Fieldwork must"):
        validate_scope(scope(fieldwork_start="2026-12-31"), "IT")
