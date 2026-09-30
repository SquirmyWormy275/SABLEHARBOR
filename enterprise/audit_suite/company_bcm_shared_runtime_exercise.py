"""Selected fictional 2027 shared-runtime BIA and payload-free recovery history."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import tempfile
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from . import company_runtime_transition_exercise as transition
from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_SELECTED_BCM_V1"
COMPANY = transition.COMPANY
AS_OF = "2026-09-29"
QUALIFICATION = "FUTURE_FICTIONAL_SELECTED_SHARED_RUNTIME_NO_REAL_OPERATION_OR_AUDIT_CREDIT"
SOURCE_REF = "enterprise/audit_suite/company_bcm_shared_runtime_exercise.py"
TRANSITION_REL = "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/run-v3"
TRANSITION_REVIEW_REL = (
    "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/"
    "independent-review-v3/REVIEW.json"
)
MATRIX_REL = (
    "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/run-v2/MATRIX.json"
)
MATRIX_REVIEW_REL = (
    "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/"
    "independent-review-v2/REVIEW.json"
)
PRIVATE_PINS = {
    f"{TRANSITION_REL}/MANIFEST.json": (
        "f7c6ec3ab460f204f69cf6b50df66399687034b3b63cb38aaee84841daedcbd4"
    ),
    f"{TRANSITION_REL}/RECEIPT.json": (
        "0a0a448f619e490870f69959d196eb6d5ca3747af0d4fb68056195910ce6cc11"
    ),
    f"{TRANSITION_REL}/company.sqlite3": (
        "428b5c740cb8fc627b38f2aa6847e450fd166e62be52a6309d4f5a7b284988fd"
    ),
    TRANSITION_REVIEW_REL: "f1acaeaea963055f99b0de120fd1b0347ee984edf085d353e7af1e427234d5a9",
    MATRIX_REL: "e9477d2074bebce185e412a3ee7c424ded395c1a1128a7c918a94f6acbd1e327",
    MATRIX_REVIEW_REL: "c4064f6217c0e7f69276adc71004d6da7971867ccf3d844a3e198145cec31ace",
}
TRACKED_PINS = {
    "docs/canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.3.1.md": (
        "5bc15670b1d7c3c98d754329a0fad44bd4a82ea7db977bfa064b5db80062b2f7"
    ),
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md": (
        "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751"
    ),
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md": (
        "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496"
    ),
    "enterprise/services/source/services.json": (
        "f9cd08b7add29b7be6c51670bf0c92bcca4b582e9853d83d25d518171da75818"
    ),
    "enterprise/services/source/runtime_sites_2026-09-11.json": (
        "fa216f629762503865fd9f1a3207e87691cd484cec9885bf25ce045b4525519c"
    ),
    "enterprise/audit_suite/runtime_transition_contract_spec_v3.json": (
        "95b92ac2870a1097c39691d33a7553e4598eb114eaf89a74a405ee1833d03dc1"
    ),
    "enterprise/audit_suite/BCM_SHARED_RUNTIME_2027_PROPOSAL.md": (
        "7cf852d956a4a74b9e618f1ea9321d5bb5336ad5bd102a8da643475a9e75244a"
    ),
}
BRANCHES = {"CLEAN": "BCM-CLEAN", "MESSY": "BCM-MESSY"}
OWNERS = {
    "authority_decision": "P001",
    "service_inventory": "AS-P007",
    "demand_forecast": "AS-P007",
    "technical_objectives": "AS-P007",
    "business_impact": "AS-P001",
    "exercise_plan": "AS-P001",
    "exercise_result": "AS-P007",
    "exercise_review": "AS-P001",
    "corrective_action": "AS-P007",
    "closure_gate": "AS-P001",
}
EXCEPTION_ID = transition.EXCEPTION_ID
RTO_MINUTES = 240
RPO_MINUTES = 15
LIMITS = [
    "Future 2027 source event/availability times are authored simulation; "
    "imported_at is actual insertion.",
    "One selected shared-service BIA and marker exercise, not enterprise "
    "or annual continuity population.",
    "No product/customer RTO or RPO, real provider operation, actual PHI/ePHI "
    "emergency access, supplier participation, audit grant, collection, "
    "workpaper, task, Key or grade.",
    "Messy key-bypass and capacity treatment remain open after local numeric "
    "retest; no risk acceptance or finding closure.",
]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private_file(path: Path) -> None:
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_nlink != 1
        or path.stat().st_mode & 0o077
        or any(p.is_symlink() for p in path.parents)
    ):
        raise CompanyStoreError("Ordinary private source file required")


def _frozen_identity(path: Path) -> tuple:
    _private_file(path)
    if any(
        Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Frozen native database has SQLite sidecar")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise CompanyStoreError("Frozen native database must be regular")
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IMODE(info.st_mode),
        info.st_size,
        info.st_mtime_ns,
        _digest(path),
    )


def _selected_transition(trans: dict, root: Path) -> dict:
    """Rejoin exact reviewed receipt tuples to immutable source rows and selected facts."""
    chosen = {
        "CLEAN": (("C-RENO", 1), ("C-BOISE", 1), ("RL-RENO", 1), ("RX-BOISE", 1), ("RL-BOISE", 1)),
        "MESSY": (
            ("C-RENO", 1),
            ("C-BOISE", 1),
            ("RL-RENO", 1),
            ("RX-BOISE", 1),
            ("EX-BOISE", 2),
            ("RX-BOISE", 2),
            ("RL-BOISE", 1),
        ),
    }
    db_path = root / TRANSITION_REL / "company.sqlite3"
    before = _frozen_identity(db_path)
    selected = {}
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Transition native database integrity failure")
        for scenario, names in chosen.items():
            selected[scenario] = {}
            for record, version in names:
                matches = [
                    r
                    for r in trans["records"][scenario]
                    if r["record"] == record and r["version"] == version
                ]
                if len(matches) != 1:
                    raise CompanyStoreError(
                        "Selected transition receipt tuple missing or duplicated"
                    )
                ref = matches[0]
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    (ref["company"], ref["branch"], ref["system"], record, version),
                ).fetchone()
                if (
                    row is None
                    or sha(row["content"]) != ref["sha256"]
                    or row["sha256"] != ref["sha256"]
                ):
                    raise CompanyStoreError("Selected transition native tuple hash differs")
                if any(row[k] != ref[k] for k in ("event_at", "available_at", "imported_at")):
                    raise CompanyStoreError("Selected transition three-clock join differs")
                body = json.loads(row["content"])
                expected_status = {
                    "C-RENO": "EXECUTED_SIMULATED",
                    "C-BOISE": "EXECUTED_SIMULATED",
                    "RL-RENO": "OPERATING_PRIMARY_SIMULATED",
                    "RL-BOISE": "OPERATING_RECOVERY_WITH_OPEN_EXCEPTION_SIMULATED"
                    if scenario == "MESSY"
                    else "OPERATING_RECOVERY_SIMULATED",
                    "RX-BOISE": "FAIL_KEY_DEPENDENCY"
                    if scenario == "MESSY" and version == 1
                    else ("PASS_AFTER_RETRY" if scenario == "MESSY" else "PASS"),
                    "EX-BOISE": "QUARANTINED_MARKER",
                }[record]
                if (
                    body["status"] != expected_status
                    or body["real_world_provider_operation"] is not False
                ):
                    raise CompanyStoreError(
                        "Selected transition status or real-world limit differs"
                    )
                if record == "EX-BOISE" and (
                    body["exception_id"] != EXCEPTION_ID or body["exception_open"] is not True
                ):
                    raise CompanyStoreError("Historical Boise bypass exception was lost")
                if record.startswith("C-"):
                    capacity = body["fictional_executed_terms"]["site_order"]["usable_it_kw"]
                    if capacity != (75 if record == "C-RENO" else 25):
                        raise CompanyStoreError("Selected synthetic contract capacity changed")
                selected[scenario][(record, version)] = {
                    "ref": {
                        k: ref[k]
                        for k in (
                            "company",
                            "branch",
                            "system",
                            "record",
                            "version",
                            "event_at",
                            "available_at",
                            "sha256",
                        )
                    },
                    "body": body,
                }
    if _frozen_identity(db_path) != before:
        raise CompanyStoreError("Frozen transition database changed during read")
    return selected


def _context(repository: Path, private_repository: Path) -> tuple[dict, dict, dict]:
    repository, private_repository = repository.resolve(), private_repository.resolve()
    pins = {}
    for relative, expected in TRACKED_PINS.items():
        path = repository / relative
        if not path.is_file() or path.is_symlink() or _digest(path) != expected:
            raise CompanyStoreError(f"Pinned tracked BCM source differs: {relative}")
        pins[f"repo://{relative}"] = expected
    appointments = (repository / "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md").read_text()
    lore = (repository / "docs/canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.3.1.md").read_text()
    if (
        not all(
            x in appointments
            for x in (
                "AS-P001 | Lila Kestrel | Chief of Enterprise Support Services",
                "AS-P007 | Elliot Tran | Head of Enterprise Technology Services",
                "AS-P004 | Nina Rowan | Corporate Secretary",
            )
        )
        or "founder, CEO, and director Daniel" not in lore
    ):
        raise CompanyStoreError("BCM authority canon differs")
    services = json.loads((repository / "enterprise/services/source/services.json").read_text())
    if "SVC-compute" not in str(services) or "SVC-backup" not in str(services):
        raise CompanyStoreError("Selected shared-service dependency absent")
    for relative, expected in PRIVATE_PINS.items():
        path = private_repository / relative
        _private_file(path)
        if _digest(path) != expected:
            raise CompanyStoreError(f"Pinned private BCM input differs: {relative}")
        pins[f"private://{relative}"] = expected
    if (
        json.loads((private_repository / TRANSITION_REVIEW_REL).read_text()).get("verdict")
        != "PASS_PRIVATE_FICTIONAL_SOURCE_FOR_INTEGRATION_REVIEW"
    ):
        raise CompanyStoreError("Transition independent review missing")
    if (
        json.loads((private_repository / MATRIX_REVIEW_REL).read_text()).get("verdict")
        != "PASS_READ_ONLY_CANDIDATE_MATRIX_FOR_INTEGRATION"
    ):
        raise CompanyStoreError("Route matrix independent review missing")
    _frozen_identity(private_repository / TRANSITION_REL / "company.sqlite3")
    transition.verify(private_repository / TRANSITION_REL, repository=repository)
    trans = json.loads((private_repository / TRANSITION_REL / "RECEIPT.json").read_text())
    selected = _selected_transition(trans, private_repository)
    matrix = json.loads((private_repository / MATRIX_REL).read_text())
    routes = {}
    for side in "AB":
        controls = [
            c
            for family in matrix["sides"][side]["families"]
            for c in family["controls"]
            if c["control_id"] in {"SH-BCM-001", "SH-BCM-004"}
        ]
        if {c["control_id"]: len(c["tasks"]) for c in controls} != {
            "SH-BCM-001": 5,
            "SH-BCM-004": 6,
        }:
            raise CompanyStoreError("Frozen eleven-route BCM cohort differs")
        if any(
            t["current_status"] != "NOT_STARTED"
            or t["current_conclusion"] != "NOT_RUN"
            or t["task_credit"] is not False
            for c in controls
            for t in c["tasks"]
        ):
            raise CompanyStoreError("BCM cohort already credited")
        routes[side] = {c["control_id"]: [t["task_id"] for t in c["tasks"]] for c in controls}
    return pins, selected, routes


def _steps(scenario: str) -> list[dict]:
    if scenario not in BRANCHES:
        raise CompanyStoreError("Unknown BCM branch")
    messy = scenario == "MESSY"
    steps = [
        dict(
            system="authority_decision",
            record="SELECTED-SERVICE",
            version=1,
            at="2027-04-01T10:00:00+00:00",
            status="BOUNDED_FICTIONAL_DELEGATION",
            actor="P001",
            refs=(),
            prior=(),
            detail={
                "issuer": "Daniel, CEO (surname unstated in canon)",
                "delegate": "AS-P001",
                "technical_owner": "AS-P007",
                "scope": "SVC-compute selected corporate shared-runtime BIA only",
                "excludes": [
                    "product owner commitments",
                    "customer SLA",
                    "ePHI emergency-mode authorization",
                    "enterprise risk acceptance",
                ],
            },
        ),
        dict(
            system="service_inventory",
            record="SVC-COMPUTE",
            version=1,
            at="2027-04-05T10:00:00+00:00",
            status="SELECTED_DEPENDENCIES_RECORDED",
            actor="AS-P007",
            refs=(("C-RENO", 1), ("C-BOISE", 1)),
            prior=("SELECTED-SERVICE",),
            detail={
                "service_id": "SVC-compute",
                "dependencies": ["SVC-backup", "RUNTIME-RENO-COLO", "RUNTIME-BOISE-DR"],
                "usable_it_kw": {"RENO": 75, "BOISE": 25},
                "population": "ONE_SELECTED_CORPORATE_SHARED_RUNTIME_NOT_ALL_BUSINESS_PRODUCTS",
            },
        ),
        dict(
            system="demand_forecast",
            record="SVC-COMPUTE",
            version=1,
            at="2027-04-10T10:00:00+00:00",
            status="SCENARIO_FORECAST_NOT_METERED_UTILIZATION",
            actor="AS-P007",
            refs=(),
            prior=("SVC-COMPUTE:service_inventory:1",),
            detail={
                "expected_kw": {"RENO": 50 if messy else 42, "BOISE": 19 if messy else 16},
                "peak_kw": {"RENO": 68 if messy else 58, "BOISE": 23 if messy else 20},
                "action_threshold_kw": {"RENO": 60, "BOISE": 22.5},
                "threshold_exceeded": messy,
                "measurement_status": "NOT_OBSERVED_SCENARIO_FORECAST",
            },
        ),
        dict(
            system="technical_objectives",
            record="SVC-COMPUTE",
            version=1,
            at="2027-04-12T10:00:00+00:00",
            status="CAPACITY_TREATMENT_PENDING"
            if messy
            else "LOCAL_TECHNICAL_FEASIBILITY_RECOMMENDED",
            actor="AS-P007",
            refs=(),
            prior=("SVC-COMPUTE:demand_forecast:1",),
            detail={
                "proposed_rto_minutes": RTO_MINUTES,
                "proposed_rpo_minutes": RPO_MINUTES,
                "recovery_priority": "SHARED_RUNTIME_MARKER_FIRST",
                "capacity_action": "EXPAND_OR_REDUCE_DEMAND_PENDING_AUTHORITY"
                if messy
                else "MONITOR_BELOW_LOCAL_THRESHOLDS",
                "real_recovery_performance_proven": False,
            },
        ),
        dict(
            system="business_impact",
            record="SVC-COMPUTE",
            version=1,
            at="2027-04-15T10:00:00+00:00",
            status="HELD_PENDING_CAPACITY_TREATMENT"
            if messy
            else "LOCAL_SELECTED_SERVICE_OBJECTIVES_ACCEPTED_SIMULATED",
            actor="AS-P001",
            refs=(),
            prior=("SELECTED-SERVICE", "SVC-COMPUTE:technical_objectives:1"),
            detail={
                "tolerable_interruption_minutes": RTO_MINUTES,
                "rto_minutes": RTO_MINUTES,
                "rpo_minutes": RPO_MINUTES,
                "accepted_local_objectives": not messy,
                "business_unit_and_customer_objectives_accepted": False,
                "capacity_treatment_open": messy,
            },
        ),
    ]
    exercise_at = "2027-08-20T15:10:00+00:00" if messy else "2027-08-15T12:35:00+00:00"
    steps.extend(
        [
            dict(
                system="exercise_plan",
                record="MARKER-RECOVERY",
                version=1,
                at="2027-08-18T10:00:00+00:00" if messy else "2027-08-12T10:00:00+00:00",
                status="SELECTED_DIAGNOSTIC_AUTHORIZED_NO_BIA_WAIVER"
                if messy
                else "SELECTED_MARKER_EXERCISE_AUTHORIZED",
                actor="AS-P001",
                refs=(("RL-RENO", 1), ("RL-BOISE", 1)),
                prior=("SVC-COMPUTE:business_impact:1",),
                detail={
                    "scope": "ONE_NONPERSONAL_PAYLOAD_FREE_MARKER",
                    "approved_emergency_ephi_access": False,
                    "supplier_or_customer_participation": False,
                    "rto_rpo_basis": "PROPOSED_ONLY"
                    if messy
                    else "LOCALLY_ACCEPTED_SELECTED_SERVICE",
                },
            ),
            dict(
                system="exercise_result",
                record="MARKER-RECOVERY",
                version=1,
                at=exercise_at,
                status="FAIL_KEY_DEPENDENCY_AND_NUMERIC_TARGETS"
                if messy
                else "PASS_SELECTED_MARKER_TARGETS",
                actor="AS-P007",
                refs=(("RX-BOISE", 1), ("EX-BOISE", 2), ("RX-BOISE", 2))
                if messy
                else (("RX-BOISE", 1),),
                prior=("MARKER-RECOVERY:exercise_plan:1",),
                detail={
                    "exercise_start_at": _time(
                        "2027-08-20T10:00:00+00:00" if messy else "2027-08-15T10:00:00+00:00"
                    ),
                    "observed_finish_at": _time(exercise_at),
                    "measured_restore_minutes_simulated": 310 if messy else 155,
                    "measured_replay_gap_minutes_simulated": 22 if messy else 8,
                    "marker_digest_match": not messy,
                    "rto_target_minutes": RTO_MINUTES,
                    "rpo_target_minutes": RPO_MINUTES,
                    "numeric_targets_met": not messy,
                    "data_usability": "NOT_VERIFIED_KEY_DEPENDENCY"
                    if messy
                    else "SELECTED_MARKER_READABLE",
                    "historical_bypass_exception_id": EXCEPTION_ID if messy else None,
                    "historical_bypass_exception_open": messy,
                    "key_failure_context": (
                        "POST_RELEASE_ROTATION_PATH_REGRESSION_AFTER_PRIOR_LOCAL_RETRY"
                        if messy
                        else None
                    ),
                    "real_application_restored": False,
                },
            ),
        ]
    )
    if messy:
        steps.extend(
            [
                dict(
                    system="corrective_action",
                    record="KEY-AND-CAPACITY",
                    version=1,
                    at="2027-08-21T10:00:00+00:00",
                    status="OPEN_TREATMENT_REQUEST",
                    actor="AS-P007",
                    refs=(("EX-BOISE", 2),),
                    prior=("MARKER-RECOVERY:exercise_result:1",),
                    detail={
                        "actions": [
                            "prove independent key recovery",
                            "address Reno and Boise forecast threshold exceedance",
                        ],
                        "risk_acceptance": "NOT_PERFORMED",
                        "historical_bypass_exception_open": True,
                    },
                ),
                dict(
                    system="exercise_result",
                    record="MARKER-RECOVERY",
                    version=2,
                    at="2027-08-23T13:00:00+00:00",
                    status="LOCAL_NUMERIC_RETEST_PASS_EXCEPTION_OPEN",
                    actor="AS-P007",
                    refs=(("RX-BOISE", 2), ("EX-BOISE", 2)),
                    prior=(
                        "MARKER-RECOVERY:exercise_result:1",
                        "KEY-AND-CAPACITY:corrective_action:1",
                    ),
                    detail={
                        "exercise_start_at": _time("2027-08-23T10:00:00+00:00"),
                        "observed_finish_at": _time("2027-08-23T13:00:00+00:00"),
                        "measured_restore_minutes_simulated": 180,
                        "measured_replay_gap_minutes_simulated": 10,
                        "marker_digest_match": True,
                        "rto_target_minutes": RTO_MINUTES,
                        "rpo_target_minutes": RPO_MINUTES,
                        "numeric_targets_met": True,
                        "data_usability": "SELECTED_MARKER_READABLE_ONLY",
                        "historical_bypass_exception_id": EXCEPTION_ID,
                        "historical_bypass_exception_open": True,
                        "capacity_treatment_open": True,
                        "bia_accepted": False,
                    },
                ),
                dict(
                    system="closure_gate",
                    record="KEY-AND-CAPACITY",
                    version=1,
                    at="2027-08-24T10:00:00+00:00",
                    status="DENIED_PENDING_AUTHORITY_AND_VALIDATION",
                    actor="AS-P001",
                    refs=(("EX-BOISE", 2),),
                    prior=("MARKER-RECOVERY:exercise_result:2",),
                    detail={
                        "historical_bypass_exception_open": True,
                        "capacity_treatment_open": True,
                        "bia_accepted": False,
                        "corrective_action_validated": False,
                        "risk_acceptance": "NOT_PERFORMED",
                    },
                ),
            ]
        )
    else:
        steps.append(
            dict(
                system="exercise_review",
                record="MARKER-RECOVERY",
                version=1,
                at="2027-08-16T10:00:00+00:00",
                status="SELECTED_EXERCISE_READOUT_ONLY",
                actor="AS-P001",
                refs=(),
                prior=("MARKER-RECOVERY:exercise_result:1",),
                detail={
                    "selected_numeric_result": "PASS",
                    "full_year_or_ephi_claim": False,
                    "customer_participation": False,
                    "corrective_action_closure_claim": False,
                },
            )
        )
    return steps


def _expected(scenario: str, selected: dict) -> list[tuple[dict, bytes]]:
    own = {}
    output = []
    for step in _steps(scenario):
        at = _time(step["at"])
        if step["system"] == "exercise_result":
            detail = step["detail"]
            start = datetime.fromisoformat(detail["exercise_start_at"])
            finish = datetime.fromisoformat(detail["observed_finish_at"])
            if (
                _time(detail["observed_finish_at"]) != at
                or (finish - start).total_seconds()
                != 60 * detail["measured_restore_minutes_simulated"]
            ):
                raise CompanyStoreError("BCM exercise measurement clock differs")
        refs = [selected[scenario][key]["ref"] for key in step["refs"]]
        if any(ref["available_at"] >= at for ref in refs):
            raise CompanyStoreError("BCM event precedes reviewed transition availability")
        prior = {}
        for name in step["prior"]:
            if name not in own:
                raise CompanyStoreError("BCM prior local source unavailable")
            if own[name]["at"] >= at:
                raise CompanyStoreError("BCM prior local event is not earlier")
            prior[name] = own[name]["hash"]
        body = {
            "schema": SCHEMA,
            "scenario": scenario,
            "system": step["system"],
            "record": step["record"],
            "version": step["version"],
            "status": step["status"],
            "event_at": at,
            "available_at": at,
            "actor_person_id": step["actor"],
            "system_custodian_person_id": OWNERS[step["system"]],
            "selected_service_id": "SVC-compute",
            "site_capacity_source_refs": refs,
            "local_prior_source_sha256": prior,
            "detail": step["detail"],
            "as_of": AS_OF,
            "real_world_operation": False,
            "actual_phi_processing": False,
            "audit_task_credit": False,
            "qualification": QUALIFICATION,
        }
        content = encoded(body)
        key = f"{step['record']}:{step['system']}:{step['version']}"
        own[key] = {"at": at, "hash": sha(content)}
        if step["system"] == "authority_decision":
            own["SELECTED-SERVICE"] = own[key]
        output.append((step, content))
    return output


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or destination.is_symlink()
        or destination != destination.resolve()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(p.is_symlink() for p in destination.parents)
    ):
        raise CompanyStoreError("New private BCM destination and parent required")
    pins, selected, routes = _context(Path(repository), Path(private_repository))
    with tempfile.TemporaryDirectory(prefix=".bcm-selected-", dir=destination.parent) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in BRANCHES.items():
            for system, owner in OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            records[scenario] = []
            for step, content in _expected(scenario, selected):
                ref = store.append_version(
                    COMPANY,
                    branch,
                    step["system"],
                    step["record"],
                    expected_version=step["version"] - 1,
                    command_id=f"BCM-{branch}-{step['system']}-{step['record']}-V{step['version']}",
                    event_at=step["at"],
                    available_at=step["at"],
                    content=content,
                    provenance={
                        "source_reference": SOURCE_REF,
                        "source_pins": pins,
                        "scenario": scenario,
                        "qualification": QUALIFICATION,
                    },
                )
                records[scenario].append(ref)
        receipt = {
            "schema": SCHEMA,
            "status": "FUTURE_FICTIONAL_SELECTED_BCM_SOURCE_NO_AUDIT_CREDIT",
            "as_of": AS_OF,
            "company": COMPANY,
            "branches": BRANCHES,
            "source_pins": pins,
            "selected_route_task_ids": routes,
            "records": records,
            "selected_population": {
                "services": 1,
                "site_capacity_inputs": 2,
                "demand_forecasts_per_branch": 1,
                "selected_exercises_per_branch": 1,
                "messy_retests": 1,
            },
            "limits": LIMITS,
            "audit_task_credit": False,
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _digest(stage / "RECEIPT.json"),
            "company_db_sha256": _digest(stage / "company.sqlite3"),
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": sum(map(len, records.values())),
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private_repository)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    root = Path(destination).absolute()
    if (
        root != root.resolve()
        or not root.is_dir()
        or root.stat().st_mode & 0o077
        or any(p.is_symlink() for p in (root, *root.parents))
        or {p.name for p in root.iterdir()} != {"RECEIPT.json", "MANIFEST.json", "company.sqlite3"}
    ):
        raise CompanyStoreError("Private ordinary three-file BCM source required")
    for name in ("RECEIPT.json", "MANIFEST.json", "company.sqlite3"):
        _private_file(root / name)
    db_before = _frozen_identity(root / "company.sqlite3")
    manifest = json.loads((root / "MANIFEST.json").read_text())
    receipt = json.loads((root / "RECEIPT.json").read_text())
    pins, selected, routes = _context(Path(repository), Path(private_repository))
    expected = {scenario: _expected(scenario, selected) for scenario in BRANCHES}
    count = sum(map(len, expected.values()))
    if manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "receipt_sha256": _digest(root / "RECEIPT.json"),
        "company_db_sha256": _digest(root / "company.sqlite3"),
        "module_sha256": _digest(Path(__file__)),
        "native_version_count": count,
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("BCM manifest differs")
    if any(
        (receipt.get(k) != v)
        for k, v in {
            "schema": SCHEMA,
            "status": "FUTURE_FICTIONAL_SELECTED_BCM_SOURCE_NO_AUDIT_CREDIT",
            "as_of": AS_OF,
            "company": COMPANY,
            "branches": BRANCHES,
            "source_pins": pins,
            "selected_route_task_ids": routes,
            "selected_population": {
                "services": 1,
                "site_capacity_inputs": 2,
                "demand_forecasts_per_branch": 1,
                "selected_exercises_per_branch": 1,
                "messy_retests": 1,
            },
            "limits": LIMITS,
            "audit_task_credit": False,
        }.items()
    ) or set(receipt.get("records", {})) != set(BRANCHES):
        raise CompanyStoreError("BCM receipt scope differs")
    with closing(
        sqlite3.connect((root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("BCM native database integrity failure")
        if any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] != expected_count
            for table, expected_count in (
                ("versions", count),
                ("systems", len(OWNERS) * 2),
                ("grants", 0),
                ("access_events", 0),
                ("collections", 0),
            )
        ):
            raise CompanyStoreError("BCM native population or audit journal differs")
        for scenario, branch in BRANCHES.items():
            rows = db.execute(
                "SELECT * FROM versions WHERE company=? AND branch=? ORDER BY rowid",
                (COMPANY, branch),
            ).fetchall()
            if len(rows) != len(expected[scenario]) or len(receipt["records"][scenario]) != len(
                rows
            ):
                raise CompanyStoreError("BCM selected branch population differs")
            for row, (step, content), ref in zip(
                rows, expected[scenario], receipt["records"][scenario], strict=True
            ):
                if any(
                    row[k] != v
                    for k, v in (
                        ("system", step["system"]),
                        ("record", step["record"]),
                        ("version", step["version"]),
                        ("event_at", _time(step["at"])),
                        ("available_at", _time(step["at"])),
                        ("origin", "AUTHORED_TRAINING_SOURCE"),
                        ("sha256", sha(content)),
                        ("content", content),
                    )
                ):
                    raise CompanyStoreError("BCM native event/content/clock differs")
                if json.loads(row["provenance"]) != {
                    "source_reference": SOURCE_REF,
                    "source_pins": pins,
                    "scenario": scenario,
                    "qualification": QUALIFICATION,
                }:
                    raise CompanyStoreError("BCM native provenance differs")
                expected_ref = {
                    k: json.loads(row[k]) if k == "provenance" else row[k]
                    for k in (
                        "company",
                        "branch",
                        "system",
                        "record",
                        "version",
                        "event_at",
                        "available_at",
                        "imported_at",
                        "origin",
                        "provenance",
                        "sha256",
                    )
                }
                if ref != expected_ref:
                    raise CompanyStoreError("BCM receipt/native tuple join differs")
                command = f"BCM-{branch}-{step['system']}-{step['record']}-V{step['version']}"
                fingerprint_input = [
                    [COMPANY, branch, step["system"], step["record"]],
                    step["version"] - 1,
                    _time(step["at"]),
                    _time(step["at"]),
                    "AUTHORED_TRAINING_SOURCE",
                    expected_ref["provenance"],
                    sha(content),
                ]
                fingerprint = hashlib.sha256(
                    json.dumps(
                        fingerprint_input,
                        sort_keys=True,
                        separators=(",", ":"),
                        allow_nan=False,
                    ).encode()
                ).hexdigest()
                if row["command_id"] != command or row["input_digest"] != fingerprint:
                    raise CompanyStoreError("BCM command provenance differs")
                imported = datetime.fromisoformat(row["imported_at"])
                if (
                    imported.tzinfo is None
                    or imported.astimezone(UTC) > datetime.now(UTC)
                    or imported.date().isoformat() < AS_OF
                ):
                    raise CompanyStoreError("BCM actual import clock invalid")
        systems = {
            (r["branch"], r["system"], r["owner"]) for r in db.execute("SELECT * FROM systems")
        }
        if systems != {
            (branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in OWNERS.items()
        }:
            raise CompanyStoreError("BCM custodian registration differs")
    if _frozen_identity(root / "company.sqlite3") != db_before:
        raise CompanyStoreError("BCM native database changed during read")
    return {
        "schema": SCHEMA + "_VERIFY",
        "native_version_count": count,
        "branch_counts": {s: len(v) for s, v in expected.items()},
        "selected_route_counts": {
            side: sum(map(len, groups.values())) for side, groups in routes.items()
        },
        "audit_task_credit": False,
        "result": "PASS_SELECTED_FICTIONAL_SOURCE_NO_AUDIT_CREDIT",
    }
