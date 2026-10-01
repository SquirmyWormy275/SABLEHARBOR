"""Company-owned reference-scope intake and legal-response exercise history.

These operations exist independently of an audit. The public recipe contains no
instructor Key. Its private receipt supplies locators, never an accepted N/A or
an assertion that an outside proceeding occurred.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from . import company_leg001_operating_docket_2027 as docket
from . import company_leg001_provision_overlay_2027 as overlay
from .company_store import CompanyStore, CompanyStoreError, _time
from .documentary_283_route_reconciliation_v6 import _p1_inventory
from .operating_source_bridge import encoded
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_LEG001_TRIGGER_SCREENING_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
SOURCE = "enterprise/audit_suite/company_leg001_trigger_screening_2027.py"
ROUTES = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V17_2026-10-01.json"
ROUTES_SHA256 = "43b33d7ca19e670eea704193fff947c268c2d1c736f0c8829420a556576e8bcb"
BRANCHES = {"CLEAN": "LEGINT-CLEAN", "MESSY": "LEGINT-MESSY"}
OWNERS = {
    "intake_channel_register": "AS-P014",
    "regulatory_response_playbook": "AS-P003",
    "intake_channel_ledger": "AS-P014",
    "intake_tail_reconciliation": "AS-P014",
    "legal_matter_classification": "AS-P003",
    "monthly_intake_screening": "AS-P014",
    "quarterly_legal_review": "AS-P003",
    "legal_response_exercise": "AS-P014",
    "legal_exception_register": "AS-P003",
    "period_legal_disposition": "AS-P003",
    "independent_intake_review": "AS-P009",
}
CHANNELS = ("LEGAL-MAIL", "REGISTERED-AGENT", "CUSTOMER-LEGAL", "PROVIDER-LEGAL")
SCOPE = {
    "company_id": COMPANY,
    "boundary": "Corporate shared-control legal intake for the approved reference assessment",
    "period_start": "2027-01-01T00:00:00+00:00",
    "period_end": "2027-12-31T23:59:59+00:00",
    "excluded": ["other legal entities", "unregistered personal inboxes", "real-world matters"],
    "unregistered_channel_completeness": "NOT_ESTABLISHED",
}
REFERENCES = {
    "access": "https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-160/subpart-C/section-160.310",
    "penalty_context": "https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-160/subpart-D",
    "hearing_context": "https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-160/subpart-E",
    "enforcement_process": "https://www.hhs.gov/hipaa/for-professionals/compliance-enforcement/enforcement-process/index.html",
}


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _context(repository, private_repository):
    repo, private = (
        Path(repository).resolve(strict=True),
        Path(private_repository).resolve(strict=True),
    )
    if _p1_inventory(private) != overlay.P1_FREEZE:
        raise CompanyStoreError("Frozen P1 inventory differs")
    pins = {ROUTES: ROUTES_SHA256, docket.APPOINTMENTS: docket.APPOINTMENTS_SHA256}
    for name, expected in pins.items():
        p = repo / name
        if p.is_symlink() or _sha(p) != expected:
            raise CompanyStoreError("Tracked legal-intake input differs")
    states = {}
    for name, expected in overlay.PRIVATE_PINS.items():
        p = private / name
        state = docket._private(p)
        if state[-1] != expected:
            raise CompanyStoreError("Reviewed legal-docket input differs")
        states[p] = state
    receipt = json.loads((private / overlay.PREDECESSOR_RUN / "RECEIPT.json").read_text())
    refs = {}
    for side in BRANCHES:
        found = [r for r in receipt["records"][side] if r["system"] == "reconciliation"]
        if len(found) != 1 or found[0]["branch"] != (
            "LEG-CLEAN" if side == "CLEAN" else "LEG-MESSY"
        ):
            raise CompanyStoreError("Branch-specific legal basis missing")
        refs[side] = found[0]
    routes = json.loads((repo / ROUTES).read_text())
    selected = []
    for r in routes["rows"]:
        if r["side"] != "A" or r["control_id"] != "SH-LEG-001":
            continue
        leads = r.get("targeted_integrated_source_ids", [])
        leads += [v for k, values in r.items() if k.endswith("reviewed_source_ids") for v in values]
        if not leads:
            selected.append(r["task_id"])
    if len(selected) != 48 or len(set(selected)) != 48:
        raise CompanyStoreError("Exact remaining legal route denominator differs")
    return {
        "repo": repo,
        "private": private,
        "pins": {**pins, **overlay.PRIVATE_PINS},
        "states": states,
        "refs": refs,
        "task_ids": sorted(selected),
    }


def _steps(scenario, basis):
    """Operational content only: no task IDs, outcomes, rubric or branch labels."""
    if scenario not in BRANCHES:
        raise CompanyStoreError("Explicit legal-intake branch required")
    rows = []

    def add(system, record, at, detail):
        rows.append((system, record, at, {"record_id": record, "scope": SCOPE, **detail}))

    add(
        "intake_channel_register",
        "REGISTRY-2027",
        "2027-01-01T09:00:00+00:00",
        {
            "approved_by": "AS-P003",
            "operating_owner": "AS-P014",
            "channels": list(CHANNELS),
            "change_rule": "Legal approves additions; preserve prior registry",
            "completeness_basis": (
                "Declared reference-scope channels; independent reconciliation required"
            ),
        },
    )
    add(
        "regulatory_response_playbook",
        "PLAYBOOK-2027",
        "2027-01-05T09:00:00+00:00",
        {
            "approved_by": "AS-P003",
            "reference_checked_as_of": "2026-10-01",
            "primary_reference_urls": REFERENCES,
            "2027_primary_authority_status": "RECHECK_AT_TRIGGER",
            "procedure": [
                "Record receipt and service facts; preserve original notice and records",
                "Counsel authenticates authority, scope and legal timing",
                "Route lawful regulator access separately from ordinary customer disclosure",
                "Escalate inaccessible provider records; preserve requests and provider responses",
                "For exigent lawful access, use counsel-authorized available access "
                "while recording limits",
                "Counsel maintains case-specific deadlines, privilege and official dispositions",
            ],
            "penalty_amounts": None,
            "hearing_or_penalty_case": None,
        },
    )
    for month in range(1, 13):
        last = calendar.monthrange(2027, month)[1]
        day = f"2027-{month:02d}-{last:02d}"
        for channel in CHANNELS:
            items = []
            if month == 9 and channel == "PROVIDER-LEGAL":
                items = [
                    {
                        "item_id": "INQ-PROVIDER-0907",
                        "received_at": "2027-09-07T11:00:00+00:00",
                        "sender_role": "Recovery-support contract manager",
                        "subject": "Customer retention and return instructions",
                        "agency_notice_attachment_ids": [],
                    }
                ]
            if month == 10 and channel == "CUSTOMER-LEGAL":
                items = [
                    {
                        "item_id": "INQ-CUSTOMER-1020",
                        "received_at": "2027-10-20T11:00:00+00:00",
                        "sender_role": "Customer contract owner",
                        "subject": "Records response service level",
                        "agency_notice_attachment_ids": [],
                    }
                ]
            add(
                "intake_channel_ledger",
                f"LEDGER-{month:02d}-{channel}",
                day + "T14:00:00+00:00",
                {
                    "channel_id": channel,
                    "window_start": f"2027-{month:02d}-01T00:00:00+00:00",
                    "window_end": day + "T23:59:59+00:00",
                    "export_cutoff": day + "T13:00:00+00:00",
                    "remaining_day_followup_required": True,
                    "intake_items": items,
                    "record_count": len(items),
                    "extract_owner": "AS-P014",
                },
            )
        reviewed = list(CHANNELS)
        if scenario == "MESSY" and month == 9:
            reviewed = list(CHANNELS[:-1])
        add(
            "monthly_intake_screening",
            f"SCREEN-{month:02d}",
            day + "T15:00:00+00:00",
            {
                "reviewed_by": "AS-P014",
                "registry_record_id": "REGISTRY-2027",
                "reviewed_channel_ids": reviewed,
                "ledger_record_ids": [f"LEDGER-{month:02d}-{c}" for c in reviewed],
                "observed_official_notice_ids": [],
                "screening_state": (
                    "CLOSED" if scenario == "MESSY" and month == 9 else "PRELIMINARY"
                ),
                "reviewed_through": day + "T15:00:00+00:00",
                "period_tail_attestation": (
                    "Channel custodians report no additional intake between export cutoff "
                    "and this review; later hours remain pending"
                ),
            },
        )
        next_day = (datetime.fromisoformat(day) + timedelta(days=1)).date().isoformat()
        add(
            "intake_tail_reconciliation",
            f"TAIL-{month:02d}",
            next_day + "T09:00:00+00:00",
            {
                "extract_owner": "AS-P014",
                "channel_ids": reviewed,
                "window_start": day + "T13:00:00+00:00",
                "window_end": day + "T23:59:59+00:00",
                "additional_intake_items": [],
                "related_screening_id": f"SCREEN-{month:02d}",
                "extract_state": "COMPLETED_RECORDED_CHANNELS",
            },
        )
    add(
        "legal_matter_classification",
        "INQ-PROVIDER-0907",
        ("2027-09-12T09:00:00+00:00" if scenario == "CLEAN" else "2027-11-09T09:00:00+00:00"),
        {
            "reviewed_by": "AS-P003",
            "source_item_id": "INQ-PROVIDER-0907",
            "classification": "CONTRACTUAL_CUSTOMER_INSTRUCTION",
            "official_regulator_notice": False,
            "reason": (
                "The retained item is a supplier question; "
                "no agency notice or case identifier is attached"
            ),
            "response_route": "Records owner obtains customer instruction; preserve the inquiry",
        },
    )
    add(
        "legal_matter_classification",
        "INQ-CUSTOMER-1020",
        "2027-10-21T09:00:00+00:00",
        {
            "reviewed_by": "AS-P003",
            "source_item_id": "INQ-CUSTOMER-1020",
            "classification": "CONTRACTUAL_SERVICE_ESCALATION",
            "official_regulator_notice": False,
            "reason": (
                "Customer service-level inquiry is separate from a Secretary complaint "
                "or determination"
            ),
        },
    )
    for quarter, month in enumerate((3, 6, 9, 12), 1):
        day = f"2027-{month:02d}-{calendar.monthrange(2027, month)[1]:02d}"
        add(
            "quarterly_legal_review",
            f"QUARTER-{quarter}",
            day + "T16:00:00+00:00",
            {
                "reviewed_by": "AS-P003",
                "screening_record_ids": [f"SCREEN-{m:02d}" for m in range(month - 2, month + 1)],
                "observed_case_ids": [],
                "review_state": "FILED",
                "review_basis": "Monthly screening summaries; retained originals remain available",
            },
        )
        completed_day = (datetime.fromisoformat(day) + timedelta(days=2)).date().isoformat()
        add(
            "quarterly_legal_review",
            f"QUARTER-{quarter}",
            completed_day + "T10:00:00+00:00",
            {
                "reviewed_by": "AS-P003",
                "tail_record_versions": {f"TAIL-{m:02d}": 1 for m in range(month - 2, month + 1)},
                "observed_case_ids": [],
                "review_state": (
                    "RECONCILIATION_REQUIRED"
                    if scenario == "MESSY" and quarter == 3
                    else "DECLARED_WINDOW_RECONCILED"
                ),
                "scope_limit": "Registered channels only",
            },
        )
    # This is a company tabletop record, never a simulated outside agency notice.
    exercise = [
        (
            "EXERCISE-REQUEST",
            "2027-03-12T09:00:00+00:00",
            {
                "exercise_only": True,
                "facilitator": "AS-P014",
                "request_summary": "Lawful regulator access to records",
                "urgent_access": True,
                "real_notice_received": False,
            },
        ),
        (
            "EXERCISE-PRESERVE",
            "2027-03-12T09:20:00+00:00",
            {
                "exercise_only": True,
                "approved_by": "AS-P003",
                "preserved_record_sets": ["intake originals", "provider correspondence"],
                "hold_state": "APPLIED_TO_EXERCISE_COPY",
            },
        ),
        (
            "EXERCISE-PROVIDER",
            "2027-03-12T09:40:00+00:00",
            {
                "exercise_only": True,
                "provider_copy_state": "TEMPORARILY_UNAVAILABLE",
                "provider_followup_owner": "AS-P014",
            },
        ),
        (
            "EXERCISE-ACCESS",
            "2027-03-12T10:00:00+00:00",
            {
                "exercise_only": True,
                "authority_reviewer": "AS-P003",
                "decision": "USE_AVAILABLE_AUTHORIZED_RECORD_ACCESS"
                if scenario == "CLEAN"
                else "WAIT_FOR_PROVIDER_COPY",
                "available_company_copy_ids": ["retained intake originals"],
                "customer_disclosure_rule_is_authority_basis": False,
            },
        ),
        (
            "EXERCISE-REPORT",
            "2027-03-14T15:00:00+00:00",
            {
                "exercise_only": True,
                "reviewed_by": "AS-P003",
                "status": "CLOSED" if scenario == "CLEAN" else "FOLLOWUP_REQUIRED",
                "urgent_access_path_exercised": scenario == "CLEAN",
                "provider_limits_retained": True,
            },
        ),
    ]
    for record, at, body in exercise:
        add("legal_response_exercise", record, at, body)
    if scenario == "MESSY":
        add(
            "legal_response_exercise",
            "EXERCISE-RETEST",
            "2027-03-18T10:00:00+00:00",
            {
                "exercise_only": True,
                "reviewed_by": "AS-P003",
                "available_company_copy_ids": ["retained intake originals"],
                "urgent_access_path_exercised": True,
                "prior_report_id": "EXERCISE-REPORT",
            },
        )
        add(
            "legal_exception_register",
            "EXC-INTAKE-2027",
            "2027-11-04T10:00:00+00:00",
            {
                "owner": "AS-P003",
                "identified_by": "AS-P009",
                "status": "OPEN",
                "affected_records": ["SCREEN-09", "QUARTER-3"],
                "registry_channel_count": 4,
                "reviewed_channel_count": 3,
                "action_owner": "AS-P014",
            },
        )
        add(
            "monthly_intake_screening",
            "SCREEN-09",
            "2027-11-10T10:00:00+00:00",
            {
                "reviewed_by": "AS-P014",
                "registry_record_id": "REGISTRY-2027",
                "reviewed_channel_ids": list(CHANNELS),
                "ledger_record_ids": [f"LEDGER-09-{c}" for c in CHANNELS],
                "observed_official_notice_ids": [],
                "screening_state": "CLOSED_AFTER_RECONCILIATION",
                "classification_record_ids": ["INQ-PROVIDER-0907"],
                "historical_exception_id": "EXC-INTAKE-2027",
            },
        )
        add(
            "intake_tail_reconciliation",
            "TAIL-09",
            "2027-11-10T11:00:00+00:00",
            {
                "extract_owner": "AS-P014",
                "channel_ids": list(CHANNELS),
                "window_start": "2027-09-30T13:00:00+00:00",
                "window_end": "2027-09-30T23:59:59+00:00",
                "additional_intake_items": [],
                "related_screening_id": "SCREEN-09",
                "related_screening_version": 2,
                "extract_state": "RETROSPECTIVE_RECONCILIATION",
                "historical_exception_id": "EXC-INTAKE-2027",
            },
        )
        add(
            "quarterly_legal_review",
            "QUARTER-3",
            "2027-11-12T10:00:00+00:00",
            {
                "reviewed_by": "AS-P003",
                "tail_record_versions": {"TAIL-07": 1, "TAIL-08": 1, "TAIL-09": 2},
                "observed_case_ids": [],
                "review_state": "DECLARED_WINDOW_RECONCILED",
                "historical_exception_id": "EXC-INTAKE-2027",
                "scope_limit": "Registered channels only",
            },
        )
    add(
        "period_legal_disposition",
        "PERIOD-2027",
        "2027-12-31T18:00:00+00:00",
        {
            "reviewed_by": "AS-P003",
            "prior_selected_contract_basis": basis,
            "monthly_screening_ids": [f"SCREEN-{m:02d}" for m in range(1, 13)],
            "registered_channel_ids": list(CHANNELS),
            "official_notice_ids": [],
            "penalty_determination_ids": [],
            "hearing_case_ids": [],
            "statement": (
                "No qualifying trigger was identified in the declared channels "
                "through this review cutoff"
            ),
            "review_cutoff": "2027-12-31T18:00:00+00:00",
            "later_period_tail": "NOT_REVIEWED",
            "unregistered_channels": "NOT_ESTABLISHED",
            "legal_reference_recheck_required_on_trigger": True,
            "open_exception_ids": [] if scenario == "CLEAN" else ["EXC-INTAKE-2027"],
        },
    )
    add(
        "independent_intake_review",
        "INDEPENDENT-2027",
        "2027-12-31T19:00:00+00:00",
        {
            "reviewed_by": "AS-P009",
            "operating_owner": "AS-P014",
            "legal_classifier": "AS-P003",
            "declared_channel_count": 4,
            "monthly_ledger_count": 48,
            "screening_record_count": 12,
            "contractual_inquiry_count": 2,
            "source_record_ids": ["REGISTRY-2027", "PERIOD-2027"],
            "review_boundary": (
                "Declared channels and retained extracts; "
                "unregistered channels and later tail excluded"
            ),
            "historical_exception_ids": [] if scenario == "CLEAN" else ["EXC-INTAKE-2027"],
            "external_auditor_acceptance": "NOT_REQUESTED",
        },
    )
    tail_versions = {
        f"TAIL-{m:02d}": 2 if scenario == "MESSY" and m == 9 else 1 for m in range(1, 13)
    }
    add(
        "period_legal_disposition",
        "PERIOD-2027",
        "2028-01-02T14:00:00+00:00",
        {
            "reviewed_by": "AS-P003",
            "prior_selected_contract_basis": basis,
            "tail_record_versions": tail_versions,
            "registered_channel_ids": list(CHANNELS),
            "reviewed_period_end": SCOPE["period_end"],
            "official_notice_ids": [],
            "penalty_determination_ids": [],
            "hearing_case_ids": [],
            "statement": (
                "No qualifying trigger was identified in the declared completed channel windows"
            ),
            "unregistered_channels": "NOT_ESTABLISHED",
            "legal_reference_recheck_required_on_trigger": True,
            "open_exception_ids": [] if scenario == "CLEAN" else ["EXC-INTAKE-2027"],
        },
    )
    add(
        "independent_intake_review",
        "INDEPENDENT-2027",
        "2028-01-03T10:00:00+00:00",
        {
            "reviewed_by": "AS-P009",
            "operating_owner": "AS-P014",
            "legal_classifier": "AS-P003",
            "declared_channel_count": 4,
            "monthly_ledger_count": 48,
            "tail_record_versions": tail_versions,
            "period_disposition_version": 2,
            "reviewed_period_end": SCOPE["period_end"],
            "review_boundary": (
                "Declared channels and completed monthly windows; unregistered channels excluded"
            ),
            "historical_exception_ids": [] if scenario == "CLEAN" else ["EXC-INTAKE-2027"],
            "external_auditor_acceptance": "NOT_REQUESTED",
        },
    )
    return rows


def _write(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _provenance():
    return {
        "source_reference": SOURCE,
        "truth_class": "AUTHORED_FICTIONAL_COMPANY_OPERATION",
        "reference_research_as_of": "2026-10-01",
    }


def _trigger_schema(db):
    expected = {}
    for table, label in (("versions", "source"), ("collections", "collection")):
        for action in ("UPDATE", "DELETE"):
            name = f"no_{'version' if table == 'versions' else 'collection'}_{action.lower()}"
            expected[name] = "".join(
                (
                    f"CREATE TRIGGER {name} BEFORE {action} ON {table} "
                    f"BEGIN SELECT RAISE(ABORT,'Immutable {label}'); END"
                ).split()
            ).lower()
    actual = {
        r[0]: "".join(r[1].split()).lower()
        for r in db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'")
    }
    if actual != expected:
        raise CompanyStoreError("Immutable legal-intake trigger schema differs")


def create(destination, *, repository, private_repository):
    destination = Path(destination).absolute()
    if destination.exists() or destination != destination.resolve():
        raise CompanyStoreError("Fresh private legal-intake destination required")
    docket._private(destination.parent, directory=True)
    context = _context(repository, private_repository)
    with tempfile.TemporaryDirectory(prefix=".legal-intake-", dir=destination.parent) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in BRANCHES.items():
            for system, owner in OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            records[scenario] = []
            versions = {}
            for system, record, at, body in _steps(scenario, context["refs"][scenario]):
                version = versions.get((system, record), 0)
                records[scenario].append(
                    store.append_version(
                        COMPANY,
                        branch,
                        system,
                        record,
                        expected_version=version,
                        command_id=f"LEGINT-{branch}-{system}-{record}-{version + 1}",
                        event_at=at,
                        available_at=at,
                        content=encoded(body),
                        provenance=_provenance(),
                    )
                )
                versions[(system, record)] = version + 1
        receipt = {
            "schema": SCHEMA,
            "status": "COMPANY_NATIVE_SELECTED_INTAKE_SOURCE_ONLY",
            "company": COMPANY,
            "branches": BRANCHES,
            "records": records,
            "source_pins": context["pins"],
            "target_task_ids_per_side": context["task_ids"],
            "nonoccurrence_acceptance": False,
            "source_complete": False,
            "audit_task_credit": False,
            "real_hipaa_applicability": "UNDETERMINED",
            "actual_phi": False,
            "outside_message_sent": False,
            "fresh_audit_pair_created": False,
        }
        _write(stage / "RECEIPT.json", receipt)
        _write(
            stage / "MANIFEST.json",
            {
                "schema": SCHEMA + "_MANIFEST",
                "receipt_sha256": _sha(stage / "RECEIPT.json"),
                "company_db_sha256": _sha(stage / "company.sqlite3"),
                "module_sha256": _sha(Path(__file__)),
                "native_version_count": sum(map(len, records.values())),
                "audit_task_credit": False,
            },
        )
        verify(stage, repository=repository, private_repository=private_repository)
        if any(docket._private(p) != old for p, old in context["states"].items()):
            raise CompanyStoreError("Legal-docket basis changed during intake operations")
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private_repository)


def verify(destination, *, repository, private_repository):
    root = Path(destination).absolute()
    docket._private(root, directory=True)
    if {p.name for p in root.iterdir()} != {"MANIFEST.json", "RECEIPT.json", "company.sqlite3"}:
        raise CompanyStoreError("Exact private legal-intake source required")
    before = {p: docket._private(p) for p in root.iterdir()}
    context = _context(repository, private_repository)
    receipt = json.loads((root / "RECEIPT.json").read_text())
    manifest = json.loads((root / "MANIFEST.json").read_text())
    if manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "receipt_sha256": _sha(root / "RECEIPT.json"),
        "company_db_sha256": _sha(root / "company.sqlite3"),
        "module_sha256": _sha(Path(__file__)),
        "native_version_count": sum(len(_steps(s, context["refs"][s])) for s in BRANCHES),
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("Legal-intake manifest differs")
    if (
        receipt.get("schema") != SCHEMA
        or receipt.get("status") != "COMPANY_NATIVE_SELECTED_INTAKE_SOURCE_ONLY"
        or receipt.get("company") != COMPANY
        or receipt.get("real_hipaa_applicability") != "UNDETERMINED"
        or receipt.get("branches") != BRANCHES
        or receipt.get("source_pins") != context["pins"]
        or receipt.get("target_task_ids_per_side") != context["task_ids"]
        or any(
            receipt.get(k) is not False
            for k in (
                "nonoccurrence_acceptance",
                "source_complete",
                "audit_task_credit",
                "actual_phi",
                "outside_message_sent",
                "fresh_audit_pair_created",
            )
        )
    ):
        raise CompanyStoreError("Legal-intake receipt boundary differs")
    with sqlite3.connect(f"file:{root / 'company.sqlite3'}?mode=ro&immutable=1", uri=True) as db:
        db.row_factory = sqlite3.Row
        _trigger_schema(db)
        expected_systems = {
            (COMPANY, b, s, owner) for b in BRANCHES.values() for s, owner in OWNERS.items()
        }
        if {
            tuple(r) for r in db.execute("SELECT company,branch,system,owner FROM systems")
        } != expected_systems:
            raise CompanyStoreError("Legal-intake system identity differs")
        for table in ("grants", "access_events", "collections"):
            if db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]:
                raise CompanyStoreError("Company source contains audit access journals")
        count = 0
        for scenario, branch in BRANCHES.items():
            versions, refs = {}, []
            for system, record, at, body in _steps(scenario, context["refs"][scenario]):
                version = versions.get((system, record), 0) + 1
                versions[(system, record)] = version
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    (COMPANY, branch, system, record, version),
                ).fetchone()
                if (
                    row is None
                    or row["content"] != encoded(body)
                    or row["sha256"] != hashlib.sha256(row["content"]).hexdigest()
                    or row["event_at"] != _time(at)
                    or row["available_at"] != _time(at)
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or json.loads(row["provenance"]) != _provenance()
                    or row["command_id"] != f"LEGINT-{branch}-{system}-{record}-{version}"
                    or _time(row["imported_at"]) != row["imported_at"]
                ):
                    raise CompanyStoreError("Exact native legal-intake record differs")
                refs.append(CompanyStore._metadata(row))
                count += 1
            if receipt["records"].get(scenario) != refs:
                raise CompanyStoreError("Legal-intake native receipt join differs")
        if db.execute("SELECT count(*) FROM versions").fetchone()[0] != count:
            raise CompanyStoreError("Legal-intake native population differs")
    if any(docket._private(p) != old for p, old in before.items()):
        raise CompanyStoreError("Legal-intake verification mutated source")
    if _p1_inventory(context["private"]) != overlay.P1_FREEZE:
        raise CompanyStoreError("Frozen P1 changed during legal-intake verification")
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args(argv)
    result = (create if args.action == "create" else verify)(
        args.destination, repository=args.repository, private_repository=args.private_repository
    )
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "counts": {s: len(r) for s, r in result["records"].items()},
                "audit_task_credit": False,
                "nonoccurrence_acceptance": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
