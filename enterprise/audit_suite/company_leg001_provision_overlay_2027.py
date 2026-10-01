"""Selected fictional 2027 counsel status hold over reviewed LEG001 originals."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from . import company_leg001_operating_docket_2027 as docket
from .company_store import CompanyStore, CompanyStoreError, _time
from .documentary_283_route_reconciliation_v6 import _p1_inventory
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_LEG001_PROVISION_OVERLAY_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
SOURCE = "enterprise/audit_suite/company_leg001_provision_overlay_2027.py"
SPEC = "enterprise/audit_suite/leg001_provision_overlay_spec_v1.json"
SPEC_SHA256 = "84e575a931ebe29e2146378af3998bd85c039709570f302517cada9fdfed64da"
APPOINTMENTS = docket.APPOINTMENTS
APPOINTMENTS_SHA256 = docket.APPOINTMENTS_SHA256
PREDECESSOR_RUN = (
    "enterprise/generated/audit-suite/company-leg001-operating-docket-2027-09-30/main-run-v1"
)
PREDECESSOR_REVIEW = (
    "enterprise/generated/audit-suite/"
    "company-leg001-operating-docket-2027-09-30/independent-review-main-v1/REVIEW.json"
)
PRIVATE_PINS = {
    PREDECESSOR_REVIEW: "3bd03221aaa69b11ba5a484c402ee12e17b67290b3732f5aab97dd3b54632cc6",
    f"{PREDECESSOR_RUN}/MANIFEST.json": "5d939d13644c2610198d8c15c75a8879a553d35b2e17f9f7730a8435f3127731",  # noqa: E501
    f"{PREDECESSOR_RUN}/RECEIPT.json": "1f445ea96df4f5cbb9505a575be25e779470368b44747bcd46ee0889f3fb7584",  # noqa: E501
    f"{PREDECESSOR_RUN}/company.sqlite3": "89045558b86513fefa5791bf5ad4749279962758d05099139ae576f0025a7cd2",  # noqa: E501
}
P1_FREEZE = {
    "file_count": 538,
    "inventory_sha256": "f266ef682b502b3b093170f8a7b64fcf5cbab722d5c8ddf6715a63c0e535360f",
}
SYSTEMS = ("obligation_snapshot", "provision_locator", "overlay_reconciliation")
PROVISION_IDS = (
    "160.101",
    "160.104",
    "160.105",
    "160.201",
    "160.202",
    "160.203",
    "160.204",
    "160.205",
    "164.102",
    "164.103",
    "164.106",
    "164.318",
    "164.532",
    "164.534",
    "164.535",
    "164.502",
    "164.509",
    "164.520",
)
REVIEW_INPUTS = {
    "AUTHORITY_CONTEXT": ["current primary text", "affected entity and function facts"],
    "EFFECTIVE_DATE_DEPENDENCY": [
        "specific final rule and effective/compliance dates",
        "transition exception facts",
    ],
    "STATE_PREEMPTION_DEPENDENCY": [
        "identified state and federal provisions",
        "documented conflict and exception decision",
    ],
    "FUNCTION_SCOPE_DEPENDENCY": [
        "actual transaction and service functions",
        "entity and organizational designation facts",
    ],
    "LEGAL_STATUS_DEPENDENCY": [
        "operative judgment or order",
        "affected regulatory text and date",
    ],
    "ACTION_LEGAL_STATUS_DEPENDENCY": [
        "affected section and subparagraph",
        "current primary authority and legal status",
    ],
    "PUBLICATION_VACATUR_REVIEW_HOLD": [
        "operative court order and scope",
        "HHS implementation status and current codification",
    ],
}
OPEN_EXCEPTIONS = docket.OPEN_EXCEPTIONS
REF_FIELDS = docket.REFERENCE_FIELDS
LIMITS = [
    "One synthetic customer-to-SHI-to-support chain; exact 34 predecessor term decisions and "
    "18 provision locators, covering only the 16 authored provision-status candidates.",
    "The predecessor's 2026-09-29 reference check and this overlay's 2026-10-01 "
    "URL research are not captured 2027 law. Every locator remains open for counsel review.",
    "The eCFR display of 164.509 and HHS's 2025 partial-vacatur notice are a status hold, "
    "not a conclusion that any specific paragraph is enforceable in 2027.",
    "Clean/Messy share a synthetic scenario theme but never cite the other branch's originals. "
    "Messy retains two distinct open historical exceptions; backfill does not cure them.",
    "No outside matter, all-company nonoccurrence, real HIPAA applicability, executed contract, "
    "legal opinion, task transition, audit credit, fresh pair or Atlas write.",
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ref(receipt: dict, scenario: str, system: str, record: str) -> dict:
    rows = [
        row
        for row in receipt["records"][scenario]
        if row["system"] == system and row["record"] == record
    ]
    if len(rows) != 1:
        raise CompanyStoreError("Exact predecessor LEG001 native locator missing")
    return rows[0]


def _context(repository: Path, private_repository: Path) -> dict:
    repo = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise CompanyStoreError("Frozen P1 inventory differs")
    for name, expected in ((SPEC, SPEC_SHA256), (APPOINTMENTS, APPOINTMENTS_SHA256)):
        path = repo / name
        if path.is_symlink() or _sha(path) != expected:
            raise CompanyStoreError("Tracked LEG001 overlay spec/authority differs")
    spec = docket._json(repo / SPEC)
    if (
        spec.get("schema") != SCHEMA.replace("OVERLAY_V1", "OVERLAY_SPEC_V1")
        or spec.get("truth_class") != "TRAINING_SCENARIO_ONLY"
        or spec.get("company") != COMPANY
        or spec.get("branches") != {"CLEAN": "LEGOV-CLEAN", "MESSY": "LEGOV-MESSY"}
        or spec.get("counsel_person_id") != "AS-P003"
        or spec.get("predecessor_legal_reference_checked_as_of") != "2026-09-29"
        or spec.get("source_research_accessed") != "2026-10-01"
        or spec.get("simulated_event_day") != "2027-12-31"
        or tuple(row["id"].removeprefix("45-CFR-") for row in spec.get("provisions", []))
        != PROVISION_IDS
        or len({row["id"] for row in spec["provisions"]}) != 18
        or any(row["category"] not in REVIEW_INPUTS for row in spec["provisions"])
        or spec["provisions"][16]["category"] != "PUBLICATION_VACATUR_REVIEW_HOLD"
        or spec.get("real_hipaa_applicability") != "UNDETERMINED"
        or any(
            spec.get(key) is not False
            for key in (
                "2027_legal_text_verified",
                "actual_phi",
                "real_contract_executed",
                "outside_message_sent",
                "audit_task_credit",
                "source_complete",
            )
        )
    ):
        raise CompanyStoreError("LEG001 overlay truth/spec boundary differs")
    if "| AS-P003 | Helena Ward | General Counsel |" not in (repo / APPOINTMENTS).read_text():
        raise CompanyStoreError("Counsel appointment projection differs")
    states = {}
    for name, expected in PRIVATE_PINS.items():
        path = private / name
        state = docket._private(path)
        if state[-1] != expected:
            raise CompanyStoreError("Reviewed LEG001 predecessor bytes differ")
        states[path] = state
    review = docket._json(private / PREDECESSOR_REVIEW)
    if (
        review.get("schema")
        != "SH_FICTIONAL_2027_LEG001_SELECTED_OPERATING_DOCKET_MAIN_INDEPENDENT_REVIEW_V1"
        or review.get("verdict") != "PASS_PRIVATE_FICTIONAL_SOURCE_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or review.get("main_run_sha256")
        != {
            "MANIFEST.json": PRIVATE_PINS[f"{PREDECESSOR_RUN}/MANIFEST.json"],
            "RECEIPT.json": PRIVATE_PINS[f"{PREDECESSOR_RUN}/RECEIPT.json"],
            "company.sqlite3": PRIVATE_PINS[f"{PREDECESSOR_RUN}/company.sqlite3"],
        }
        or review.get("p1_freeze") != freeze
        or review.get("audit_task_credit") is not False
        or review.get("real_hipaa_applicability") != "UNDETERMINED"
        or review.get("outside_message_sent") is not False
    ):
        raise CompanyStoreError("LEG001 predecessor independent review differs")
    predecessor = docket.verify(
        private / PREDECESSOR_RUN, repository=repo, private_repository=private
    )
    if (
        predecessor.get("schema") != docket.SCHEMA
        or predecessor.get("selected_chain") != spec["selected_chain"]
        or predecessor.get("unsupported_authored_routes_per_side") != 66
        or predecessor.get("selected_term_occurrences_per_branch") != 34
        or predecessor.get("selected_scope_complete") != {"CLEAN": True, "MESSY": False}
        or predecessor.get("audit_task_credit") is not False
    ):
        raise CompanyStoreError("Selected predecessor chain or denominator differs")
    refs = {}
    for scenario in ("CLEAN", "MESSY"):
        branch = {"CLEAN": "LEG-CLEAN", "MESSY": "LEG-MESSY"}[scenario]
        rows = predecessor["records"][scenario]
        if len(rows) != 50 or any(row["branch"] != branch for row in rows):
            raise CompanyStoreError("Predecessor branch isolation differs")
        scope = _ref(predecessor, scenario, "scope_decision", "LEG001-SCOPE-01")
        reconciliation = _ref(predecessor, scenario, "reconciliation", "LEG001-SELECTED-RECON")
        term_refs = [row for row in rows if row["system"] == "term_status"]
        if len(term_refs) != 34:
            raise CompanyStoreError("Predecessor selected term refs differ")
        _, scope_body = docket._native(
            private / PREDECESSOR_RUN / "company.sqlite3", predecessor, scenario, scope
        )
        _, recon_body = docket._native(
            private / PREDECESSOR_RUN / "company.sqlite3",
            predecessor,
            scenario,
            reconciliation,
        )
        open_ids = [] if scenario == "CLEAN" else OPEN_EXCEPTIONS
        if (
            scope_body["detail"]["open_historical_exception_ids"] != open_ids
            or recon_body["detail"]["open_historical_exception_ids"] != open_ids
            or recon_body["detail"]["term_owner_decisions"] != 34
            or recon_body["detail"]["authored_task_status"] != "NOT_STARTED"
            or recon_body["detail"]["authored_task_conclusion"] != "NOT_RUN"
        ):
            raise CompanyStoreError("Predecessor selected scope/open history differs")
        refs[scenario] = {
            "scope": scope,
            "reconciliation": reconciliation,
            "terms": term_refs,
            "exception_refs": predecessor["source_exception_refs"][scenario],
            "open_exception_ids": open_ids,
        }
    if any(docket._private(path) != state for path, state in states.items()):
        raise CompanyStoreError("Reviewed LEG001 predecessor changed during context read")
    if _p1_inventory(private) != freeze:
        raise CompanyStoreError("P1 changed during LEG001 overlay read")
    return {
        "spec": spec,
        "pins": {"repo://" + SPEC: SPEC_SHA256, "repo://" + APPOINTMENTS: APPOINTMENTS_SHA256}
        | {"private://" + name: digest for name, digest in PRIVATE_PINS.items()},
        "refs": refs,
        "states": states,
        "freeze": freeze,
    }


def _steps(context: dict, scenario: str) -> list[tuple[str, str, str, str, dict]]:
    spec = context["spec"]
    refs = context["refs"][scenario]
    base = {
        "schema": SCHEMA,
        "scenario": scenario,
        "truth_class": "TRAINING_SCENARIO_ONLY",
        "counsel_person_id": "AS-P003",
        "real_hipaa_applicability": "UNDETERMINED",
        "2027_legal_text_verified": False,
        "actual_phi": False,
        "real_contract_executed": False,
        "outside_message_sent": False,
        "audit_task_credit": False,
        "source_complete": False,
    }
    steps = []

    def add(system: str, record: str, event: str, available: str, detail: dict) -> None:
        steps.append(
            (
                system,
                record,
                event,
                available,
                base
                | {
                    "system": system,
                    "record": record,
                    "event_at": _time(event),
                    "available_at": _time(available),
                    "detail": detail,
                },
            )
        )

    day = spec["simulated_event_day"]
    add(
        "obligation_snapshot",
        "CHAIN-TERMS-01",
        day + "T17:05:00+00:00",
        day + "T17:06:00+00:00",
        {
            "chain": spec["selected_chain"],
            "predecessor_scope_ref": refs["scope"],
            "predecessor_reconciliation_ref": refs["reconciliation"],
            "selected_term_refs": refs["terms"],
            "selected_term_count": 34,
            "contract_term_status": "SELECTED_FICTIONAL_TERMS_INDEXED_NOT_REAL_EXECUTION",
            "performance_fact_status": "NOT_ESTABLISHED_BY_TERM_INDEX",
            "open_historical_exception_ids": refs["open_exception_ids"],
            "exception_refs": refs["exception_refs"],
            "backfill_not_retroactive_cure": scenario == "MESSY",
            "all_contracts_or_operations_reconciled": False,
        },
    )
    for index, provision in enumerate(spec["provisions"], 1):
        add(
            "provision_locator",
            f"PROVISION-{index:02d}",
            day + "T17:10:00+00:00",
            day + "T17:11:00+00:00",
            {
                "provision": provision,
                "predecessor_legal_reference_checked_as_of": spec[
                    "predecessor_legal_reference_checked_as_of"
                ],
                "source_research_accessed": spec["source_research_accessed"],
                "hhs_vacatur_status_url": (
                    spec["hhs_vacatur_status_url"]
                    if provision["id"] in ("45-CFR-164.502", "45-CFR-164.509", "45-CFR-164.520")
                    else None
                ),
                "locator_status": "2026_REFERENCE_ONLY",
                "applicability_status": "UNDETERMINED_FOR_REAL_AND_FICTIONAL_2027",
                "trigger_status": "NOT_ESTABLISHED_OUTSIDE_SELECTED_CHAIN",
                "nonoccurrence_status": "NOT_ESTABLISHED_ALL_COMPANY_OR_OUTSIDE",
                "counsel_authority": "AS-P003_INTAKE_CUSTODY_ONLY",
                "qualified_review_status": "OPEN_2027_PRIMARY_AND_FACT_RECHECK",
                "contract_term_status": "SEPARATE_SELECTED_34_TERMS_ONLY",
                "performance_fact_status": "NOT_ESTABLISHED_BY_LOCATOR",
                "publication_status_hold": provision["id"] == "45-CFR-164.509",
                "required_qualified_review_inputs": REVIEW_INPUTS[provision["category"]],
                "2026_snapshot_note": (
                    "eCFR display and HHS partial-vacatur notice require reconciliation"
                    if provision["id"] == "45-CFR-164.509"
                    else "reference locator only; no 2027 legal-status conclusion"
                ),
                "predecessor_scope_ref": refs["scope"],
                "open_historical_exception_ids": refs["open_exception_ids"],
                "not_applicable_conclusion": False,
            },
        )
    add(
        "overlay_reconciliation",
        "LEG001-PROVISION-OVERLAY-01",
        day + "T18:00:00+00:00",
        day + "T18:01:00+00:00",
        {
            "predecessor_reconciliation_ref": refs["reconciliation"],
            "selected_term_count": 34,
            "provision_locator_count": 18,
            "authored_provision_candidate_count": 16,
            "unresolved_qualified_review_count": 18,
            "open_historical_exception_ids": refs["open_exception_ids"],
            "2027_primary_text_rechecked": False,
            "all_company_matter_nonoccurrence_established": False,
            "outside_matter_response_claimed": False,
            "authored_task_status": "NOT_STARTED",
            "authored_task_conclusion": "NOT_RUN",
            "authored_clause_satisfied": False,
        },
    )
    if len(steps) != 20 or len({(system, record) for system, record, *_ in steps}) != 20:
        raise CompanyStoreError("LEG001 overlay selected record denominator differs")
    return steps


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink() or destination != destination.resolve():
        raise CompanyStoreError("Fresh private LEG001 overlay destination required")
    docket._private(destination.parent, directory=True)
    context = _context(repository, private_repository)
    with tempfile.TemporaryDirectory(
        prefix=".leg001-overlay-stage-", dir=destination.parent
    ) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in context["spec"]["branches"].items():
            for system in SYSTEMS:
                store.register_system(COMPANY, branch, system, "AS-P003")
            records[scenario] = []
            for system, record, event, available, body in _steps(context, scenario):
                records[scenario].append(
                    store.append_version(
                        COMPANY,
                        branch,
                        system,
                        record,
                        expected_version=0,
                        command_id=f"LEGOV-{branch}-{system}-{record}",
                        event_at=event,
                        available_at=available,
                        content=encoded(body),
                        provenance={
                            "source_reference": SOURCE,
                            "scenario": scenario,
                            "source_pins": context["pins"],
                            "qualification": "FUTURE_TRAINING_LOCATORS_OPEN_NO_LEGAL_OPINION",
                        },
                    )
                )
        receipt = {
            "schema": SCHEMA,
            "status": "FUTURE_FICTIONAL_LEG001_PROVISION_OVERLAY_OPEN_NO_AUDIT_CREDIT",
            "company": COMPANY,
            "branches": context["spec"]["branches"],
            "source_pins": context["pins"],
            "selected_chain": context["spec"]["selected_chain"],
            "predecessor_selected_refs": context["refs"],
            "selected_term_count_per_branch": 34,
            "provision_locator_count_per_branch": 18,
            "bounded_authored_provision_candidates_per_side": 16,
            "remaining_unmodeled_authored_candidates_per_side": 50,
            "open_historical_exception_ids": {
                scenario: context["refs"][scenario]["open_exception_ids"]
                for scenario in ("CLEAN", "MESSY")
            },
            "real_hipaa_applicability": "UNDETERMINED",
            "2027_legal_text_verified": False,
            "actual_phi": False,
            "real_contract_executed": False,
            "outside_message_sent": False,
            "source_complete": False,
            "audit_task_credit": False,
            "records": records,
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
                "spec_sha256": _sha(Path(repository) / SPEC),
                "native_version_count": 40,
                "audit_task_credit": False,
            },
        )
        if any(docket._private(path) != state for path, state in context["states"].items()):
            raise CompanyStoreError("LEG001 predecessor changed during overlay build")
        if _p1_inventory(private_repository) != context["freeze"]:
            raise CompanyStoreError("P1 changed during LEG001 overlay build")
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private_repository)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    root = Path(destination).absolute()
    docket._private(root, directory=True)
    if {path.name for path in root.iterdir()} != {
        "RECEIPT.json",
        "MANIFEST.json",
        "company.sqlite3",
    }:
        raise CompanyStoreError("Exact private LEG001 overlay three-file source required")
    paths = {name: root / name for name in ("RECEIPT.json", "MANIFEST.json", "company.sqlite3")}
    before = {name: docket._private(path) for name, path in paths.items()}
    docket._no_sidecars(paths["company.sqlite3"])
    context = _context(repository, private_repository)
    receipt = docket._json(paths["RECEIPT.json"])
    manifest = docket._json(paths["MANIFEST.json"])
    if manifest != {
        "schema": SCHEMA + "_MANIFEST",
        "receipt_sha256": before["RECEIPT.json"][-1],
        "company_db_sha256": before["company.sqlite3"][-1],
        "module_sha256": _sha(Path(__file__)),
        "spec_sha256": _sha(Path(repository) / SPEC),
        "native_version_count": 40,
        "audit_task_credit": False,
    }:
        raise CompanyStoreError("LEG001 overlay native manifest differs")
    expected = {
        "schema": SCHEMA,
        "status": "FUTURE_FICTIONAL_LEG001_PROVISION_OVERLAY_OPEN_NO_AUDIT_CREDIT",
        "company": COMPANY,
        "branches": context["spec"]["branches"],
        "source_pins": context["pins"],
        "selected_chain": context["spec"]["selected_chain"],
        "predecessor_selected_refs": context["refs"],
        "selected_term_count_per_branch": 34,
        "provision_locator_count_per_branch": 18,
        "bounded_authored_provision_candidates_per_side": 16,
        "remaining_unmodeled_authored_candidates_per_side": 50,
        "open_historical_exception_ids": {
            scenario: context["refs"][scenario]["open_exception_ids"]
            for scenario in ("CLEAN", "MESSY")
        },
        "real_hipaa_applicability": "UNDETERMINED",
        "2027_legal_text_verified": False,
        "actual_phi": False,
        "real_contract_executed": False,
        "outside_message_sent": False,
        "source_complete": False,
        "audit_task_credit": False,
        "records": receipt.get("records"),
        "limits": LIMITS,
    }
    if receipt != expected or set(receipt.get("records", {})) != {"CLEAN", "MESSY"}:
        raise CompanyStoreError("LEG001 overlay receipt/scope differs")
    with closing(
        sqlite3.connect(paths["company.sqlite3"].as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("LEG001 overlay SQLite integrity differs")
        counts = {
            table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("systems", "versions", "grants", "collections", "access_events")
        }
        if counts != {
            "systems": 6,
            "versions": 40,
            "grants": 0,
            "collections": 0,
            "access_events": 0,
        }:
            raise CompanyStoreError("LEG001 overlay native population/access differs")
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        if systems != {
            (COMPANY, branch, system, "AS-P003")
            for branch in context["spec"]["branches"].values()
            for system in SYSTEMS
        }:
            raise CompanyStoreError("LEG001 overlay branch/authority custody differs")
        seen = set()
        for scenario, branch in context["spec"]["branches"].items():
            steps, refs = _steps(context, scenario), receipt["records"][scenario]
            if len(refs) != 20:
                raise CompanyStoreError("LEG001 overlay branch native denominator differs")
            for (system, record, event, available, body), ref in zip(steps, refs, strict=True):
                route = (COMPANY, branch, system, record, 1)
                if (
                    tuple(ref[key] for key in ("company", "branch", "system", "record", "version"))
                    != route
                ):
                    raise CompanyStoreError("LEG001 overlay native identity differs")
                rows = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    route,
                ).fetchall()
                if len(rows) != 1:
                    raise CompanyStoreError("LEG001 overlay native version missing/duplicated")
                row = rows[0]
                native = {
                    key: json.loads(row[key]) if key == "provenance" else row[key]
                    for key in REF_FIELDS
                }
                if (
                    native != ref
                    or sha(row["content"]) != ref["sha256"]
                    or json.loads(row["content"]) != body
                    or ref["event_at"] != _time(event)
                    or ref["available_at"] != _time(available)
                    or ref["imported_at"] >= _time("2027-01-01T00:00:00+00:00")
                    or ref["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or ref["provenance"]
                    != {
                        "source_reference": SOURCE,
                        "scenario": scenario,
                        "source_pins": context["pins"],
                        "qualification": "FUTURE_TRAINING_LOCATORS_OPEN_NO_LEGAL_OPINION",
                    }
                ):
                    raise CompanyStoreError(
                        "LEG001 overlay native content/clocks/provenance differ"
                    )
                seen.add(route)
        if len(seen) != 40:
            raise CompanyStoreError("LEG001 overlay exact native route count differs")
    docket._no_sidecars(paths["company.sqlite3"])
    if {name: docket._private(path) for name, path in paths.items()} != before:
        raise CompanyStoreError("LEG001 overlay changed during read-only verification")
    if any(docket._private(path) != state for path, state in context["states"].items()):
        raise CompanyStoreError("LEG001 predecessor changed during verification")
    if _p1_inventory(private_repository) != context["freeze"]:
        raise CompanyStoreError("P1 changed during LEG001 overlay verification")
    return receipt
