"""Read-only reconciliation of genuine native parent and continuation fixtures."""

import json
from copy import deepcopy

import pytest

from enterprise.audit_suite.access_remediation_reconciliation import analyze
from enterprise.audit_suite.company_access_remediation_activity import generate_pair
from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_access_remediation_operator import ROOT
from tests.audit_suite.test_company_access_remediation_operator import prepared as prepared_source
from tests.audit_suite.test_company_access_remediation_review import _recipe

SCOPE = {
    "period_start": "2027-01-01",
    "period_end": "2027-12-31",
    "timezone": "UTC",
    "boundaries": ["corporate"],
}


@pytest.fixture(scope="module")
def native_case(tmp_path_factory):
    directory = tmp_path_factory.mktemp("removal-observations")
    root, recipe = prepared_source.__wrapped__(directory)
    output = directory / "continued"
    generate_pair(output, repository=ROOT, source_root=root / "company", recipe=_recipe(recipe))
    sources, bodies, labels = [], {}, {}
    for component, store_root in [("identity-b", root / "company"), ("continuation", output)]:
        store = CompanyStore(store_root)
        with store._db() as db:
            rows = [dict(r) for r in db.execute("SELECT * FROM versions")]
        for row in rows:
            if component == "identity-b" and not any(
                all(
                    row[k] == ref[k]
                    for k in ("company", "branch", "system", "record", "version", "sha256")
                )
                for ref in recipe["source_refs"]
            ):
                continue
            sid = f"{component}:{row['branch']}:{row['system']}:{row['record']}:v{row['version']}"
            sources.append(
                {
                    "id": sid,
                    "source_store_id": component,
                    "source_system_alias": component + ":" + row["system"],
                    "registry_sha256": "a" * 64,
                    **{
                        k: row[k]
                        for k in (
                            "company",
                            "branch",
                            "system",
                            "record",
                            "version",
                            "sha256",
                            "event_at",
                            "available_at",
                        )
                    },
                }
            )
            bodies[sid] = json.loads(row["content"])
            labels[component, row["branch"], row["system"], row["version"]] = sid
    parent = {
        k: labels["identity-b", "activity-messy", system, version]
        for k, system, version in [
            ("population_ref_id", "review_population", 1),
            ("decisions_ref_id", "review_decisions", 1),
            ("reconciliation_ref_id", "review_reconciliation", 1),
            ("application_ref_id", "application", 2),
            ("hr_ref_id", "hr", 3),
        ]
    }
    contracts = []
    for branch in ("removal-a", "removal-b"):

        def ref(system, version, branch=branch):
            return labels["continuation", branch, system, version]

        contracts.append(
            {
                "parent": parent,
                "producer_label_expected": recipe["source_store_id"],
                "baseline_ref_id": ref("entitlement_state", 1),
                "request_ref_id": ref("removal_requests", 1),
                "attempts": [
                    {
                        "resolver_ref_id": ref("permission_resolver", n),
                        "execution_ref_id": ref("execution_attempts", n),
                        "state_ref_id": ref("entitlement_state", n + 1),
                        "verification_ref_id": ref("validation_probes", n),
                    }
                    for n in (1, 2)
                ],
                "followup_ref_ids": [ref("remediation_followup", 1)],
            }
        )
    return contracts, sources, bodies


@pytest.fixture
def case(native_case):
    return deepcopy(native_case)


def test_actual_paired_local_records_preserve_limits_and_metadata_uncertainty(case):
    result = analyze(*case, SCOPE)
    assert len(case[1]) == 27 and len(result) == 2
    for item in result:
        assert item["baseline_matches_selected_application"]
        assert item["request_matches_selected_decision"]
        assert item["metadata_verification"] == "NOT_RECOMPUTABLE_FROM_RETAINED_FIELDS"
        assert item["declared_metadata_digests_consistent"]
        assert item["whole_review_closure"] == "NOT_ESTABLISHED"
        assert item["professional_assurance"] == "NOT_PERFORMED"
        assert item["recorded_unresolved_population_ids"] == ["P014"]
        assert all(
            link["status"] == "EXACT_MATCH"
            and link["available_before_dependent_event"]
            and not link["self_reference"]
            for link in item["lineage"]
        )
        assert all(
            row["parent_native_pins_match"]
            and row["producer_label_matches"]
            and row["parent_available_at_input"]
            for row in item["source_checks"]
        )
        for attempt in item["attempts"]:
            assert attempt["state_matches_local_transition"]
            assert attempt["permission_probe_results_match_state"]
            assert attempt["recorded_operating_actors_distinct"]
            assert attempt["causal_availability_matches"]
    assert result[0]["attempts"][0]["recorded_after_rights"] == ["inventory-admin"]
    assert result[1]["attempts"][0]["recorded_after_rights"] == ["billing-admin", "inventory-admin"]
    assert result[1]["attempts"][1]["recorded_after_rights"] == ["inventory-admin"]


@pytest.mark.parametrize(
    "fault",
    [
        "probe",
        "before",
        "after",
        "removed",
        "mapping",
        "metadata",
        "parentpin",
        "label",
        "late",
    ],
)
def test_substantive_mismatches_are_observations_not_acceptance(case, fault):
    contracts, sources, bodies = case
    contract = contracts[1]
    attempt = contract["attempts"][0]
    if fault == "probe":
        bodies[attempt["verification_ref_id"]]["removed_permission_probes"]["billing-admin"] = (
            "DENY"
        )
    elif fault == "before":
        bodies[attempt["execution_ref_id"]]["before_rights"] = []
    elif fault == "after":
        bodies[attempt["state_ref_id"]]["rights"] = []
    elif fault == "removed":
        bodies[attempt["execution_ref_id"]]["removed_rights"] = ["billing-admin"]
    elif fault == "mapping":
        bodies[attempt["resolver_ref_id"]]["mapping"] = {"billing-admin": "inventory-admin"}
    elif fault == "metadata":
        bodies[contract["request_ref_id"]]["source_versions_sha256"] = "b" * 64
    elif fault == "parentpin":
        bodies[contract["request_ref_id"]]["source_records"][0]["sha256"] = "b" * 64
    elif fault == "label":
        contract["producer_label_expected"] = "other-native-label"
    else:
        row = next(r for r in sources if r["id"] == attempt["state_ref_id"])
        row["available_at"] = "2027-07-01T09:16:00Z"
    result = analyze(contracts, sources, bodies, SCOPE)[1]
    key = {
        "probe": "permission_probe_results_match_state",
        "before": "execution_before_matches_prior_state",
        "after": "state_matches_local_transition",
        "removed": "execution_removed_matches_state_difference",
        "mapping": "mapping_within_requested_authority",
        "late": "causal_availability_matches",
    }.get(fault)
    if key:
        assert result["attempts"][0][key] is False
    elif fault == "metadata":
        assert result["declared_metadata_digests_consistent"] is False
    else:
        assert any(
            not r["parent_native_pins_match" if fault == "parentpin" else "producer_label_matches"]
            for r in result["source_checks"]
        )
    assert result["professional_assurance"] == "NOT_PERFORMED"


@pytest.mark.parametrize(
    "fault",
    ["bool_version", "duplicate", "unknown", "wrong_role", "cross_branch", "control", "quota"],
)
def test_invalid_structural_or_scoped_contract_fails_closed(case, fault):
    contracts, sources, bodies = case
    if fault == "bool_version":
        sources[0]["version"] = True
    elif fault == "duplicate":
        contracts.append(contracts[0])
    elif fault == "unknown":
        contracts[0]["request_ref_id"] = "missing"
    elif fault == "wrong_role":
        contracts[0]["attempts"][0]["resolver_ref_id"] = contracts[0]["followup_ref_ids"][0]
    elif fault == "cross_branch":
        contracts[0]["attempts"][0] = contracts[1]["attempts"][0]
    elif fault == "control":
        bodies[contracts[0]["request_ref_id"]]["control_ids"] = ["SH-IAM-003"]
    else:
        sources.extend(deepcopy(sources) * 3)
    with pytest.raises(DomainError):
        analyze(contracts, sources, bodies, SCOPE)


def test_missing_selected_lineage_support_is_not_nonexistent_evidence(case):
    contracts, sources, bodies = case
    contracts = contracts[:1]
    contracts[0]["followup_ref_ids"] = []
    result = analyze(contracts, sources, bodies, SCOPE)[0]
    assert any(r["status"] == "MISSING_SELECTED_SUPPORT" for r in result["lineage"])
    assert result["whole_review_closure"] == "NOT_ESTABLISHED"


@pytest.mark.parametrize("fault", ["execution_status", "state_status"])
def test_status_text_cannot_override_recorded_local_state(case, fault):
    contracts, sources, bodies = case
    attempt = contracts[1]["attempts"][0]
    if fault == "execution_status":
        bodies[attempt["execution_ref_id"]]["status"] = "APPLIED_OR_ALREADY_ABSENT"
    else:
        bodies[attempt["state_ref_id"]]["execution_status"] = "APPLIED_OR_ALREADY_ABSENT"
    result = analyze(contracts, sources, bodies, SCOPE)[1]["attempts"][0]
    assert (
        result[
            "execution_status_matches_mapping"
            if fault == "execution_status"
            else "state_status_matches_execution"
        ]
        is False
    )
    assert result["recorded_after_rights"] == ["billing-admin", "inventory-admin"]


def test_missing_capture_route_or_source_id_is_typed_failure(case):
    contracts, sources, bodies = case
    del sources[0]["source_store_id"]
    with pytest.raises(DomainError):
        analyze(contracts, sources, bodies, SCOPE)
