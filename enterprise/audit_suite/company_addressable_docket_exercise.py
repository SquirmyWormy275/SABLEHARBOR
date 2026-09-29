"""Prospective HIPAA addressable-specification intake docket, not legal decisions."""

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

SCHEMA = "SH_PROSPECTIVE_ADDRESSABLE_DOCKET_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
QUALIFICATION = "LOCAL_PENDING_DOCKET_NO_HIPAA_APPLICABILITY_OR_SAFEGUARD_DECISION"
RELATED_EXCEPTION_CONTROL = "SH-POL-003"
LEGAL_CONTACT_CONTROL = "SH-LEG-001"
OMITTED_LOCATOR = "164.312(e)(2)(ii)"
EXCEPTION_ID = "EXC-ADDRESSABLE-01-OMISSION-AND-BLANKET-WAIVER"
INVENTORY = "enterprise/ccf/assurance/review_data/addressable_specifications.json"
SOURCES = (
    INVENTORY,
    "enterprise/ccf/assurance/review_data/findings.json",
    "enterprise/ccf/assurance/review_data/REVIEW_NOTES.md",
    "enterprise/ccf/assurance/design_data/control_procedures.json",
    "enterprise/ccf/assurance/design_data/hipaa_analysis.json",
    "docs/internal/development/CCF_ASSURANCE_SCOPE_PROPOSAL_2026-09-11.md",
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
)
EVENTS = {
    "CLEAN": (
        ("INVENTORY_RECONCILE", "NEW", "PENDING_REVIEW", "2027-03-02T09:00:00+00:00", 0, 22),
        (
            "ENVIRONMENT_AND_AUTHORITY_HOLD",
            "PENDING_REVIEW",
            "PENDING_REVIEW",
            "2027-03-02T10:00:00+00:00",
            0,
            22,
        ),
    ),
    "MESSY": (
        (
            "PREMATURE_BLANKET_WAIVER_MARKER",
            "NEW",
            "MISLABELED_WAIVER",
            "2027-03-02T09:00:00+00:00",
            0,
            21,
        ),
        (
            "SOURCE_RECONCILE",
            "MISLABELED_WAIVER",
            "QUARANTINED",
            "2027-03-02T10:00:00+00:00",
            60,
            21,
        ),
        ("BACKFILL_RECONCILE", "QUARANTINED", "QUARANTINED", "2027-03-03T13:00:00+00:00", 0, 22),
        (
            "ENVIRONMENT_AND_AUTHORITY_HOLD",
            "QUARANTINED",
            "QUARANTINED",
            "2027-03-03T14:00:00+00:00",
            0,
            22,
        ),
    ),
}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _new_private(destination: Path) -> Path:
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
            raise CompanyStoreError("Required source unavailable")
        pins[name] = _digest(path)
    specs = json.loads((repository / INVENTORY).read_text())
    if (
        len(specs) != 22
        or len({x["locator"] for x in specs}) != 22
        or OMITTED_LOCATOR not in {x["locator"] for x in specs}
        or any(
            x["implementation_class"] != "ADDRESSABLE"
            or x["disposition"] != "ENVIRONMENTAL_DECISION_REQUIRED"
            or x["review"] is not None
            or x["requirement_id"] not in {"HIPAA:164.308", "HIPAA:164.310", "HIPAA:164.312"}
            for x in specs
        )
    ):
        raise CompanyStoreError("The 22-entry unresolved source inventory changed")
    findings = json.loads((repository / SOURCES[1]).read_text())
    selected = [x for x in findings if x["id"] == "H-ADDRESSABLE"]
    if (
        len(selected) != 1
        or RELATED_EXCEPTION_CONTROL not in selected[0]["control_ids"]
        or selected[0]["remaining_decision"] != "RISK_CRITERIA_AND_QUALIFIED_INTERPRETATION"
        or selected[0]["status"] != "AUTHOR_FINDING_NOT_INDEPENDENT_ACCEPTANCE"
    ):
        raise CompanyStoreError("Addressable finding boundary changed")
    org = snapshot(repository)
    a = next(x for x in org["control_assignments"] if x["control_id"] == RELATED_EXCEPTION_CONTROL)
    legal = next(x for x in org["control_assignments"] if x["control_id"] == LEGAL_CONTACT_CONTROL)
    if (
        a["primary_person_id"] != "AS-P005"
        or a["custodian_person_id"] != "AS-P014"
        or a["operating_reviewer_person_id"] != "AS-P003"
        or a["status"] != "PROPOSED_CURRENT_ASSIGNMENT"
        or legal["primary_person_id"] != "AS-P003"
        or legal["status"] != "PROPOSED_CURRENT_ASSIGNMENT"
    ):
        raise CompanyStoreError("Proposed control contacts changed")
    contacts = {
        "related_generic_exception_control": {
            "control_id": RELATED_EXCEPTION_CONTROL,
            "primary_contact": a["primary_person_id"],
            "custodian_contact": a["custodian_person_id"],
            "status": a["status"],
            "authority_limit": a["authority_limit"],
        },
        "proposed_legal_consultation_contact": {
            "source_control_id": LEGAL_CONTACT_CONTROL,
            "person_id": legal["primary_person_id"],
            "status": legal["status"],
            "authority_limit": legal["authority_limit"],
        },
        "actual_addressable_decision_owner": "UNASSIGNED_PENDING_OWNER_AND_LEGAL_CONFIRMATION",
    }
    pins.update(org["source_sha256"])
    pins["enterprise/audit_suite/company_addressable_docket_exercise.py"] = _digest(Path(__file__))
    return pins, specs, contacts


def _candidate(spec: dict, *, scenario: str, late: bool) -> dict:
    return {
        "schema": SCHEMA,
        "scenario": scenario,
        "related_generic_exception_control_id": RELATED_EXCEPTION_CONTROL,
        "relationship_limit": "NOT_A_SH_POL_003_CONTROL_EXCEPTION_OR_HIPAA_DECISION",
        "source_requirement_id": spec["requirement_id"],
        "source_locator": spec["locator"],
        "source_label": spec["source_label"],
        "source_implementation_class": spec["implementation_class"],
        "source_disposition": spec["disposition"],
        "source_inventory_sha256": None,
        "docket_state": "PENDING_ENVIRONMENT_AND_QUALIFIED_LEGAL_REVIEW",
        "late_backfill": late,
        "actual_service_environment": None,
        "actual_ephi_systems": None,
        "entity_role_and_hipaa_applicability": "UNDETERMINED",
        "reasonableness_analysis": None,
        "risk_contribution": None,
        "selected_specification": None,
        "nonimplementation_rationale": None,
        "equivalent_alternative_analysis": None,
        "implemented_safeguard_evidence": None,
        "approver_id": None,
        "approval_at": None,
        "reassessment_trigger": "PENDING_ACTUAL_ENVIRONMENT_AND_ROLE_FACTS",
        "generic_waiver_effect": "NONE",
        "qualification": QUALIFICATION,
    }


def _event(scenario: str, ordinal: int, spec_locators: set[str]) -> dict:
    action, before, after, at, lag_minutes, observed_count = EVENTS[scenario][ordinal - 1]
    available = datetime.fromisoformat(at) + timedelta(minutes=lag_minutes)
    missing = [] if observed_count == 22 else [OMITTED_LOCATOR]
    exception = scenario == "MESSY"
    return {
        "schema": SCHEMA,
        "scenario": scenario,
        "sequence": ordinal,
        "related_generic_exception_control_id": RELATED_EXCEPTION_CONTROL,
        "relationship_limit": "DOES_NOT_RESOLVE_SH_POL_003_OPEN_SOURCE_GAP",
        "action": action,
        "before": before,
        "after": after,
        "event_at": _time(at),
        "available_at": _time(available.isoformat()),
        "expected_source_count": 22,
        "observed_docket_count": observed_count,
        "missing_source_locators": missing,
        "source_locators_sha256": sha(encoded(sorted(spec_locators))),
        "local_waiver_marker": ("INVALID_NO_LEGAL_OR_CONTROL_EFFECT" if exception else "NONE"),
        "candidate_decision_status": "ALL_PENDING_NO_IMPLEMENTATION_SELECTION",
        "actual_addressable_reviewer": None,
        "proposed_consultation_contacts": ["AS-P003", "AS-P005"],
        "review_contact_authority": "NO_ACTUAL_ADDRESSABLE_REVIEW_APPOINTMENT_OR_APPROVAL",
        "required_next_facts": [
            "actual service and ePHI environment",
            "entity and business-associate/subcontractor role",
            "risk contribution and reasonableness per locator",
            "implemented specification or reasoned equivalent alternative",
            "qualified legal and accountable risk-owner decisions",
        ],
        "exception_id": EXCEPTION_ID if exception else None,
        "exception_open": exception,
        "actual_hipaa_applicability": "UNDETERMINED",
        "approved_substitution": False,
        "implemented_safeguards_claimed": False,
        "actual_risk_waiver": False,
        "actual_owner_approval": False,
        "actual_legal_approval": False,
        "actual_cure_completed": False,
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
    """Create an isolated source docket; no audit access, evidence collection or credit."""
    repository = Path(repository).resolve()
    destination = _new_private(Path(destination))
    branches = {"CLEAN": _id(clean_branch), "MESSY": _id(messy_branch)}
    if branches["CLEAN"] == branches["MESSY"]:
        raise CompanyStoreError("Distinct branch identities required")
    pins, specs, contacts = _source_context(repository)
    locators = {x["locator"] for x in specs}
    with tempfile.TemporaryDirectory(prefix=".addressable-stage-", dir=destination.parent) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records = {"CLEAN": [], "MESSY": []}
        for scenario in ("CLEAN", "MESSY"):
            branch = branches[scenario]
            for system, owner in (
                ("addressable_candidate", "AS-P014"),
                ("docket_event", "AS-P005"),
            ):
                store.register_system(COMPANY, branch, system, owner)
            provenance = {
                "source_reference": "enterprise/audit_suite/company_addressable_docket_exercise.py",
                "source_pins": pins,
                "proposed_contacts": contacts,
                "scenario": scenario,
                "qualification": QUALIFICATION,
            }

            def emit(
                system: str,
                record: str,
                body: dict,
                *,
                branch: str = branch,
                scenario: str = scenario,
                provenance: dict = provenance,
            ) -> dict:
                raw = encoded(body)
                ref = store.append_version(
                    COMPANY,
                    branch,
                    system,
                    record,
                    expected_version=0,
                    command_id=f"AD-{branch}-{system}-{record}",
                    event_at=body["event_at"],
                    available_at=body["available_at"],
                    content=raw,
                    provenance=provenance,
                )
                records[scenario].append(ref)
                return ref

            def emit_candidate(index: int, *, scenario: str = scenario, emit=emit) -> None:
                spec = specs[index]
                late = scenario == "MESSY" and spec["locator"] == OMITTED_LOCATOR
                at = (
                    datetime.fromisoformat("2027-03-03T12:00:00+00:00")
                    if late
                    else datetime.fromisoformat("2027-03-01T08:00:00+00:00")
                    + timedelta(minutes=index)
                )
                body = _candidate(spec, scenario=scenario, late=late)
                body["source_inventory_sha256"] = pins[INVENTORY]
                body["event_at"] = body["available_at"] = _time(at.isoformat())
                emit("addressable_candidate", f"SPEC-{index + 1:02d}", body)

            for index, spec in enumerate(specs):
                if scenario == "MESSY" and spec["locator"] == OMITTED_LOCATOR:
                    continue
                emit_candidate(index)
            state, previous_sha = "NEW", None
            for ordinal in range(1, 1 + len(EVENTS[scenario])):
                if scenario == "MESSY" and ordinal == 3:
                    late_index = next(
                        i for i, spec in enumerate(specs) if spec["locator"] == OMITTED_LOCATOR
                    )
                    emit_candidate(late_index)
                body = _event(scenario, ordinal, locators)
                if body["before"] != state:
                    raise CompanyStoreError("Invalid docket transition")
                if body["observed_docket_count"] != sum(
                    ref["system"] == "addressable_candidate" for ref in records[scenario]
                ):
                    raise CompanyStoreError("Docket observation count differs")
                body["previous_event_sha256"] = previous_sha
                ref = emit("docket_event", f"GATE-{ordinal:02d}", body)
                state, previous_sha = body["after"], ref["sha256"]
        receipt = {
            "schema": SCHEMA,
            "status": "PROSPECTIVE_COMPANY_NATIVE_PENDING_DOCKET_NO_AUDIT_CREDIT",
            "company": COMPANY,
            "branches": branches,
            "records": records,
            "source_pins": pins,
            "proposed_contacts": contacts,
            "addressable_inventory_role": "22_ITEM_SOURCE_LOCATOR_INVENTORY_NOT_DECISIONS",
            "hipaa_analysis_role": "SEPARATE_SECTION_DESIGN_ANALYSIS_NOT_22_ITEM_REGISTER",
            "related_sh_pol003_gap": "OPEN_INSUFFICIENT_SOURCE_UNCHANGED",
            "source_locator_count": 22,
            "omitted_initially_in_messy": OMITTED_LOCATOR,
            "final_docket_counts": {"CLEAN": 22, "MESSY": 22},
            "initial_messy_docket_count": 21,
            "final_states": {"CLEAN": "PENDING_REVIEW", "MESSY": "QUARANTINED"},
            "open_exception_ids": {"CLEAN": [], "MESSY": [EXCEPTION_ID]},
            "open_exception_counts": {"CLEAN": 0, "MESSY": 1},
            "exception_event_row_counts": {"CLEAN": 0, "MESSY": 4},
            "qualification": QUALIFICATION,
            "limits": [
                "22 exact source-inventory locators are pending docket cases, not 22 "
                "environmental determinations.",
                "No actual HIPAA applicability, ePHI environment, implemented safeguard, "
                "reasoned equivalent alternative, approved substitution or risk waiver "
                "is asserted.",
                "SH-POL-003 governs generic exceptions and waivers. This HIPAA pending "
                "docket is distinct and does not resolve its active OPEN/INSUFFICIENT_SOURCE gap.",
                "The 22-item source inventory and the separate HIPAA section design analysis "
                "are pinned; publisher text and current legal status are not revalidated here.",
                "The Messy blanket-waiver marker has no effect; its source omission is "
                "backfilled but the invalid-marker exception remains open.",
                "2027 event and availability clocks are authored prospective times; imported_at "
                "is actual insertion time, not historic operation.",
                "No grant, collection, audit workpaper/task, Key, grade or active company "
                "fact is changed.",
            ],
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "status": receipt["status"],
            "receipt_sha256": _digest(stage / "RECEIPT.json"),
            "company_db_sha256": _digest(stage / "company.sqlite3"),
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": 50,
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return manifest


def verify(destination: Path, *, repository: Path | None = None) -> dict:
    """Reperform exact source inventory, native chronology and pending-state constraints."""
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
        raise CompanyStoreError("Private ordinary source files required")
    manifest = json.loads((root / "MANIFEST.json").read_text())
    receipt = json.loads((root / "RECEIPT.json").read_text())
    if (
        manifest["receipt_sha256"] != _digest(root / "RECEIPT.json")
        or manifest["company_db_sha256"] != _digest(root / "company.sqlite3")
        or manifest["module_sha256"] != _digest(Path(__file__))
        or manifest["native_version_count"] != 50
        or manifest["audit_task_credit"] is not False
    ):
        raise CompanyStoreError("Docket receipt pin mismatch")
    if (
        receipt["schema"] != SCHEMA
        or receipt["status"] != manifest["status"]
        or receipt["company"] != COMPANY
        or receipt["qualification"] != QUALIFICATION
        or receipt["addressable_inventory_role"] != "22_ITEM_SOURCE_LOCATOR_INVENTORY_NOT_DECISIONS"
        or receipt["hipaa_analysis_role"] != "SEPARATE_SECTION_DESIGN_ANALYSIS_NOT_22_ITEM_REGISTER"
        or receipt["related_sh_pol003_gap"] != "OPEN_INSUFFICIENT_SOURCE_UNCHANGED"
        or receipt["source_locator_count"] != 22
        or receipt["omitted_initially_in_messy"] != OMITTED_LOCATOR
        or receipt["final_docket_counts"] != {"CLEAN": 22, "MESSY": 22}
        or receipt["initial_messy_docket_count"] != 21
        or receipt["final_states"] != {"CLEAN": "PENDING_REVIEW", "MESSY": "QUARANTINED"}
        or receipt["open_exception_ids"] != {"CLEAN": [], "MESSY": [EXCEPTION_ID]}
        or receipt["open_exception_counts"] != {"CLEAN": 0, "MESSY": 1}
        or receipt["exception_event_row_counts"] != {"CLEAN": 0, "MESSY": 4}
        or set(receipt["branches"]) != set(EVENTS)
        or receipt["branches"]["CLEAN"] == receipt["branches"]["MESSY"]
    ):
        raise CompanyStoreError("Docket scope or exception receipt differs")
    repository = (
        Path(repository).resolve()
        if repository is not None
        else Path(__file__).resolve().parents[2]
    )
    pins, specs, contacts = _source_context(repository)
    if receipt["source_pins"] != pins or receipt["proposed_contacts"] != contacts:
        raise CompanyStoreError("Canonical addressable source or contact pins differ")
    locators = {x["locator"] for x in specs}
    with closing(
        sqlite3.connect((root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Native source database integrity failure")
        if (
            db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != 50
            or db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] != 0
            or db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] != 0
        ):
            raise CompanyStoreError("Native docket row or access count differs")
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        expected_systems = {
            (COMPANY, branch, system, owner)
            for branch in receipt["branches"].values()
            for system, owner in (
                ("addressable_candidate", "AS-P014"),
                ("docket_event", "AS-P005"),
            )
        }
        if systems != expected_systems:
            raise CompanyStoreError("Native docket system custody differs")
        for scenario in ("CLEAN", "MESSY"):
            branch = receipt["branches"][scenario]
            refs = receipt["records"][scenario]
            if len(refs) != 22 + len(EVENTS[scenario]):
                raise CompanyStoreError("Incomplete native docket chain")
            state, previous_sha, observed_candidates = "NEW", None, 0
            initial = [
                ("candidate", i)
                for i, spec in enumerate(specs)
                if scenario == "CLEAN" or spec["locator"] != OMITTED_LOCATOR
            ]
            late_index = next(
                i for i, spec in enumerate(specs) if spec["locator"] == OMITTED_LOCATOR
            )
            steps = (
                initial + [("event", 1), ("event", 2)]
                if scenario == "CLEAN"
                else initial
                + [
                    ("event", 1),
                    ("event", 2),
                    ("candidate", late_index),
                    ("event", 3),
                    ("event", 4),
                ]
            )
            for ref, (kind, number) in zip(refs, steps, strict=True):
                candidate = kind == "candidate"
                system = "addressable_candidate" if candidate else "docket_event"
                record = f"SPEC-{number + 1:02d}" if candidate else f"GATE-{number:02d}"
                if (
                    ref["company"],
                    ref["branch"],
                    ref["system"],
                    ref["record"],
                    ref["version"],
                ) != (COMPANY, branch, system, record, 1):
                    raise CompanyStoreError("Exact native docket route differs")
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    (COMPANY, branch, system, record, 1),
                ).fetchone()
                if (
                    row is None
                    or row["sha256"] != ref["sha256"]
                    or sha(row["content"]) != ref["sha256"]
                    or row["command_id"] != f"AD-{branch}-{system}-{record}"
                    or ref["event_at"] != row["event_at"]
                    or ref["available_at"] != row["available_at"]
                    or ref["imported_at"] != row["imported_at"]
                    or _time(row["imported_at"]) != row["imported_at"]
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                ):
                    raise CompanyStoreError("Native docket source identity or clocks differ")
                provenance = json.loads(row["provenance"])
                if (
                    provenance["source_pins"] != pins
                    or provenance["proposed_contacts"] != contacts
                    or provenance["scenario"] != scenario
                    or provenance["qualification"] != QUALIFICATION
                    or ref["provenance"] != provenance
                ):
                    raise CompanyStoreError("Native docket provenance differs")
                body = json.loads(row["content"])
                if candidate:
                    observed_candidates += 1
                    spec = specs[number]
                    late = scenario == "MESSY" and spec["locator"] == OMITTED_LOCATOR
                    at = (
                        datetime.fromisoformat("2027-03-03T12:00:00+00:00")
                        if late
                        else datetime.fromisoformat("2027-03-01T08:00:00+00:00")
                        + timedelta(minutes=number)
                    )
                    expected = _candidate(spec, scenario=scenario, late=late)
                    expected["source_inventory_sha256"] = pins[INVENTORY]
                    expected["event_at"] = expected["available_at"] = _time(at.isoformat())
                else:
                    ordinal = number
                    expected = _event(scenario, ordinal, locators)
                    expected["previous_event_sha256"] = previous_sha
                    if (
                        expected["before"] != state
                        or expected["observed_docket_count"] != observed_candidates
                    ):
                        raise CompanyStoreError("Invalid docket transition")
                    state = expected["after"]
                    previous_sha = row["sha256"]
                if (
                    body != expected
                    or row["event_at"] != expected["event_at"]
                    or row["available_at"] != expected["available_at"]
                    or row["available_at"] < row["event_at"]
                ):
                    raise CompanyStoreError("Causal docket content or chronology differs")
            if state != receipt["final_states"][scenario]:
                raise CompanyStoreError("Final docket state differs")
    return manifest
