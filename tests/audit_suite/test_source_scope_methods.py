"""Scope facts depend on genuine ordinary collected bytes, not cached bodies."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.full_scope_company_pair import FullScopePair, PinnedReview
from enterprise.audit_suite.persistent_company_journey import write
from enterprise.audit_suite.source_library_audit import (
    LIBRARY_MANIFEST_SCHEMA,
    LIBRARY_REVIEW_SCHEMA,
    LIBRARY_REVIEW_VERDICT,
    AcceptedLibrary,
    BusinessRoute,
    file_sha,
)
from enterprise.audit_suite.source_scope_execution import (
    SCHEMA,
    VERDICT,
    acquire_scope,
    execute_scope,
)
from enterprise.audit_suite.source_scope_methods import CONTRACTS, TASKS, examine

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "enterprise/generated/audit-suite/build/program-pack.json"
DOCUMENTS = {
    "phi_ba.operation_scope": {
        "fictional_contracting_entity_id": "NEUTRAL-ENTITY",
        "sim_service_id": "neutral-flow",
        "data_class": "PAYLOAD_FREE",
        "fixture_contains_real_phi": False,
        "actual_legal_applicability": "UNDETERMINED",
    },
    "phi_ba.flow_register": {
        "action": "LOCAL_MARKER",
        "payload_bytes": 0,
        "fixture_contains_real_phi": False,
        "exception_open": False,
    },
    "phi_ba.contract_register": {
        "contract_id": "neutral-synthetic-agreement",
        "contract_party_ids": ["NEUTRAL-ENTITY", "neutral-customer"],
        "contract_executed_in_simulation": True,
        "real_signature_or_agreement": False,
    },
    "phi_ba.legal_decision": {
        "actor_id": "neutral-counsel",
        "actor_authority": "SELECTED_FICTIONAL_ROLE",
        "legal_role_decision": "TRAINING_ONLY",
        "actual_legal_applicability": "UNDETERMINED",
    },
    "transition.site_release": {
        "site": {"site_id": "neutral-recovery", "source_operating_2026": False},
        "status": "SIMULATED_OPERATING",
        "fictional_in_universe_operating_release": True,
    },
    "transition.provider_contract": {
        "site": {"entity_reference": "NEUTRAL-ENTITY"},
        "fictional_in_universe_contract_executed": True,
        "real_external_signature": False,
    },
    "person-access-history.account_system_inventory": {
        "systems": [
            {"system": "neutral-directory", "owner": "neutral-owner"},
            {"system": "neutral-app", "owner": "neutral-owner"},
        ],
        "other_estate_inventory": "UNESTABLISHED",
    },
    "person-access-history.company_authority": {
        "issued_by": "neutral-management",
        "management_acceptance": ["neutral-management"],
        "forecast_positions_are_operating_workers": False,
    },
    "person-access-history.affiliation_register": {
        "person_id": "shared-display-token",
        "relationship_kind": "PROPOSED_CONTACT",
        "included_in_service_boundary": False,
        "source_status": "PROPOSED_NOT_APPOINTED",
    },
    "legprovision.provision_locator": {
        "2027_legal_text_verified": False,
        "detail": {
            "locator_status": "REFERENCE_ONLY",
            "qualified_review_status": "OPEN_PRIMARY_RECHECK",
            "applicability_status": "UNDETERMINED",
        },
    },
    "legprovision.obligation_snapshot": {
        "2027_legal_text_verified": False,
        "detail": {
            "open_historical_exception_ids": ["neutral-history"],
            "performance_fact_status": "NOT_ESTABLISHED_BY_TERMS",
        },
    },
    "assuranceops.assurance_scope": {
        "period": {"start": "2027-07-01", "end": "2027-09-30"},
        "excluded": ["FULL_YEAR", "REAL_EPHI"],
        "boundary_id": "corporate",
        "service_id": "separate-local-marker",
    },
    "assuranceops.assurance_independence": {
        "preparer_id": "neutral-preparer",
        "quality_reviewer_id": "neutral-reviewer",
        "actual_credentials_verified": False,
        "professional_external_opinion_authority": False,
    },
    "assuranceops.assurance_review": {
        "preparer_id": "neutral-preparer",
        "reviewer_id": "neutral-reviewer",
        "review_disposition": "SELECTED_ONLY",
        "description_version": 1,
        "complete_soc2_description_or_external_opinion": False,
    },
}


@pytest.fixture(scope="module")
def collected(tmp_path_factory):
    root = tmp_path_factory.mktemp("genuine-scope-source")
    root.chmod(0o700)
    source = root / "accepted"
    source.mkdir(mode=0o700)
    store = CompanyStore(source)
    routes = {}
    for mode, branch in (("CLEAN", "NORTH"), ("MESSY", "SOUTH")):
        routes[mode] = []
        for system, body in DOCUMENTS.items():
            store.register_system("NEUTRAL-SCOPE", branch, system, "neutral-owner")
            family, role = system.split(".", 1)
            routes[mode].append(BusinessRoute("NEUTRAL-SCOPE", branch, system, family, role))
            store.append_version(
                "NEUTRAL-SCOPE",
                branch,
                system,
                "neutral-record",
                expected_version=0,
                command_id=branch + system,
                event_at="2027-02-01T09:00:00Z",
                available_at="2027-02-01T09:00:00Z",
                content=json.dumps({**body, "engineering_neutral_fixture": True}).encode(),
                provenance={
                    "name": "native.json",
                    "content_type": "application/json",
                    "source_reference": "engineering-neutral-company-original",
                },
            )
    database, manifest, review = (
        source / "company.sqlite3",
        source / "MANIFEST.json",
        source / "REVIEW.json",
    )
    write(
        manifest,
        {"schema": LIBRARY_MANIFEST_SCHEMA, "files": {"company.sqlite3": file_sha(database)}},
    )
    write(
        review,
        {
            "schema": LIBRARY_REVIEW_SCHEMA,
            "verdict": LIBRARY_REVIEW_VERDICT,
            "source_quality_accepted_for_final_learner_audit": True,
            "native_versions": 2 * len(DOCUMENTS),
            "library_pins": {
                "company.sqlite3": file_sha(database),
                "MANIFEST.json": file_sha(manifest),
            },
            "engineering_fixture_not_actual_acceptance": True,
        },
    )
    accepted = AcceptedLibrary(
        database,
        file_sha(database),
        manifest,
        file_sha(manifest),
        review,
        file_sha(review),
        2 * len(DOCUMENTS),
    )
    pair = FullScopePair.initialize(
        accepted=accepted,
        repository=REPO,
        program_pack=PACK,
        routes_by_mode=routes,
        destination=root / "pair",
        operator_id="NEUTRAL-COMPANY-OPERATOR",
        engineering_only=True,
    )
    gate = root / "SCOPE-ENGINEERING-GATE.json"
    write(
        gate,
        {
            "schema": SCHEMA,
            "verdict": VERDICT,
            "source_execution_authorized": True,
            "selected_task_ids": list(TASKS),
            "task_contracts": CONTRACTS,
            "scope_method_module_sha256": file_sha(
                REPO / "enterprise/audit_suite/source_scope_methods.py"
            ),
            "scope_writer_module_sha256": file_sha(
                REPO / "enterprise/audit_suite/source_scope_execution.py"
            ),
            "full_scope_pair_module_sha256": file_sha(
                REPO / "enterprise/audit_suite/full_scope_company_pair.py"
            ),
            "workpaper_links_sha256": file_sha(REPO / "enterprise/audit_suite/workpaper_links.py"),
            "engineering_fixture_not_actual_independent_acceptance": True,
        },
    )
    approval = PinnedReview(gate, file_sha(gate))
    rows = {}
    for mode, room in pair.rooms.items():
        rows[mode] = acquire_scope(
            room,
            review=approval,
            task_id=TASKS[1],
            systems=list(DOCUMENTS),
            purpose="Reconcile declared scope company facts",
        )
        assert len(rows[mode]) == len(DOCUMENTS)
    return pair, approval, rows, root


def changed(rows, system, **fields):
    rows = deepcopy(rows)
    row = next(r for r in rows if r["source"]["system"] == system)
    body = json.loads(row["retained_bytes"])
    body.update(fields)
    row["retained_bytes"] = json.dumps(body).encode()
    row["source"]["sha256"] = hashlib.sha256(row["retained_bytes"]).hexdigest()
    row["artifact_sha256"] = row["source"]["sha256"]
    row["receipt"]["source"] = deepcopy(row["source"])
    row["receipt"]["content_bytes"] = len(row["retained_bytes"])
    return rows


def test_source_changes_affect_counts_and_recorded_exceptions(collected):
    pair, _, rows, _ = collected
    original = examine(rows["CLEAN"], as_of=pair.rooms["CLEAN"].state()["simulated_at"])
    modified = changed(
        rows["CLEAN"],
        "person-access-history.account_system_inventory",
        systems=[{"system": "neutral-only"}],
    )
    modified = changed(
        modified, "phi_ba.flow_register", exception_open=True, exception_id="new-native-failure"
    )
    result = examine(modified, as_of=pair.rooms["CLEAN"].state()["simulated_at"])

    def count(vector):
        return next(
            o["facts"]["recomputed_declared_system_count"]
            for o in vector[1]["observations"]
            if o["id"].startswith("declared-local-system-population")
        )

    assert count(original) == 2 and count(result) == 1
    assert result[1]["result"]["observed_exception_records"] == 1
    assert all(
        i["disposition"]["status"] == "IN_PROGRESS"
        and i["disposition"]["conclusion"] == "LIMITATION"
        for i in result
    )
    assert all(
        i["result"]["actual_professional_or_owner_acceptance"] == "NOT_ASSERTED" for i in result
    )


def test_cache_and_qualified_company_claims_do_not_supply_audit_acceptance(collected):
    pair, _, rows, _ = collected
    stale = deepcopy(rows["CLEAN"])
    for row in stale:
        row["document"] = {"owner_accepted_entire_audit": True, "2027_legal_text_verified": True}
    result = examine(stale, as_of=pair.rooms["CLEAN"].state()["simulated_at"])
    assert any(o["status"] == "SUPPORT_UNAVAILABLE" for o in result[0]["observations"])
    assert result[0]["result"]["actual_professional_or_owner_acceptance"] == "NOT_ASSERTED"


@pytest.mark.parametrize(
    "mutation", ["version", "receipt_version", "bytes", "future_clock", "branch", "role"]
)
def test_strict_custody_and_actual_roles(collected, mutation):
    pair, _, rows, _ = collected
    bad = deepcopy(rows["CLEAN"])
    row = bad[0]
    if mutation == "version":
        row["source"]["version"] = True
        row["receipt"]["source"]["version"] = True
    elif mutation == "receipt_version":
        row["receipt"]["source"]["version"] = True
    elif mutation == "bytes":
        row["receipt"]["content_bytes"] = True
    elif mutation == "future_clock":
        row["receipt"]["simulated_as_of"] = "2028-02-01T00:00:00Z"
    elif mutation == "branch":
        row["source"]["branch"] = "OTHER"
        row["receipt"]["source"]["branch"] = "OTHER"
    else:
        row["logical_system"] = "wrong-role"
    with pytest.raises(ProcedureError):
        examine(bad, as_of=pair.rooms["CLEAN"].state()["simulated_at"])


def test_missing_roles_are_explicit_without_company_nonoccurrence(collected):
    pair, _, rows, _ = collected
    selected = [r for r in rows["CLEAN"] if r["source"]["system"] == "phi_ba.operation_scope"]
    result = examine(selected, as_of=pair.rooms["CLEAN"].state()["simulated_at"])
    missing = [o for i in result for o in i["observations"] if o["id"].startswith("uncollected-")]
    assert len(missing) == 9
    assert all(
        o["status"] == "SUPPORT_UNAVAILABLE"
        and o["facts"]["company_nonoccurrence_or_inapplicability"] == "NOT_INFERRED"
        for o in missing
    )


def test_dedup_real_collection_and_two_no_control_scope_workpapers(collected):
    pair, approval, rows, _ = collected
    room = pair.rooms["CLEAN"]
    before = room.state()
    reused = acquire_scope(
        room,
        review=approval,
        task_id=TASKS[0],
        systems=list(DOCUMENTS),
        purpose="Inspect source interpretation dependencies",
        as_of="2027-03-01T00:00:00Z",
    )
    assert [r["artifact_id"] for r in reused] == [r["artifact_id"] for r in rows["CLEAN"]]
    assert room.state()["artifacts"] == before["artifacts"]
    prior = room.state()
    links = execute_scope(room, review=approval, rows=reused)
    after = room.state()
    assert len(links) == 2 and len(after["workpapers"]) == 2
    assert all(p["control_id"] is None for p in after["workpapers"])
    assert all(
        after[k] == prior[k] == []
        for k in ("populations", "selections", "sample_executions", "reviews")
    )
    assert all(
        t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN"
        for t in after["tasks"]
        if t["id"] not in TASKS
    )
    assert all(
        t["status"] == "IN_PROGRESS"
        and t["conclusion"] == "LIMITATION"
        and t["professional_acceptance"] == "NOT_ASSERTED"
        for t in after["tasks"]
        if t["id"] in TASKS
    )
    assert all(r["control_id"] is None and r["person_id"] is None for r in after["requests"])
    with pytest.raises(ProcedureError, match="overwrite"):
        execute_scope(room, review=approval, rows=reused)


def test_writer_refuses_forged_artifact_before_any_task_or_workpaper_write(collected):
    pair, approval, rows, _ = collected
    room = pair.rooms["MESSY"]
    bad = deepcopy(rows["MESSY"])
    bad[0]["artifact_id"] = "not-in-this-actual-engagement"
    before = room.state()
    with pytest.raises(ProcedureError, match="Foreign or invented"):
        execute_scope(room, review=approval, rows=bad)
    assert room.state() == before


@pytest.mark.parametrize("lead", [None, "distinct-lead"])
def test_quality_self_review_preserved_independently_of_lead_role(collected, lead):
    pair, _, rows, _ = collected
    altered = changed(
        rows["MESSY"],
        "assuranceops.assurance_review",
        reviewer_id=lead,
        quality_reviewer_id="neutral-preparer",
    )
    result = examine(altered, as_of=pair.rooms["MESSY"].state()["simulated_at"])
    observations = [
        o
        for o in result[0]["observations"]
        if o["id"].startswith("attributed-selected-company-review")
    ]
    assert any(
        o["status"] == "EXCEPTION_RECORDED"
        and o["facts"]["actual_preparer_equals_each_reviewer"]["quality_reviewer_id"] is True
        for o in observations
    )


def test_proposed_affiliation_is_not_silently_treated_as_employee(collected):
    pair, _, rows, _ = collected
    altered = changed(
        rows["MESSY"],
        "person-access-history.affiliation_register",
        included_in_service_boundary=True,
    )
    result = examine(altered, as_of=pair.rooms["MESSY"].state()["simulated_at"])
    assert any(
        o["id"].startswith("dated-affiliation-boundary") and o["status"] == "EXCEPTION_RECORDED"
        for o in result[1]["observations"]
    )
    invalid = changed(
        rows["MESSY"], "person-access-history.affiliation_register", included_in_service_boundary=1
    )
    with pytest.raises(ProcedureError, match="Strict scope Boolean"):
        examine(invalid, as_of=pair.rooms["MESSY"].state()["simulated_at"])


def test_exact_native_join_is_not_replaced_by_record_alias_or_boolean_version(collected):
    pair, _, rows, _ = collected
    target = next(r for r in rows["MESSY"] if r["source"]["system"] == "phi_ba.operation_scope")
    reference = {
        k: v
        for k, v in target["source"].items()
        if k
        in (
            "company",
            "branch",
            "system",
            "record",
            "version",
            "sha256",
            "event_at",
            "available_at",
        )
    }
    altered = changed(
        rows["MESSY"], "person-access-history.company_authority", source_refs=[reference]
    )
    result = examine(altered, as_of=pair.rooms["MESSY"].state()["simulated_at"])
    assert (
        result[1]["result"]["native_dependency_reconciliation"][0]["status"]
        == "EXACT_AVAILABLE_ORIGINAL"
    )
    missing = [r for r in altered if r["source"]["system"] != "phi_ba.operation_scope"]
    result = examine(missing, as_of=pair.rooms["MESSY"].state()["simulated_at"])
    assert (
        result[1]["result"]["native_dependency_reconciliation"][0]["status"]
        == "ORIGINAL_NOT_COLLECTED"
    )
    reference["version"] = True
    invalid = changed(
        rows["MESSY"], "person-access-history.company_authority", source_refs=[reference]
    )
    with pytest.raises(ProcedureError, match="strict-version business reference"):
        examine(invalid, as_of=pair.rooms["MESSY"].state()["simulated_at"])
