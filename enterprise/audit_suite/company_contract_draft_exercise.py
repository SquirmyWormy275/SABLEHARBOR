"""Prospective company-owned provider/BA contract draft gate; never an agreement."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _id, _time
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish

SCHEMA = "SH_PROSPECTIVE_CONTRACT_DRAFT_GATE_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
QUALIFICATION = "LOCAL_PROSPECTIVE_DRAFT_DECISION_NO_CONTRACT_OR_PHI_OPERATION"
EXCEPTION_ID = "EXC-CONTRACT-01-PREMATURE-CLEARANCE"
CONTROLS = ("SH-LEG-001", "SH-LEG-002", "SH-TPR-003", "SH-TPR-005")
SOURCES = (
    "enterprise/services/source/runtime_sites_2026-09-11.json",
    "docs/canon/RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md",
    "docs/canon/THIRD_PARTY_SERVICES_SOURCING_DECISIONS_2026-09-09.md",
    "docs/internal/development/CCF_ASSURANCE_SCOPE_PROPOSAL_2026-09-11.md",
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
    "enterprise/ccf/assurance/design_data/control_procedures.json",
    "enterprise/ccf/assurance/design_data/hipaa_analysis.json",
)
PROVIDERS = {
    "CP-SWITCH": ("RUNTIME-RENO-COLO", "RT-SO-RENO", "DEP-colo-primary", "PRIMARY"),
    "CP-IDACORE": ("RUNTIME-BOISE-DR", "RT-SO-BOISE", "DEP-colo-recovery", "RECOVERY"),
}
CLAUSE_CANDIDATES = (
    "service_scope_and_responsibilities",
    "security_and_physical_access",
    "privacy_data_rights_and_permitted_uses",
    "incident_reporting_and_notice_routing",
    "assurance_evidence_and_exception_access",
    "continuity_and_independent_recovery",
    "subcontractor_flowdown_if_applicable",
    "termination_exit_data_return_or_destruction",
)
REQUIRED_FACTS = (
    "counterparty_legal_entity_and_negotiated_text",
    "actual_service_and_data_access_boundary",
    "actual_phi_and_business_associate_role_determination",
    "upstream_customer_agreement_and_delegated_duties",
    "downstream_subcontractor_population_and_written_arrangements_if_applicable",
    "legal_security_privacy_finance_and_insurance_reviews",
    "delegated_signature_authority_and_executed_terms",
)
EVENTS = {
    "CLEAN": (
        (
            "DRAFT_CLAUSE_MATRIX",
            "NEW",
            "DRAFT",
            "2027-05-01T09:00:00+00:00",
            0,
            ("CP-SWITCH", "CP-IDACORE"),
        ),
        (
            "CONDITIONAL_OBLIGATION_SCREEN",
            "DRAFT",
            "DRAFT",
            "2027-05-01T10:00:00+00:00",
            0,
            ("CP-SWITCH", "CP-IDACORE"),
        ),
        (
            "INTERNAL_REVIEW_ROUTE",
            "DRAFT",
            "HOLD",
            "2027-05-01T11:00:00+00:00",
            0,
            ("CP-SWITCH", "CP-IDACORE"),
        ),
        (
            "UNRESOLVED_FACTS_RECONCILE",
            "HOLD",
            "HOLD",
            "2027-05-01T12:00:00+00:00",
            0,
            ("CP-SWITCH", "CP-IDACORE"),
        ),
    ),
    "MESSY": (
        (
            "DRAFT_CLAUSE_MATRIX",
            "NEW",
            "DRAFT_INCOMPLETE",
            "2027-05-01T09:00:00+00:00",
            0,
            ("CP-SWITCH",),
        ),
        (
            "PREMATURE_LOCAL_CLEARANCE_MARKER",
            "DRAFT_INCOMPLETE",
            "MISLABELED_LOCAL_CLEARANCE",
            "2027-05-01T10:00:00+00:00",
            0,
            ("CP-SWITCH",),
        ),
        (
            "LATE_INTERNAL_REVIEW",
            "MISLABELED_LOCAL_CLEARANCE",
            "QUARANTINED",
            "2027-05-03T09:00:00+00:00",
            60,
            ("CP-SWITCH",),
        ),
        (
            "DRAFT_BACKFILL",
            "QUARANTINED",
            "QUARANTINED",
            "2027-05-03T11:00:00+00:00",
            0,
            ("CP-SWITCH", "CP-IDACORE"),
        ),
        (
            "PROPOSED_CURE_ROUTE",
            "QUARANTINED",
            "QUARANTINED",
            "2027-05-03T12:00:00+00:00",
            0,
            ("CP-SWITCH", "CP-IDACORE"),
        ),
        (
            "UNRESOLVED_EXCEPTION_RECONCILE",
            "QUARANTINED",
            "QUARANTINED",
            "2027-05-03T13:00:00+00:00",
            0,
            ("CP-SWITCH", "CP-IDACORE"),
        ),
    ),
}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private_new(destination: Path) -> Path:
    destination = destination.absolute()
    if (
        destination.exists()
        or destination.is_symlink()
        or destination != destination.resolve()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(p.is_symlink() for p in (destination, *destination.parents))
    ):
        raise CompanyStoreError("New private nonsymlink destination required")
    return destination


def _source_context(repository: Path) -> tuple[dict, list[dict], dict]:
    pins = {}
    for name in SOURCES:
        path = repository / name
        if not path.is_file() or path.is_symlink():
            raise CompanyStoreError("Required canon source unavailable")
        pins[name] = _digest(path)
    sites = json.loads((repository / SOURCES[0]).read_bytes())
    boundaries = []
    for provider_id, (site_id, contract_id, dependency_id, role) in PROVIDERS.items():
        selected = [s for s in sites["sites"] if s["id"] == site_id]
        if len(selected) != 1:
            raise CompanyStoreError("Exact planned provider boundary required")
        site = selected[0]
        if any(
            (
                site.get("provider_id") != provider_id,
                site.get("contract_id") != contract_id,
                site.get("dependency_id") != dependency_id,
                site.get("status") != "PROVIDER_SELECTED_PROCUREMENT_PENDING",
                site.get("contract_status") != "DRAFT",
                site.get("contract_executed") is not False,
                site.get("operating") is not False,
                site.get("provider_legal_name") is not None,
            )
        ):
            raise CompanyStoreError("Source contract/operation state changed")
        boundaries.append(
            {
                "provider_id": provider_id,
                "site_id": site_id,
                "contract_id": contract_id,
                "dependency_id": dependency_id,
                "planned_role": role,
                "site_name": site["name"],
                "provider_label": site["provider"],
                "entity_id": site["entity_id"],
                "facility_id": site["facility_id"],
                "planned_environment_ids": site["planned_environment_ids"],
                "source_pointer": SOURCES[0] + "#/sites/" + str(sites["sites"].index(site)),
                "source_sha256": pins[SOURCES[0]],
                "provider_legal_name": None,
                "contract_status": "DRAFT",
                "contract_executed": False,
                "capacity_reserved": False,
                "operating": False,
            }
        )
    if len({x["provider_id"] for x in boundaries}) != 2:
        raise CompanyStoreError("Duplicate planned provider")
    org = snapshot(repository)
    assignments = {a["control_id"]: a for a in org["control_assignments"]}
    expected = {
        "SH-LEG-001": ("AS-P003", "AS-P004"),
        "SH-LEG-002": ("AS-P003", "AS-P004"),
        "SH-TPR-003": ("AS-P003", "AS-P013"),
        "SH-TPR-005": ("AS-P013", "AS-P013"),
    }
    custody = {}
    for control, (primary, custodian) in expected.items():
        a = assignments[control]
        if (a["primary_person_id"], a["custodian_person_id"], a["status"]) != (
            primary,
            custodian,
            "PROPOSED_CURRENT_ASSIGNMENT",
        ):
            raise CompanyStoreError("Scoped proposed contact assignment changed")
        custody[control] = {
            "primary_person_id": primary,
            "custodian_person_id": custodian,
            "status": a["status"],
            "authority_limit": a["authority_limit"],
        }
    pins.update(org["source_sha256"])
    pins["enterprise/audit_suite/company_contract_draft_exercise.py"] = _digest(Path(__file__))
    return pins, boundaries, custody


def _definition(scenario: str, branch: str, boundaries: list[dict], custody: dict) -> dict:
    return {
        "schema": SCHEMA,
        "scenario": scenario,
        "branch": branch,
        "boundary_id": "corporate-shared-controls-reno-primary-boise-recovery",
        "reference_scope": (
            "SOC2_SECURITY_AVAILABILITY_CONFIDENTIALITY_TYPE2_READINESS_"
            "AND_HYPOTHETICAL_HIPAA_BA_SUBCONTRACTOR"
        ),
        "selected_planned_providers": boundaries,
        "control_ids": list(CONTROLS),
        "proposed_contacts": custody,
        "clause_candidate_ids": list(CLAUSE_CANDIDATES),
        "conditional_fact_gates": list(REQUIRED_FACTS),
        "authority_status": "PROPOSED_CONTACTS_NOT_SIGNATURE_OR_LEGAL_ACCEPTANCE",
        "actual_phi_status": "UNASSERTED",
        "actual_ba_status": "UNASSERTED",
        "upstream_customer_agreement_status": "UNASSERTED",
        "downstream_subcontractor_status": "UNDETERMINED_NO_ACTUAL_DATA_FLOW",
        "qualification": QUALIFICATION,
    }


def _event_body(scenario: str, ordinal: int, event: tuple) -> dict:
    action, before, after, at, lag_minutes, draft_providers = event
    missing = sorted(set(PROVIDERS) - set(draft_providers))
    open_exception = scenario == "MESSY" and ordinal >= 2
    return {
        "schema": SCHEMA,
        "scenario": scenario,
        "sequence": ordinal,
        "action": action,
        "before": before,
        "after": after,
        "event_at": _time(at),
        "available_at": _time(
            (datetime.fromisoformat(at) + timedelta(minutes=lag_minutes)).isoformat()
        ),
        "draft_provider_ids": list(draft_providers),
        "missing_provider_ids": missing,
        "clause_candidate_ids": list(CLAUSE_CANDIDATES),
        "candidate_clause_status": "INTERNAL_CHECKLIST_NO_NEGOTIATED_COUNTERPARTY_TEXT",
        "conditional_ba_flowdown": "CANDIDATE_ONLY_ROLE_AND_PHI_FACTS_UNDETERMINED",
        "internal_review_contact": "AS-P003",
        "procurement_contact": "AS-P013",
        "review_authority": "PROPOSED_CONTACTS_ONLY_NO_SIGNATURE_DELEGATION",
        "local_disposition": (
            "HOLD_PENDING_SOURCE_AND_AUTHORITY_FACTS"
            if scenario == "CLEAN"
            else "PREMATURE_MARKER_NOT_APPROVAL"
            if ordinal == 2
            else "QUARANTINE_AND_PROPOSE_CURE"
            if ordinal >= 3
            else "INCOMPLETE_DRAFT"
        ),
        "required_fact_gates": list(REQUIRED_FACTS),
        "cure_proposal": (
            "Invalidate premature marker, reconcile both provider clause candidates, "
            "obtain real source terms and qualified owner/counsel decisions; no cure asserted"
            if scenario == "MESSY" and ordinal >= 3
            else None
        ),
        "exception_id": EXCEPTION_ID if open_exception else None,
        "exception_open": open_exception,
        "legal_approval": False,
        "signature": False,
        "contract_execution": False,
        "external_communication": False,
        "actual_phi_processing": False,
        "ba_role_determined": False,
        "provider_operating": False,
        "actual_cure_completed": False,
        "actual_termination": False,
        "known_material_vendor_violation": "NOT_ASSERTED",
        "contractual_cure_right": "UNDETERMINED_NO_SIGNED_TERM",
        "qualification": QUALIFICATION,
    }


def _write(path: Path, value: dict) -> None:
    with open(path, "x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def create(destination: Path, *, repository: Path, clean_branch: str, messy_branch: str) -> dict:
    """Append isolated prospective company versions; no audit grant or collection."""
    repository = Path(repository).resolve()
    destination = _private_new(Path(destination))
    branches = {"CLEAN": _id(clean_branch), "MESSY": _id(messy_branch)}
    if branches["CLEAN"] == branches["MESSY"]:
        raise CompanyStoreError("Distinct branch identities required")
    pins, boundaries, custody = _source_context(repository)
    with tempfile.TemporaryDirectory(
        prefix=".contract-draft-stage-", dir=destination.parent
    ) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records = {"CLEAN": [], "MESSY": []}
        for scenario in ("CLEAN", "MESSY"):
            branch = branches[scenario]
            for system in ("contract_scope", "contract_event"):
                store.register_system(
                    COMPANY, branch, system, "AS-P004" if system == "contract_scope" else "AS-P003"
                )
            provenance = {
                "source_reference": "enterprise/audit_suite/company_contract_draft_exercise.py",
                "source_pins": pins,
                "proposed_contacts": custody,
                "scenario": scenario,
                "qualification": QUALIFICATION,
            }
            definition = _definition(scenario, branch, boundaries, custody)
            at = _time("2027-05-01T08:00:00+00:00")
            ref = store.append_version(
                COMPANY,
                branch,
                "contract_scope",
                "SCOPE-01",
                expected_version=0,
                command_id=f"CD-{branch}-SCOPE",
                event_at=at,
                available_at=at,
                content=encoded(definition),
                provenance=provenance,
            )
            records[scenario].append(ref)
            prior_sha, state = ref["sha256"], "NEW"
            for ordinal, event in enumerate(EVENTS[scenario], 1):
                body = _event_body(scenario, ordinal, event)
                if body["before"] != state:
                    raise CompanyStoreError("Invalid contract draft transition")
                body["scope_sha256"] = records[scenario][0]["sha256"]
                body["previous_sha256"] = prior_sha
                ref = store.append_version(
                    COMPANY,
                    branch,
                    "contract_event",
                    f"DRAFT-01-E{ordinal:02d}",
                    expected_version=0,
                    command_id=f"CD-{branch}-E{ordinal:02d}",
                    event_at=body["event_at"],
                    available_at=body["available_at"],
                    content=encoded(body),
                    provenance=provenance,
                )
                records[scenario].append(ref)
                prior_sha, state = ref["sha256"], body["after"]
        receipt = {
            "schema": SCHEMA,
            "status": "PROSPECTIVE_COMPANY_NATIVE_DRAFT_NO_AUDIT_CREDIT",
            "company": COMPANY,
            "branches": branches,
            "records": records,
            "final_states": {"CLEAN": "HOLD", "MESSY": "QUARANTINED"},
            "open_exception_ids": {"CLEAN": [], "MESSY": [EXCEPTION_ID]},
            "open_exception_counts": {"CLEAN": 0, "MESSY": 1},
            "exception_event_row_counts": {"CLEAN": 0, "MESSY": 5},
            "source_pins": pins,
            "proposed_contacts": custody,
            "provider_boundaries": boundaries,
            "qualification": QUALIFICATION,
            "limits": [
                "2027 event and availability clocks are prospective authored exercise times; "
                "imported_at is real insertion time and does not establish historic operation.",
                "No signed agreement, external communication, actual PHI/BA role, downstream "
                "processing, deployed provider, legal acceptance, actual cure or termination "
                "is asserted.",
                "Messy premature local clearance is an invalid internal marker, not approval or "
                "procurement acceptance; draft backfill does not close its exception.",
                "Only selected planned Reno and Boise boundaries and proposed contacts are "
                "represented; this is not a complete provider or obligation census.",
                "No audit grant, collection, workpaper, task, Key, grade, release or active "
                "company fact is changed.",
            ],
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "status": receipt["status"],
            "receipt_sha256": _digest(stage / "RECEIPT.json"),
            "company_db_sha256": _digest(stage / "company.sqlite3"),
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": sum(map(len, records.values())),
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return manifest


def verify(destination: Path, *, repository: Path | None = None) -> dict:
    """Independently reperform exact native route, chronology, source pins and causality."""
    root = Path(destination).absolute()
    names = ("RECEIPT.json", "MANIFEST.json", "company.sqlite3")
    if (
        root != root.resolve()
        or any(p.is_symlink() for p in (root, *root.parents))
        or not root.is_dir()
        or root.stat().st_mode & 0o077
        or any(
            (root / n).is_symlink()
            or (root / n).stat().st_nlink != 1
            or (root / n).stat().st_mode & 0o077
            for n in names
        )
        or any(p.name.endswith(("-wal", "-shm")) for p in root.iterdir())
    ):
        raise CompanyStoreError("Private ordinary source files without active sidecars required")
    manifest = json.loads((root / "MANIFEST.json").read_text())
    receipt = json.loads((root / "RECEIPT.json").read_text())
    if (
        manifest["receipt_sha256"] != _digest(root / "RECEIPT.json")
        or manifest["company_db_sha256"] != _digest(root / "company.sqlite3")
        or manifest["module_sha256"] != _digest(Path(__file__))
        or manifest["native_version_count"] != 12
        or manifest["audit_task_credit"] is not False
    ):
        raise CompanyStoreError("Draft exercise receipt pin mismatch")
    if (
        receipt["schema"] != SCHEMA
        or receipt["status"] != manifest["status"]
        or receipt["qualification"] != QUALIFICATION
        or receipt["company"] != COMPANY
        or receipt["final_states"] != {"CLEAN": "HOLD", "MESSY": "QUARANTINED"}
        or receipt["open_exception_ids"] != {"CLEAN": [], "MESSY": [EXCEPTION_ID]}
        or receipt["open_exception_counts"] != {"CLEAN": 0, "MESSY": 1}
        or receipt["exception_event_row_counts"] != {"CLEAN": 0, "MESSY": 5}
        or set(receipt["branches"]) != set(EVENTS)
        or receipt["branches"]["CLEAN"] == receipt["branches"]["MESSY"]
    ):
        raise CompanyStoreError("Draft exercise scope or exception receipt differs")
    repository = (
        Path(repository).resolve()
        if repository is not None
        else Path(__file__).resolve().parents[2]
    )
    pins, boundaries, custody = _source_context(repository)
    if (
        receipt["source_pins"] != pins
        or receipt["provider_boundaries"] != boundaries
        or receipt["proposed_contacts"] != custody
    ):
        raise CompanyStoreError("Canonical provider boundary or contact pins differ")
    with closing(
        sqlite3.connect((root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Native source database integrity failure")
        if (
            db.execute("SELECT COUNT(*) FROM grants").fetchone()[0]
            or db.execute("SELECT COUNT(*) FROM collections").fetchone()[0]
        ):
            raise CompanyStoreError("Draft exercise must not mint audit grants/collections")
        if db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != 12:
            raise CompanyStoreError("Unexpected native version count")
        for scenario in ("CLEAN", "MESSY"):
            branch = receipt["branches"][scenario]
            refs = receipt["records"][scenario]
            if len(refs) != 1 + len(EVENTS[scenario]):
                raise CompanyStoreError("Incomplete contract source chain")
            state, prior_sha = "NEW", None
            for index, ref in enumerate(refs):
                system = "contract_scope" if index == 0 else "contract_event"
                record = "SCOPE-01" if index == 0 else f"DRAFT-01-E{index:02d}"
                command = f"CD-{branch}-SCOPE" if index == 0 else f"CD-{branch}-E{index:02d}"
                if (
                    ref["company"],
                    ref["branch"],
                    ref["system"],
                    ref["record"],
                    ref["version"],
                ) != (COMPANY, branch, system, record, 1):
                    raise CompanyStoreError("Exact native contract routing differs")
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    (COMPANY, branch, system, record, 1),
                ).fetchone()
                if (
                    row is None
                    or row["command_id"] != command
                    or row["sha256"] != ref["sha256"]
                    or sha(row["content"]) != ref["sha256"]
                ):
                    raise CompanyStoreError("Native contract source identity/content mismatch")
                if (ref["event_at"], ref["available_at"], ref["imported_at"]) != (
                    row["event_at"],
                    row["available_at"],
                    row["imported_at"],
                ):
                    raise CompanyStoreError("Contract source timestamp receipt differs")
                if (
                    _time(row["imported_at"]) != row["imported_at"]
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                ):
                    raise CompanyStoreError("Actual import clock or source origin differs")
                body = json.loads(row["content"])
                provenance = json.loads(row["provenance"])
                if (
                    provenance["source_pins"] != receipt["source_pins"]
                    or provenance["proposed_contacts"] != receipt["proposed_contacts"]
                    or provenance["scenario"] != scenario
                    or provenance["qualification"] != QUALIFICATION
                    or ref["provenance"] != provenance
                ):
                    raise CompanyStoreError("Native contract provenance differs")
                if index == 0:
                    if body != _definition(
                        scenario,
                        branch,
                        receipt["provider_boundaries"],
                        receipt["proposed_contacts"],
                    ):
                        raise CompanyStoreError("Contract scope source differs")
                    expected_event = expected_available = _time("2027-05-01T08:00:00+00:00")
                else:
                    expected = _event_body(scenario, index, EVENTS[scenario][index - 1])
                    expected["scope_sha256"] = refs[0]["sha256"]
                    expected["previous_sha256"] = prior_sha
                    if body != expected or body["before"] != state:
                        raise CompanyStoreError("Causal contract trace differs")
                    expected_event, expected_available = (
                        expected["event_at"],
                        expected["available_at"],
                    )
                    state = body["after"]
                if (
                    row["event_at"] != expected_event
                    or row["available_at"] != expected_available
                    or row["available_at"] < row["event_at"]
                ):
                    raise CompanyStoreError(
                        "Authored contract event/availability chronology differs"
                    )
                prior_sha = row["sha256"]
            if state != receipt["final_states"][scenario]:
                raise CompanyStoreError("Final contract state differs")
    return manifest
