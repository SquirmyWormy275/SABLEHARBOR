"""Actual company-before-workroom collection and distinct assurance attributes."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.full_scope_company_pair import (
    GENERAL_METHOD_SCHEMA,
    GENERAL_METHOD_VERDICT,
    FullScopePair,
    PinnedReview,
)
from enterprise.audit_suite.persistent_company_journey import write
from enterprise.audit_suite.source_assurance_task_methods import (
    BUSINESS_ID,
    contracts,
    examine,
    task_plan,
)
from enterprise.audit_suite.source_library_audit import (
    LIBRARY_MANIFEST_SCHEMA,
    LIBRARY_REVIEW_SCHEMA,
    LIBRARY_REVIEW_VERDICT,
    AcceptedLibrary,
    BusinessRoute,
    file_sha,
)

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "enterprise/generated/audit-suite/build/program-pack.json"
COMPANY = "NEUTRAL-ASSURANCE-TASKS"
pytestmark = pytest.mark.skipif(not PACK.exists(), reason="Private exact program pack required")


def fixture_source(root, *, self_review=False, future_dependency=False, many_owners=False):
    root.mkdir(mode=0o700)
    store = CompanyStore(root)
    systems = set()
    for branch in ["NORTH", "SOUTH"]:

        def append(system, record, body, at, *, branch=branch):
            if (branch, system) not in systems:
                store.register_system(COMPANY, branch, system, "NEUTRAL-OWNER")
                systems.add((branch, system))
            actual = store.append_version(
                COMPANY,
                branch,
                system,
                record,
                expected_version=0,
                command_id=branch + ":" + system + ":" + record,
                event_at=at,
                available_at=at,
                content=json.dumps({"engineering_neutral_fixture": True, **body}).encode(),
                provenance={
                    "source_reference": "owned-neutral-company-source",
                    "name": "original.json",
                    "content_type": "application/json",
                },
            )
            return {k: actual[k] for k in BUSINESS_ID}

        screen = append(
            "assurance.issue_screening",
            "issue-one",
            {"issue_manager_person_id": "evaluator", "status": "SELECTED_DEFECT_REQUIRES_FINDING"},
            "2027-08-01T09:00:00Z",
        )
        finding = append(
            "assurance.issue_finding",
            "issue-one",
            {
                "finding_closed": False,
                "severity": "HIGH",
                "severity_basis": "missed obligation",
                "technical_action_owner_person_id": "operator",
                "plan_response_due_at": "2027-09-01T09:00:00Z",
                "closure_criteria": "independent retest",
                "prior_issue_event_sha256": screen["sha256"],
            },
            "2027-08-02T09:00:00Z",
        )
        technical = append(
            "bcm.exercise_result",
            "exercise-one",
            {"measured_minutes": 8},
            "2027-12-01T09:00:00Z" if future_dependency else "2027-08-03T09:00:00Z",
        )
        append(
            "ass001002.monitoring_scope",
            "scope-one",
            {
                "quarter": "2027-Q3",
                "selected_control": "control-one",
                "selected_service": "service-one",
                "criteria": ["owner statement", "prior issues"],
                "trigger": "quarterly",
                "upstream_refs": [screen, technical],
            },
            "2027-09-05T09:00:00Z",
        )
        owner = append(
            "ass001002.owner_self_assessment",
            "owner-one",
            {
                "quarter": "2027-Q3",
                "selected_control": "control-one",
                "selected_service": "service-one",
                "statement": "SELECTED_RETEST_PASSED_NO_OPEN_ISSUE_REPORTED",
            },
            "2027-09-08T09:00:00Z",
        )
        append(
            "ass001002.second_line_observation",
            "evaluation-one",
            {
                "actor_person_id": "evaluator",
                "owner_submission_sha256": owner["sha256"],
                "technical_input": technical,
                "nontechnical_input": finding,
                "evaluated_effectiveness": "NOT_CONCLUDED",
            },
            "2027-09-12T09:00:00Z",
        )
        independence = append(
            "assuranceops.assurance_independence",
            "independence-one",
            {
                "preparer_id": "preparer",
                "quality_reviewer_id": "preparer" if self_review else "quality",
                "actual_credentials_verified": False,
                "reviewer_prepared_tests": False,
            },
            "2027-09-15T09:00:00Z",
        )
        review = append(
            "assuranceops.assurance_review",
            "review-one",
            {
                "preparer_id": "preparer",
                "reviewer_id": "preparer" if self_review else "quality",
                "dependencies": [independence],
            },
            "2027-09-16T09:00:00Z",
        )
        append(
            "assuranceops.assurance_programme",
            "programme-one",
            {"status": "SCHEDULED", "due_at": "2027-10-01T09:00:00Z", "dependencies": [review]},
            "2027-09-17T09:00:00Z",
        )
        append(
            "assuranceops.assurance_description",
            "description-one",
            {
                "assertions": [
                    {
                        "assertion_id": "issue-disclosure",
                        "statement": "Selected issue disclosed",
                        "sources": [finding],
                    }
                ],
                "customer_release_status": "HELD_FOR_RECONCILIATION",
            },
            "2027-09-18T09:00:00Z",
        )
        if many_owners:
            for number in range(23):
                append(
                    "ass001002.owner_self_assessment",
                    "extra-" + str(number),
                    {
                        "quarter": "2027-Q3",
                        "selected_control": "control-one",
                        "selected_service": "service-one",
                        "statement": "CORRECTED_OPEN_HISTORICAL_ISSUE_DISCLOSED",
                    },
                    "2027-09-19T09:00:00Z",
                )
    database, manifest, review = (
        root / "company.sqlite3",
        root / "MANIFEST.json",
        root / "REVIEW.json",
    )
    write(
        manifest,
        {"schema": LIBRARY_MANIFEST_SCHEMA, "files": {"company.sqlite3": file_sha(database)}},
    )
    count = 66 if many_owners else 20
    write(
        review,
        {
            "schema": LIBRARY_REVIEW_SCHEMA,
            "verdict": LIBRARY_REVIEW_VERDICT,
            "source_quality_accepted_for_final_learner_audit": True,
            "library_pins": {
                "company.sqlite3": file_sha(database),
                "MANIFEST.json": file_sha(manifest),
            },
            "native_versions": count,
            "engineering_neutral_test_fixture_not_actual_independent_acceptance": True,
        },
    )
    accepted = AcceptedLibrary(
        database, file_sha(database), manifest, file_sha(manifest), review, file_sha(review), count
    )
    routes = {
        mode: [
            BusinessRoute(COMPANY, branch, system, *system.split(".", 1))
            for b, system in sorted(systems)
            if b == branch
        ]
        for mode, branch in [("CLEAN", "NORTH"), ("MESSY", "SOUTH")]
    }
    return accepted, routes


def collect(tmp_path, **variant):
    tmp_path.chmod(0o700)
    accepted, routes = fixture_source(tmp_path / "native-before-audit", **variant)
    pair = FullScopePair.initialize(
        accepted=accepted,
        repository=REPO,
        program_pack=PACK,
        routes_by_mode=routes,
        destination=tmp_path / "fresh-pair",
        operator_id="NEUTRAL-COMPANY-OPERATOR",
        engineering_only=True,
    )
    room = pair.rooms["CLEAN"]
    assert len(room.state()["tasks"]) == 409 and not room.state()["artifacts"]
    rows = room.acquire(
        systems=[r.system for r in routes["CLEAN"]],
        control_id="SH-ASS-001",
        purpose="Reperform distinct assurance facets from the actual neutral company",
    )
    return pair, room, rows


def test_all23_distinct_tasks_use_actual_collections_with_separate_kind_and_clause_facets(tmp_path):
    pair, room, rows = collect(tmp_path)
    before = room.state()
    result = examine(rows, as_of=before["simulated_at"])
    assert len(result) == 23 and [i["task_id"] for i in result] == [
        t["task_id"] for t in task_plan()
    ]
    for item in result:
        room._validate_inspection(rows, item, contracts()[item["task_id"]])
        assert item["disposition"]["conclusion"] == "LIMITATION"
    assert room.state() == before and not pair.rooms["MESSY"].state()["artifacts"]
    by_id = {i["task_id"]: i for i in result}
    assert any(
        o["status"] == "EXCEPTION_RECORDED"
        for o in by_id["TASK-SH-ASS-001-corporate-TOE"]["observations"]
    )
    assert any(
        o["id"].startswith("design-")
        for o in by_id["TASK-SH-ASS-001-corporate-TOD"]["observations"]
    )
    assert any(
        o["id"].startswith("accountability-")
        for o in by_id["TASK-SH-ASS-001-corporate-ACTION-S-ACCOUNTABILITY"]["observations"]
    )
    assert any(
        o["id"].startswith("description-")
        for o in by_id["TASK-SH-ASS-004-corporate-ACTION-S-DESCRIPTION"]["observations"]
    )


def test_fresh_company_future_original_does_not_supply_earlier_evaluation_credit(tmp_path):
    _, room, rows = collect(tmp_path, future_dependency=True)
    result = examine(rows, as_of=room.state()["simulated_at"])
    item = next(i for i in result if i["task_id"] == "TASK-SH-ASS-002-corporate-IMPLEMENTATION")
    assert "SOURCE_UNAVAILABLE_AT_COMPANY_EVENT" in json.dumps(item)
    assert 'independence_verified": false' in json.dumps(item)


def test_actual_self_review_is_reported_without_treating_synthetic_identity_as_credential(tmp_path):
    _, room, rows = collect(tmp_path, self_review=True)
    result = examine(rows, as_of=room.state()["simulated_at"])
    item = next(i for i in result if i["task_id"] == "TASK-SH-ASS-002-corporate-CHECK-SOC2:CC4.1")
    assert any(
        o["id"].startswith("objectivity-") and o["status"] == "EXCEPTION_RECORDED"
        for o in item["observations"]
    )
    assert all(
        o["facts"]["actual_credentials_verified_by_auditor"] is False
        for o in item["observations"]
        if o["id"].startswith("objectivity-")
    )


@pytest.mark.parametrize(
    "mutation", ["boolean_version", "bad_bytes", "role_alias", "future_collection"]
)
def test_exact_ordinary_receipt_and_role_clock_guards_reject_changed_input(tmp_path, mutation):
    _, room, rows = collect(tmp_path)
    changed = deepcopy(rows)
    row = changed[0]
    if mutation == "boolean_version":
        row["source"]["version"] = True
        row["receipt"]["source"]["version"] = True
    elif mutation == "bad_bytes":
        row["retained_bytes"] += b" "
    elif mutation == "role_alias":
        row["logical_system"] = "other-role"
    else:
        row["receipt"]["simulated_as_of"] = "2028-02-01T00:00:00Z"
    with pytest.raises(ProcedureError):
        examine(changed, as_of=room.state()["simulated_at"])


def test_many_originals_keep_every_citation_below_fixed_writer_cap_and_append23_once(tmp_path):
    pair, room, rows = collect(tmp_path, many_owners=True)
    items = examine(rows, as_of=room.state()["simulated_at"])
    toe = next(i for i in items if i["task_id"] == "TASK-SH-ASS-001-corporate-TOE")
    assert any(o["facts"].get("citation_partitions", 0) > 1 for o in toe["observations"])
    assert all(1 <= len(o["evidence"]) <= 20 for i in items for o in i["observations"])
    owner_ids = {
        r["artifact_id"] for r in rows if r["source"]["system"] == "ass001002.owner_self_assessment"
    }
    assert owner_ids <= set(toe["artifact_ids"])
    gate = room.root / "AUTHOR-NEUTRAL-METHOD-REVIEW.json"
    write(
        gate,
        {
            "schema": GENERAL_METHOD_SCHEMA,
            "verdict": GENERAL_METHOD_VERDICT,
            "source_execution_authorized": True,
            "method_module_sha256": file_sha(
                Path(__file__).parents[2]
                / "enterprise/audit_suite/source_assurance_task_methods.py"
            ),
            "method_callable": examine.__module__ + "." + examine.__qualname__,
            "selected_task_ids": [t["task_id"] for t in task_plan()],
            "task_contracts": contracts(),
            "dependency_module_sha256": {},
            "engineering_neutral_fixture_not_independent_acceptance": True,
        },
    )
    links = room.append_reviewed_batch(
        batch="B08-NEUTRAL", review=PinnedReview(gate, file_sha(gate)), rows=rows, method=examine
    )
    assert len(links) == len(room.state()["workpapers"]) == 23
    assert sum(t["status"] == "NOT_STARTED" for t in room.state()["tasks"]) == 386
    assert all(t["status"] == "NOT_STARTED" for t in pair.rooms["MESSY"].state()["tasks"])
    with pytest.raises(ProcedureError, match="overwrite"):
        room.append_reviewed_batch(
            batch="B08-NEUTRAL-AGAIN",
            review=PinnedReview(gate, file_sha(gate)),
            rows=rows,
            method=examine,
        )


def test_preparsed_cache_does_not_change_genuine_original_results(tmp_path):
    _, room, rows = collect(tmp_path)
    original = examine(rows, as_of=room.state()["simulated_at"])
    changed = deepcopy(rows)
    for row in changed:
        row["document"] = {"statement": "FAKE_CLEAR", "finding_closed": True}
    assert examine(changed, as_of=room.state()["simulated_at"]) == original
