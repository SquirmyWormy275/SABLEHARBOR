"""Selected fictional company change queue; no real deployment or audit collection."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from . import company_sec005_operated_2027 as sec
from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_ENG005_SELECTED_CHANGE_OPERATION_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
BRANCHES = {"CLEAN": "ENG005-OPERATED-CLEAN", "MESSY": "ENG005-OPERATED-MESSY"}
SOURCE_REFERENCE = "enterprise/audit_suite/company_eng005_operating_2027.py"
SPEC = "enterprise/audit_suite/eng005_operating_2027_spec_v1.json"
SPEC_SHA256 = "a497fab4b3ca909f55b3376efec15c28f6195394d6f085d4aaf0b99d51043d6a"
TRANSITION_ROOT = "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/run-v3"
HISTORICAL_PROSPECTIVE = (
    "enterprise/generated/audit-suite/company-emergency-change-2027-simulation-"
    "2026-09-29/run-v1/SOURCE_RECEIPT.json"
)
HISTORICAL_SHA256 = "efa67bb2cf9934a62e91ea51b109e61f2954bbb8b83ef84e2c5f1e6f344d78d9"
CANON_SHA = {
    "docs/canon/THIRD_PARTY_SERVICES_SOURCING_DECISIONS_2026-09-09.md": (
        "53dc3c69be68cd66fe9fdd30048f8229416fd6bd6660272dfeae20f802f986d4"
    ),
    "docs/canon/RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md": (
        "fd309a9bdf596ea96498b7207b60ea3bea70a35d8c418371aa96c06d928bb17b"
    ),
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md": (
        "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496"
    ),
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md": (
        "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433"
    ),
    "docs/governance/ENTERPRISE_TECHNOLOGY_SERVICES_DOCTRINE.md": (
        "8dbfbd6a7b9414df28088d6e37ec7ba9e086616b5d4a2deb5cd33da845fa64fd"
    ),
    "docs/internal/development/audit-suite/ORGANIZATION_APPOINTMENT_PROPOSALS_2026-09-13.json": (
        "53681cf60e85d130d04ef79ed437e70da9b3211896e2098f049bc9ff26f54681"
    ),
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md": (
        "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751"
    ),
    "enterprise/services/source/runtime_sites_2026-09-11.json": (
        "fa216f629762503865fd9f1a3207e87691cd484cec9885bf25ce045b4525519c"
    ),
    "enterprise/services/source/services.json": (
        "f9cd08b7add29b7be6c51670bf0c92bcca4b582e9853d83d25d518171da75818"
    ),
    "enterprise/audit_suite/ENG005_SELECTED_SOURCE_GAP_PROPOSAL.md": (
        "93cce721a103baf87ca06ad7f30738e9d2ecf405794ab594a22c485522252723"
    ),
}
SYSTEM_OWNERS = {
    "change_request": "AS-P014",
    "change_risk": "AS-P007",
    "change_test": "AS-P007",
    "change_approval": "AS-P008",
    "change_release": "AS-P014",
    "change_application": "AS-P007",
    "change_verification": "AS-P008",
    "change_recovery": "AS-P007",
    "change_review": "AS-P005",
    "exception_register": "AS-P005",
}
LIMITS = [
    "Fictional 2027 selected SVC-compute change population; 2026 canon stays nonoperating.",
    "Exactly two selected requests: ordinary Reno and emergency Boise; not a full-period queue.",
    "Dated office identities and simulated local decisions grant no corporate change authority.",
    "No corporate emergency delegation is evidenced. Clean blocks; Messy bypass is invalid.",
    "Earlier ENG005-SELECTED-2027-001 in-memory exercise remains distinct historical source.",
    "Data-only configuration model; no device write, packet, executable, PHI or customer effect.",
    "Event and availability clocks are authored 2027 simulation; import clock is actual creation.",
    "Messy correction and rollback do not close historical exceptions or grant audit credit.",
]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _configuration_sha(case: dict, value: int) -> str:
    """Bind each modeled result to one selected immutable configuration tuple."""
    if type(value) is not int or value < 1 or value > 60:
        raise CompanyStoreError("Selected configuration value is out of local range")
    return sha(
        encoded(
            {
                "service_id": "SVC-compute",
                "site": case["site"],
                "configuration_key": case["configuration_key"],
                "value": value,
            }
        )
    )


def _ordinary_tests(case: dict) -> dict[str, bool]:
    return {
        "SCHEMA": type(case["candidate"]) is int and 1 <= case["candidate"] <= 60,
        "BOUNDARY": case["candidate"] <= case["baseline"],
        "RECOVERY": case["rollback"] == case["baseline"],
    }


def _context(repository: Path, private_repository: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    for name, digest in {SPEC: SPEC_SHA256, **CANON_SHA}.items():
        path = repository / name
        if path.is_symlink() or not path.is_file() or _digest(path) != digest:
            raise CompanyStoreError("Pinned ENG005 source/canon bytes differ")
    historical = private_repository / HISTORICAL_PROSPECTIVE
    sec._private(historical.parent, directory=True)
    before = sec._frozen({"historical": historical})
    if before["historical"][-1] != HISTORICAL_SHA256:
        raise CompanyStoreError("Distinct historical prospective exercise bytes differ")
    earlier = json.loads(historical.read_text())
    if earlier.get("exercise_id") != "ENG005-SELECTED-2027-001":
        # Retain a hash-pinned reference, even if the old receipt uses another key.
        if "ENG005-SELECTED-2027-001" not in historical.read_text():
            raise CompanyStoreError("Historical prospective identity differs")
    spec = json.loads((repository / SPEC).read_text())
    ordinary = spec.get("ordinary", {})
    emergency = spec.get("emergency", {})
    if (
        spec.get("schema") != "SH_ENG005_SELECTED_OPERATING_CHANGE_SPEC_V1"
        or spec.get("qualification")
        != "FICTIONAL_2027_COMPANY_SELECTED_CHANGE_OPERATION_NO_REAL_DEPLOYMENT"
        or spec.get("company") != COMPANY
        or spec.get("service_id") != "SVC-compute"
        or spec.get("selected_population") != ["CHG-RNO-MARKER-2027-01", "CHG-BOI-GATE-2027-02"]
        or spec.get("historical_prospective_exercise_id") != "ENG005-SELECTED-2027-001"
        or spec.get("historical_exercise_is_operating_source") is not False
        or ordinary.get("site") != "RUNTIME-RENO-COLO"
        or ordinary.get("required_tests") != ["SCHEMA", "BOUNDARY", "RECOVERY"]
        or ordinary.get("requester") != "AS-P014"
        or ordinary.get("executor") != "AS-P007"
        or ordinary.get("independent_security_reviewer") != "AS-P008"
        or ordinary.get("baseline") != ordinary.get("rollback")
        or ordinary.get("candidate") == ordinary.get("baseline")
        or emergency.get("site") != "RUNTIME-BOISE-DR"
        or emergency.get("corporate_emergency_authority_status") != "NOT_EVIDENCED_OPEN"
        or emergency.get("requester") != "AS-P007"
        or emergency.get("independent_retrospective_reviewer") != "AS-P008"
        or emergency.get("baseline") != emergency.get("rollback")
        or emergency.get("candidate") == emergency.get("baseline")
        or any(
            spec.get(name)
            for name in (
                "real_deployment",
                "actual_phi",
                "enterprise_policy_approved",
                "audit_task_credit",
            )
        )
        or spec.get("external_packets_or_writes") != 0
    ):
        raise CompanyStoreError("Selected ENG005 operating specification differs")
    appointment_path = (
        "docs/internal/development/audit-suite/ORGANIZATION_APPOINTMENT_PROPOSALS_2026-09-13.json"
    )
    appointments = json.loads((repository / appointment_path).read_text())
    if appointments.get("repository_acceptance_status") != "PROPOSED_NOT_ACCEPTED_CANON" or not {
        "AS-P005",
        "AS-P007",
        "AS-P008",
        "AS-P014",
    } <= {person["person_id"] for person in appointments["people"]}:
        raise CompanyStoreError("Planning appointment derivative differs")
    dated_appointments = (
        repository / "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md"
    ).read_text()
    for person_id, name, office in (
        ("AS-P005", "Martin Ives", "Head of Risk and Compliance"),
        ("AS-P007", "Elliot Tran", "Head of Enterprise Technology Services"),
        ("AS-P008", "Dana West", "Chief Information Security Officer"),
        ("AS-P014", "Omar Vale", "Data Governance and Records Lead"),
    ):
        if f"| {person_id} | {name} | {office} |" not in dated_appointments:
            raise CompanyStoreError("Dated enterprise office identity differs")
    sites = json.loads(
        (repository / "enterprise/services/source/runtime_sites_2026-09-11.json").read_text()
    )["sites"]
    selected = {
        row["id"]: row for row in sites if row["id"] in {ordinary["site"], emergency["site"]}
    }
    if set(selected) != {ordinary["site"], emergency["site"]} or any(
        row["status"] != "PROVIDER_SELECTED_PROCUREMENT_PENDING"
        or row["contract_executed"] is not False
        or row["operating"] is not False
        for row in selected.values()
    ):
        raise CompanyStoreError("2026 nonoperating site boundary differs")
    transition_root = private_repository / TRANSITION_ROOT
    releases = sec._transition_context(repository, transition_root)
    if sec._frozen({"historical": historical}) != before:
        raise CompanyStoreError("Historical exercise changed during source check")
    return {"spec": spec, "releases": releases}


def _rows(context: dict, scenario: str) -> list[dict]:
    if scenario not in BRANCHES:
        raise CompanyStoreError("Unknown ENG005 branch")
    spec = context["spec"]
    ordinary, emergency = spec["ordinary"], spec["emergency"]
    tests = _ordinary_tests(ordinary)
    if not all(tests.values()):
        raise CompanyStoreError("Selected ordinary test inputs fail")
    rows: list[dict] = []
    refs: dict[str, dict] = {}
    previous: dict | None = None
    messy = scenario == "MESSY"

    def emit(
        system: str,
        record: str,
        at: str,
        actor: str,
        case: dict,
        action: str,
        detail: dict,
        depends: tuple[str, ...] = (),
    ) -> None:
        nonlocal previous
        event = _time(at)
        available = _time((datetime.fromisoformat(event) + timedelta(minutes=15)).isoformat())
        if previous and previous["available_at"] >= event:
            raise CompanyStoreError("ENG005 event precedes predecessor availability")
        if any(name not in refs for name in depends):
            raise CompanyStoreError("ENG005 predecessor missing")
        body = {
            "qualification": spec["qualification"],
            "company": COMPANY,
            "scenario": scenario,
            "service_id": spec["service_id"],
            "selected_period": spec["selected_period"],
            "system": system,
            "record": record,
            "change_id": case["change_id"],
            "site": case["site"],
            "configuration_key": case["configuration_key"],
            "baseline_config_sha256": _configuration_sha(case, case["baseline"]),
            "candidate_config_sha256": _configuration_sha(case, case["candidate"]),
            "event_at": event,
            "available_at": available,
            "actor_id": actor,
            "action": action,
            "source_previous": previous,
            "source_refs": {name: refs[name] for name in depends},
            "upstream_site_release": context["releases"][scenario][
                "RENO" if case is ordinary else "BOISE"
            ],
            "historical_prospective_exercise_id": spec["historical_prospective_exercise_id"],
            "historical_exercise_is_operating_source": False,
            "real_deployment": False,
            "actual_phi": False,
            "external_packets_or_writes": 0,
            "enterprise_policy_approved": False,
            "audit_task_credit": False,
            **detail,
        }
        body["value_digests"] = {
            key: _configuration_sha(case, detail[key])
            for key in (
                "tested_candidate",
                "applied_value",
                "observed_value",
                "restored_value",
                "rehearsed_baseline",
                "restored_active_value",
                "current_selected_value",
            )
            if key in detail
        }
        raw = encoded(body)
        row = {
            "system": system,
            "record": record,
            "event_at": event,
            "available_at": available,
            "sha256": sha(raw),
            "content": raw,
        }
        rows.append(row)
        previous = {
            key: row[key] for key in ("system", "record", "sha256", "event_at", "available_at")
        }
        previous["version"] = 1
        refs[record] = previous

    emit(
        "change_request",
        "ORD-REQUEST",
        "2027-09-12T10:00:00+00:00",
        "AS-P014",
        ordinary,
        "ORDINARY_CHANGE_REQUEST",
        {
            "business_intent": "Selected nonpersonal marker freshness",
            "baseline": ordinary["baseline"],
            "candidate": ordinary["candidate"],
            "rollback": ordinary["rollback"],
            "affected_data": "NONPERSONAL_MARKER_ONLY",
        },
    )
    emit(
        "change_risk",
        "ORD-RISK",
        "2027-09-13T10:00:00+00:00",
        "AS-P007",
        ordinary,
        "SELECTED_SCOPE_AND_RECOVERY_RISK",
        {
            "test_plan": ordinary["required_tests"],
            "rollback_reference": "ORD-REQUEST",
            "full_service_population": False,
        },
        ("ORD-REQUEST",),
    )
    emit(
        "change_test",
        "ORD-TEST-INITIAL",
        "2027-09-14T10:00:00+00:00",
        "AS-P007",
        ordinary,
        "BOUND_TEST_RESULT",
        {
            "tested_candidate": ordinary["candidate"],
            "passed_tests": ["SCHEMA", "BOUNDARY"] if messy else ordinary["required_tests"],
            "test_results": {
                name: tests[name]
                for name in (["SCHEMA", "BOUNDARY"] if messy else ordinary["required_tests"])
            },
            "required_tests": ordinary["required_tests"],
            "release_gate_passed": not messy,
        },
        ("ORD-RISK",),
    )
    emit(
        "change_approval",
        "ORD-SECURITY-DECISION",
        "2027-09-15T10:00:00+00:00",
        "AS-P008",
        ordinary,
        "DISTINCT_SECURITY_REVIEW",
        {
            "decision": "HOLD_MISSING_RECOVERY_TEST" if messy else "APPROVE_SELECTED_LOCAL_CHANGE",
            "independent_of_requester_and_executor": True,
            "corporate_policy_approval": False,
        },
        ("ORD-TEST-INITIAL",),
    )
    if messy:
        emit(
            "change_application",
            "ORD-INVALID-APPLY",
            "2027-09-18T10:00:00+00:00",
            "AS-P007",
            ordinary,
            "UNAUTHORIZED_LOCAL_BYPASS_APPLY",
            {
                "applied_value": ordinary["candidate"],
                "approval_gate_satisfied": False,
                "real_device_write": False,
            },
            ("ORD-SECURITY-DECISION",),
        )
        emit(
            "change_verification",
            "ORD-MISMATCH",
            "2027-09-19T10:00:00+00:00",
            "AS-P008",
            ordinary,
            "CONFIGURATION_AND_GATE_MISMATCH",
            {
                "observed_value": ordinary["candidate"],
                "expected_authorized_value": ordinary["baseline"],
                "approval_missing": True,
                "recovery_test_missing": True,
            },
            ("ORD-INVALID-APPLY",),
        )
        emit(
            "exception_register",
            "EXC-ENG005-ORD-01",
            "2027-09-20T10:00:00+00:00",
            "AS-P005",
            ordinary,
            "OPEN_HISTORICAL_ORDINARY_BYPASS",
            {
                "status": "OPEN",
                "cause": "RELEASE_AFTER_HELD_SECURITY_REVIEW",
                "closure_authority_evidenced": False,
            },
            ("ORD-MISMATCH",),
        )
        emit(
            "change_recovery",
            "ORD-ROLLBACK",
            "2027-09-21T10:00:00+00:00",
            "AS-P007",
            ordinary,
            "RESTORE_SELECTED_BASELINE",
            {
                "restored_value": ordinary["rollback"],
                "verified_by": "AS-P008",
                "historical_exception_closed": False,
            },
            ("EXC-ENG005-ORD-01",),
        )
        emit(
            "change_test",
            "ORD-TEST-CORRECTED",
            "2027-09-22T10:00:00+00:00",
            "AS-P007",
            ordinary,
            "COMPLETE_BOUND_TEST_REPERFORMANCE",
            {
                "tested_candidate": ordinary["candidate"],
                "passed_tests": ordinary["required_tests"],
                "test_results": tests,
                "required_tests": ordinary["required_tests"],
                "release_gate_passed": True,
            },
            ("ORD-ROLLBACK",),
        )
        emit(
            "change_approval",
            "ORD-CORRECTED-SECURITY",
            "2027-09-23T10:00:00+00:00",
            "AS-P008",
            ordinary,
            "DISTINCT_CORRECTED_SECURITY_APPROVAL",
            {
                "decision": "APPROVE_SELECTED_LOCAL_CHANGE",
                "historical_exception_closed": False,
                "independent_of_executor": True,
            },
            ("ORD-TEST-CORRECTED",),
        )
        approval = "ORD-CORRECTED-SECURITY"
    else:
        approval = "ORD-SECURITY-DECISION"
    emit(
        "change_release",
        "ORD-RELEASE",
        "2027-09-24T10:00:00+00:00",
        "AS-P014",
        ordinary,
        "SCOPED_LOCAL_RELEASE_DECISION",
        {
            "decision": "APPROVE_SELECTED_NONPERSONAL_CONFIG",
            "security_decision_ref": approval,
            "corporate_policy_approval": False,
        },
        (approval,),
    )
    emit(
        "change_application",
        "ORD-APPLY-APPROVED",
        "2027-09-25T10:00:00+00:00",
        "AS-P007",
        ordinary,
        "FICTIONAL_SELECTED_CONFIG_APPLICATION",
        {
            "applied_value": ordinary["candidate"],
            "release_ref": "ORD-RELEASE",
            "real_device_write": False,
        },
        ("ORD-RELEASE",),
    )
    emit(
        "change_verification",
        "ORD-VERIFY",
        "2027-09-26T10:00:00+00:00",
        "AS-P008",
        ordinary,
        "POST_CHANGE_CONFIG_RECONCILIATION",
        {
            "observed_value": ordinary["candidate"],
            "approved_value": ordinary["candidate"],
            "approved_release_ref": "ORD-RELEASE",
            "local_match": True,
        },
        ("ORD-APPLY-APPROVED",),
    )
    emit(
        "change_recovery",
        "ORD-ROLLBACK-REHEARSAL",
        "2027-09-27T10:00:00+00:00",
        "AS-P007",
        ordinary,
        "DATA_ONLY_ROLLBACK_REHEARSAL",
        {
            "rehearsed_baseline": ordinary["rollback"],
            "restored_active_value": ordinary["candidate"],
            "real_device_write": False,
        },
        ("ORD-VERIFY",),
    )
    emit(
        "change_review",
        "ORD-REVIEW",
        "2027-09-28T10:00:00+00:00",
        "AS-P005",
        ordinary,
        "SELECTED_ORDINARY_CHANGE_REVIEW",
        {
            "current_selected_value": ordinary["candidate"],
            "historical_exception_open": messy,
            "full_population_review": False,
        },
        ("ORD-ROLLBACK-REHEARSAL",),
    )

    emit(
        "change_request",
        "EMG-REQUEST",
        "2027-10-11T10:00:00+00:00",
        "AS-P007",
        emergency,
        "EMERGENCY_CHANGE_REQUEST",
        {
            "reason": "Stale nonpersonal Boise recovery marker retry decision",
            "baseline": emergency["baseline"],
            "candidate": emergency["candidate"],
            "rollback": emergency["rollback"],
            "affected_data": "NONPERSONAL_MARKER_ONLY",
            "requested_bypass_scope": "ONE_SELECTED_BOISE_RETRY_SETTING",
        },
        ("ORD-REVIEW",),
    )
    emit(
        "change_approval",
        "EMG-AUTHORITY-GATE",
        "2027-10-11T12:00:00+00:00",
        "AS-P008",
        emergency,
        "CORPORATE_EMERGENCY_AUTHORITY_CHECK",
        {
            "corporate_emergency_authority_status": "NOT_EVIDENCED_OPEN",
            "decision": "HOLD_NO_AUTHORITY",
            "independent_of_requester": True,
        },
        ("EMG-REQUEST",),
    )
    if messy:
        emit(
            "change_application",
            "EMG-INVALID-BYPASS",
            "2027-10-12T10:00:00+00:00",
            "AS-P007",
            emergency,
            "INVALID_LOCAL_EMERGENCY_BYPASS",
            {
                "applied_value": emergency["candidate"],
                "authority_gate_satisfied": False,
                "real_device_write": False,
            },
            ("EMG-AUTHORITY-GATE",),
        )
        emit(
            "change_verification",
            "EMG-ADVERSE-VERIFY",
            "2027-10-13T10:00:00+00:00",
            "AS-P008",
            emergency,
            "UNAUTHORIZED_SELECTED_CONFIG_OBSERVED",
            {
                "observed_value": emergency["candidate"],
                "authorized_value": emergency["baseline"],
                "gate_bypass_detected": True,
            },
            ("EMG-INVALID-BYPASS",),
        )
        emit(
            "change_recovery",
            "EMG-ROLLBACK",
            "2027-10-14T10:00:00+00:00",
            "AS-P007",
            emergency,
            "RESTORE_BOISE_SELECTED_BASELINE",
            {
                "restored_value": emergency["rollback"],
                "verified_by": "AS-P008",
                "authority_retroactively_granted": False,
            },
            ("EMG-ADVERSE-VERIFY",),
        )
        emit(
            "change_review",
            "EMG-RETROSPECTIVE",
            "2027-10-15T10:00:00+00:00",
            "AS-P008",
            emergency,
            "INDEPENDENT_OF_EXECUTOR_RETROSPECTIVE",
            {
                "decision": "INVALID_BYPASS_RETAIN_AND_ESCALATE",
                "independent_of_executor": True,
                "emergency_authority_established": False,
            },
            ("EMG-ROLLBACK",),
        )
        emit(
            "exception_register",
            "EXC-ENG005-EMG-01",
            "2027-10-16T10:00:00+00:00",
            "AS-P005",
            emergency,
            "OPEN_HISTORICAL_EMERGENCY_BYPASS",
            {
                "status": "OPEN",
                "cause": "EXECUTION_AFTER_MISSING_AUTHORITY",
                "rollback_completed": True,
                "closure_authority_evidenced": False,
            },
            ("EMG-RETROSPECTIVE",),
        )
    else:
        emit(
            "change_review",
            "EMG-BLOCKED-REVIEW",
            "2027-10-12T10:00:00+00:00",
            "AS-P005",
            emergency,
            "UNEXECUTED_EMERGENCY_REQUEST_REVIEW",
            {
                "decision": "RETAIN_HOLD_REQUEST_AUTHORITY_DECISION",
                "current_selected_value": emergency["baseline"],
                "emergency_authority_established": False,
            },
            ("EMG-AUTHORITY-GATE",),
        )
    return rows


def _provenance(scenario: str) -> dict:
    return {
        "source_reference": SOURCE_REFERENCE,
        "scenario": scenario,
        "qualification": "FICTIONAL_SELECTED_COMPANY_OPERATION_NO_REAL_DEPLOYMENT_OR_AUDIT_CREDIT",
        "spec_sha256": SPEC_SHA256,
        "canon_sha256": CANON_SHA,
        "historical_prospective_receipt_sha256": HISTORICAL_SHA256,
        "transition_pins": sec.TRANSITION_PINS,
        "transition_review_sha256": sec.TRANSITION_REVIEW_SHA,
    }


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Publish a new private native source, without grants, collection or I/O."""
    destination = Path(destination).absolute()
    sec._private(destination.parent, directory=True)
    if destination.exists() or destination.is_symlink() or destination != destination.resolve():
        raise CompanyStoreError("New private ENG005 destination required")
    context = _context(repository, private_repository)
    with tempfile.TemporaryDirectory(
        prefix=".eng005-operated-stage-", dir=destination.parent
    ) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in BRANCHES.items():
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            records[scenario] = []
            for row in _rows(context, scenario):
                ref = store.append_version(
                    COMPANY,
                    branch,
                    row["system"],
                    row["record"],
                    expected_version=0,
                    command_id=f"E5O-{branch}-{row['record']}",
                    event_at=row["event_at"],
                    available_at=row["available_at"],
                    content=row["content"],
                    provenance=_provenance(scenario),
                )
                if ref["sha256"] != row["sha256"]:
                    raise CompanyStoreError("ENG005 native bytes differ")
                records[scenario].append(ref)
        receipt = {
            "schema": SCHEMA,
            "company": COMPANY,
            "branches": BRANCHES,
            "records": records,
            "selected_service_id": context["spec"]["service_id"],
            "selected_population": context["spec"]["selected_population"],
            "selected_period": context["spec"]["selected_period"],
            "source_pins": {SPEC: SPEC_SHA256, **CANON_SHA},
            "historical_prospective_receipt_path": HISTORICAL_PROSPECTIVE,
            "historical_prospective_receipt_sha256": HISTORICAL_SHA256,
            "historical_exercise_is_operating_source": False,
            "transition_pins": sec.TRANSITION_PINS,
            "transition_review_sha256": sec.TRANSITION_REVIEW_SHA,
            "upstream_transition_site_release_refs": context["releases"],
            "native_version_counts": {side: len(rows) for side, rows in records.items()},
            "open_exception_counts": {"CLEAN": 0, "MESSY": 2},
            "open_exception_ids": {
                "CLEAN": [],
                "MESSY": ["EXC-ENG005-ORD-01", "EXC-ENG005-EMG-01"],
            },
            "corporate_emergency_authority_status": "NOT_EVIDENCED_OPEN",
            "full_period_or_enterprise_change_population_complete": False,
            "source_complete": False,
            "authored_eng005_clause_satisfied": False,
            "real_deployment": False,
            "actual_phi": False,
            "external_packets_or_writes": 0,
            "enterprise_policy_approved": False,
            "audit_task_credit": False,
            "limits": LIMITS,
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _digest(stage / "RECEIPT.json"),
            "db_sha256": _digest(stage / "company.sqlite3"),
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": sum(len(rows) for rows in records.values()),
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return manifest


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Reperform pinned source history, exact native bytes, clocks and claim limits."""
    root = sec._private(destination, directory=True)
    paths = {name: root / name for name in ("MANIFEST.json", "RECEIPT.json", "company.sqlite3")}
    before = sec._frozen(paths)
    if {path.name for path in root.iterdir()} != set(paths):
        raise CompanyStoreError("Exact private ENG005 three-file source required")
    manifest = json.loads(paths["MANIFEST.json"].read_text())
    receipt = json.loads(paths["RECEIPT.json"].read_text())
    context = _context(repository, private_repository)
    expected = {side: _rows(context, side) for side in BRANCHES}
    counts = {side: len(rows) for side, rows in expected.items()}
    if (
        manifest.get("schema") != SCHEMA + "_MANIFEST"
        or manifest.get("receipt_sha256") != before["RECEIPT.json"][-1]
        or manifest.get("db_sha256") != before["company.sqlite3"][-1]
        or manifest.get("module_sha256") != _digest(Path(__file__))
        or manifest.get("native_version_count") != sum(counts.values())
        or manifest.get("audit_task_credit") is not False
        or receipt.get("schema") != SCHEMA
        or receipt.get("company") != COMPANY
        or receipt.get("branches") != BRANCHES
        or receipt.get("selected_service_id") != context["spec"]["service_id"]
        or receipt.get("selected_population") != context["spec"]["selected_population"]
        or receipt.get("selected_period") != context["spec"]["selected_period"]
        or receipt.get("source_pins") != {SPEC: SPEC_SHA256, **CANON_SHA}
        or receipt.get("historical_prospective_receipt_path") != HISTORICAL_PROSPECTIVE
        or receipt.get("historical_prospective_receipt_sha256") != HISTORICAL_SHA256
        or receipt.get("historical_exercise_is_operating_source") is not False
        or receipt.get("transition_pins") != sec.TRANSITION_PINS
        or receipt.get("transition_review_sha256") != sec.TRANSITION_REVIEW_SHA
        or receipt.get("upstream_transition_site_release_refs") != context["releases"]
        or receipt.get("native_version_counts") != counts
        or receipt.get("open_exception_counts") != {"CLEAN": 0, "MESSY": 2}
        or receipt.get("open_exception_ids")
        != {"CLEAN": [], "MESSY": ["EXC-ENG005-ORD-01", "EXC-ENG005-EMG-01"]}
        or receipt.get("corporate_emergency_authority_status") != "NOT_EVIDENCED_OPEN"
        or any(
            receipt.get(key) is not False
            for key in (
                "full_period_or_enterprise_change_population_complete",
                "source_complete",
                "authored_eng005_clause_satisfied",
                "real_deployment",
                "actual_phi",
                "enterprise_policy_approved",
                "audit_task_credit",
            )
        )
        or receipt.get("external_packets_or_writes") != 0
        or receipt.get("limits") != LIMITS
        or set(receipt.get("records", {})) != set(BRANCHES)
    ):
        raise CompanyStoreError("ENG005 manifest/receipt scope differs")
    with closing(
        sqlite3.connect(paths["company.sqlite3"].as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("ENG005 native DB integrity differs")
        if db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != sum(counts.values()) or any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections", "access_events")
        ):
            raise CompanyStoreError("ENG005 native/access population differs")
        systems = {
            (COMPANY, branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in SYSTEM_OWNERS.items()
        }
        if {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        } != systems:
            raise CompanyStoreError("ENG005 source owner roster differs")
        for side, branch in BRANCHES.items():
            refs = receipt["records"][side]
            if len(refs) != counts[side]:
                raise CompanyStoreError("ENG005 receipt count differs")
            for row, ref in zip(expected[side], refs, strict=True):
                native = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? "
                    "AND system=? AND record=? AND version=1",
                    (COMPANY, branch, row["system"], row["record"]),
                ).fetchone()
                if native is None or native["content"] != row["content"]:
                    raise CompanyStoreError("ENG005 raw native record differs")
                if (
                    native["sha256"] != row["sha256"]
                    or native["event_at"] != row["event_at"]
                    or native["available_at"] != row["available_at"]
                    or json.loads(native["provenance"]) != _provenance(side)
                    or native["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or native["command_id"] != f"E5O-{branch}-{row['record']}"
                    or native["imported_at"] >= "2027-01-01"
                    or _time(native["imported_at"]) != native["imported_at"]
                    or ref != CompanyStore._metadata(native)
                ):
                    raise CompanyStoreError("ENG005 native tuple/clocks/provenance differ")
    if sec._frozen(paths) != before:
        raise CompanyStoreError("ENG005 source changed during immutable read")
    return {
        "status": "VERIFIED_FICTIONAL_SELECTED_CHANGE_NO_AUDIT_CREDIT",
        "native_version_counts": counts,
    }
