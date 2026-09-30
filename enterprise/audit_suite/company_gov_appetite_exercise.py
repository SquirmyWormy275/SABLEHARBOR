"""One fictional 2027 Board envelope and bounded management authority history.

Separate member actions are retained before a simulated collective result. This
source is not actual Board minutes, legal applicability or audit collection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import stat
import tempfile
from pathlib import Path

from . import company_assurance_findings_exercise as issue
from . import company_bcm_shared_runtime_exercise as bcm
from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_SELECTED_GOV_POL_ERM_APPETITE_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
AS_OF = "2026-09-30"
SOURCE_REF = "enterprise/audit_suite/company_gov_appetite_exercise.py"
BRANCHES = {"CLEAN": "GOVAPP-CLEAN", "MESSY": "GOVAPP-MESSY"}
RECORD = "SVC-COMPUTE-RENO-BOISE-SELECTED"
MATRIX = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V3_2026-09-29.json"
PBC = "enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_2026-09-29.json"
MATRIX_REVIEW = (
    "enterprise/generated/audit-suite/documentary-283-route-reconciliation-v3-2026-09-29/"
    "independent-review-v1/REVIEW.json"
)
BCM = "enterprise/generated/audit-suite/company-bcm-shared-runtime-2026-09-29/run-v2"
BCM_REVIEW = (
    "enterprise/generated/audit-suite/company-bcm-shared-runtime-2026-09-29/"
    "independent-review-v2/REVIEW.json"
)
ISSUE = "enterprise/generated/audit-suite/company-assurance-findings-2026-09-29/run-v1"
ISSUE_REVIEW = (
    "enterprise/generated/audit-suite/company-assurance-findings-2026-09-29/"
    "independent-review-v1/REVIEW.json"
)
BOARD = "docs/governance/structured/board_and_committees.json"
CHART = "docs/organization/source/chartbook.json"
TRACKED_PINS = {
    MATRIX: "f7549eca0957a92d442cfabb385ae9eed4509fada804a3dfea5d371cfbbf4d33",
    PBC: "25ea72e4b2480e11d6dc2b8d3018fb04cc1be019eb9da69bd5c6e881d947aa05",
    BOARD: "87afbe2d1500f25931e530bda95ed9fb7175fa6cb9573b0952072765f2cd2fa2",
    CHART: "6ba4f1ed1a14581455a62c3e79a29ca59dbaf1270dfb0db850c0376c15507b49",
    "docs/governance/BOARD_AND_CAPITAL_GOVERNANCE_v1.0.1.md": (
        "dc1e2e3ea6e7ea8d364eae87bd890a8c79a5a577a7554ed371cda3810ea945a8"
    ),
    "docs/governance/GOVERNANCE_CONSTITUTION.md": (
        "efa3e78c9d86786f66159c6470a163dffc77f811679d16b876f049bc23498cef"
    ),
    "docs/governance/RESERVED_MATTERS_AND_SUBSIDIARY_AUTONOMY.md": (
        "323a9611891d41dafa6eb00ed891ba4b0917a4b2329fd29e52bd730cc92d3313"
    ),
    "docs/governance/ENTERPRISE_COORDINATION_2026-09-13.md": (
        "3f358e1a89ba640ab35be53682388e7d9604c0f5627dfeb5a176a6de1e7c2da9"
    ),
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md": (
        "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751"
    ),
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md": (
        "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496"
    ),
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md": (
        "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433"
    ),
}
PRIVATE_PINS = {
    MATRIX_REVIEW: "b671d3547670b5de9c7f714d51e44b6d2e65b02502dac752464b9f36d7ca1603",
    f"{BCM}/MANIFEST.json": "ea52c6c0210da3840a94a922c122b43b3e054d986cd02650a9ff70adb316d3a1",
    f"{BCM}/RECEIPT.json": "3cd0b62de445cde7c1a76f61a156fb0fd5fa9c443cf3255ca85876b6f2c4de9a",
    f"{BCM}/company.sqlite3": "9227da660fb2bf910c877fa7abbe71f119a468040c0447092d0dee8b6da64b8e",
    BCM_REVIEW: "bff0e70bf1f8e72e2e94bf9c2fa91c4adec811a13d2a53f85788b57d967d9476",
    f"{ISSUE}/MANIFEST.json": "2a5db28d3024d00e194e02219428bb133dfbbe085123bf776980ac6b68f8b89f",
    f"{ISSUE}/RECEIPT.json": "74c614682c269eb1aff431b0c834e6c0581ebbb921e2549b0e200923d2129091",
    f"{ISSUE}/company.sqlite3": "0e010fb8f34acb7c4c8dfff6e43d8e9f2d9c01c99ae36311547175a6d0026c53",
    ISSUE_REVIEW: "23033dcf6641d18038bc58a1e02fd1b014a4e550fe0ae78bd854e1f7f5552f58",
}
CONTROLS = {"SH-GOV-003": 6, "SH-POL-002": 6, "SH-ERM-002": 4}
PBC_COUNTS = {"SH-GOV-003": 3, "SH-POL-002": 3, "SH-ERM-002": 1}
DIRECTOR_IDS = (
    "DIR-KINCAID",
    "DIR-DANIEL",
    "DIR-RAMAN",
    "DIR-BELL",
    "DIR-CALDER",
    "DIR-MERCER",
    "DIR-VOSS",
    "DIR-GALIULLINA",
    "DIR-VAN-DER-VELDE",
)
SOURCE_FIELDS = (
    "company",
    "branch",
    "system",
    "record",
    "version",
    "sha256",
    "event_at",
    "available_at",
    "imported_at",
)
SYSTEM_OWNERS = {
    "appetite_motion": "AS-P005",
    "measure_challenge": "AS-P008",
    "board_member_action": "AS-P004",
    "board_decision": "AS-P004",
    "ceo_delegation": "P001",
    "control_mapping": "AS-P005",
    "selected_application": "AS-P005",
    "waiver_request": "AS-P007",
    "security_challenge": "AS-P008",
    "ceo_disposition": "P001",
}
LIMITS = [
    "Future fictional Board/member/CEO actions only; no real minutes, signatures "
    "or legal quorum claim.",
    "One selected SVC-compute Reno/Boise recovery envelope; no enterprise-wide risk mandate.",
    "240/15 are internal diagnostic-marker limits, not a customer SLA or full "
    "service availability.",
    "The HIPAA/security-official, hybrid-entity and actual BA applicability decisions remain open.",
    "Messy local retest cannot waive the key-bypass or capacity hold; challenge stays open.",
    "No actual PHI, real provider deployment, Board approval, audit collection or task credit.",
]


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def _private(path: Path) -> tuple:
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_nlink != 1
        or path.stat().st_mode & 0o077
        or any(p.is_symlink() for p in path.parents)
    ):
        raise CompanyStoreError("Private ordinary governance source required")
    info = path.stat()
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IMODE(info.st_mode),
        info.st_size,
        info.st_mtime_ns,
        _sha(path),
    )


def _frozen(path: Path) -> tuple:
    before = _private(path)
    if any(
        Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Frozen governance source has SQLite sidecar")
    return before


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def _native_refs(root: Path, receipt: dict, scenario: str) -> dict:
    db_path = root / "company.sqlite3"
    before = _frozen(db_path)
    refs = receipt["records"][scenario]
    with sqlite3.connect(db_path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Upstream governance source integrity differs")
        rows = db.execute(
            "SELECT * FROM versions WHERE branch=? ORDER BY rowid", (receipt["branches"][scenario],)
        ).fetchall()
        if len(rows) != len(refs):
            raise CompanyStoreError("Upstream governance original population differs")
        for row, ref in zip(rows, refs, strict=True):
            if (
                any(row[k] != ref[k] for k in SOURCE_FIELDS)
                or hashlib.sha256(row["content"]).hexdigest() != ref["sha256"]
            ):
                raise CompanyStoreError("Upstream governance original tuple differs")
    if _frozen(db_path) != before:
        raise CompanyStoreError("Upstream governance source changed during read")
    return {
        (ref["system"], ref["record"], ref["version"]): {key: ref[key] for key in SOURCE_FIELDS}
        for ref in refs
    }


def _context(repository: Path, private_repository: Path) -> tuple[dict, dict, dict, dict, dict]:
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    pins, stable = {}, {}
    for relative, expected in TRACKED_PINS.items():
        path = repository / relative
        if not path.is_file() or path.is_symlink() or _sha(path) != expected:
            raise CompanyStoreError(f"Tracked governance source differs: {relative}")
        info = path.stat()
        stable[("repo", relative)] = (info.st_dev, info.st_ino, info.st_mtime_ns, expected)
        pins[f"repo://{relative}"] = expected
    for relative, expected in PRIVATE_PINS.items():
        path = private_repository / relative
        before = _frozen(path) if relative.endswith("company.sqlite3") else _private(path)
        if before[-1] != expected:
            raise CompanyStoreError(f"Reviewed governance source differs: {relative}")
        stable[("private", relative)] = before
        pins[f"private://{relative}"] = expected
    board = json.loads((repository / BOARD).read_text())
    directors = board["directors"]
    if (
        board["state"] != "LOCKED"
        or len(directors) != 9
        or {d["id"] for d in directors} != set(DIRECTOR_IDS)
        or next(d for d in directors if d["id"] == "DIR-KINCAID")["capacity"] != "independent-chair"
        or next(d for d in directors if d["id"] == "DIR-DANIEL")["capacity"]
        != "founder-ceo-director"
    ):
        raise CompanyStoreError("Locked nine-director governance differs")
    chart = json.loads((repository / CHART).read_text())
    ceo = [n for n in chart["nodes"] if n.get("id") == "P001"]
    if (
        len(ceo) != 1
        or ceo[0]["name"] != "Daniel Mercer"
        or ceo[0]["title"] != "Chief Executive Officer"
    ):
        raise CompanyStoreError("CEO actor identity differs")
    appointments = (repository / "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md").read_text()
    for expected in (
        "| AS-P001 | Lila Kestrel | Chief of Enterprise Support Services |",
        "| AS-P003 | Helena Ward | General Counsel |",
        "| AS-P004 | Nina Rowan | Corporate Secretary |",
        "| AS-P005 | Martin Ives | Head of Risk and Compliance |",
        "| AS-P007 | Elliot Tran | Head of Enterprise Technology Services |",
        "| AS-P008 | Dana West | Chief Information Security Officer |",
    ):
        if expected not in appointments:
            raise CompanyStoreError("Selected management appointment differs")
    matrix = json.loads((repository / MATRIX).read_text())
    review = json.loads((private_repository / MATRIX_REVIEW).read_text())
    if (
        matrix.get("schema") != "SH_DOCUMENTARY_283_PAIRED_ROUTE_CANDIDATE_RECONCILIATION_V3"
        or matrix.get("audit_task_credit") is not False
        or not str(review.get("verdict", "")).startswith("PASS")
    ):
        raise CompanyStoreError("Reviewed governance route matrix differs")
    routes = {}
    for side in "AB":
        rows = [r for r in matrix["rows"] if r["side"] == side and r["control_id"] in CONTROLS]
        if len(rows) != 16 or any(
            sum(r["control_id"] == control for r in rows) != count
            for control, count in CONTROLS.items()
        ):
            raise CompanyStoreError("Sixteen selected governance routes differ")
        if any(
            r["current_status"] != "NOT_STARTED"
            or r["current_conclusion"] != "NOT_RUN"
            or r["audit_task_credit"] is not False
            for r in rows
        ):
            raise CompanyStoreError("Governance audit route status differs")
        routes[side] = [
            {
                "task_id": r["task_id"],
                "control_id": r["control_id"],
                "authored_test_clause": r["authored_test_clause"],
                "remaining_test_gate": r["remaining_test_gate"],
            }
            for r in rows
        ]
    pbc = json.loads((repository / PBC).read_text())
    groups = [g for g in pbc["request_groups"] if g["control_id"] in CONTROLS]
    if (
        len(groups) != 3
        or {g["control_id"] for g in groups} != set(CONTROLS)
        or any(
            g["routes_per_side"] != PBC_COUNTS[g["control_id"]]
            or g["request_status"] != "DRAFT_NOT_SENT"
            or g["task_credit"] is not False
            or g["candidate_contact_person_id"]
            != ("AS-P004" if g["control_id"] == "SH-GOV-003" else "AS-P005")
            for g in groups
        )
    ):
        raise CompanyStoreError("Governance PBC candidate request differs")
    for group in groups:
        control = group["control_id"]
        for side in "AB":
            authored = {
                row["task_id"]
                for row in routes[side]
                if row["control_id"] == control and row["authored_test_clause"] is not None
            }
            if set(group["task_ids_per_side"][side]) != authored:
                raise CompanyStoreError("Governance PBC authored-route join differs")
    bcm.verify(
        private_repository / BCM, repository=repository, private_repository=private_repository
    )
    issue.verify(
        private_repository / ISSUE, repository=repository, private_repository=private_repository
    )
    bcm_receipt = json.loads((private_repository / BCM / "RECEIPT.json").read_text())
    issue_receipt = json.loads((private_repository / ISSUE / "RECEIPT.json").read_text())
    originals = {
        scenario: {
            "bcm": _native_refs(private_repository / BCM, bcm_receipt, scenario),
            "issue": _native_refs(private_repository / ISSUE, issue_receipt, scenario),
        }
        for scenario in BRANCHES
    }
    for scenario in BRANCHES:
        if len(originals[scenario]["bcm"]) != (8 if scenario == "CLEAN" else 10) or len(
            originals[scenario]["issue"]
        ) != (1 if scenario == "CLEAN" else 5):
            raise CompanyStoreError("Selected governance upstream original count differs")
    for (kind, relative), before in stable.items():
        path = (repository if kind == "repo" else private_repository) / relative
        if kind == "repo":
            info = path.stat()
            after = (info.st_dev, info.st_ino, info.st_mtime_ns, _sha(path))
        else:
            after = _frozen(path) if relative.endswith("company.sqlite3") else _private(path)
        if before != after:
            raise CompanyStoreError("Reviewed governance source changed during read")
    return (
        pins,
        routes,
        {g["control_id"]: g for g in groups},
        {d["id"]: d for d in directors},
        originals,
    )


def _pick(originals: dict, family: str, system: str, version: int = 1) -> dict:
    record = (
        "MARKER-RECOVERY"
        if system == "exercise_result"
        else ("KEY-AND-CAPACITY" if system == "closure_gate" else "BOISE-KEY-BYPASS-SELECTED")
    )
    try:
        return originals[family][system, record, version]
    except KeyError as exc:
        raise CompanyStoreError("Selected governance original tuple missing") from exc


def _steps(scenario: str, directors: dict, originals: dict) -> list[dict]:
    events = []

    def add(
        system: str, record: str, version: int, when: str, actor: str, **fields: object
    ) -> dict:
        body = {
            "schema": SCHEMA,
            "scenario": scenario,
            "system": system,
            "record": record,
            "version": version,
            "event_at": _time(when),
            "actor_id": actor,
            "future_fictional_event": True,
            "real_world_board_or_operating_action": False,
            "audit_task_credit": False,
            **fields,
        }
        events.append({"system": system, "record": record, "version": version, "body": body})
        return body

    draft = add(
        "appetite_motion",
        RECORD,
        1,
        "2027-01-03T10:00:00Z",
        "AS-P005",
        status="DRAFT_NOT_EFFECTIVE",
        proposed_objective="HIGH_AVAILABILITY_UNMEASURED",
        board_decision=False,
        scope="SELECTED_SVC_COMPUTE_RENO_BOISE_ONLY",
    )
    challenge = add(
        "measure_challenge",
        RECORD,
        1,
        "2027-01-04T10:00:00Z",
        "AS-P008",
        status="MEASURABILITY_AND_KEY_GATE_CHALLENGE",
        draft_sha256=hashlib.sha256(encoded(draft)).hexdigest(),
        needs=[
            "NUMERIC_SELECTED_RECOVERY_LIMITS",
            "NO_UNREVIEWED_KEY_BYPASS",
            "SEPARATE_ACTUAL_LEGAL_APPLICABILITY_GATE",
        ],
        challenge_disposition="REVISED_MOTION_REQUIRED",
    )
    motion = add(
        "appetite_motion",
        RECORD,
        2,
        "2027-01-06T10:00:00Z",
        "AS-P005",
        status="REVISED_MOTION_SUBMITTED_NOT_YET_EFFECTIVE",
        supersedes_draft_sha256=hashlib.sha256(encoded(draft)).hexdigest(),
        challenge_sha256=hashlib.sha256(encoded(challenge)).hexdigest(),
        selected_service="SVC-compute",
        sites=["Reno", "Boise"],
        internal_marker_rto_minutes_max=240,
        internal_marker_rpo_minutes_max=15,
        unreviewed_boise_key_gate_bypass_tolerance=0,
        threshold_breach_route="AS-P008_SECURITY_AND_AS-P005_RISK_TO_P001_CEO_WITHIN_48H",
        material_challenge_route="BOARD_AUDIT_COMPLIANCE_ROUTING_REQUEST_WITHIN_72H",
        actual_hipaa_applicability="UNDETERMINED",
        actual_security_official_designation="NOT_ASSERTED",
        customer_service_commitment="NOT_ESTABLISHED",
        full_service_availability_metric="NOT_ESTABLISHED",
    )
    motion_sha = hashlib.sha256(encoded(motion)).hexdigest()
    vote_refs = []
    for index, director_id in enumerate(DIRECTOR_IDS):
        director = directors[director_id]
        vote = "DISSENT" if director_id == "DIR-CALDER" else "SUPPORT"
        action = add(
            "board_member_action",
            director_id,
            1,
            f"2027-01-10T10:{index:02d}:00Z",
            director_id,
            status="SIMULATED_INDIVIDUAL_MEMBER_ACTION",
            motion_sha256=motion_sha,
            member_name=director["name"],
            member_capacity=director["capacity"],
            attendance="PRESENT_SIMULATED",
            vote=vote,
            dissent_reason=(
                "SELECTED_MONITORING_NOT_YET_A_COMPLETE_PERIOD_OR_LEGAL_APPLICABILITY_DECISION"
                if vote == "DISSENT"
                else None
            ),
            simulated_member_attestation=True,
            real_member_signature=False,
        )
        vote_refs.append(
            {
                "director_id": director_id,
                "action_sha256": hashlib.sha256(encoded(action)).hexdigest(),
                "vote": vote,
                "event_at": action["event_at"],
            }
        )
    board = add(
        "board_decision",
        RECORD,
        1,
        "2027-01-10T11:00:00Z",
        "DIR-KINCAID",
        status="APPROVED_IN_FICTIONAL_TRAINING_BRANCH_ONLY",
        secretary_custodian_person_id="AS-P004",
        motion_sha256=motion_sha,
        delegated_management_authority="P001_CEO_WITHIN_SELECTED_ENVELOPE_ONLY",
        reserved_boundary_route="BOARD_OR_AUTHORIZED_BODY_FOR_MATERIAL_DEPARTURE",
        member_actions=vote_refs,
        support_count=8,
        dissent_count=1,
        all_nine_members_present_simulated=True,
        chair_certification_after_member_actions=True,
        cultural_support_norm_not_legal_quorum=True,
        real_board_minutes_or_legal_validity=False,
        dissent_retained=True,
        effective_at=_time("2027-01-12T00:00:00Z"),
        expires_at=_time("2027-12-31T23:59:59Z"),
        accepted_motion_sha256=motion_sha,
    )
    board_sha = hashlib.sha256(encoded(board)).hexdigest()
    delegation = add(
        "ceo_delegation",
        RECORD,
        1,
        "2027-01-12T10:00:00Z",
        "P001",
        status="SELECTED_MANAGEMENT_DELEGATION_SIMULATED",
        board_decision_sha256=board_sha,
        service_coordinator_person_id="AS-P001",
        risk_monitor_person_id="AS-P005",
        technology_owner_person_id="AS-P007",
        security_challenge_person_id="AS-P008",
        legal_applicability_person_id="AS-P003",
        technical_configuration_authority="SEPARATE_SCOPED_APPROVAL_REQUIRED",
        security_official_designation="NOT_MADE_BY_THIS_RECORD",
        waiver_of_board_envelope=False,
        scope="ONE_SELECTED_SVC_COMPUTE_RENO_BOISE_FICTIONAL_2027_ENVELOPE",
    )
    delegation_sha = hashlib.sha256(encoded(delegation)).hexdigest()
    add(
        "control_mapping",
        RECORD,
        1,
        "2027-01-13T10:00:00Z",
        "AS-P005",
        status="SELECTED_CONTROL_MAPPING_NOT_FULL_CCF_ACCEPTANCE",
        source_decision_sha256=board_sha,
        source_delegation_sha256=delegation_sha,
        control_ids=list(CONTROLS),
        rationale="RESERVED_AUTHORITY_TO_MEASURABLE_RECOVERY_AND_EXCEPTION_GATE",
        accountable_roles={
            "board": "COLLECTIVE_NINE_DIRECTOR_BODY",
            "ceo": "P001",
            "risk_monitor": "AS-P005",
            "technical_owner": "AS-P007",
            "security_challenge": "AS-P008",
        },
        evidence_expectations=[
            "MEMBER_ACTIONS",
            "BOUNDED_DELEGATION",
            "SELECTED_MARKER_ORIGINALS",
            "OPEN_EXCEPTION_ROUTE",
        ],
        change_history=[
            {"version": 1, "reason": "FIRST_SELECTED_LOCAL_MAPPING", "supersedes": None}
        ],
        full_ccf_population_complete=False,
    )
    if scenario == "CLEAN":
        result = _pick(originals, "bcm", "exercise_result")
        screen = _pick(originals, "issue", "issue_screening")
        add(
            "selected_application",
            RECORD,
            1,
            "2027-09-15T10:00:00Z",
            "AS-P005",
            status="NO_SELECTED_MARKER_ESCALATION_NOT_PERIOD_CONCLUSION",
            source_refs=[result, screen],
            board_decision_sha256=board_sha,
            measured_selected_marker_restore_minutes=155,
            measured_selected_marker_replay_gap_minutes=8,
            selected_key_bypass_open=False,
            entire_service_or_period_assessed=False,
        )
    else:
        retest = _pick(originals, "bcm", "exercise_result", 2)
        gate = _pick(originals, "bcm", "closure_gate")
        finding = _pick(originals, "issue", "issue_finding")
        overdue = _pick(originals, "issue", "overdue_escalation")
        waiver = add(
            "waiver_request",
            RECORD,
            1,
            "2027-09-15T10:00:00Z",
            "AS-P007",
            status="LOCAL_RETEST_PASS_MISUSED_AS_WAIVER_REQUEST_NOT_EFFECTIVE",
            source_refs=[retest, gate, finding, overdue],
            requested_waiver="BOISE_KEY_BYPASS_AND_CAPACITY_HOLD",
            claimed_selected_retest_restore_minutes=180,
            claimed_selected_retest_replay_gap_minutes=10,
            actual_key_bypass_open=True,
            board_decision_sha256=board_sha,
        )
        waiver_sha = hashlib.sha256(encoded(waiver)).hexdigest()
        challenge = add(
            "security_challenge",
            RECORD,
            1,
            "2027-09-16T10:00:00Z",
            "AS-P008",
            status="UNAUTHORIZED_WAIVER_CHALLENGED_AND_HELD",
            waiver_request_sha256=waiver_sha,
            source_refs=[gate, finding, overdue],
            conflict="NUMERIC_RETEST_DOES_NOT_CLOSE_UNREVIEWED_KEY_GATE_OR_CAPACITY_HOLD",
            conflicting_assignment=(
                "TECHNICAL_OWNER_REQUESTS_OWN_WAIVER_OUTSIDE_DELEGATED_APPROVAL"
            ),
            original_challenge_retained=True,
            technical_configuration_grant_unaffected=True,
            board_decision_sha256=board_sha,
        )
        add(
            "ceo_disposition",
            RECORD,
            1,
            "2027-09-17T10:00:00Z",
            "P001",
            status="WAIVER_DENIED_OVERSIGHT_ROUTING_REQUESTED_OPEN",
            waiver_request_sha256=waiver_sha,
            security_challenge_sha256=hashlib.sha256(encoded(challenge)).hexdigest(),
            board_decision_sha256=board_sha,
            requested_body="BOARD_AUDIT_AND_COMPLIANCE_COMMITTEE",
            committee_acknowledgment=False,
            collective_committee_decision="NOT_RECORDED",
            risk_acceptance=False,
            issue_closed=False,
            challenge_open=True,
        )
    for entry in events:
        body = entry["body"]
        for ref in body.get("source_refs", []):
            if ref["available_at"] >= body["event_at"]:
                raise CompanyStoreError("Governance decision precedes original availability")
    return events


def _provenance(pins: dict, scenario: str) -> dict:
    return {
        "source_reference": SOURCE_REF,
        "source_pins": pins,
        "scenario": scenario,
        "qualification": "FUTURE_FICTIONAL_SELECTED_GOVERNANCE_NO_REAL_BOARD_OR_AUDIT_CREDIT",
    }


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or destination.is_symlink()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(p.is_symlink() for p in destination.parents)
    ):
        raise CompanyStoreError("Fresh private governance source required")
    pins, routes, pbc, directors, originals = _context(repository, private_repository)
    with tempfile.TemporaryDirectory(prefix=".govapp-stage-", dir=destination.parent) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in BRANCHES.items():
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            records[scenario] = []
            for step in _steps(scenario, directors, originals[scenario]):
                body = step["body"]
                ref = store.append_version(
                    COMPANY,
                    branch,
                    step["system"],
                    step["record"],
                    expected_version=step["version"] - 1,
                    command_id=(
                        f"GOVAPP-{branch}-{step['system']}-{step['record']}-V{step['version']}"
                    ),
                    event_at=body["event_at"],
                    available_at=body["event_at"],
                    content=encoded(body),
                    provenance=_provenance(pins, scenario),
                )
                records[scenario].append(ref)
        receipt = {
            "schema": SCHEMA,
            "as_of": AS_OF,
            "company": COMPANY,
            "branches": BRANCHES,
            "status": "FUTURE_FICTIONAL_SELECTED_BOARD_MANAGEMENT_ENVELOPE_NO_CREDIT",
            "source_pins": pins,
            "selected_routes": routes,
            "pbc_candidate_groups": pbc,
            "population": {
                "services": 1,
                "board_directors_per_branch": 9,
                "board_decisions_per_branch": 1,
                "clean_native_versions": 16,
                "messy_native_versions": 18,
            },
            "records": records,
            "messy_challenge_open": True,
            "real_board_approval": False,
            "actual_hipaa_applicability": "UNDETERMINED",
            "real_provider_or_phi_operation": False,
            "source_complete": False,
            "audit_task_credit": False,
            "limits": LIMITS,
        }
        _write(stage / "RECEIPT.json", receipt)
        _write(
            stage / "MANIFEST.json",
            {
                "schema": SCHEMA + "_MANIFEST",
                "receipt_sha256": _sha(stage / "RECEIPT.json"),
                "company_db_sha256": _sha(stage / "company.sqlite3"),
                "module_sha256": _sha(Path(__file__)),
                "native_version_count": 34,
                "audit_task_credit": False,
            },
        )
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private_repository)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    root = Path(destination).absolute()
    if (
        not root.is_dir()
        or root.is_symlink()
        or root.stat().st_mode & 0o077
        or any(p.is_symlink() for p in root.parents)
        or {p.name for p in root.iterdir()} != {"RECEIPT.json", "MANIFEST.json", "company.sqlite3"}
    ):
        raise CompanyStoreError("Private ordinary three-file governance source required")
    for name in ("RECEIPT.json", "MANIFEST.json", "company.sqlite3"):
        _private(root / name)
    before = _frozen(root / "company.sqlite3")
    manifest = json.loads((root / "MANIFEST.json").read_text())
    receipt = json.loads((root / "RECEIPT.json").read_text())
    pins, routes, pbc, directors, originals = _context(repository, private_repository)
    if manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "receipt_sha256": _sha(root / "RECEIPT.json"),
        "company_db_sha256": _sha(root / "company.sqlite3"),
        "module_sha256": _sha(Path(__file__)),
        "native_version_count": 34,
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("Governance source manifest differs")
    expected = {
        "schema": SCHEMA,
        "as_of": AS_OF,
        "company": COMPANY,
        "branches": BRANCHES,
        "status": "FUTURE_FICTIONAL_SELECTED_BOARD_MANAGEMENT_ENVELOPE_NO_CREDIT",
        "source_pins": pins,
        "selected_routes": routes,
        "pbc_candidate_groups": pbc,
        "population": {
            "services": 1,
            "board_directors_per_branch": 9,
            "board_decisions_per_branch": 1,
            "clean_native_versions": 16,
            "messy_native_versions": 18,
        },
        "messy_challenge_open": True,
        "real_board_approval": False,
        "actual_hipaa_applicability": "UNDETERMINED",
        "real_provider_or_phi_operation": False,
        "source_complete": False,
        "audit_task_credit": False,
        "limits": LIMITS,
    }
    if (
        set(receipt) != set(expected) | {"records"}
        or any(receipt.get(k) != v for k, v in expected.items())
        or set(receipt["records"]) != set(BRANCHES)
    ):
        raise CompanyStoreError("Governance source qualification differs")
    with sqlite3.connect(
        (root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Governance native database integrity differs")
        counts = {
            table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("systems", "versions", "grants", "collections", "access_events")
        }
        if counts != {
            "systems": 20,
            "versions": 34,
            "grants": 0,
            "collections": 0,
            "access_events": 0,
        }:
            raise CompanyStoreError("Governance native/access population differs")
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        if systems != {
            (COMPANY, branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in SYSTEM_OWNERS.items()
        }:
            raise CompanyStoreError("Governance native custody differs")
        for scenario, branch in BRANCHES.items():
            steps = _steps(scenario, directors, originals[scenario])
            rows = db.execute(
                "SELECT * FROM versions WHERE branch=? ORDER BY rowid", (branch,)
            ).fetchall()
            refs = receipt["records"][scenario]
            if len(rows) != len(steps) or len(rows) != len(refs):
                raise CompanyStoreError("Governance branch version denominator differs")
            for row, step, ref in zip(rows, steps, refs, strict=True):
                body = step["body"]
                command = f"GOVAPP-{branch}-{step['system']}-{step['record']}-V{step['version']}"
                if (
                    (row["company"], row["branch"], row["system"], row["record"], row["version"])
                    != (COMPANY, branch, step["system"], step["record"], step["version"])
                    or row["content"] != encoded(body)
                    or row["sha256"] != hashlib.sha256(encoded(body)).hexdigest()
                    or row["event_at"] != body["event_at"]
                    or row["available_at"] != body["event_at"]
                    or row["imported_at"] >= row["event_at"]
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or row["command_id"] != command
                    or json.loads(row["provenance"]) != _provenance(pins, scenario)
                    or any(row[key] != ref[key] for key in SOURCE_FIELDS)
                ):
                    raise CompanyStoreError("Governance native action/authority/clock differs")
    if _frozen(root / "company.sqlite3") != before:
        raise CompanyStoreError("Governance source changed during verification")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    action = create if args.action == "create" else verify
    result = action(
        args.destination, repository=args.repository, private_repository=args.private_repository
    )
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, sort_keys=True))


if __name__ == "__main__":
    main()
