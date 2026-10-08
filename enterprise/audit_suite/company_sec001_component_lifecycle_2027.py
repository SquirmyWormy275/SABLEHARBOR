"""Selected fictional SEC001 component-lifecycle source without audit credit."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import stat
import tempfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _time
from .documentary_283_route_reconciliation_v6 import _p1_inventory
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_SEC001_SELECTED_SYNTHETIC_COMPONENT_LIFECYCLE_SOURCE_V1"
MANIFEST_SCHEMA = "SH_SEC001_SELECTED_SYNTHETIC_COMPONENT_LIFECYCLE_MANIFEST_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
CONTROL = "SH-SEC-001"
TASK = "TASK-SH-SEC-001-corporate-CHECK-SOC2:CC5.2"
CLAUSE = (
    "Reconcile technologies and outsourced components to controls and test an "
    "unsupported component; a hardening baseline alone does not cover the technology lifecycle."
)
EXERCISE = "SIM-SEC001-COMPONENT-LIFECYCLE-2027-001"
CORE = "SIM-INTERNAL-CONTROL-GATEWAY-01"
OUTSOURCED = "SIM-UNNAMED-OUTSOURCED-CANDIDATE-01"
EXCEPTION = "SIM-SEC001-COMPONENT-FALSE-CLOSE-EXC-001"
START = "2027-10-12T09:00:00+00:00"
AS_OF = "2026-09-30"
BRANCHES = {"CLEAN": "SEC001-COMPONENT-CLEAN", "MESSY": "SEC001-COMPONENT-MESSY"}
SYSTEM_OWNERS = {
    "component_inventory": "AS-P007",
    "ownership": "AS-P007",
    "control_mapping": "AS-P008",
    "lifecycle": "AS-P007",
    "challenge": "AS-P008",
    "supplier_risk": "AS-P013",
    "exception_register": "AS-P008",
}
PEOPLE = {
    "AS-P007": ("Elliot Tran", "Head of Enterprise Technology Services", "ROLE-33"),
    "AS-P008": ("Dana West", "Chief Information Security Officer", "ROLE-34"),
    "AS-P013": ("Erin Cross", "Procurement and Supplier Risk Lead", "AS-ROLE-PROCUREMENT"),
}
ROUTE_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V10_2026-09-30.json"
ROUTE_REVIEW = (
    "enterprise/generated/audit-suite/documentary-283-route-reconciliation-v10-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
ROUTE_SHA = "d7904fe36b8307e31071a24086d71b2500910e88e5243256a1d5bf4b4f050324"
REVIEW_SHA = "b702667f9f480774c07d160c31939250c7ad76a65661a1f7c8c41f23e068b674"
P1_FREEZE = {
    "file_count": 538,
    "inventory_sha256": ("f266ef682b502b3b093170f8a7b64fcf5cbab722d5c8ddf6715a63c0e535360f"),
}
CANON_SHA = {
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md": (
        "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433"
    ),
    "docs/controls/CCF_CONTROL_OBJECTIVES_v0.1.md": (
        "db7a189139b86fb51d684b6af3e681002b5e0f3f81c38c5bc15a61c20e4a59a3"
    ),
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md": (
        "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751"
    ),
    "docs/organization/source/chartbook.json": (
        "6ba4f1ed1a14581455a62c3e79a29ca59dbaf1270dfb0db850c0376c15507b49"
    ),
    "docs/structured/enterprise_leadership_2026-09-13.json": (
        "90ec45642cc50219544910e60e4bf6d28b810302c62f29c5936bf965501d673d"
    ),
    "enterprise/ccf/assurance/design_data/control_procedures.json": (
        "258f5c868e16f3dc197594857dc86a4f2b3ef11e3e5a36dd0a80a9fc6d40c679"
    ),
    "docs/canon/SABLE_HARBOR_CANONICAL_ARCHITECTURE_HANDOVER.md": (
        "ef0fe5602ab41f1de0a0c29146476dbb406cb56e28407652f7d00f357e3fc636"
    ),
    "docs/governance/ENTERPRISE_TECHNOLOGY_SERVICES_DOCTRINE.md": (
        "8dbfbd6a7b9414df28088d6e37ec7ba9e086616b5d4a2deb5cd33da845fa64fd"
    ),
    "enterprise/audit_suite/SEC001_SELECTED_COMPONENT_LIFECYCLE_2027_PROPOSAL.md": (
        "16ac75e137659827bfcf687da6f1155dca76e37baf34c11d1f462f1653668608"
    ),
}
PLAN = {
    "CLEAN": (
        ("component_inventory", "INVENTORY", 0, 0),
        ("ownership", "OWNERS", 10, 0),
        ("control_mapping", "CONTROL-MAP", 20, 0),
        ("lifecycle", "CORE-SUPPORT", 30, 0),
        ("supplier_risk", "OUTSOURCED-STATUS", 40, 0),
        ("challenge", "UNSUPPORTED-CHALLENGE", 50, 0),
        ("challenge", "USE-BLOCK", 60, 0),
        ("supplier_risk", "EVIDENCE-REQUEST", 70, 0),
        ("control_mapping", "REVIEW", 80, 0),
        ("exception_register", "FINAL", 90, 0),
    ),
    "MESSY": (
        ("component_inventory", "INVENTORY", 0, 0),
        ("ownership", "OWNERS", 10, 0),
        ("control_mapping", "CONTROL-MAP", 20, 0),
        ("control_mapping", "FALSE-CLOSE", 30, 2),
        ("challenge", "UNSUPPORTED-CHALLENGE", 40, 0),
        ("exception_register", "GAP-DISCOVERY", 50, 0),
        ("exception_register", "EXCEPTION-OPEN", 60, 0),
        ("component_inventory", "INVENTORY-CORRECTION", 70, 0),
        ("ownership", "OWNER-CORRECTION", 80, 0),
        ("control_mapping", "MAP-CORRECTION", 90, 0),
        ("supplier_risk", "OUTSOURCED-STATUS", 100, 0),
        ("supplier_risk", "EVIDENCE-REQUEST", 110, 0),
        ("challenge", "USE-BLOCK", 120, 0),
        ("exception_register", "FALSE-CLOSE-CORRECTION", 130, 0),
        ("exception_register", "FINAL", 140, 0),
    ),
}
ACTORS = {
    "INVENTORY": "AS-P007",
    "OWNERS": "AS-P007",
    "CONTROL-MAP": "AS-P008",
    "CORE-SUPPORT": "AS-P007",
    "OUTSOURCED-STATUS": "AS-P013",
    "UNSUPPORTED-CHALLENGE": "AS-P008",
    "USE-BLOCK": "AS-P008",
    "EVIDENCE-REQUEST": "AS-P013",
    "REVIEW": "AS-P008",
    "FALSE-CLOSE": "AS-P007",
    "GAP-DISCOVERY": "AS-P008",
    "EXCEPTION-OPEN": "AS-P008",
    "INVENTORY-CORRECTION": "AS-P007",
    "OWNER-CORRECTION": "AS-P013",
    "MAP-CORRECTION": "AS-P008",
    "FALSE-CLOSE-CORRECTION": "AS-P008",
    "FINAL": "AS-P008",
}
LINKS = {
    "INVENTORY": (),
    "OWNERS": ("INVENTORY",),
    "CONTROL-MAP": ("INVENTORY", "OWNERS"),
    "CORE-SUPPORT": ("CONTROL-MAP",),
    "OUTSOURCED-STATUS": ("CONTROL-MAP",),
    "UNSUPPORTED-CHALLENGE": ("CONTROL-MAP",),
    "USE-BLOCK": ("UNSUPPORTED-CHALLENGE",),
    "EVIDENCE-REQUEST": ("OUTSOURCED-STATUS",),
    "REVIEW": ("USE-BLOCK", "EVIDENCE-REQUEST"),
    "FALSE-CLOSE": ("CONTROL-MAP",),
    "GAP-DISCOVERY": ("FALSE-CLOSE", "UNSUPPORTED-CHALLENGE"),
    "EXCEPTION-OPEN": ("GAP-DISCOVERY",),
    "INVENTORY-CORRECTION": ("EXCEPTION-OPEN",),
    "OWNER-CORRECTION": ("INVENTORY-CORRECTION",),
    "MAP-CORRECTION": ("OWNER-CORRECTION",),
    "FALSE-CLOSE-CORRECTION": ("FALSE-CLOSE", "USE-BLOCK"),
    "FINAL": (),
}
ORIGINAL_FIELDS = (
    "company",
    "branch",
    "system",
    "record",
    "version",
    "event_at",
    "available_at",
    "imported_at",
    "sha256",
)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private_file(path: Path) -> tuple:
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise CompanyStoreError("Private component path alias forbidden")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600:
        raise CompanyStoreError("Ordinary 0600 private component file required")
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, _digest(path)


def _pins(repository: Path) -> dict:
    pins = {}
    for name, expected in CANON_SHA.items():
        path = repository / name
        if path.is_symlink() or not path.is_file() or _digest(path) != expected:
            raise CompanyStoreError(f"Selected component canon pin differs: {name}")
        pins[name] = expected
    module = "enterprise/audit_suite/company_sec001_component_lifecycle_2027.py"
    pins[module] = _digest(repository / module)
    return pins


def _canon(repository: Path) -> None:
    chart = json.loads((repository / "docs/organization/source/chartbook.json").read_bytes())
    leaders = json.loads(
        (repository / "docs/structured/enterprise_leadership_2026-09-13.json").read_bytes()
    )
    for person, (name, title, role) in PEOPLE.items():
        cards = [
            x for x in chart["nodes"] if x.get("person_id") == person and x.get("type") == "person"
        ]
        leadership = [x for x in leaders["people"] if x["person_id"] == person]
        if (
            len(cards) != 1
            or len(leadership) != 1
            or (cards[0]["name"], cards[0]["title"], cards[0]["role_id"]) != (name, title, role)
            or cards[0]["title_state"] != "DELEGATED_FICTIONAL_APPOINTMENT_PENDING_ACCEPTANCE"
            or (leadership[0]["name"], leadership[0]["title"], leadership[0]["org_role_id"])
            != (name, title, role)
        ):
            raise CompanyStoreError("Selected component actor authority differs")
    handover = (
        repository / "docs/canon/SABLE_HARBOR_CANONICAL_ARCHITECTURE_HANDOVER.md"
    ).read_text()
    if "The third-party landscape has not yet been designed." not in handover:
        raise CompanyStoreError("Locked third-party design boundary differs")
    catalog = (repository / "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md").read_text()
    if (
        "| SH-SEC-001 | Security architecture" not in catalog
        or "| SH-CFG-003 | Patch and lifecycle" not in catalog
    ):
        raise CompanyStoreError("Selected architecture/lifecycle control canon differs")
    procedures = json.loads(
        (repository / "enterprise/ccf/assurance/design_data/control_procedures.json").read_bytes()
    )
    selected = [row for row in procedures if row.get("control_id") == CONTROL]
    if (
        len(selected) != 1
        or selected[0].get("proposed_system_of_record") != "Security architecture repository"
        or selected[0].get("reviewer_role_description") != "Security architecture authority"
    ):
        raise CompanyStoreError("Proposed security architecture authority differs")


def _route(repository: Path, private: Path) -> tuple[dict, dict]:
    ledger_path = repository / ROUTE_LEDGER
    review_path = private / ROUTE_REVIEW
    before = _private_file(review_path)
    if _digest(ledger_path) != ROUTE_SHA or before[-1] != REVIEW_SHA:
        raise CompanyStoreError("Reviewed V10 component route bytes differ")
    ledger = json.loads(ledger_path.read_bytes())
    review = json.loads(review_path.read_bytes())
    if (
        review.get("verdict")
        != "PASS_READ_ONLY_SELECTED_ETH001_ROUTE_RECONCILIATION_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or review.get("main_tracked_sha256", {}).get(ROUTE_LEDGER) != ROUTE_SHA
        or review.get("p1_freeze") != P1_FREEZE
        or review.get("audit_task_credit") is not False
        or ledger.get("audit_task_credit") is not False
        or ledger.get("active_pair_mutated") is not False
    ):
        raise CompanyStoreError("Reviewed V10 component route claim differs")
    selected = {}
    for side in "AB":
        rows = [row for row in ledger["rows"] if row["side"] == side and row["task_id"] == TASK]
        if len(rows) != 1:
            raise CompanyStoreError("Selected CC5.2 route missing")
        row = rows[0]
        if (
            row["control_id"] != CONTROL
            or row["classification"] != "UNSUPPORTED_EXACT_CLAUSE"
            or row["requirement_ids"] != ["SOC2:CC5.2"]
            or row["authored_test_clause"] != CLAUSE
            or row["remaining_test_gate"] != CLAUSE
            or row["targeted_integrated_source_ids"] != ["SEC003_SELECTED_VULNERABILITY_V1"]
            or row["v6_reviewed_source_ids"] != ["SEC003_SELECTED_VULNERABILITY_V1"]
            or "No full inventory, scanner execution or authored CC7.1/CC5.2 support."
            not in row["v6_source_limits"]["SEC003_SELECTED_VULNERABILITY_V1"]
            or row["candidate_or_design_source_ids"]
            or row["current_status"] != "NOT_STARTED"
            or row["current_conclusion"] != "NOT_RUN"
            or row["audit_task_credit"] is not False
        ):
            raise CompanyStoreError("Selected CC5.2 authored clause boundary differs")
        selected[side] = {
            "task_id": TASK,
            "authored_test_clause": row["authored_test_clause"],
            "screen_row_sha256": row["screen_row_sha256"],
            "classification": row["classification"],
            "current_status": row["current_status"],
            "current_conclusion": row["current_conclusion"],
            "source_limit": row["source_limit"],
            "existing_targeted_integrated_source_ids": row["targeted_integrated_source_ids"],
            "audit_task_credit": False,
        }
    if _private_file(review_path) != before or _digest(ledger_path) != ROUTE_SHA:
        raise CompanyStoreError("Reviewed V10 component route changed during read")
    return selected, {ROUTE_LEDGER: ROUTE_SHA, ROUTE_REVIEW: REVIEW_SHA}


def _ref(row: dict) -> dict:
    return {key: row[key] for key in ORIGINAL_FIELDS}


def _detail(scenario: str, record: str) -> dict:
    common = {
        "scope": "TWO_SELECTED_FUTURE_FICTIONAL_NON_DEPLOYED_COMPONENT_FIXTURES",
        "actual_deployed_component": False,
        "actual_supplier_selected_or_contracted": False,
        "full_technology_population": False,
    }
    details = {
        "INVENTORY": {
            "component_ids": [CORE, OUTSOURCED] if scenario == "CLEAN" else [CORE],
            "outsourced_candidate_included": scenario == "CLEAN",
        },
        "OWNERS": {
            "owner_ids": {CORE: "AS-P007", OUTSOURCED: "AS-P013"}
            if scenario == "CLEAN"
            else {CORE: "AS-P007"},
        },
        "CONTROL-MAP": {
            "mapped_component_ids": [CORE, OUTSOURCED] if scenario == "CLEAN" else [CORE],
            "control_ids": [CONTROL, "SH-CFG-003"],
            "mapping_is_design_only": True,
        },
        "CORE-SUPPORT": {"support_state": "SIMULATED_CURRENT", "actual_entitlement": False},
        "OUTSOURCED-STATUS": {
            "component_id": OUTSOURCED,
            "support_state": "UNKNOWN_UNVERIFIED",
            "named_vendor": None,
            "contract_or_entitlement": None,
        },
        "FALSE-CLOSE": {
            "claimed_full_component_coverage": True,
            "basis": "INTERNAL_HARDENING_BASELINE_ONLY",
            "actually_incomplete": True,
            "exception_id": EXCEPTION,
        },
        "UNSUPPORTED-CHALLENGE": {
            "component_id": OUTSOURCED,
            "challenge_result": "UNSUPPORTED_STATUS_UNVERIFIED_AND_USE_INELIGIBLE",
            "missing_inventory_and_mapping": scenario == "MESSY",
            "no_live_probe": True,
        },
        "GAP-DISCOVERY": {
            "omitted_outsourced_candidate_found": True,
            "false_close_retained": True,
            "exception_id": EXCEPTION,
        },
        "EXCEPTION-OPEN": {"exception_id": EXCEPTION, "status": "OPEN"},
        "INVENTORY-CORRECTION": {
            "component_ids": [CORE, OUTSOURCED],
            "original_incomplete_inventory_retained": True,
        },
        "OWNER-CORRECTION": {"component_id": OUTSOURCED, "local_contact": "AS-P013"},
        "MAP-CORRECTION": {
            "component_id": OUTSOURCED,
            "control_ids": [CONTROL, "SH-CFG-003"],
            "design_only": True,
        },
        "EVIDENCE-REQUEST": {
            "component_id": OUTSOURCED,
            "requested": ["supplier_identity", "support_window", "control_responsibilities"],
            "received": False,
        },
        "USE-BLOCK": {
            "component_id": OUTSOURCED,
            "deployment_allowed": False,
            "reason": "UNVERIFIED_SUPPORT_AND_SUPPLIER_BOUNDARY",
        },
        "REVIEW": {
            "selected_fixture_reconciled": True,
            "independent_audit_test": False,
            "deployment_approved": False,
        },
        "FALSE-CLOSE-CORRECTION": {
            "false_close_corrected": True,
            "false_close_erased": False,
            "exception_open": True,
            "exception_id": EXCEPTION,
        },
        "FINAL": {
            "selected_fixture_reconciled": True,
            "outsourced_candidate_blocked": True,
            "exception_open": scenario == "MESSY",
            "open_exception_ids": [EXCEPTION] if scenario == "MESSY" else [],
            "authored_clause_satisfied": False,
        },
    }
    return {**common, **details[record]}


def _body(scenario: str, record: str, refs: dict, previous: dict | None) -> dict:
    links = list(LINKS[record])
    if record == "UNSUPPORTED-CHALLENGE" and scenario == "CLEAN":
        links.append("OUTSOURCED-STATUS")
    if record == "OUTSOURCED-STATUS" and scenario == "MESSY":
        links = ["MAP-CORRECTION"]
    if record == "USE-BLOCK" and scenario == "MESSY":
        links.append("EVIDENCE-REQUEST")
    if record == "FINAL":
        links = ["REVIEW"] if scenario == "CLEAN" else ["FALSE-CLOSE-CORRECTION", "USE-BLOCK"]
    return {
        "schema": SCHEMA,
        "exercise_id": EXERCISE,
        "control_id": CONTROL,
        "selected_task_id": TASK,
        "scenario": scenario,
        "record_id": record,
        "actor_id": ACTORS[record],
        "actor_authority": "CANON_LISTED_FICTIONAL_APPOINTMENT_PENDING_ACCEPTANCE",
        "qualification": "AUTHORED_FUTURE_SELECTED_EXERCISE_NOT_REAL_OPERATION",
        "record_links": {name: refs[name] for name in links},
        "previous_original": previous,
        "detail": _detail(scenario, record),
        "source_complete": False,
        "audit_task_credit": False,
    }


def _provenance(pins: dict, route_pins: dict) -> dict:
    return {
        "source_reference": EXERCISE,
        "source_sha256": pins,
        "route_sha256": route_pins,
        "control_ids": [CONTROL, "SH-CFG-003"],
        "operational_fact_status": "FUTURE_FICTIONAL_SELECTED_EXERCISE_ONLY",
        "actor_authority": "CANON_LISTED_FICTIONAL_APPOINTMENTS_PENDING_ACCEPTANCE",
        "actual_supplier_or_deployment": False,
    }


def _receipt(originals: list[dict], pins: dict, route_pins: dict, routes: dict) -> dict:
    return {
        "schema": SCHEMA,
        "status": "SEALED_SELECTED_FUTURE_FICTIONAL_COMPANY_SOURCE_NO_AUDIT_CREDIT",
        "exercise_id": EXERCISE,
        "control_id": CONTROL,
        "task_id": TASK,
        "selected_authored_clause": CLAUSE,
        "branch_ids": BRANCHES,
        "branch_counts": {scenario: len(plan) for scenario, plan in PLAN.items()},
        "source_sha256": pins,
        "route_sha256": route_pins,
        "route_disposition": routes,
        "native_originals": originals,
        "native_count": len(originals),
        "selected_component_count": 2,
        "selected_component_ids": [CORE, OUTSOURCED],
        "actor_authority": "CANON_LISTED_FICTIONAL_APPOINTMENTS_PENDING_ACCEPTANCE",
        "clean_selected_reconciliation": "FICTIONAL_SELECTED_COMPONENTS_MAPPED_WITH_USE_BLOCK",
        "messy_false_close_corrected": True,
        "messy_historical_exception_open": True,
        "outsourced_component_challenged_and_blocked": True,
        "actual_supplier_selected_or_contracted": False,
        "actual_deployed_component": False,
        "approved_enterprise_architecture": False,
        "independent_approval": False,
        "population_complete": False,
        "source_complete": False,
        "audit_task_credit": False,
        "active_P1_mutated": False,
    }


def _input_digest(
    branch: str,
    system: str,
    record: str,
    event: str,
    available: str,
    provenance: dict,
    content: bytes,
) -> str:
    return sha(
        encoded(
            [
                [COMPANY, branch, system, record],
                0,
                event,
                available,
                "AUTHORED_TRAINING_SOURCE",
                provenance,
                sha(content),
            ]
        )
    )


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Append independent Clean/Messy originals without audit-journal writes."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    destination = Path(destination).absolute()
    if (
        destination.exists()
        or destination.is_symlink()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(path.is_symlink() for path in (destination, *destination.parents))
    ):
        raise CompanyStoreError("New private selected component destination required")
    if _p1_inventory(private) != P1_FREEZE:
        raise CompanyStoreError("Frozen P1 inventory differs")
    pins = _pins(repository)
    _canon(repository)
    routes, route_pins = _route(repository, private)
    start = datetime.fromisoformat(_time(START))
    if start.date().isoformat() <= AS_OF:
        raise CompanyStoreError("Prospective synthetic component chronology required")
    originals = []
    with tempfile.TemporaryDirectory(
        prefix="sec001-component-stage-", dir=destination.parent
    ) as staged:
        stage = Path(staged)
        store = CompanyStore(stage)
        for scenario, branch in BRANCHES.items():
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            refs: dict[str, dict] = {}
            previous = None
            for system, record, minute, lag in PLAN[scenario]:
                event = _time((start + timedelta(minutes=minute)).isoformat())
                available = _time((start + timedelta(minutes=minute + lag)).isoformat())
                content = encoded(
                    {
                        **_body(scenario, record, refs, previous),
                        "event_at": event,
                        "available_at": available,
                    }
                )
                provenance = _provenance(pins, route_pins)
                command = "SEC1-COMP-" + sha(encoded([branch, system, record]))
                original = store.append_version(
                    COMPANY,
                    branch,
                    system,
                    record,
                    expected_version=0,
                    command_id=command,
                    event_at=event,
                    available_at=available,
                    content=content,
                    provenance=provenance,
                )
                originals.append(
                    {
                        **original,
                        "command_id": command,
                        "input_digest": _input_digest(
                            branch, system, record, event, available, provenance, content
                        ),
                    }
                )
                previous = refs[record] = _ref(original)
        receipt = _receipt(originals, pins, route_pins, routes)
        source = stage / "SOURCE_RECEIPT.json"
        source.write_bytes(encoded(receipt))
        source.chmod(0o600)
        database = stage / "company.sqlite3"
        manifest = {
            "schema": MANIFEST_SCHEMA,
            "status": "SEALED_PRIVATE_FUTURE_SOURCE_ONLY",
            "source_receipt_sha256": _digest(source),
            "native_db_sha256": _digest(database),
            "module_sha256": pins[
                "enterprise/audit_suite/company_sec001_component_lifecycle_2027.py"
            ],
            "proposal_sha256": pins[
                "enterprise/audit_suite/SEC001_SELECTED_COMPONENT_LIFECYCLE_2027_PROPOSAL.md"
            ],
            "native_count": len(originals),
            "audit_task_credit": False,
            "active_P1_mutated": False,
        }
        path = stage / "RUN-MANIFEST.json"
        path.write_bytes(encoded(manifest))
        path.chmod(0o600)
        publish(stage, destination)
    return verify(destination, repository=repository, private_repository=private)


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    """Reperform exact originals, provenance, three clocks and route claims."""
    raw = Path(destination).absolute()
    if any(path.is_symlink() for path in (raw, *raw.parents)):
        raise CompanyStoreError("Private selected component directory alias forbidden")
    destination = raw.resolve(strict=True)
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    if _p1_inventory(private) != P1_FREEZE:
        raise CompanyStoreError("Frozen P1 inventory differs")
    database = destination / "company.sqlite3"
    if any(Path(str(database) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
        raise CompanyStoreError("Selected component SQLite sidecar forbidden")
    if destination.stat().st_mode & 0o077 or {p.name for p in destination.iterdir()} != {
        "SOURCE_RECEIPT.json",
        "RUN-MANIFEST.json",
        "company.sqlite3",
    }:
        raise CompanyStoreError("Exact private selected component layout required")
    paths = {
        name: destination / name
        for name in (
            "SOURCE_RECEIPT.json",
            "RUN-MANIFEST.json",
            "company.sqlite3",
        )
    }
    before = {name: _private_file(path) for name, path in paths.items()}
    pins = _pins(repository)
    _canon(repository)
    routes, route_pins = _route(repository, private)
    receipt = json.loads(paths["SOURCE_RECEIPT.json"].read_bytes())
    manifest = json.loads(paths["RUN-MANIFEST.json"].read_bytes())
    if manifest != {
        "schema": MANIFEST_SCHEMA,
        "status": "SEALED_PRIVATE_FUTURE_SOURCE_ONLY",
        "source_receipt_sha256": before["SOURCE_RECEIPT.json"][-1],
        "native_db_sha256": before["company.sqlite3"][-1],
        "module_sha256": pins["enterprise/audit_suite/company_sec001_component_lifecycle_2027.py"],
        "proposal_sha256": pins[
            "enterprise/audit_suite/SEC001_SELECTED_COMPONENT_LIFECYCLE_2027_PROPOSAL.md"
        ],
        "native_count": 25,
        "audit_task_credit": False,
        "active_P1_mutated": False,
    }:
        raise CompanyStoreError("Selected component manifest differs")
    expected = []
    start = datetime.fromisoformat(_time(START))
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Selected component database integrity failed")
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        if systems != {
            (COMPANY, branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in SYSTEM_OWNERS.items()
        }:
            raise CompanyStoreError("Selected component system custody differs")
        if db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != 25 or any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections", "access_events")
        ):
            raise CompanyStoreError("Selected component rows or audit journals differ")
        for scenario, branch in BRANCHES.items():
            refs: dict[str, dict] = {}
            previous = None
            for system, record, minute, lag in PLAN[scenario]:
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=1",
                    (COMPANY, branch, system, record),
                ).fetchone()
                event = _time((start + timedelta(minutes=minute)).isoformat())
                available = _time((start + timedelta(minutes=minute + lag)).isoformat())
                body = encoded(
                    {
                        **_body(scenario, record, refs, previous),
                        "event_at": event,
                        "available_at": available,
                    }
                )
                provenance = _provenance(pins, route_pins)
                if (
                    row is None
                    or row["event_at"] != event
                    or row["available_at"] != available
                    or not row["imported_at"].startswith("2026-")
                    or _time(row["imported_at"]) != row["imported_at"]
                    or (previous is not None and row["imported_at"] < previous["imported_at"])
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or row["provenance"]
                    != json.dumps(provenance, sort_keys=True, separators=(",", ":"))
                    or row["content"] != body
                    or row["sha256"] != sha(body)
                    or row["command_id"] != "SEC1-COMP-" + sha(encoded([branch, system, record]))
                    or row["input_digest"]
                    != _input_digest(branch, system, record, event, available, provenance, body)
                ):
                    raise CompanyStoreError(
                        "Selected component original, provenance or clocks differ"
                    )
                original = {
                    key: (json.loads(row[key]) if key == "provenance" else row[key])
                    for key in (
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
                        "command_id",
                        "input_digest",
                    )
                }
                expected.append(original)
                previous = refs[record] = _ref(original)
        if receipt != _receipt(expected, pins, route_pins, routes):
            raise CompanyStoreError("Selected component receipt or original claim differs")
    if any(_private_file(path) != before[name] for name, path in paths.items()):
        raise CompanyStoreError("Selected component source changed during verification")
    if _pins(repository) != pins or _p1_inventory(private) != P1_FREEZE:
        raise CompanyStoreError("Selected component pins or P1 changed during verification")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    result = (
        create(
            args.destination, repository=args.repository, private_repository=args.private_repository
        )
        if args.action == "create"
        else verify(
            args.destination, repository=args.repository, private_repository=args.private_repository
        )
    )
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "native_count": result["native_count"],
                "branch_counts": result["branch_counts"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
