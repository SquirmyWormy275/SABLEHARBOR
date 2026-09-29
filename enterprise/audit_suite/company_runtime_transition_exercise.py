"""Fictional 2027 Reno/Boise transition in an isolated company-native source.

The 2026 canon remains selected/procurement-pending and nonoperating. These
future authored records are in-universe training facts, never real contracts,
provider actions, PHI activity, or current audit evidence.
"""

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
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_RUNTIME_TRANSITION_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
QUALIFICATION = "AUTHORED_FUTURE_IN_UNIVERSE_SOURCE_NO_REAL_DEPLOYMENT_OR_AUDIT_CREDIT"
DECISION = "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md"
DECISION_SHA256 = "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496"
SITES = "enterprise/services/source/runtime_sites_2026-09-11.json"
SOURCE_PATHS = (
    DECISION,
    SITES,
    "docs/canon/RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md",
    "docs/internal/development/CCF_ASSURANCE_SCOPE_PROPOSAL_2026-09-11.md",
    "enterprise/services/source/services.json",
    "enterprise/services/source/components.json",
    "enterprise/services/source/workloads.json",
    "docs/controls/RUNTIME_CONTROL_AND_EVIDENCE_MATRIX_2026-09-11.md",
    "docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md",
    "enterprise/audit_suite/RUNTIME_TRANSITION_PROPOSAL.md",
)
SITE_IDS = {"RENO": "RUNTIME-RENO-COLO", "BOISE": "RUNTIME-BOISE-DR"}
PROVIDER_IDS = {"RENO": "CP-SWITCH", "BOISE": "CP-IDACORE"}
CONTRACT_IDS = {"RENO": "RT-SO-RENO", "BOISE": "RT-SO-BOISE"}
SYSTEM_OWNERS = {
    "provider_contract": "AS-P013",
    "site_installation": "AS-P007",
    "site_commissioning": "AS-P007",
    "recovery_exercise": "AS-P007",
    "site_release": "AS-P007",
    "exception_event": "AS-P008",
}
EXCEPTION_ID = "EXC-TRANSITION-BOISE-KEY-BYPASS-01"
FIXTURE_SHA256 = sha(encoded({"marker": "NONPERSONAL_PAYLOAD_FREE_RECOVERY", "version": 1}))
DENOMINATORS = {
    "selected_sites": 2,
    "provider_contracts": 2,
    "site_installations": 2,
    "final_commissioning_decisions": 2,
    "final_recovery_exercises": 1,
    "final_site_releases": 2,
}


def _step(system, record, version, site, at, status, *, lag=0, depends=None):
    return (system, record, version, site, at, status, lag, depends)


COMMON = (
    _step(
        "provider_contract", "C-RENO", 1, "RENO", "2027-02-15T10:00:00+00:00", "EXECUTED_SIMULATED"
    ),
    _step(
        "provider_contract",
        "C-BOISE",
        1,
        "BOISE",
        "2027-03-05T10:00:00+00:00",
        "EXECUTED_SIMULATED",
    ),
    _step(
        "site_installation",
        "I-RENO",
        1,
        "RENO",
        "2027-04-03T12:00:00+00:00",
        "INSTALLED_SIMULATED",
        depends="C-RENO",
    ),
    _step(
        "site_commissioning",
        "CM-RENO",
        1,
        "RENO",
        "2027-05-08T12:00:00+00:00",
        "PASS",
        depends="I-RENO",
    ),
    _step(
        "site_release",
        "RL-RENO",
        1,
        "RENO",
        "2027-05-20T14:00:00+00:00",
        "OPERATING_PRIMARY_SIMULATED",
        depends="CM-RENO",
    ),
    _step(
        "site_installation",
        "I-BOISE",
        1,
        "BOISE",
        "2027-06-08T12:00:00+00:00",
        "INSTALLED_SIMULATED",
        depends="C-BOISE",
    ),
)
CLEAN = COMMON + (
    _step(
        "site_commissioning",
        "CM-BOISE",
        1,
        "BOISE",
        "2027-07-12T12:00:00+00:00",
        "PASS",
        depends="I-BOISE",
    ),
    _step(
        "recovery_exercise",
        "RX-BOISE",
        1,
        "BOISE",
        "2027-07-21T10:00:00+00:00",
        "PASS",
        depends="CM-BOISE",
    ),
    _step(
        "site_release",
        "RL-BOISE",
        1,
        "BOISE",
        "2027-07-28T14:00:00+00:00",
        "OPERATING_RECOVERY_SIMULATED",
        depends="RX-BOISE",
    ),
)
MESSY = COMMON + (
    _step(
        "site_commissioning",
        "CM-BOISE",
        1,
        "BOISE",
        "2027-07-12T12:00:00+00:00",
        "HOLD_KEY_DEPENDENCY",
        depends="I-BOISE",
    ),
    _step(
        "exception_event",
        "EX-BOISE",
        1,
        "BOISE",
        "2027-07-13T10:00:00+00:00",
        "INVALID_LOCAL_READY_MARKER",
        depends="CM-BOISE",
    ),
    _step(
        "recovery_exercise",
        "RX-BOISE",
        1,
        "BOISE",
        "2027-07-20T10:00:00+00:00",
        "FAIL_KEY_DEPENDENCY",
        lag=60,
        depends="CM-BOISE",
    ),
    _step(
        "exception_event",
        "EX-BOISE",
        2,
        "BOISE",
        "2027-07-22T10:00:00+00:00",
        "QUARANTINED_MARKER",
        depends="RX-BOISE",
    ),
    _step(
        "site_commissioning",
        "CM-BOISE",
        2,
        "BOISE",
        "2027-08-02T12:00:00+00:00",
        "PASS_AFTER_CORRECTION",
        depends="CM-BOISE",
    ),
    _step(
        "recovery_exercise",
        "RX-BOISE",
        2,
        "BOISE",
        "2027-08-05T10:00:00+00:00",
        "PASS_AFTER_RETRY",
        depends="CM-BOISE",
    ),
    _step(
        "site_release",
        "RL-BOISE",
        1,
        "BOISE",
        "2027-08-10T14:00:00+00:00",
        "OPERATING_RECOVERY_WITH_OPEN_EXCEPTION_SIMULATED",
        depends="RX-BOISE",
    ),
)
EVENTS = {"CLEAN": CLEAN, "MESSY": MESSY}


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


def _source_context(repository: Path) -> tuple[dict, dict]:
    pins = {}
    for name in SOURCE_PATHS:
        path = repository / name
        if not path.is_file() or path.is_symlink():
            raise CompanyStoreError("Required transition source unavailable")
        pins[name] = _digest(path)
    if pins[DECISION] != DECISION_SHA256:
        raise CompanyStoreError("Owner scenario decision changed")
    source = json.loads((repository / SITES).read_text())
    sites = {}
    for role, site_id in SITE_IDS.items():
        matches = [row for row in source["sites"] if row["id"] == site_id]
        if len(matches) != 1:
            raise CompanyStoreError("Exact selected runtime site missing")
        site = matches[0]
        if any(
            (
                site.get("provider_id") != PROVIDER_IDS[role],
                site.get("contract_id") != CONTRACT_IDS[role],
                site.get("status") != "PROVIDER_SELECTED_PROCUREMENT_PENDING",
                site.get("contract_status") != "DRAFT",
                site.get("contract_executed") is not False,
                site.get("capacity_reserved") is not False,
                site.get("operating") is not False,
                site.get("provider_legal_name") is not None,
                role == "BOISE" and site.get("independence_required") is not True,
                role == "BOISE" and site.get("independence_verified") is not False,
            )
        ):
            raise CompanyStoreError("2026 selected/nonoperating baseline changed")
        sites[role] = {
            "site_id": site_id,
            "provider_id": site["provider_id"],
            "provider_label": site["provider"],
            "contract_id": site["contract_id"],
            "entity_reference": site["entity_id"],
            "source_status_2026": site["status"],
            "source_operating_2026": False,
            "source_contract_executed_2026": False,
            "source_pointer": SITES + "#/sites/" + str(source["sites"].index(site)),
        }
    services = json.loads((repository / "enterprise/services/source/services.json").read_text())
    if not {"SVC-compute", "SVC-identity", "SVC-siem", "SVC-backup"} <= {
        row[0] for row in services["services"]
    }:
        raise CompanyStoreError("Shared service inventory changed")
    pins["enterprise/audit_suite/company_runtime_transition_exercise.py"] = _digest(Path(__file__))
    return pins, sites


def _checks(system: str, status: str, site: str) -> dict:
    if system == "provider_contract":
        return {
            "site_scope": "PASS",
            "supplier_owner_split": "PASS",
            "fictional_execution_record": "PASS",
            "real_signature_not_asserted": "PASS",
        }
    if system == "site_installation":
        return {
            x: "PASS"
            for x in ("asset_inventory", "custody", "configuration_baseline", "security_gate")
        }
    if system == "site_commissioning":
        names = (
            "power_path",
            "carrier_path",
            "access_boundary",
            "independent_key_recovery" if site == "BOISE" else "key_custody",
        )
        return {
            x: (
                "FAIL"
                if status == "HOLD_KEY_DEPENDENCY" and x == "independent_key_recovery"
                else "PASS"
            )
            for x in names
        }
    if system == "recovery_exercise":
        return {
            "independent_admin_credentials": "PASS",
            "carrier_path": "PASS",
            "independent_key_recovery": "FAIL" if status == "FAIL_KEY_DEPENDENCY" else "PASS",
            "fixture_hash_reconciled": "NOT_RUN" if status == "FAIL_KEY_DEPENDENCY" else "PASS",
        }
    return {}


def _body(
    scenario: str, step: tuple, sites: dict, previous: str | None, dependency: str | None
) -> dict:
    system, record, version, site, at, status, lag, depends = step
    available = datetime.fromisoformat(at) + timedelta(minutes=lag)
    checks = _checks(system, status, site)
    exception = scenario == "MESSY" and (
        system == "exception_event"
        or record in {"RX-BOISE", "RL-BOISE"}
        or (record == "CM-BOISE" and version == 2)
    )
    return {
        "schema": SCHEMA,
        "scenario": scenario,
        "system": system,
        "record": record,
        "version": version,
        "site": sites[site],
        "status": status,
        "event_at": _time(at),
        "available_at": _time(available.isoformat()),
        "previous_event_sha256": previous,
        "depends_on_record": depends,
        "depends_on_sha256": dependency,
        "local_checks": checks,
        "local_checks_denominator": len(checks),
        "local_checks_passed": sum(v == "PASS" for v in checks.values()),
        "fixture_metadata_sha256": FIXTURE_SHA256 if system == "recovery_exercise" else None,
        "restored_fixture_sha256": (
            FIXTURE_SHA256 if system == "recovery_exercise" and status.startswith("PASS") else None
        ),
        "exception_id": EXCEPTION_ID if exception else None,
        "exception_open": exception,
        "local_ready_marker_valid": False if system == "exception_event" else None,
        "fictional_in_universe_contract_executed": system == "provider_contract",
        "fictional_in_universe_operating_release": system == "site_release",
        "fictional_contract_scope_summary": (
            {
                "site_service_order_id": sites[site]["contract_id"],
                "customer_entity_reference": sites[site]["entity_reference"],
                "provider_id": sites[site]["provider_id"],
                "provider_service": "COLOCATION_FACILITY_POWER_COOLING_PHYSICAL_ACCESS",
                "sable_harbor_retained": "EQUIPMENT_STACK_IDENTITY_KEYS_BACKUP_OVERSIGHT",
                "recovery_independence_required": site == "BOISE",
                "exact_signed_terms": "NOT_RETAINED_IN_THIS_BOUNDED_EXERCISE",
            }
            if system == "provider_contract"
            else None
        ),
        "real_external_signature": False,
        "real_world_provider_operation": False,
        "actual_real_world_phi_processing": False,
        "business_associate_role": "UNDETERMINED_SEPARATE_SCENARIO",
        "data_class": "NONPERSONAL_PAYLOAD_FREE_METADATA",
        "proposed_actor_roles": {
            "contract": ["AS-P013", "AS-P003", "AS-P002"],
            "technical": ["AS-P007", "AS-P008"],
        },
        "proposed_contract_signatory_person_id": (
            "AS-P002" if system == "provider_contract" else None
        ),
        "signatory_authority_status": (
            "PROPOSED_IN_UNIVERSE_ROLE_PENDING_INDEPENDENT_REVIEW"
            if system == "provider_contract"
            else "NOT_APPLICABLE"
        ),
        "actor_authority_limit": (
            "IN_UNIVERSE_SIMULATION_NO_CANON_DELEGATED_SIGNATURE_OR_REAL_PROVIDER_ACTION"
        ),
        "supplier_duties_candidate": ["facility_perimeter", "power_cooling", "physical_access"],
        "sable_harbor_duties_candidate": [
            "equipment",
            "network_edge",
            "identity",
            "keys",
            "backup_recovery",
            "provider_oversight",
        ],
        "customer_duties_status": "CONDITIONAL_UNDETERMINED_NO_CUSTOMER_CONTRACT",
        "qualification": QUALIFICATION,
    }


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def _observed_counts(steps: tuple) -> dict:
    latest = {(step[0], step[1]): step for step in steps}
    accepted = {
        "provider_contract": {"EXECUTED_SIMULATED"},
        "site_installation": {"INSTALLED_SIMULATED"},
        "site_commissioning": {"PASS", "PASS_AFTER_CORRECTION"},
        "recovery_exercise": {"PASS", "PASS_AFTER_RETRY"},
        "site_release": {
            "OPERATING_PRIMARY_SIMULATED",
            "OPERATING_RECOVERY_SIMULATED",
            "OPERATING_RECOVERY_WITH_OPEN_EXCEPTION_SIMULATED",
        },
    }

    def passing(system: str) -> int:
        return sum(step[0] == system and step[5] in accepted[system] for step in latest.values())

    return {
        "selected_sites": len(SITE_IDS),
        "provider_contracts": passing("provider_contract"),
        "site_installations": passing("site_installation"),
        "final_commissioning_decisions": passing("site_commissioning"),
        "final_recovery_exercises": passing("recovery_exercise"),
        "final_site_releases": passing("site_release"),
        "failed_commissioning_versions": sum(step[5] == "HOLD_KEY_DEPENDENCY" for step in steps),
        "failed_recovery_attempts": sum(step[5] == "FAIL_KEY_DEPENDENCY" for step in steps),
        "invalid_ready_markers": sum(step[5] == "INVALID_LOCAL_READY_MARKER" for step in steps),
    }


def create(destination: Path, *, repository: Path, clean_branch: str, messy_branch: str) -> dict:
    """Create isolated fictional company records; never grant or collect audit evidence."""
    repository = Path(repository).resolve()
    destination = _new_private(Path(destination))
    branches = {"CLEAN": _id(clean_branch), "MESSY": _id(messy_branch)}
    if branches["CLEAN"] == branches["MESSY"]:
        raise CompanyStoreError("Distinct branch identities required")
    pins, sites = _source_context(repository)
    observed = {scenario: _observed_counts(steps) for scenario, steps in EVENTS.items()}
    if any(
        {key: counts[key] for key in DENOMINATORS} != DENOMINATORS for counts in observed.values()
    ):
        raise CompanyStoreError("Final local transition source population incomplete")
    with tempfile.TemporaryDirectory(
        prefix=".runtime-transition-stage-", dir=destination.parent
    ) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records = {"CLEAN": [], "MESSY": []}
        for scenario, steps in EVENTS.items():
            branch = branches[scenario]
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            provenance = {
                "source_reference": "enterprise/audit_suite/company_runtime_transition_exercise.py",
                "source_pins": pins,
                "scenario": scenario,
                "qualification": QUALIFICATION,
            }
            latest = {}
            previous = None
            for step in steps:
                system, record, version, site, at, status, lag, depends = step
                dependency = latest[depends]["sha256"] if depends else None
                body = _body(scenario, step, sites, previous, dependency)
                if depends and _time(at) <= latest[depends]["event_at"]:
                    raise CompanyStoreError("Transition dependency chronology invalid")
                if system == "site_release":
                    if site == "RENO" and latest["CM-RENO"]["body_status"] != "PASS":
                        raise CompanyStoreError("Reno release lacks passed commissioning")
                    if site == "BOISE" and (
                        latest["CM-BOISE"]["body_status"] not in {"PASS", "PASS_AFTER_CORRECTION"}
                        or latest["RX-BOISE"]["body_status"] not in {"PASS", "PASS_AFTER_RETRY"}
                    ):
                        raise CompanyStoreError("Boise release lacks corrected recovery gates")
                ref = store.append_version(
                    COMPANY,
                    branch,
                    system,
                    record,
                    expected_version=version - 1,
                    command_id=f"RT-{branch}-{record}-V{version}",
                    event_at=body["event_at"],
                    available_at=body["available_at"],
                    content=encoded(body),
                    provenance=provenance,
                )
                records[scenario].append(ref)
                latest[record] = {**ref, "body_status": status}
                previous = ref["sha256"]
        receipt = {
            "schema": SCHEMA,
            "status": "FICTIONAL_FUTURE_COMPANY_NATIVE_TRANSITION_NO_AUDIT_CREDIT",
            "company": COMPANY,
            "branches": branches,
            "records": records,
            "source_pins": pins,
            "site_baseline": sites,
            "local_denominators": DENOMINATORS,
            "observed_local_counts": observed,
            "final_site_status": {
                "CLEAN": {
                    "RENO": "OPERATING_PRIMARY_SIMULATED",
                    "BOISE": "OPERATING_RECOVERY_SIMULATED",
                },
                "MESSY": {
                    "RENO": "OPERATING_PRIMARY_SIMULATED",
                    "BOISE": "OPERATING_RECOVERY_WITH_OPEN_EXCEPTION_SIMULATED",
                },
            },
            "open_exception_ids": {"CLEAN": [], "MESSY": [EXCEPTION_ID]},
            "open_exception_counts": {"CLEAN": 0, "MESSY": 1},
            "exception_event_row_counts": {"CLEAN": 0, "MESSY": 2},
            "qualification": QUALIFICATION,
            "limits": [
                "2027 events and availability are authored future in-universe clocks "
                "as of 2026-09-29; imported_at is actual insertion.",
                "The original 2026 selected/procurement-pending, unsigned/unreserved/"
                "nonoperating site source is unchanged.",
                "No real external signature, provider account, deployment, PHI/ePHI, "
                "BA status, customer contract or BAA is asserted.",
                "Local denominator is exactly the two selected sites, not a complete "
                "enterprise provider/system population.",
                "Messy invalid ready marker and failed recovery remain in history; "
                "one historical bypass exception stays open after technical recovery.",
                "No active audit grant, collection, workpaper, task, Key, grade or "
                "release is changed.",
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
    """Reperform native source identity, causal chronology and claim limits."""
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
        or manifest["schema"] != SCHEMA + "_MANIFEST"
        or manifest["native_version_count"] != 22
        or manifest["audit_task_credit"] is not False
    ):
        raise CompanyStoreError("Transition manifest pin mismatch")
    repository = Path(repository).resolve() if repository else Path(__file__).resolve().parents[2]
    pins, sites = _source_context(repository)
    observed = {scenario: _observed_counts(steps) for scenario, steps in EVENTS.items()}
    if any(
        {key: counts[key] for key in DENOMINATORS} != DENOMINATORS for counts in observed.values()
    ):
        raise CompanyStoreError("Final local transition source population incomplete")
    if (
        receipt["schema"] != SCHEMA
        or receipt["status"] != manifest["status"]
        or receipt["company"] != COMPANY
        or receipt["qualification"] != QUALIFICATION
        or receipt["source_pins"] != pins
        or receipt["site_baseline"] != sites
        or receipt["local_denominators"] != DENOMINATORS
        or receipt["observed_local_counts"] != observed
        or receipt["open_exception_counts"] != {"CLEAN": 0, "MESSY": 1}
        or receipt["exception_event_row_counts"] != {"CLEAN": 0, "MESSY": 2}
        or receipt["open_exception_ids"] != {"CLEAN": [], "MESSY": [EXCEPTION_ID]}
        or receipt["final_site_status"]
        != {
            "CLEAN": {
                "RENO": "OPERATING_PRIMARY_SIMULATED",
                "BOISE": "OPERATING_RECOVERY_SIMULATED",
            },
            "MESSY": {
                "RENO": "OPERATING_PRIMARY_SIMULATED",
                "BOISE": "OPERATING_RECOVERY_WITH_OPEN_EXCEPTION_SIMULATED",
            },
        }
        or set(receipt["branches"]) != set(EVENTS)
        or receipt["branches"]["CLEAN"] == receipt["branches"]["MESSY"]
    ):
        raise CompanyStoreError("Transition scope or causal receipt differs")
    with closing(
        sqlite3.connect((root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Native transition database integrity failure")
        if (
            db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != 22
            or db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] != 0
            or db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] != 0
        ):
            raise CompanyStoreError("Native transition count or access differs")
        systems = {tuple(r) for r in db.execute("SELECT company,branch,system,owner FROM systems")}
        expected_systems = {
            (COMPANY, branch, system, owner)
            for branch in receipt["branches"].values()
            for system, owner in SYSTEM_OWNERS.items()
        }
        if systems != expected_systems:
            raise CompanyStoreError("Transition system custody differs")
        for scenario, steps in EVENTS.items():
            branch = receipt["branches"][scenario]
            refs = receipt["records"][scenario]
            if len(refs) != len(steps):
                raise CompanyStoreError("Incomplete native transition chain")
            latest = {}
            previous = None
            for ref, step in zip(refs, steps, strict=True):
                system, record, version, site, at, status, lag, depends = step
                route = (COMPANY, branch, system, record, version)
                if (
                    tuple(ref[k] for k in ("company", "branch", "system", "record", "version"))
                    != route
                ):
                    raise CompanyStoreError("Exact transition source route differs")
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    route,
                ).fetchone()
                if (
                    row is None
                    or row["sha256"] != ref["sha256"]
                    or sha(row["content"]) != ref["sha256"]
                    or row["command_id"] != f"RT-{branch}-{record}-V{version}"
                    or any(row[k] != ref[k] for k in ("event_at", "available_at", "imported_at"))
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or _time(row["imported_at"]) != row["imported_at"]
                ):
                    raise CompanyStoreError("Native transition source identity differs")
                provenance = json.loads(row["provenance"])
                if provenance != ref["provenance"] or provenance != {
                    "source_reference": (
                        "enterprise/audit_suite/company_runtime_transition_exercise.py"
                    ),
                    "source_pins": pins,
                    "scenario": scenario,
                    "qualification": QUALIFICATION,
                }:
                    raise CompanyStoreError("Native transition provenance differs")
                dependency = latest[depends]["sha256"] if depends else None
                expected = _body(scenario, step, sites, previous, dependency)
                if (
                    json.loads(row["content"]) != expected
                    or row["event_at"] != expected["event_at"]
                    or row["available_at"] != expected["available_at"]
                    or row["available_at"] < row["event_at"]
                    or (depends and row["event_at"] <= latest[depends]["event_at"])
                ):
                    raise CompanyStoreError("Transition chronology or content differs")
                latest[record] = {**ref, "body_status": status}
                previous = ref["sha256"]
    return manifest
