"""Selected fictional committee-cycle originals, anchored to branch-matched SEC003 history."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from . import company_sec003_selected_vulnerability_2027 as sec3
from .company_store import CompanyStore, CompanyStoreError, _time
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_GOV_SELECTED_OVERSIGHT_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
BRANCHES = {"CLEAN": "GOV-OVERSIGHT-CLEAN", "MESSY": "GOV-OVERSIGHT-MESSY"}
SOURCE_REFERENCE = "enterprise/audit_suite/company_gov_selected_oversight_2027.py"
SPEC = "enterprise/audit_suite/gov_selected_oversight_2027_spec_v1.json"
SPEC_SHA256 = "ff5151cc7e788f502d0324b1aa859750284d36c80a7558817fd38aff923e23a6"
ROUTE_BASELINE = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V15_2026-09-30.json"
SEC3_RUN = (
    "enterprise/generated/audit-suite/company-sec003-selected-vulnerability-2026-09-30/main-run-v1"
)
SEC3_REVIEW = (
    "enterprise/generated/audit-suite/company-sec003-selected-vulnerability-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
TRACKED_PINS = {
    SPEC: SPEC_SHA256,
    ROUTE_BASELINE: "bb3b74930b256f5396d2393438236e2bd9a3dd654d829080d0927129954a535c",
    "enterprise/audit_suite/company_sec003_selected_vulnerability_2027.py": (
        "2ae6e7ff15fedc7e1c1e74b8da4cfc5c6b036e3e4612829eb2a54cfb7e5a0551"
    ),
    "enterprise/audit_suite/sec003_selected_vulnerability_spec_v1.json": (
        "c4ac9b9de07f046027bb02bdbc4328ef3b49b6f5cba32ad4013280e06e91110d"
    ),
    "docs/governance/BOARD_AND_CAPITAL_GOVERNANCE_v1.0.1.md": (
        "dc1e2e3ea6e7ea8d364eae87bd890a8c79a5a577a7554ed371cda3810ea945a8"
    ),
    "docs/governance/GOVERNANCE_CONSTITUTION.md": (
        "efa3e78c9d86786f66159c6470a163dffc77f811679d16b876f049bc23498cef"
    ),
    "docs/governance/committees/AUDIT_AND_COMPLIANCE_COMMITTEE_CHARTER.md": (
        "d59a708310e56dbe67fc28629efbedd4f790a4ef9765d841b651f3335ab8e993"
    ),
    "docs/governance/committees/GOVERNANCE_AND_NOMINATING_COMMITTEE_CHARTER.md": (
        "d3afcfbaad2af59209b50994b15ae0846c329ebfb807e6ab14876bd2d9eb544e"
    ),
    "docs/governance/structured/board_and_committees.json": (
        "87afbe2d1500f25931e530bda95ed9fb7175fa6cb9573b0952072765f2cd2fa2"
    ),
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md": (
        "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751"
    ),
    "docs/governance/ENTERPRISE_COORDINATION_2026-09-13.md": (
        "3f358e1a89ba640ab35be53682388e7d9604c0f5627dfeb5a176a6de1e7c2da9"
    ),
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md": (
        "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496"
    ),
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md": (
        "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433"
    ),
}
PRIVATE_PINS = {
    f"{SEC3_RUN}/MANIFEST.json": "4ae2200e8735ea60e4a85f1158782926fdd50eda96238fc15031d5d9eda69af3",
    f"{SEC3_RUN}/RECEIPT.json": "85233a1e785ffea73f32996bc3f410e9b5c381720b6cbe941ff8a2bbd5474ff8",
    f"{SEC3_RUN}/company.sqlite3": (
        "a94b9f0e2d18e06afd2c83ae2012cea8da72102f9bafcf0e3968959eb6f1539f"
    ),
    SEC3_REVIEW: "f15bc7d94d04fa3599a0f852470e81ea53ce3dc1685d05d0fb15a65901013f36",
}
SELECTED_SOURCE_RECORDS = {
    "CLEAN": (
        ("vulnerability_reconciliation", "RECON-OCT-01", "RECONCILE_CENSUS_SCAN_BASELINE"),
        ("vulnerability_reconciliation", "CLOSE-01", "CLOSE_SELECTED_FINDING"),
    ),
    "MESSY": (
        ("vulnerability_reconciliation", "RECON-OCT-01", "FALSE_CLEAN_SIGNOFF"),
        (
            "vulnerability_reconciliation",
            "DISCOVER-NOV-01",
            "DISCOVER_CENSUS_BASELINE_AND_FINDING_GAP",
        ),
        ("vulnerability_exception", "EXC-SEC003-Q4-01", "OPEN_HISTORICAL_COVERAGE_EXCEPTION"),
    ),
}
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
    "origin",
    "provenance",
)
AUDIT_MEMBERS = ("DIR-CALDER", "DIR-GALIULLINA", "DIR-KINCAID")
GOVNOM_MEMBERS = ("DIR-KINCAID", "DIR-CALDER", "DIR-BELL")
TARGETS = tuple(
    f"TASK-{control}-corporate-{procedure}"
    for control in ("SH-GOV-001", "SH-GOV-004")
    for procedure in ("CHECK-SOC2:CC1.2", "IMPLEMENTATION", "TOD", "TOE")
)
SYSTEM_OWNERS = {
    "secretariat_intake": "AS-P004",
    "charter_register": "AS-P004",
    "committee_roster": "AS-P004",
    "conflict_questionnaire": "AS-P004",
    "eligibility_review": "AS-P004",
    "audit_committee_packet": "AS-P004",
    "committee_note": "AS-P004",
    "action_register": "AS-P004",
    "secretariat_discovery": "AS-P004",
    "governance_exception": "AS-P004",
    "secretariat_reconciliation": "AS-P004",
}


def _sha(path: Path) -> str:
    return sec3._sha(path)


def _frozen(paths: dict[str, Path]) -> dict:
    return {name: (sec3._private(path), _sha(path)) for name, path in paths.items()}


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    path.chmod(0o600)


def _context(repository: Path, private_repository: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    for rel, digest in TRACKED_PINS.items():
        path = repository / rel
        if path.is_symlink() or not path.is_file() or _sha(path) != digest:
            raise CompanyStoreError(f"Pinned GOV source/canon bytes differ: {rel}")
    spec = json.loads((repository / SPEC).read_text())
    if (
        spec.get("schema") != "SH_FICTIONAL_2027_GOV_SELECTED_OVERSIGHT_SPEC_V1"
        or spec.get("truth_class") != "TRAINING_SCENARIO_ONLY"
        or spec.get("case_id") != "SIM-GOV-SEC003-Q4-01"
        or spec.get("selected_committees") != ["COM-AUDIT", "COM-GOVNOM"]
        or spec.get("selected_director_for_eligibility") != "DIR-CALDER"
        or spec.get("secretary_contact") != "AS-P004"
        or spec.get("expected_native_versions") != {"CLEAN": 9, "MESSY": 14}
        or spec.get("chronology") != {"CLEAN": "2027-11-15", "MESSY": "2027-11-16"}
        or spec.get("selected_clean_source_records")
        != [[system, record] for system, record, _ in SELECTED_SOURCE_RECORDS["CLEAN"]]
        or spec.get("selected_messy_source_records")
        != [[system, record] for system, record, _ in SELECTED_SOURCE_RECORDS["MESSY"]]
    ):
        raise CompanyStoreError("Selected GOV specification differs")
    baseline = json.loads((repository / ROUTE_BASELINE).read_text())
    if len(baseline.get("rows", [])) != 566 or any(
        {
            row["task_id"]
            for row in baseline["rows"]
            if row["side"] == side and row["task_id"] in TARGETS
        }
        != set(TARGETS)
        or any(
            row["targeted_integrated_source_ids"]
            for row in baseline["rows"]
            if row["side"] == side and row["task_id"] in TARGETS
        )
        for side in "AB"
    ):
        raise CompanyStoreError("Selected GOV route baseline differs")
    board = json.loads(
        (repository / "docs/governance/structured/board_and_committees.json").read_text()
    )
    committees = {item["id"]: item for item in board["committees"]}
    if (
        board.get("state") != "LOCKED"
        or board.get("version") != "1.0.1"
        or tuple(committees["COM-AUDIT"]["members"]) != AUDIT_MEMBERS
        or committees["COM-AUDIT"]["chair"] != "DIR-CALDER"
        or tuple(committees["COM-GOVNOM"]["members"]) != GOVNOM_MEMBERS
        or committees["COM-GOVNOM"]["chair"] != "DIR-KINCAID"
    ):
        raise CompanyStoreError("Locked committee roster differs")
    paths = {rel: private / rel for rel in PRIVATE_PINS}
    before = _frozen(paths)
    if {name: value[-1] for name, value in before.items()} != PRIVATE_PINS:
        raise CompanyStoreError("Reviewed SEC003 source bytes differ")
    review = json.loads(paths[SEC3_REVIEW].read_text())
    if (
        review.get("verdict") != "PASS_SELECTED_FICTIONAL_COMPANY_SOURCE_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or review.get("sha256", {}).get("main_manifest")
        != PRIVATE_PINS[f"{SEC3_RUN}/MANIFEST.json"]
        or review.get("sha256", {}).get("main_receipt") != PRIVATE_PINS[f"{SEC3_RUN}/RECEIPT.json"]
        or review.get("sha256", {}).get("main_native_db")
        != PRIVATE_PINS[f"{SEC3_RUN}/company.sqlite3"]
    ):
        raise CompanyStoreError("SEC003 independent review join differs")
    sec3.verify(private / SEC3_RUN, repository=repository, private_repository=private)
    if _frozen(paths) != before:
        raise CompanyStoreError("SEC003 source changed during verification")
    receipt = json.loads(paths[f"{SEC3_RUN}/RECEIPT.json"].read_text())
    if (
        receipt.get("schema") != sec3.SCHEMA
        or receipt.get("branches") != sec3.BRANCHES
        or receipt.get("native_version_counts") != {"CLEAN": 11, "MESSY": 18}
        or receipt.get("messy_historical_exception_status") != "OPEN"
        or receipt.get("source_complete") is not False
        or receipt.get("audit_task_credit") is not False
    ):
        raise CompanyStoreError("SEC003 source boundary differs")
    refs = {}
    with sqlite3.connect(
        paths[f"{SEC3_RUN}/company.sqlite3"].as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        for side, branch in sec3.BRANCHES.items():
            refs[side] = []
            for system, record, action in SELECTED_SOURCE_RECORDS[side]:
                selected = [
                    item
                    for item in receipt["records"][side]
                    if (item["system"], item["record"], item["version"]) == (system, record, 1)
                ]
                if len(selected) != 1 or selected[0]["branch"] != branch:
                    raise CompanyStoreError("Cross-branch or missing SEC003 source tuple")
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=1",
                    (COMPANY, branch, system, record),
                ).fetchone()
                if row is None or CompanyStore._metadata(row) != selected[0]:
                    raise CompanyStoreError("SEC003 exact native source tuple differs")
                body = json.loads(row["content"])
                if (
                    body.get("scenario") != side
                    or body.get("action") != action
                    or body.get("audit_task_credit") is not False
                    or _time(row["available_at"]) >= _time("2027-11-15T09:00:00+00:00")
                ):
                    raise CompanyStoreError("SEC003 branch, action or chronology differs")
                if (
                    side == "MESSY"
                    and record == "RECON-OCT-01"
                    and body["detail"]
                    != {
                        "reported_coverage": "4/4",
                        "actual_coverage": "3/4",
                        "decision": "INCORRECTLY_ACCEPTED",
                        "independent_assurance": False,
                    }
                ):
                    raise CompanyStoreError("Messy false-clean decision differs")
                if (
                    side == "MESSY"
                    and record == "DISCOVER-NOV-01"
                    and (body["detail"].get("self_review_of_october") is not True)
                ):
                    raise CompanyStoreError("Messy self-review boundary differs")
                if (
                    side == "MESSY"
                    and record == "EXC-SEC003-Q4-01"
                    and (
                        body["detail"].get("status") != "OPEN"
                        or body["detail"].get("independent_assurance") is not False
                    )
                ):
                    raise CompanyStoreError("Messy historical exception differs")
                if (
                    side == "CLEAN"
                    and record == "RECON-OCT-01"
                    and (
                        body["detail"].get("decision") != "OPEN_SELECTED_FINDING"
                        or body["detail"].get("observed_count") != 4
                    )
                ):
                    raise CompanyStoreError("Clean selected finding differs")
                if (
                    side == "CLEAN"
                    and record == "CLOSE-01"
                    and (
                        body["detail"].get("selected_finding_closed") is not True
                        or body["detail"].get("enterprise_population_complete") is not False
                    )
                ):
                    raise CompanyStoreError("Clean selected closure differs")
                refs[side].append({key: selected[0][key] for key in SOURCE_FIELDS})
    if _frozen(paths) != before:
        raise CompanyStoreError("SEC003 source changed during exact tuple read")
    return {"spec": spec, "refs": refs, "pins": {**TRACKED_PINS, **PRIVATE_PINS}}


def _plan(side: str) -> list[tuple[str, str, str, str, str, str, dict]]:
    if side == "CLEAN":
        return [
            (
                "15T09:00",
                "secretariat_intake",
                "CASE-01",
                "AS-P004",
                "OPEN_SELECTED_GOV_CASE",
                "SELECTED_REVIEW_OPEN",
                {},
            ),
            (
                "15T09:10",
                "charter_register",
                "CHARTER-CHECK-01",
                "AS-P004",
                "COMPARE_LOCKED_2026_INSTRUMENTS",
                "REFERENCE_ONLY_NO_NEW_APPROVAL",
                {},
            ),
            (
                "15T09:20",
                "committee_roster",
                "ROSTER-01",
                "AS-P004",
                "CHECK_SELECTED_COMMITTEE_MEMBERS",
                "SELECTED_ROSTER_MATCHES_2026_REFERENCE",
                {"audit_members": AUDIT_MEMBERS, "govnom_members": GOVNOM_MEMBERS},
            ),
            (
                "15T09:30",
                "conflict_questionnaire",
                "CALDER-Q-01",
                "DIR-CALDER",
                "RETURN_SELECTED_SUBJECT_ATTESTATION",
                "NO_CONFLICT_SELF_REPORTED_FOR_SELECTED_CASE",
                {"self_report_only": True},
            ),
            (
                "15T09:40",
                "eligibility_review",
                "ELIGIBILITY-01",
                "AS-P004",
                "RECORD_GOVNOM_SELECTED_PARTICIPATION_REVIEW",
                "SELECTED_PARTICIPATION_NOT_OBJECTED",
                {
                    "review_contacts": ["DIR-KINCAID", "DIR-BELL"],
                    "subject_recused_from_own_review": "DIR-CALDER",
                    "collective_resolution": False,
                },
            ),
            (
                "15T10:00",
                "audit_committee_packet",
                "PACKET-01",
                "AS-P004",
                "PREPARE_COMPLETE_SELECTED_FINDING_PACKET",
                "SELECTED_FINDING_AND_CLOSURE_VISIBLE",
                {"presented_source_records": ["RECON-OCT-01", "CLOSE-01"]},
            ),
            (
                "15T11:00",
                "committee_note",
                "DRAFT-NOTE-01",
                "AS-P004",
                "RECORD_SELECTED_COMMITTEE_CHALLENGE_DRAFT",
                "UNADOPTED_DRAFT_CHALLENGE",
                {
                    "questioner": "DIR-GALIULLINA",
                    "question": (
                        "What independently corroborates selected closure and what remains "
                        "outside the four-asset footprint?"
                    ),
                    "no_control_failure_in_clean_source": True,
                },
            ),
            (
                "15T11:20",
                "action_register",
                "ACTION-01",
                "AS-P004",
                "KEEP_SELECTED_ASSURANCE_QUESTION_OPEN",
                "OPEN_REQUEST_FOR_INDEPENDENT_REVIEW",
                {"board_agenda_request_only": True},
            ),
            (
                "15T11:30",
                "secretariat_reconciliation",
                "RECON-01",
                "AS-P004",
                "RECONCILE_SELECTED_DRAFT_AND_OPEN_QUESTION",
                "SELECTED_CYCLE_OPEN_NO_COLLECTIVE_APPROVAL",
                {},
            ),
        ]
    if side != "MESSY":
        raise CompanyStoreError("Unknown GOV branch")
    return [
        (
            "16T09:00",
            "secretariat_intake",
            "CASE-01",
            "AS-P004",
            "OPEN_SELECTED_GOV_CASE",
            "SELECTED_REVIEW_OPEN",
            {},
        ),
        (
            "16T09:10",
            "charter_register",
            "CHARTER-CHECK-01",
            "AS-P004",
            "COMPARE_LOCKED_2026_INSTRUMENTS",
            "REFERENCE_ONLY_NO_NEW_APPROVAL",
            {},
        ),
        (
            "16T09:20",
            "committee_roster",
            "ROSTER-01",
            "AS-P004",
            "CHECK_SELECTED_COMMITTEE_MEMBERS",
            "SELECTED_ROSTER_MATCHES_2026_REFERENCE",
            {"audit_members": AUDIT_MEMBERS, "govnom_members": GOVNOM_MEMBERS},
        ),
        (
            "16T09:30",
            "conflict_questionnaire",
            "CALDER-Q-PENDING",
            "AS-P004",
            "REQUEST_SELECTED_SUBJECT_ATTESTATION",
            "QUESTIONNAIRE_NOT_RETURNED",
            {"self_report_only": False},
        ),
        (
            "16T09:40",
            "eligibility_review",
            "ELIGIBILITY-INITIAL",
            "AS-P004",
            "CLAIM_SELECTED_ELIGIBILITY_WITHOUT_ATTESTATION",
            "FALSE_ELIGIBILITY_CLEAN",
            {"questionnaire_returned": False, "collective_resolution": False},
        ),
        (
            "16T10:00",
            "audit_committee_packet",
            "PACKET-INITIAL",
            "AS-P004",
            "OMIT_HISTORICAL_EXCEPTION_FROM_PACKET",
            "ADVERSE_RECORD_OMITTED",
            {"presented_source_records": [], "omitted_source_record": "EXC-SEC003-Q4-01"},
        ),
        (
            "16T11:00",
            "committee_note",
            "DRAFT-NOTE-INITIAL",
            "AS-P004",
            "DRAFT_FALSE_NO_ADVERSE_MATTERS",
            "FALSE_CLEAN_UNADOPTED_DRAFT",
            {"challenge_recorded": False},
        ),
        (
            "16T11:20",
            "action_register",
            "ACTION-FALSE-CLOSE",
            "AS-P004",
            "CLAIM_CASE_CLOSED",
            "FALSE_CLOSE",
            {"historical_exception_disclosed": False},
        ),
        (
            "17T09:00",
            "secretariat_discovery",
            "DISCOVERY-01",
            "AS-P004",
            "RECONCILE_PACKET_TO_SEC003_ORIGINALS",
            "OMISSION_AND_FALSE_CLOSE_CONFIRMED",
            {"source_exception": "EXC-SEC003-Q4-01"},
        ),
        (
            "17T09:10",
            "governance_exception",
            "EXC-OPEN-01",
            "AS-P004",
            "OPEN_SELECTED_GOVERNANCE_EXCEPTION",
            "OPEN",
            {"missing_questionnaire": True, "packet_omission": True, "false_close": True},
        ),
        (
            "17T09:20",
            "audit_committee_packet",
            "PACKET-CORRECTED",
            "AS-P004",
            "DISTRIBUTE_CORRECTED_INTERNAL_PACKET",
            "CORRECTED_INTERNAL_DRAFT",
            {"presented_source_records": ["RECON-OCT-01", "DISCOVER-NOV-01", "EXC-SEC003-Q4-01"]},
        ),
        (
            "17T09:30",
            "committee_note",
            "DRAFT-NOTE-AMENDMENT",
            "AS-P004",
            "DRAFT_CHALLENGE_OF_FALSE_CLEAN",
            "UNADOPTED_DRAFT_CHALLENGE",
            {
                "questioner": "DIR-GALIULLINA",
                "question": (
                    "Why was 3/4 reported 4/4, and who will review AS-P008's self-review "
                    "independently?"
                ),
                "historical_exception_open": True,
            },
        ),
        (
            "17T09:40",
            "action_register",
            "ACTION-REOPEN",
            "AS-P004",
            "REOPEN_SELECTED_ASSURANCE_ACTION",
            "OPEN_INDEPENDENT_REVIEW_PENDING",
            {"board_agenda_request_only": True},
        ),
        (
            "17T09:50",
            "secretariat_reconciliation",
            "RECON-01",
            "AS-P004",
            "RECONCILE_CORRECTION_AND_HISTORICAL_EXCEPTION",
            "HISTORICAL_GOV_EXCEPTION_OPEN",
            {"questionnaire_still_missing": True, "adopted_minutes": False},
        ),
    ]


def _rows(context: dict, side: str) -> list[dict]:
    spec = context["spec"]
    branch = BRANCHES[side]
    rows = []
    for clock, system, record, actor, action, status, detail in _plan(side):
        event = _time("2027-11-" + clock + ":00+00:00")
        available = _time((datetime.fromisoformat(event) + timedelta(minutes=1)).isoformat())
        body = {
            "schema": SCHEMA + "_NATIVE_EVENT",
            "truth_class": "TRAINING_SCENARIO_ONLY",
            "company": COMPANY,
            "branch": branch,
            "scenario": side,
            "case_id": spec["case_id"],
            "system": system,
            "record": record,
            "actor_id": actor,
            "action": action,
            "status": status,
            "detail": detail,
            "event_at": event,
            "available_at": available,
            "upstream_original_refs": context["refs"][side],
            "previous_native_content": (
                {"record": rows[-1]["record"], "sha256": rows[-1]["sha256"]} if rows else None
            ),
            "locked_charter_reference_only": True,
            "fictional_committee_cycle": True,
            "actual_board_meeting": False,
            "legal_quorum_established": False,
            "collective_resolution_recorded": False,
            "adopted_minutes": False,
            "complete_oversight_population": False,
            "authored_cc12_clause_satisfied": False,
            "independent_assurance_completed": False,
            "real_external_messages_sent": 0,
            "actual_phi_processing": False,
            "source_complete": False,
            "fresh_audit_pair_created": False,
            "audit_task_credit": False,
        }
        content = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        rows.append(
            {
                "system": system,
                "record": record,
                "event_at": event,
                "available_at": available,
                "content": content,
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    if len(rows) != spec["expected_native_versions"][side]:
        raise CompanyStoreError("Selected GOV native denominator differs")
    return rows


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    destination = Path(destination).absolute()
    sec3._private(destination.parent, directory=True)
    if destination.exists() or destination.is_symlink() or destination != destination.resolve():
        raise CompanyStoreError("Fresh private GOV destination required")
    context = _context(repository, private_repository)
    with tempfile.TemporaryDirectory(prefix=".gov-selected-stage-", dir=destination.parent) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        refs = {}
        for side, branch in BRANCHES.items():
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            refs[side] = []
            for row in _rows(context, side):
                ref = store.append_version(
                    COMPANY,
                    branch,
                    row["system"],
                    row["record"],
                    expected_version=0,
                    command_id=f"GOV-{branch}-{row['record']}",
                    event_at=row["event_at"],
                    available_at=row["available_at"],
                    content=row["content"],
                    provenance={
                        "source_reference": SOURCE_REFERENCE,
                        "truth_class": "TRAINING_SCENARIO_ONLY",
                    },
                )
                if ref["sha256"] != row["sha256"]:
                    raise CompanyStoreError("GOV native content differs")
                refs[side].append(ref)
        receipt = {
            "schema": SCHEMA,
            "company": COMPANY,
            "branches": BRANCHES,
            "records": refs,
            "spec_sha256": SPEC_SHA256,
            "source_pins": context["pins"],
            "upstream_original_refs": context["refs"],
            "native_version_counts": {side: len(rows) for side, rows in refs.items()},
            "selected_case_count": 1,
            "target_task_ids": list(TARGETS),
            "clean_selected_finding_status": "CLOSED_SELECTED_ONLY",
            "messy_historical_sec003_exception_status": "OPEN",
            "messy_historical_governance_exception_status": "OPEN",
            "actual_board_meeting": False,
            "legal_quorum_established": False,
            "adopted_minutes": False,
            "complete_oversight_population": False,
            "authored_cc12_clause_satisfied": False,
            "independent_assurance_completed": False,
            "real_external_messages_sent": 0,
            "actual_phi_processing": False,
            "source_complete": False,
            "fresh_audit_pair_created": False,
            "audit_task_credit": False,
            "limits": context["spec"]["limits"],
        }
        _write(stage / "RECEIPT.json", receipt)
        _write(
            stage / "MANIFEST.json",
            {
                "schema": SCHEMA + "_MANIFEST",
                "receipt_sha256": _sha(stage / "RECEIPT.json"),
                "db_sha256": _sha(stage / "company.sqlite3"),
                "module_sha256": _sha(Path(__file__)),
                "native_version_count": 23,
                "audit_task_credit": False,
            },
        )
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private_repository)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    root = Path(destination).absolute()
    sec3._private(root, directory=True)
    paths = {name: root / name for name in ("MANIFEST.json", "RECEIPT.json", "company.sqlite3")}
    if {path.name for path in root.iterdir()} != set(paths):
        raise CompanyStoreError("Exact three-file GOV source required")
    before = _frozen(paths)
    context = _context(repository, private_repository)
    receipt = json.loads(paths["RECEIPT.json"].read_text())
    manifest = json.loads(paths["MANIFEST.json"].read_text())
    if manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "receipt_sha256": _sha(paths["RECEIPT.json"]),
        "db_sha256": _sha(paths["company.sqlite3"]),
        "module_sha256": _sha(Path(__file__)),
        "native_version_count": 23,
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("GOV manifest differs")
    expected = {
        "schema": SCHEMA,
        "company": COMPANY,
        "branches": BRANCHES,
        "records": receipt.get("records"),
        "spec_sha256": SPEC_SHA256,
        "source_pins": context["pins"],
        "upstream_original_refs": context["refs"],
        "native_version_counts": {"CLEAN": 9, "MESSY": 14},
        "selected_case_count": 1,
        "target_task_ids": list(TARGETS),
        "clean_selected_finding_status": "CLOSED_SELECTED_ONLY",
        "messy_historical_sec003_exception_status": "OPEN",
        "messy_historical_governance_exception_status": "OPEN",
        "actual_board_meeting": False,
        "legal_quorum_established": False,
        "adopted_minutes": False,
        "complete_oversight_population": False,
        "authored_cc12_clause_satisfied": False,
        "independent_assurance_completed": False,
        "real_external_messages_sent": 0,
        "actual_phi_processing": False,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": context["spec"]["limits"],
    }
    if receipt != expected:
        raise CompanyStoreError("GOV receipt scope differs")
    with sqlite3.connect(
        paths["company.sqlite3"].as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("GOV native SQLite integrity differs")
        page_size = db.execute("PRAGMA page_size").fetchone()[0]
        page_count = db.execute("PRAGMA page_count").fetchone()[0]
        if paths["company.sqlite3"].stat().st_size != page_size * page_count:
            raise CompanyStoreError("GOV native SQLite physical byte extent differs")
        for table in ("grants", "collections", "access_events"):
            if db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]:
                raise CompanyStoreError("GOV source contains audit access journal")
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        if systems != {
            (COMPANY, branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in SYSTEM_OWNERS.items()
        }:
            raise CompanyStoreError("GOV native system roster differs")
        if db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != 23:
            raise CompanyStoreError("GOV native version count differs")
        for side, branch in BRANCHES.items():
            rows = _rows(context, side)
            refs = receipt["records"][side]
            native = db.execute(
                "SELECT * FROM versions WHERE branch=? ORDER BY rowid", (branch,)
            ).fetchall()
            if len(rows) != len(native) or len(rows) != len(refs):
                raise CompanyStoreError("GOV native branch count differs")
            for row, stored, ref in zip(rows, native, refs, strict=True):
                if (
                    (
                        stored["company"],
                        stored["branch"],
                        stored["system"],
                        stored["record"],
                        stored["version"],
                    )
                    != (COMPANY, branch, row["system"], row["record"], 1)
                    or stored["content"] != row["content"]
                    or stored["sha256"] != row["sha256"]
                    or stored["event_at"] != row["event_at"]
                    or stored["available_at"] != row["available_at"]
                    or stored["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or stored["command_id"] != f"GOV-{branch}-{row['record']}"
                    or json.loads(stored["provenance"])
                    != {
                        "source_reference": SOURCE_REFERENCE,
                        "truth_class": "TRAINING_SCENARIO_ONLY",
                    }
                    or _time(stored["imported_at"]) != stored["imported_at"]
                    or stored["imported_at"] >= "2027-01-01"
                    or CompanyStore._metadata(stored) != ref
                ):
                    raise CompanyStoreError("GOV native bytes, branch, clocks or receipt differ")
    if _frozen(paths) != before:
        raise CompanyStoreError("GOV source changed during verification")
    return {
        "status": "VERIFIED_FICTIONAL_SELECTED_GOV_OVERSIGHT_NO_AUDIT_CREDIT",
        "native_version_counts": {"CLEAN": 9, "MESSY": 14},
        "audit_task_credit": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("destination", type=Path)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    args = parser.parse_args()
    command = create if args.action == "create" else verify
    print(
        json.dumps(
            command(
                args.destination,
                repository=args.repository,
                private_repository=args.private_repository,
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
