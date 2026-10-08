"""Bounded fictional Reno/Boise physical-site history; no real site action."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import stat
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_SELECTED_PHYSICAL_SITE_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
BRANCHES = {"CLEAN": "PHYSICAL-CLEAN", "MESSY": "PHYSICAL-MESSY"}
SOURCE = "enterprise/audit_suite/company_physical_site_2027.py"
SPEC = "enterprise/audit_suite/physical_site_2027_spec_v1.json"
SPEC_SHA256 = "a9a65de2316452ab0d85325b150a3d0777560380426313822fa11fddcc15831c"
ROUTES = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V5_2026-09-30.json"
TRANSITION = "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/run-v3"
TRANSITION_REVIEW = (
    "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/"
    "independent-review-v3/REVIEW.json"
)
BCM = "enterprise/generated/audit-suite/company-bcm-shared-runtime-2026-09-29/run-v2"
BCM_REVIEW = (
    "enterprise/generated/audit-suite/company-bcm-shared-runtime-2026-09-29/"
    "independent-review-v2/REVIEW.json"
)
ROUTE_REVIEW = (
    "enterprise/generated/audit-suite/documentary-283-route-reconciliation-v5-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
TRACKED = {
    ROUTES: "61d16ce933628b7c6bda4b90e5ee5292fd1634d1c9c9e2ac0201a46e02726a10",
    "enterprise/services/source/runtime_sites_2026-09-11.json": (
        "fa216f629762503865fd9f1a3207e87691cd484cec9885bf25ce045b4525519c"
    ),
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md": (
        "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751"
    ),
    "docs/controls/RUNTIME_CONTROL_AND_EVIDENCE_MATRIX_2026-09-11.md": (
        "b8661434b6af1580017fb9351879bee7078073e09094827b797c32c3253cdf9f"
    ),
    "enterprise/services/source/services.json": (
        "f9cd08b7add29b7be6c51670bf0c92bcca4b582e9853d83d25d518171da75818"
    ),
}
PRIVATE = {
    f"{TRANSITION}/RECEIPT.json": (
        "0a0a448f619e490870f69959d196eb6d5ca3747af0d4fb68056195910ce6cc11"
    ),
    f"{TRANSITION}/MANIFEST.json": (
        "f7c6ec3ab460f204f69cf6b50df66399687034b3b63cb38aaee84841daedcbd4"
    ),
    f"{TRANSITION}/company.sqlite3": (
        "428b5c740cb8fc627b38f2aa6847e450fd166e62be52a6309d4f5a7b284988fd"
    ),
    TRANSITION_REVIEW: "f1acaeaea963055f99b0de120fd1b0347ee984edf085d353e7af1e427234d5a9",
    f"{BCM}/RECEIPT.json": "3cd0b62de445cde7c1a76f61a156fb0fd5fa9c443cf3255ca85876b6f2c4de9a",
    f"{BCM}/MANIFEST.json": "ea52c6c0210da3840a94a922c122b43b3e054d986cd02650a9ff70adb316d3a1",
    f"{BCM}/company.sqlite3": "9227da660fb2bf910c877fa7abbe71f119a468040c0447092d0dee8b6da64b8e",
    BCM_REVIEW: "bff0e70bf1f8e72e2e94bf9c2fa91c4adec811a13d2a53f85788b57d967d9476",
    ROUTE_REVIEW: "89d03c1b1b4a2450524c6093dbe5ab9c02452afde351da939c92e3f9c835497b",
}
OWNERS = {
    "site_authority": "AS-P012",
    "site_zoning": "AS-P012",
    "badge_lifecycle": "AS-P008",
    "visitor_access": "AS-P012",
    "environment_monitor": "AS-P012",
    "environment_response": "AS-P012",
    "site_reconciliation": "AS-P008",
    "site_exception": "AS-P008",
}
FIELDS = (
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
TARGET_TASKS = {
    "TASK-SH-SEC-001-corporate-CHECK-SOC2:CC6.4",
    "TASK-SH-SEC-001-corporate-CHECK-SOC2:A1.2",
    "TASK-SH-BCM-004-corporate-CHECK-SOC2:CC9.1",
    *{
        f"TASK-{control}-corporate-{gate}"
        for control in ("SH-SEC-001", "SH-BCM-004")
        for gate in ("IMPLEMENTATION", "TOD", "TOE")
    },
}
LIMITS = [
    "Selected fictional 2027 two-cage source; 2026 provider sites remain procurement-pending.",
    "Provider building perimeters, complete access and environmental populations, "
    "and annual operation are untested.",
    "Messy October false closure and unescorted entry remain originals; "
    "historical exception stays open.",
    "Boise temperature response is a selected local incident, not a BCM exercise "
    "or recovery-capacity test.",
    "No actual provider action, deployment, person, PHI, packet, independent "
    "assurance or audit credit.",
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private(path: Path, directory: bool = False) -> tuple:
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise CompanyStoreError("Private alias forbidden")
    s = path.stat()
    if directory:
        if not path.is_dir() or stat.S_IMODE(s.st_mode) != 0o700:
            raise CompanyStoreError("Private 0700 directory required")
    elif not path.is_file() or s.st_nlink != 1 or stat.S_IMODE(s.st_mode) != 0o600:
        raise CompanyStoreError("Private 0600 single-link file required")
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, stat.S_IMODE(s.st_mode)


def _native_ref(
    root: Path, family: str, scenario: str, system: str, record: str, version: int
) -> dict:
    receipt = json.loads((root / family / "RECEIPT.json").read_text())
    matches = [
        r
        for r in receipt["records"][scenario]
        if (r["system"], r["record"], r["version"]) == (system, record, version)
    ]
    if len(matches) != 1:
        raise CompanyStoreError("Selected reviewed upstream tuple absent")
    ref = {key: matches[0][key] for key in FIELDS}
    path = root / family / "company.sqlite3"
    before = _private(path), _sha(path)
    if any(
        Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Upstream SQLite sidecar forbidden")
    with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Reviewed upstream database integrity differs")
        rows = db.execute(
            "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
            "AND record=? AND version=?",
            (ref["company"], ref["branch"], system, record, version),
        ).fetchall()
        if len(rows) != 1:
            raise CompanyStoreError("Reviewed upstream native row absent")
        row = rows[0]
        if any((json.loads(row[k]) if k == "provenance" else row[k]) != ref[k] for k in FIELDS):
            raise CompanyStoreError("Reviewed upstream native tuple differs")
        if hashlib.sha256(row["content"]).hexdigest() != ref["sha256"]:
            raise CompanyStoreError("Reviewed upstream native content differs")
    if (_private(path), _sha(path)) != before:
        raise CompanyStoreError("Reviewed upstream changed during read")
    return ref


def _context(repository: Path, private_repository: Path) -> dict:
    repo, private = (
        Path(repository).resolve(strict=True),
        Path(private_repository).resolve(strict=True),
    )
    pins = {}
    for rel, digest in TRACKED.items():
        path = repo / rel
        if path.is_symlink() or _sha(path) != digest:
            raise CompanyStoreError(f"Tracked physical-site input differs: {rel}")
        pins["repo://" + rel] = digest
    for rel, digest in PRIVATE.items():
        path = private / rel
        before = _private(path)
        if _sha(path) != digest or _private(path) != before:
            raise CompanyStoreError(f"Reviewed private physical-site input differs: {rel}")
        pins["private://" + rel] = digest
    if _sha(repo / SPEC) != SPEC_SHA256:
        raise CompanyStoreError("Selected physical-site spec pin differs")
    spec = json.loads((repo / SPEC).read_text())
    if (
        spec.get("schema") != "SH_FICTIONAL_2027_SELECTED_PHYSICAL_SITE_SPEC_V1"
        or spec.get("company") != COMPANY
        or spec.get("sites") != {"RENO": "RUNTIME-RENO-COLO", "BOISE": "RUNTIME-BOISE-DR"}
        or spec.get("selected_zones") != ["RNO-CAGE-A", "BOI-CAGE-R"]
        or spec.get("selected_badges") != ["BADGE-FAC-01", "BADGE-BOI-TECH-01"]
        or spec.get("selected_environment_point") != "BOI-CAGE-R-TEMP-01"
        or spec.get("selected_period") != ["2027-09-10T10:00:00+00:00", "2027-11-14T12:00:00+00:00"]
        or any(
            spec.get(k)
            for k in (
                "real_site_action",
                "actual_phi",
                "actual_personal_data",
                "network_packets",
                "audit_task_credit",
            )
        )
    ):
        raise CompanyStoreError("Selected physical-site spec differs")
    pins["repo://" + SPEC] = SPEC_SHA256
    sites = json.loads(
        (repo / "enterprise/services/source/runtime_sites_2026-09-11.json").read_text()
    )
    for site in sites["sites"][:2]:
        if (
            site["status"] != "PROVIDER_SELECTED_PROCUREMENT_PENDING"
            or site["operating"]
            or site["contract_executed"]
        ):
            raise CompanyStoreError("2026 procurement boundary differs")
    appointments = (repo / "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md").read_text()
    if not all(
        f"| {person} |" in appointments for person in ("AS-P001", "AS-P012", "AS-P008", "AS-P007")
    ):
        raise CompanyStoreError("Site actor appointment differs")
    services = (repo / "enterprise/services/source/services.json").read_text()
    if (
        '"SVC-physical-security"' not in services
        or '"TEAM-physical"' not in services
        or '"SVC-facilities"' not in services
    ):
        raise CompanyStoreError("Physical-security and facilities service scope differs")
    reviews = [
        json.loads((private / rel).read_text())
        for rel in (TRANSITION_REVIEW, BCM_REVIEW, ROUTE_REVIEW)
    ]
    if (
        reviews[0].get("verdict") != "PASS_PRIVATE_FICTIONAL_SOURCE_FOR_INTEGRATION_REVIEW"
        or reviews[0].get("run_receipt_sha256") != PRIVATE[f"{TRANSITION}/RECEIPT.json"]
        or reviews[0].get("run_manifest_sha256") != PRIVATE[f"{TRANSITION}/MANIFEST.json"]
        or reviews[0].get("native_db_sha256") != PRIVATE[f"{TRANSITION}/company.sqlite3"]
        or reviews[1].get("verdict") != "PASS_PRIVATE_FICTIONAL_SOURCE_FOR_INTEGRATION_REVIEW"
        or reviews[1].get("run_sha256")
        != {n: PRIVATE[f"{BCM}/{n}"] for n in ("RECEIPT.json", "MANIFEST.json", "company.sqlite3")}
        or reviews[2].get("verdict")
        != "PASS_READ_ONLY_PARTIAL_ROUTE_RECONCILIATION_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or reviews[2].get("main_tracked_sha256", {}).get("ledger_json") != TRACKED[ROUTES]
    ):
        raise CompanyStoreError("Independent upstream review authority differs")
    ledger = json.loads((repo / ROUTES).read_text())
    routes = {}
    for side in "AB":
        rows = [r for r in ledger["rows"] if r["side"] == side and r["task_id"] in TARGET_TASKS]
        if (
            len(rows) != len(TARGET_TASKS)
            or {r["task_id"] for r in rows} != TARGET_TASKS
            or any(
                r["current_status"] != "NOT_STARTED"
                or r["current_conclusion"] != "NOT_RUN"
                or r["audit_task_credit"] is not False
                for r in rows
            )
            or any(
                r["classification"]
                != (
                    "SOURCE_CANDIDATE_PARTIAL"
                    if r["control_id"] == "SH-BCM-004"
                    else "UNSUPPORTED_EXACT_CLAUSE"
                )
                for r in rows
                if r["authored_test_clause"] is not None
            )
        ):
            raise CompanyStoreError("Selected physical-site routes differ")
        routes[side] = [
            {
                k: r[k]
                for k in (
                    "task_id",
                    "control_id",
                    "classification",
                    "authored_test_clause",
                    "remaining_test_gate",
                )
            }
            for r in sorted(rows, key=lambda x: x["task_id"])
        ]
    if routes["A"] != routes["B"]:
        raise CompanyStoreError("Paired physical-site routes differ")
    upstream = {}
    for scenario in BRANCHES:
        upstream[scenario] = {
            "reno_release": _native_ref(
                private, TRANSITION, scenario, "site_release", "RL-RENO", 1
            ),
            "boise_release": _native_ref(
                private, TRANSITION, scenario, "site_release", "RL-BOISE", 1
            ),
            "bcm_result": _native_ref(
                private, BCM, scenario, "exercise_result", "MARKER-RECOVERY", 1
            ),
        }
        if scenario == "MESSY":
            upstream[scenario]["bcm_open_gate"] = _native_ref(
                private, BCM, scenario, "closure_gate", "KEY-AND-CAPACITY", 1
            )
        if any(
            _time(r["available_at"]) >= _time("2027-09-10T10:00:00+00:00")
            for r in upstream[scenario].values()
        ):
            raise CompanyStoreError("Upstream unavailable at selected site start")
    return {"pins": pins, "spec": spec, "routes": routes, "upstream": upstream}


def _step(system: str, record: str, at: str, actor: str, detail: dict, *, lag: int = 1) -> dict:
    return {
        "system": system,
        "record": record,
        "event_at": at,
        "available_at": (datetime.fromisoformat(at) + timedelta(minutes=lag)).isoformat(),
        "actor": actor,
        "detail": detail,
    }


def _steps(scenario: str, context: dict) -> list[dict]:
    common = [
        _step(
            "site_authority",
            "SELECTED-SITE-ORDER",
            "2027-09-10T10:00:00+00:00",
            "AS-P001",
            {
                "decision": "FICTIONAL_LOCAL_DELEGATION",
                "scope": "two selected cages only",
                "delegated_to": "AS-P012",
                "facilities_owner": "AS-P012",
                "security_reviewer": "AS-P008",
                "technology_contact": "AS-P007",
                "expires_at": "2027-12-31T23:59:59+00:00",
                "provider_building_control": "unverified external dependency",
            },
        ),
        _step(
            "site_zoning",
            "RNO-CAGE-A",
            "2027-09-11T10:00:00+00:00",
            "AS-P012",
            {
                "site": "RENO",
                "zone": "RNO-CAGE-A",
                "entry_rule": "named badge and approved escorted visitor",
                "provider_perimeter": "outside company-selected scope",
            },
        ),
        _step(
            "site_zoning",
            "BOI-CAGE-R",
            "2027-09-12T10:00:00+00:00",
            "AS-P012",
            {
                "site": "BOISE",
                "zone": "BOI-CAGE-R",
                "entry_rule": "named badge and approved escorted visitor",
                "provider_perimeter": "outside company-selected scope",
            },
        ),
        _step(
            "badge_lifecycle",
            "BADGE-FAC-01",
            "2027-09-13T10:00:00+00:00",
            "AS-P008",
            {
                "site": "RENO",
                "role": "selected facilities custodian",
                "status": "ACTIVE",
                "zone": "RNO-CAGE-A",
                "real_person": False,
            },
        ),
        _step(
            "badge_lifecycle",
            "BADGE-BOI-TECH-01",
            "2027-09-14T10:00:00+00:00",
            "AS-P008",
            {
                "site": "BOISE",
                "role": "fictional contractor token",
                "status": "ACTIVE",
                "zone": "BOI-CAGE-R",
                "real_person": False,
            },
        ),
        _step(
            "environment_monitor",
            "BOI-CAGE-R-TEMP-01",
            "2027-09-15T10:00:00+00:00",
            "AS-P012",
            {
                "site": "BOISE",
                "zone": "BOI-CAGE-R",
                "threshold_c": 30,
                "sample_interval_minutes": 5,
                "selected_point_only": True,
            },
        ),
        _step(
            "visitor_access",
            "BOI-VISIT-01",
            "2027-10-02T09:00:00+00:00",
            "AS-P012",
            {
                "site": "BOISE",
                "purpose": "inspect selected temperature probe",
                "zone": "BOI-CAGE-R",
                "escort_role": "facilities custodian",
                "valid_until": "2027-10-02T12:00:00+00:00",
                "visitor_token": "FICTIONAL-VISITOR-01",
                "real_person": False,
            },
        ),
    ]
    if scenario == "CLEAN":
        tail = [
            _step(
                "visitor_access",
                "BOI-VISIT-01-CLOSE",
                "2027-10-02T11:30:00+00:00",
                "AS-P012",
                {
                    "authorization": "BOI-VISIT-01",
                    "entry": "ESCORTED",
                    "exit_confirmed": True,
                    "zone": "BOI-CAGE-R",
                },
            ),
            _step(
                "badge_lifecycle",
                "BADGE-BOI-TECH-01-REVOKE",
                "2027-10-03T10:00:00+00:00",
                "AS-P008",
                {
                    "badge": "BADGE-BOI-TECH-01",
                    "reason": "selected assignment ended",
                    "controller_state": "DISABLED",
                    "effective_at": "2027-10-03T10:00:00+00:00",
                },
            ),
            _step(
                "environment_monitor",
                "BOI-ALARM-01",
                "2027-10-18T10:00:00+00:00",
                "AS-P012",
                {
                    "point": "BOI-CAGE-R-TEMP-01",
                    "observed_c": 31,
                    "threshold_c": 30,
                    "state": "ALARM",
                    "payload": "none",
                },
            ),
            _step(
                "environment_response",
                "BOI-WO-01",
                "2027-10-18T10:15:00+00:00",
                "AS-P012",
                {
                    "alarm": "BOI-ALARM-01",
                    "action": "fictional local cooling inspection",
                    "authorized_entry": "FACILITIES_BADGE",
                    "actual_provider_action": False,
                },
            ),
            _step(
                "environment_monitor",
                "BOI-ALARM-01-RECHECK",
                "2027-10-18T11:00:00+00:00",
                "AS-P012",
                {"point": "BOI-CAGE-R-TEMP-01", "observed_c": 24, "local_alarm_cleared": True},
            ),
            _step(
                "site_reconciliation",
                "SELECTED-OCT-RECON",
                "2027-10-20T10:00:00+00:00",
                "AS-P008",
                {
                    "selected_badges_expected": 2,
                    "selected_badges_observed": 2,
                    "revoked_boise_badge_disabled": True,
                    "selected_visits_expected": 1,
                    "selected_visits_observed": 1,
                    "alarm_reviewed": True,
                    "decision": "SELECTED_PASS",
                },
            ),
        ]
    else:
        tail = [
            _step(
                "visitor_access",
                "BOI-VISIT-01-CLOSE",
                "2027-10-02T11:30:00+00:00",
                "AS-P012",
                {
                    "authorization": "BOI-VISIT-01",
                    "entry": "REPORTED_ESCORTED",
                    "exit_confirmed": True,
                    "underlying_controller_entry_not_checked": True,
                },
            ),
            _step(
                "badge_lifecycle",
                "BADGE-BOI-TECH-01-REVOKE",
                "2027-10-03T10:00:00+00:00",
                "AS-P008",
                {
                    "badge": "BADGE-BOI-TECH-01",
                    "reason": "selected assignment ended",
                    "ticket_state": "CLOSED",
                    "controller_state": "ACTIVE",
                    "unverified_false_close": True,
                },
            ),
            _step(
                "environment_monitor",
                "BOI-ALARM-01",
                "2027-10-18T10:00:00+00:00",
                "AS-P012",
                {
                    "point": "BOI-CAGE-R-TEMP-01",
                    "observed_c": 33,
                    "threshold_c": 30,
                    "state": "ALARM",
                    "payload": "none",
                },
            ),
            _step(
                "visitor_access",
                "BOI-DOOR-ADVERSE-01",
                "2027-10-18T10:08:00+00:00",
                "AS-P012",
                {
                    "badge": "BADGE-BOI-TECH-01",
                    "controller_entry": "ALLOWED",
                    "escort": "NONE",
                    "authorization": "EXPIRED",
                    "zone": "BOI-CAGE-R",
                    "source": "fictional controller event",
                },
            ),
            _step(
                "environment_response",
                "BOI-WO-01",
                "2027-10-18T10:20:00+00:00",
                "AS-P012",
                {
                    "alarm": "BOI-ALARM-01",
                    "action": "fictional cooling response",
                    "adverse_entry_referenced": "BOI-DOOR-ADVERSE-01",
                    "actual_provider_action": False,
                },
            ),
            _step(
                "environment_monitor",
                "BOI-ALARM-01-RECHECK",
                "2027-10-18T11:30:00+00:00",
                "AS-P012",
                {"point": "BOI-CAGE-R-TEMP-01", "observed_c": 25, "local_alarm_cleared": True},
            ),
            _step(
                "site_reconciliation",
                "SELECTED-OCT-RECON",
                "2027-10-20T10:00:00+00:00",
                "AS-P008",
                {
                    "selected_badges_expected": 2,
                    "selected_badges_observed": 1,
                    "selected_visits_expected": 1,
                    "selected_visits_observed": 1,
                    "controller_export_consulted": False,
                    "decision": "FALSE_CLEAN_PASS",
                },
            ),
            _step(
                "site_reconciliation",
                "SOURCE-RECHECK-NOV",
                "2027-11-05T10:00:00+00:00",
                "AS-P008",
                {
                    "independent_controller_export": "FICTIONAL-BOI-CONTROLLER-NOV",
                    "found": [
                        "ACTIVE_AFTER_REVOCATION",
                        "UNESCORTED_EXPIRED_ENTRY",
                        "OCTOBER_FALSE_PASS",
                    ],
                    "self_review_of_october": True,
                },
            ),
            _step(
                "site_exception",
                "EXC-PHYSICAL-BOISE-01",
                "2027-11-05T11:00:00+00:00",
                "AS-P008",
                {
                    "status": "OPEN",
                    "historical_window": "2027-10-03/2027-11-06",
                    "cause": "revocation ticket not reconciled to controller and visitor "
                    "close lacked entry join",
                    "alarm_closed_locally": True,
                    "assurance": "NONE",
                },
            ),
            _step(
                "badge_lifecycle",
                "BADGE-BOI-TECH-01-CORRECT",
                "2027-11-06T10:00:00+00:00",
                "AS-P008",
                {
                    "badge": "BADGE-BOI-TECH-01",
                    "controller_state": "DISABLED",
                    "authorized_by": "AS-P008",
                    "historical_entry_erased": False,
                },
            ),
            _step(
                "site_reconciliation",
                "SELECTED-NOV-RECON",
                "2027-11-14T12:00:00+00:00",
                "AS-P008",
                {
                    "selected_current_badge_state": "DISABLED",
                    "historical_exception_status": "OPEN",
                    "independent_assurance": False,
                    "October_originals_preserved": True,
                },
            ),
        ]
    steps = common + tail
    for step in steps:
        if _time(step["event_at"]) < _time("2027-09-10T10:00:00+00:00") or _time(
            step["event_at"]
        ) >= _time(step["available_at"]):
            raise CompanyStoreError("Selected event/availability chronology differs")
        step["body"] = {
            "schema": SCHEMA,
            "company": COMPANY,
            "scenario": scenario,
            "system": step["system"],
            "record": step["record"],
            "event_at": step["event_at"],
            "available_at": step["available_at"],
            "actor": step["actor"],
            "detail": step["detail"],
            "upstream_native_refs_available_at_event": context["upstream"][scenario],
            "actual_personal_data": False,
            "actual_phi": False,
            "real_site_action": False,
            "network_packets": 0,
            "audit_task_credit": False,
        }
    return steps


def _write(path: Path, value: dict) -> None:
    path.write_bytes(encoded(value) + b"\n")
    path.chmod(0o600)


def _receipt(context: dict, records: dict) -> dict:
    return {
        "schema": SCHEMA,
        "status": "FUTURE_FICTIONAL_SELECTED_PHYSICAL_SITE_NO_AUDIT_CREDIT",
        "company": COMPANY,
        "branches": BRANCHES,
        "selected_sites": context["spec"]["sites"],
        "selected_zones": context["spec"]["selected_zones"],
        "selected_badges": context["spec"]["selected_badges"],
        "selected_environment_point": context["spec"]["selected_environment_point"],
        "source_pins": context["pins"],
        "upstream_native_refs": context["upstream"],
        "selected_routes": context["routes"],
        "records": records,
        "native_version_counts": {scenario: len(rows) for scenario, rows in records.items()},
        "messy_false_close_preserved": True,
        "messy_unescorted_entry_preserved": True,
        "messy_historical_exception_status": "OPEN",
        "provider_and_enterprise_population_complete": False,
        "authored_clauses_satisfied": False,
        "independent_assurance_completed": False,
        "actual_operation_eligibility_as_of_2026_09_30": False,
        "real_site_action": False,
        "actual_personal_data": False,
        "actual_phi": False,
        "network_packets": 0,
        "audit_task_credit": False,
        "limits": LIMITS,
    }


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    destination = Path(destination).absolute()
    _private(destination.parent, directory=True)
    if destination.exists() or destination.is_symlink() or destination != destination.resolve():
        raise CompanyStoreError("Fresh private physical-site destination required")
    context = _context(repository, private_repository)
    with tempfile.TemporaryDirectory(
        prefix=".physical-site-stage-", dir=destination.parent
    ) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in BRANCHES.items():
            for system, owner in OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            records[scenario] = []
            for step in _steps(scenario, context):
                records[scenario].append(
                    store.append_version(
                        COMPANY,
                        branch,
                        step["system"],
                        step["record"],
                        expected_version=0,
                        command_id=f"PHY-{branch}-{step['record']}",
                        event_at=step["event_at"],
                        available_at=step["available_at"],
                        content=encoded(step["body"]),
                        provenance={
                            "source_reference": SOURCE,
                            "qualification": SCHEMA,
                            "scenario": scenario,
                            "source_pins": context["pins"],
                        },
                    )
                )
        receipt = _receipt(context, records)
        _write(stage / "RECEIPT.json", receipt)
        _write(
            stage / "MANIFEST.json",
            {
                "schema": SCHEMA + "_MANIFEST",
                "receipt_sha256": _sha(stage / "RECEIPT.json"),
                "company_db_sha256": _sha(stage / "company.sqlite3"),
                "module_sha256": _sha(Path(__file__)),
                "spec_sha256": _sha(Path(repository) / SPEC),
                "native_version_count": sum(map(len, records.values())),
                "audit_task_credit": False,
            },
        )
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private_repository)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    root = Path(destination).absolute()
    _private(root, directory=True)
    if {p.name for p in root.iterdir()} != {"RECEIPT.json", "MANIFEST.json", "company.sqlite3"}:
        raise CompanyStoreError("Exact physical-site three-file source required")
    paths = {name: root / name for name in ("RECEIPT.json", "MANIFEST.json", "company.sqlite3")}
    before = {name: (_private(path), _sha(path)) for name, path in paths.items()}
    if any(
        Path(str(paths["company.sqlite3"]) + suffix).exists()
        or Path(str(paths["company.sqlite3"]) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Physical-site SQLite sidecar forbidden")
    context = _context(repository, private_repository)
    receipt, manifest = (
        json.loads(paths[name].read_text()) for name in ("RECEIPT.json", "MANIFEST.json")
    )
    if receipt != _receipt(context, receipt.get("records", {})) or manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "receipt_sha256": before["RECEIPT.json"][1],
        "company_db_sha256": before["company.sqlite3"][1],
        "module_sha256": _sha(Path(__file__)),
        "spec_sha256": _sha(Path(repository) / SPEC),
        "native_version_count": 31,
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("Physical-site receipt/manifest boundary differs")
    with sqlite3.connect(
        paths["company.sqlite3"].as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Physical-site SQLite integrity differs")
        systems = db.execute("SELECT * FROM systems").fetchall()
        if len(systems) != 2 * len(OWNERS) or any(
            r["company"] != COMPANY
            or r["branch"] not in BRANCHES.values()
            or OWNERS.get(r["system"]) != r["owner"]
            for r in systems
        ):
            raise CompanyStoreError("Physical-site owner roster differs")
        if any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections", "access_events")
        ):
            raise CompanyStoreError("Physical-site audit access or collection present")
        for scenario, branch in BRANCHES.items():
            rows = db.execute(
                "SELECT * FROM versions WHERE branch=? ORDER BY rowid", (branch,)
            ).fetchall()
            steps, refs = _steps(scenario, context), receipt["records"][scenario]
            if len(rows) != len(steps) or len(refs) != len(steps):
                raise CompanyStoreError("Physical-site selected denominator differs")
            for row, step, ref in zip(rows, steps, refs, strict=True):
                if (
                    (row["company"], row["branch"], row["system"], row["record"], row["version"])
                    != (COMPANY, branch, step["system"], step["record"], 1)
                    or row["content"] != encoded(step["body"])
                    or row["sha256"] != hashlib.sha256(row["content"]).hexdigest()
                    or row["event_at"] != _time(step["event_at"])
                    or row["available_at"] != _time(step["available_at"])
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or json.loads(row["provenance"])
                    != {
                        "source_reference": SOURCE,
                        "qualification": SCHEMA,
                        "scenario": scenario,
                        "source_pins": context["pins"],
                    }
                    or row["imported_at"] >= _time("2027-01-01T00:00:00+00:00")
                    or {k: (json.loads(row[k]) if k == "provenance" else row[k]) for k in FIELDS}
                    != ref
                ):
                    raise CompanyStoreError("Physical-site native version differs")
    if {name: (_private(path), _sha(path)) for name, path in paths.items()} != before:
        raise CompanyStoreError("Physical-site source changed during verify")
    return receipt
