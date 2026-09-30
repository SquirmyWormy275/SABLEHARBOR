"""Payload-free fictional 2027 ePHI/BA source history, gated on reviewed site release.

This producer is separate from audit collection. Every legal, contract, and
operating fact it emits is a labeled training-world assumption, never an actual
Sable Harbor assertion or real PHI processing record.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import tempfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _id, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_PHI_BA_FLOW_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
QUALIFICATION = "PAYLOAD_FREE_FUTURE_TRAINING_WORLD_NO_REAL_PHI_OR_LEGAL_STATUS"
EXCEPTION_ID = "EXC-SIM-BA-FLOWDOWN-01"
TRANSITION_SCHEMA = "SH_FICTIONAL_2027_RUNTIME_TRANSITION_V3"
SOURCE_PINS = {
    ("docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md"): (
        "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496"
    ),
    ("docs/internal/development/CCF_ASSURANCE_SCOPE_PROPOSAL_2026-09-11.md"): (
        "0ea41553d1f8bc975242f7ea8939f8750ec6f74e3aceb43f2e82101421a8b25a"
    ),
    ("docs/canon/RUNTIME_HOSTING_AND_DATA_CENTER_DECISIONS_2026-09-11.md"): (
        "fd309a9bdf596ea96498b7207b60ea3bea70a35d8c418371aa96c06d928bb17b"
    ),
    ("enterprise/services/source/runtime_sites_2026-09-11.json"): (
        "fa216f629762503865fd9f1a3207e87691cd484cec9885bf25ce045b4525519c"
    ),
    ("enterprise/ccf/assurance/design_data/SERVICE_DESCRIPTION.md"): (
        "d4697f8c01a9311cc208c2e4b1bd4bf1067bd02a001d4acb33cde29f15d30e89"
    ),
    ("enterprise/ccf/assurance/design_data/control_procedures.json"): (
        "258f5c868e16f3dc197594857dc86a4f2b3ef11e3e5a36dd0a80a9fc6d40c679"
    ),
    ("enterprise/ccf/assurance/design_data/hipaa_analysis.json"): (
        "27bb69cffd19e266abd56149db33da710dba07078328361fe9aca7293daa17c8"
    ),
    ("docs/canon/DECISION_REGISTER_ADDENDUM_2026-09-06_CLOSEOUT.md"): (
        "7405bf888afc85634f9dfaa062a51c440e06a2588df0f44ac7ef9953b892530e"
    ),
    ("docs/canon/INDUSTRIAL_CLOSEOUT_2026-09-05.md"): (
        "0b21f22c2a8ffe55fa4e43898834ddc38389e42efe2e9c11ff48c7418dad8be7"
    ),
    ("docs/canon/ENTERPRISE_APPOINTMENTS_2026-09-13.md"): (
        "1707ed7021576048ca5f1904ca5e94d484e8f7e2992da5c9e04965421f79a751"
    ),
    ("enterprise/audit_suite/phi_ba_2027_contract_spec_v1.json"): (
        "557cd3ddf09195207de93be2441710f38be9aa8693de729c07d8cf45e45a081f"
    ),
}
SYSTEM_OWNERS = {
    "scenario_scope": "AS-P014",
    "legal_decision": "AS-P003",
    "contract_authority": "SH-CEO-DANIEL-MERCER",
    "contract_approval": "AS-P003",
    "counterparty_acceptance": "AS-P004",
    "contract_register": "AS-P002",
    "flow_register": "AS-P014",
    "exception_register": "AS-P003",
}
CLAUSE_CANDIDATES = (
    "permitted_uses_and_disclosures",
    "safeguards_and_security",
    "incident_and_breach_reporting",
    "subcontractor_flowdown",
    "rights_request_support",
    "regulator_records_access",
    "return_or_destruction_and_continuing_protection",
    "material_breach_cure_and_termination",
)

# Independently reviewed V3 transition only; REVIEW.json SHA-256
# f1acaeaea963055f99b0de120fd1b0347ee984edf085d353e7af1e427234d5a9.
# Tests may inject fixture pins; production accepts only these sealed run bytes.
REVIEWED_TRANSITION_PINS: dict[str, str] = {
    "receipt": "0a0a448f619e490870f69959d196eb6d5ca3747af0d4fb68056195910ce6cc11",
    "manifest": "f7c6ec3ab460f204f69cf6b50df66399687034b3b63cb38aaee84841daedcbd4",
    "database": "428b5c740cb8fc627b38f2aa6847e450fd166e62be52a6309d4f5a7b284988fd",
}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private_path(path: Path, *, directory: bool) -> Path:
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise CompanyStoreError("Private nonsymlink source path required")
    if directory:
        if not path.is_dir() or path.stat().st_mode & 0o077:
            raise CompanyStoreError("Existing private directory required")
    else:
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077:
            raise CompanyStoreError("Private regular source file required")
    return path


def _frozen_snapshot(paths: dict[str, Path]) -> dict[str, tuple]:
    """Bind immutable reads to private, ordinary, sidecar-free file identities."""
    database = paths["database"]
    if any(
        Path(str(database) + suffix).exists() or Path(str(database) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Frozen database with no sidecars required")
    result = {}
    for name, path in paths.items():
        _private_path(path, directory=False)
        info = path.stat()
        result[name] = (
            info.st_dev,
            info.st_ino,
            stat.S_IMODE(info.st_mode),
            info.st_size,
            info.st_mtime_ns,
            _digest(path),
        )
    return result


def _new_private(destination: Path) -> Path:
    destination = Path(destination).absolute()
    _private_path(destination.parent, directory=True)
    if destination.exists() or destination.is_symlink() or destination != destination.resolve():
        raise CompanyStoreError("New canonical destination required")
    return destination


def _source_context(repository: Path) -> dict[str, str]:
    repository = Path(repository).resolve(strict=True)
    for name, expected in SOURCE_PINS.items():
        path = repository / name
        if not path.is_file() or path.is_symlink() or _digest(path) != expected:
            raise CompanyStoreError("2026 canon or approved scenario decision pin differs")
    spec = json.loads(
        (repository / "enterprise/audit_suite/phi_ba_2027_contract_spec_v1.json").read_text()
    )
    if (
        spec.get("schema") != "SH_FICTIONAL_2027_PHI_BA_CONTRACT_SPEC_V1"
        or spec.get("truth_class") != "TRAINING_SCENARIO_ONLY"
        or spec.get("canonical_source_pins")
        != {k: SOURCE_PINS[k] for k in spec.get("canonical_source_pins", {})}
        or spec.get("fictional_2027_boundary", {}).get("contracting_entity_id") != "SHI"
        or spec.get("limited_fictional_delegation", {}).get("scope")
        != ["SIM-BAA-CUST-01", "SIM-BAA-SUB-01"]
        or spec.get("clause_candidates") != list(CLAUSE_CANDIDATES)
        or set(spec.get("synthetic_terms", {})) != {"SIM-BAA-CUST-01", "SIM-BAA-SUB-01"}
        or any(
            len(spec["synthetic_terms"][contract]) != len(CLAUSE_CANDIDATES)
            or [x.get("clause_candidate_id") for x in spec["synthetic_terms"][contract]]
            != list(CLAUSE_CANDIDATES)
            or any(
                not isinstance(x.get("scenario_obligation"), str) or not x["scenario_obligation"]
                for x in spec["synthetic_terms"][contract]
            )
            for contract in ("SIM-BAA-CUST-01", "SIM-BAA-SUB-01")
        )
    ):
        raise CompanyStoreError("Fictional BA contract/authority specification differs")
    sites = json.loads(
        (repository / "enterprise/services/source/runtime_sites_2026-09-11.json").read_text()
    )
    for site_id, provider_id in (
        ("RUNTIME-RENO-COLO", "CP-SWITCH"),
        ("RUNTIME-BOISE-DR", "CP-IDACORE"),
    ):
        matching = [x for x in sites["sites"] if x["id"] == site_id]
        if len(matching) != 1 or any(
            (
                matching[0]["provider_id"] != provider_id,
                matching[0]["status"] != "PROVIDER_SELECTED_PROCUREMENT_PENDING",
                matching[0]["contract_executed"] is not False,
                matching[0]["operating"] is not False,
            )
        ):
            raise CompanyStoreError("2026 planned/nonoperating site boundary differs")
    return SOURCE_PINS.copy()


def _contract_terms(repository: Path) -> dict:
    spec = json.loads(
        (repository / "enterprise/audit_suite/phi_ba_2027_contract_spec_v1.json").read_text()
    )
    return spec["synthetic_terms"]


def _transition_context(root: Path, expected: dict[str, str] | None) -> dict:
    if not expected or set(expected) != {"receipt", "manifest", "database"}:
        raise CompanyStoreError("Independently reviewed transition pins required")
    root = _private_path(root, directory=True)
    paths = {
        "receipt": _private_path(root / "RECEIPT.json", directory=False),
        "manifest": _private_path(root / "MANIFEST.json", directory=False),
        "database": _private_path(root / "company.sqlite3", directory=False),
    }
    before = _frozen_snapshot(paths)
    if any(before[k][-1] != expected[k] for k in paths):
        raise CompanyStoreError("Reviewed transition source bytes differ")
    manifest = json.loads(paths["manifest"].read_text())
    receipt = json.loads(paths["receipt"].read_text())
    if (
        manifest.get("schema") != TRANSITION_SCHEMA + "_MANIFEST"
        or manifest.get("receipt_sha256") != expected["receipt"]
        or manifest.get("company_db_sha256") != expected["database"]
        or manifest.get("audit_task_credit") is not False
        or receipt.get("schema") != TRANSITION_SCHEMA
        or receipt.get("company") != COMPANY
        or receipt.get("open_exception_counts") != {"CLEAN": 0, "MESSY": 1}
        or set(receipt.get("branches", {})) != {"CLEAN", "MESSY"}
        or receipt.get("source_pins", {}).get(
            "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md"
        )
        != SOURCE_PINS[
            "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md"
        ]
    ):
        raise CompanyStoreError("Reviewed transition scope or source pin differs")
    status = receipt.get("final_site_status", {})
    expected_status = {
        "CLEAN": {"RENO": "OPERATING_PRIMARY_SIMULATED", "BOISE": "OPERATING_RECOVERY_SIMULATED"},
        "MESSY": {
            "RENO": "OPERATING_PRIMARY_SIMULATED",
            "BOISE": "OPERATING_RECOVERY_WITH_OPEN_EXCEPTION_SIMULATED",
        },
    }
    if status != expected_status:
        raise CompanyStoreError("Branch-specific site release not established")
    releases = {}
    with closing(
        sqlite3.connect(paths["database"].as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Reviewed transition database integrity failure")
        if any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections")
        ):
            raise CompanyStoreError("Transition run must not include audit access or collection")
        for scenario in ("CLEAN", "MESSY"):
            branch = receipt["branches"][scenario]
            _id(branch)
            releases[scenario] = {}
            for site in ("RENO", "BOISE"):
                record = f"RL-{site}"
                refs = [
                    x
                    for x in receipt["records"][scenario]
                    if x["system"] == "site_release" and x["record"] == record
                ]
                if len(refs) != 1:
                    raise CompanyStoreError("Exact reviewed site release reference required")
                ref = refs[0]
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? "
                    "AND system=? AND record=? AND version=?",
                    (COMPANY, branch, "site_release", record, 1),
                ).fetchone()
                if (
                    row is None
                    or ref["version"] != 1
                    or ref["sha256"] != row["sha256"]
                    or sha(row["content"]) != ref["sha256"]
                    or ref["event_at"] != row["event_at"]
                    or ref["available_at"] != row["available_at"]
                    or ref["imported_at"] != row["imported_at"]
                ):
                    raise CompanyStoreError("Transition native release/receipt join differs")
                body = json.loads(row["content"])
                if (
                    body["status"] != status[scenario][site]
                    or body["fictional_in_universe_operating_release"] is not True
                    or body["real_world_provider_operation"] is not False
                    or body["actual_real_world_phi_processing"] is not False
                    or row["available_at"] < row["event_at"]
                ):
                    raise CompanyStoreError("Transition release fact differs")
                releases[scenario][site] = ref
    if _frozen_snapshot(paths) != before:
        raise CompanyStoreError("Reviewed transition changed during read")
    return {
        "root": str(root),
        "pins": expected.copy(),
        "branches": receipt["branches"],
        "releases": releases,
    }


def _when(base: str, hours: float) -> str:
    return _time((datetime.fromisoformat(base) + timedelta(hours=hours)).isoformat())


def _scope(scenario: str, branch: str, transition: dict) -> dict:
    return {
        "schema": SCHEMA,
        "scenario": scenario,
        "branch": branch,
        "truth_class": "TRAINING_SCENARIO_ONLY",
        "sim_customer_id": "SIM-COVERED-CUSTOMER-01",
        "sim_service_id": "SIM-RESTRICTED-HOSTING-01",
        "sim_subcontractor_id": "SIM-RECOVERY-SUPPORT-01",
        "data_class": "SYNTHETIC_EPHI_ANALOG_PAYLOAD_FREE",
        "fixture_contains_real_phi": False,
        "actual_legal_applicability": "UNDETERMINED",
        "actual_sable_harbor_ba_status": "UNDETERMINED",
        "site_provider_ba_status": "UNDETERMINED_NOT_AUTOMATIC",
        "contract_spec_sha256": SOURCE_PINS[
            "enterprise/audit_suite/phi_ba_2027_contract_spec_v1.json"
        ],
        "fictional_contracting_entity_id": "SHI",
        "fictional_delegation_scope": ["SIM-BAA-CUST-01", "SIM-BAA-SUB-01"],
        "scenario_responsibilities": {
            "customer": "ASSUMED_COVERED_ENTITY_PURPOSE_AND_RIGHTS_DIRECTION",
            "sable_harbor": "ASSUMED_BA_HOSTING_SECURITY_AND_RECOVERY",
            "support_party": "ASSUMED_SUBCONTRACTOR_RECOVERY_SUPPORT",
            "site_providers": "PHYSICAL_SITE_DEPENDENCIES_ROLE_UNDETERMINED",
        },
        "transition_branch": transition["branches"][scenario],
        "transition_release_refs": transition["releases"][scenario],
        "transition_pins": transition["pins"],
        "qualification": QUALIFICATION,
    }


def _approval_steps(contract: str, start: float, before: str, after: str) -> list[tuple]:
    roles = ("LEGAL", "TECH", "SEC", "DATA")
    return [
        (
            "contract_approval",
            f"AP-{contract}-{role}",
            f"{contract}_ROLE_SIGNOFF_{role}",
            start + index / 10,
            0,
            before if index == 0 else f"{contract}_REVIEW_{roles[index - 1]}",
            after if index == len(roles) - 1 else f"{contract}_REVIEW_{role}",
        )
        for index, role in enumerate(roles)
    ]


def _plan(scenario: str, base: str) -> list[tuple]:
    common = [
        (
            "legal_decision",
            "ROLE-01",
            "SIMULATED_ROLE_DECISION",
            2,
            0,
            "SCOPE_REGISTERED",
            "ROLE_ASSUMED",
        ),
        (
            "contract_authority",
            "DA-PHI-BA-2027",
            "LIMITED_SIMULATED_DELEGATION",
            2.2,
            0,
            "ROLE_ASSUMED",
            "DELEGATED",
        ),
        *_approval_steps("CUST", 2.3, "DELEGATED", "UP_APPROVED"),
        (
            "counterparty_acceptance",
            "VA-CUST-01",
            "CUSTOMER_SCENARIO_ACCEPTANCE",
            2.7,
            0,
            "UP_APPROVED",
            "UP_ACCEPTED",
        ),
        (
            "contract_register",
            "BAA-CUST-01",
            "SIMULATED_UPSTREAM_BAA",
            3,
            0,
            "UP_ACCEPTED",
            "UPSTREAM_BAA",
        ),
    ]
    if scenario == "CLEAN":
        rest = [
            *_approval_steps("SUB", 3.2, "UPSTREAM_BAA", "DOWN_APPROVED"),
            (
                "counterparty_acceptance",
                "VA-SUB-01",
                "SUPPORT_SCENARIO_ACCEPTANCE",
                3.6,
                0,
                "DOWN_APPROVED",
                "DOWN_ACCEPTED",
            ),
            (
                "contract_register",
                "BAA-SUB-01",
                "SIMULATED_DOWNSTREAM_BAA",
                4,
                0,
                "DOWN_ACCEPTED",
                "FLOWDOWN_BAA",
            ),
            (
                "flow_register",
                "FLOW-RENO-01",
                "RENO_INTAKE_MARKER",
                5,
                0,
                "FLOWDOWN_BAA",
                "RENO_ADMITTED",
            ),
            (
                "flow_register",
                "FLOW-BOISE-01",
                "BOISE_REPLICA_ACK",
                6,
                0,
                "RENO_ADMITTED",
                "BOISE_ACKNOWLEDGED",
            ),
            (
                "flow_register",
                "FLOW-RECON-01",
                "SOURCE_DESTINATION_RECONCILE",
                7,
                0,
                "BOISE_ACKNOWLEDGED",
                "RECONCILED",
            ),
        ]
    else:
        rest = [
            (
                "flow_register",
                "FLOW-RENO-01",
                "RENO_INTAKE_MARKER",
                4,
                0,
                "UPSTREAM_BAA",
                "RENO_ADMITTED",
            ),
            (
                "flow_register",
                "FLOW-BOISE-01",
                "PREMATURE_BOISE_ROUTE_MARKER",
                5,
                0,
                "RENO_ADMITTED",
                "ROUTE_UNVERIFIED",
            ),
            (
                "exception_register",
                "EXC-01",
                "LATE_FLOWDOWN_DETECTION",
                6,
                2,
                "ROUTE_UNVERIFIED",
                "QUARANTINED",
            ),
            *_approval_steps("SUB", 9, "QUARANTINED", "QUARANTINED"),
            (
                "counterparty_acceptance",
                "VA-SUB-01",
                "LATE_SUPPORT_SCENARIO_ACCEPTANCE",
                9.5,
                0,
                "QUARANTINED",
                "QUARANTINED",
            ),
            (
                "contract_register",
                "BAA-SUB-01",
                "LATE_SIMULATED_DOWNSTREAM_BAA",
                10,
                0,
                "QUARANTINED",
                "QUARANTINED",
            ),
            (
                "flow_register",
                "FLOW-RECON-01",
                "UNVERIFIED_ACK_RECONCILE",
                11,
                0,
                "QUARANTINED",
                "QUARANTINED",
            ),
        ]
    return [
        (*step[:3], _when(base, step[3]), _when(base, step[3] + step[4]), *step[5:])
        for step in common + rest
    ]


def _check_event_gate(scenario: str, record: str, event_at: str, gate_refs: dict) -> None:
    cust_approvals = {f"AP-CUST-{role}" for role in ("LEGAL", "TECH", "SEC", "DATA")}
    sub_approvals = {f"AP-SUB-{role}" for role in ("LEGAL", "TECH", "SEC", "DATA")}
    required_by_record = {
        "DA-PHI-BA-2027": {"ROLE-01"},
        "VA-CUST-01": cust_approvals,
        "BAA-CUST-01": {"ROLE-01", "DA-PHI-BA-2027", "VA-CUST-01"} | cust_approvals,
        "VA-SUB-01": sub_approvals,
        "BAA-SUB-01": {"DA-PHI-BA-2027", "VA-SUB-01", "BAA-CUST-01"} | sub_approvals,
    }
    required = required_by_record.get(record, set())
    if record in cust_approvals:
        required |= {"ROLE-01", "DA-PHI-BA-2027"}
    elif record in sub_approvals:
        required |= {"ROLE-01", "DA-PHI-BA-2027", "BAA-CUST-01"}
    if record in {"FLOW-RENO-01", "FLOW-BOISE-01", "FLOW-RECON-01"}:
        required |= {"ROLE-01", "BAA-CUST-01"}
        if scenario == "CLEAN" or record == "FLOW-RECON-01":
            required.add("BAA-SUB-01")
        if scenario == "MESSY" and record == "FLOW-BOISE-01" and "BAA-SUB-01" in gate_refs:
            raise CompanyStoreError("Messy premature route must precede downstream terms")
    if not required <= set(gate_refs) or any(
        gate_refs[k]["effective_at"] > event_at or gate_refs[k]["available_at"] > event_at
        for k in required
    ):
        raise CompanyStoreError("Fictional flow authority not effective and available")


def _body(
    scenario: str,
    ordinal: int,
    step: tuple,
    *,
    scope_sha: str,
    previous_sha: str,
    gate_refs: dict,
    releases: dict,
    terms: dict,
) -> dict:
    system, record, action, event_at, available_at, before, after = step
    exception_open = scenario == "MESSY" and ordinal >= 10
    contract = system == "contract_register"
    flow = system == "flow_register"
    agreement_id = (
        "SIM-BAA-CUST-01" if "CUST" in record else "SIM-BAA-SUB-01" if "SUB" in record else None
    )
    actor = (
        "SH-CEO-DANIEL-MERCER"
        if system == "contract_authority"
        else "SIM-CUSTOMER-SIGNATORY-01"
        if record == "VA-CUST-01"
        else "SIM-SUPPORT-SIGNATORY-01"
        if record == "VA-SUB-01"
        else {"LEGAL": "AS-P003", "TECH": "AS-P007", "SEC": "AS-P008", "DATA": "AS-P014"}[
            record.rsplit("-", 1)[-1]
        ]
        if system == "contract_approval"
        else "AS-P003"
        if system in {"legal_decision", "exception_register"}
        else "AS-P002"
        if contract
        else "AS-P014"
    )
    return {
        "schema": SCHEMA,
        "truth_class": "TRAINING_SCENARIO_ONLY",
        "scenario": scenario,
        "sequence": ordinal,
        "system": system,
        "record": record,
        "action": action,
        "before": before,
        "after": after,
        "event_at": event_at,
        "available_at": available_at,
        "actor_id": actor,
        "actor_authority": "IN_UNIVERSE_SCENARIO_ASSUMPTION_NOT_CANON_DELEGATION",
        "contract_spec_sha256": SOURCE_PINS[
            "enterprise/audit_suite/phi_ba_2027_contract_spec_v1.json"
        ],
        "scope_sha256": scope_sha,
        "previous_sha256": previous_sha,
        "site_release_sha256": {site: ref["sha256"] for site, ref in releases.items()},
        "authorization_gate_refs": gate_refs.copy(),
        "sim_customer_id": "SIM-COVERED-CUSTOMER-01",
        "sim_service_id": "SIM-RESTRICTED-HOSTING-01",
        "sim_subcontractor_id": "SIM-RECOVERY-SUPPORT-01",
        "legal_role_decision": "BA_AND_SUBCONTRACTOR_FOR_TRAINING_ONLY"
        if system == "legal_decision"
        else None,
        "role_rationale": (
            "Assumed covered-entity customer, on-behalf-of hosting, and separate "
            "recovery-support maintenance of a payload-free analog; training only"
            if system == "legal_decision"
            else None
        ),
        "real_world_legal_approval": False,
        "actual_legal_applicability": "UNDETERMINED",
        "candidate_rule_locators": ["45-CFR-164.308(b)", "45-CFR-164.504(e)"],
        "limited_delegation_record_id": (
            "DA-PHI-BA-2027" if system == "contract_authority" else None
        ),
        "limited_delegation_scope": (
            ["SIM-BAA-CUST-01", "SIM-BAA-SUB-01"] if system == "contract_authority" else []
        ),
        "delegator_id": ("SH-CEO-DANIEL-MERCER" if system == "contract_authority" else None),
        "delegatee_id": "AS-P002" if system == "contract_authority" else None,
        "approval_reviewer_ids": [actor] if system == "contract_approval" else [],
        "approval_status": (
            "SIMULATED_ROLE_AND_CLAUSE_REVIEW_APPROVED" if system == "contract_approval" else None
        ),
        "reviewed_synthetic_terms_sha256": (
            sha(encoded(terms[agreement_id]))
            if agreement_id
            and system in {"contract_approval", "counterparty_acceptance", "contract_register"}
            else None
        ),
        "counterparty_persona_id": actor if system == "counterparty_acceptance" else None,
        "counterparty_acceptance_status": (
            "ACCEPTED_IN_TRAINING_SCENARIO_ONLY" if system == "counterparty_acceptance" else None
        ),
        "contract_id": "SIM-BAA-CUST-01"
        if record == "BAA-CUST-01"
        else "SIM-BAA-SUB-01"
        if record == "BAA-SUB-01"
        else None,
        "contract_party_ids": (
            ["SIM-COVERED-CUSTOMER-01", "SHI"]
            if record == "BAA-CUST-01"
            else ["SHI", "SIM-RECOVERY-SUPPORT-01"]
            if record == "BAA-SUB-01"
            else []
        ),
        "simulated_signer_ids": (
            ["SIM-CUSTOMER-SIGNATORY-01", "AS-P002"]
            if record == "BAA-CUST-01"
            else ["AS-P002", "SIM-SUPPORT-SIGNATORY-01"]
            if record == "BAA-SUB-01"
            else []
        ),
        "simulated_contract_effective_at": event_at if contract else None,
        "simulated_signer_authority": (
            "TRAINING_ASSUMPTION_PENDING_INDEPENDENT_REVIEW" if contract else None
        ),
        "clause_candidate_ids": list(CLAUSE_CANDIDATES) if contract else [],
        "synthetic_terms": terms[agreement_id] if contract else [],
        "contract_executed_in_simulation": contract,
        "real_signature_or_agreement": False,
        "flow_marker_id": "SIM-EHR-MARKER-001" if flow else None,
        "marker_metadata_sha256": sha(encoded({"marker": "SIM-EHR-MARKER-001", "payload_bytes": 0}))
        if flow
        else None,
        "payload_bytes": 0,
        "fixture_contains_real_phi": False,
        "site_route": "RENO_TO_BOISE_SIMULATION" if flow else None,
        "destination_ack": "SIMULATED"
        if scenario == "CLEAN" and record in {"FLOW-BOISE-01", "FLOW-RECON-01"}
        else "UNVERIFIED"
        if scenario == "MESSY" and record in {"FLOW-BOISE-01", "FLOW-RECON-01"}
        else None,
        "simulated_support_copy_acknowledgement_status": (
            "SIMULATED_ACKNOWLEDGED"
            if scenario == "CLEAN" and record in {"FLOW-BOISE-01", "FLOW-RECON-01"}
            else "NOT_ESTABLISHED"
            if scenario == "MESSY" and record in {"FLOW-BOISE-01", "FLOW-RECON-01"}
            else None
        ),
        "simulated_copy_reached_support": (
            "UNDETERMINED"
            if scenario == "MESSY" and record in {"FLOW-BOISE-01", "FLOW-RECON-01"}
            else "SIMULATED_ACK_ONLY"
            if scenario == "CLEAN" and record in {"FLOW-BOISE-01", "FLOW-RECON-01"}
            else None
        ),
        "flow_gate_disposition": (
            "ALL_SCENARIO_GATES_EFFECTIVE_AND_AVAILABLE"
            if scenario == "CLEAN" and flow
            else "UPSTREAM_ONLY_RENO_LOCAL"
            if scenario == "MESSY" and record == "FLOW-RENO-01"
            else "DOWNSTREAM_FLOWDOWN_BYPASSED"
            if scenario == "MESSY" and record == "FLOW-BOISE-01"
            else "QUARANTINED_ACK_UNVERIFIED"
            if scenario == "MESSY" and record == "FLOW-RECON-01"
            else None
        ),
        "exception_id": EXCEPTION_ID if exception_open else None,
        "exception_open": exception_open,
        "detected_at": event_at if action == "LATE_FLOWDOWN_DETECTION" else None,
        "affected_marker_id": "SIM-EHR-MARKER-001" if exception_open else None,
        "exception_cure_proposal": (
            "Quarantine route, obtain downstream terms, reconcile acknowledgements, "
            "and independently disposition exposure; late terms do not erase history"
            if exception_open
            else None
        ),
        "cure_status": "LATE_CONTRACT_DOES_NOT_RETROACTIVELY_CURE_ROUTE"
        if scenario == "MESSY" and record in {"BAA-SUB-01", "FLOW-RECON-01"}
        else None,
        "real_world_operation": False,
        "audit_task_credit": False,
        "qualification": QUALIFICATION,
    }


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def create(
    destination: Path,
    *,
    repository: Path,
    transition_root: Path,
    clean_branch: str,
    messy_branch: str,
) -> dict:
    """Create isolated source versions only after the reviewed transition is pinned."""
    destination = _new_private(destination)
    branches = {"CLEAN": _id(clean_branch), "MESSY": _id(messy_branch)}
    if branches["CLEAN"] == branches["MESSY"]:
        raise CompanyStoreError("Distinct Clean/Messy branches required")
    source_pins = _source_context(repository)
    terms = _contract_terms(repository)
    transition = _transition_context(transition_root, REVIEWED_TRANSITION_PINS)
    with tempfile.TemporaryDirectory(prefix=".phi-ba-stage-", dir=destination.parent) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records = {"CLEAN": [], "MESSY": []}
        for scenario in ("CLEAN", "MESSY"):
            branch = branches[scenario]
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            provenance = {
                "source_reference": "enterprise/audit_suite/company_phi_ba_2027_simulation.py",
                "source_pins": source_pins,
                "transition_pins": transition["pins"],
                "scenario": scenario,
                "qualification": QUALIFICATION,
            }
            base = _time(
                max(
                    transition["releases"][scenario][site]["available_at"]
                    for site in ("RENO", "BOISE")
                )
            )
            scope = _scope(scenario, branch, transition)
            scope_at = _when(base, 1)
            first = store.append_version(
                COMPANY,
                branch,
                "scenario_scope",
                "SCOPE-01",
                expected_version=0,
                command_id=f"PB-{branch}-SCOPE",
                event_at=scope_at,
                available_at=scope_at,
                content=encoded(scope),
                provenance=provenance,
            )
            records[scenario].append(first)
            prior_sha, state = first["sha256"], "SCOPE_REGISTERED"
            gate_refs = {}
            for ordinal, step in enumerate(_plan(scenario, base), 1):
                system, record, _action, event_at, available_at, before, after = step
                if before != state or event_at <= scope_at:
                    raise CompanyStoreError("Fictional flow causal chronology invalid")
                _check_event_gate(scenario, record, event_at, gate_refs)
                body = _body(
                    scenario,
                    ordinal,
                    step,
                    scope_sha=first["sha256"],
                    previous_sha=prior_sha,
                    gate_refs=gate_refs,
                    releases=transition["releases"][scenario],
                    terms=terms,
                )
                ref = store.append_version(
                    COMPANY,
                    branch,
                    system,
                    record,
                    expected_version=0,
                    command_id=f"PB-{branch}-{record}",
                    event_at=event_at,
                    available_at=available_at,
                    content=encoded(body),
                    provenance=provenance,
                )
                records[scenario].append(ref)
                if record.startswith(("AP-CUST-", "AP-SUB-")) or record in {
                    "ROLE-01",
                    "DA-PHI-BA-2027",
                    "VA-CUST-01",
                    "BAA-CUST-01",
                    "VA-SUB-01",
                    "BAA-SUB-01",
                }:
                    gate_refs[record] = {
                        "sha256": ref["sha256"],
                        "effective_at": event_at,
                        "available_at": ref["available_at"],
                    }
                prior_sha, state = ref["sha256"], after
        receipt = {
            "schema": SCHEMA,
            "status": "FICTIONAL_FUTURE_COMPANY_NATIVE_PHI_BA_FLOW_NO_AUDIT_CREDIT",
            "company": COMPANY,
            "branches": branches,
            "records": records,
            "source_pins": source_pins,
            "transition_pins": transition["pins"],
            "transition_releases": transition["releases"],
            "final_states": {"CLEAN": "RECONCILED", "MESSY": "QUARANTINED"},
            "open_exception_ids": {"CLEAN": [], "MESSY": [EXCEPTION_ID]},
            "open_exception_counts": {"CLEAN": 0, "MESSY": 1},
            "exception_event_row_counts": {"CLEAN": 0, "MESSY": 9},
            "qualification": QUALIFICATION,
            "limits": [
                "All 2027 facts are future simulation; imported_at records actual insertion.",
                "No real PHI, person payload, contract, legal role or deployment is asserted.",
                "Switch and IDACORE are site providers; no BA role is inferred.",
                "Messy acknowledgement is unverified; late terms do not cure the open exception.",
                "No audit grant, collection, workpaper, task, Key, grade or release is made.",
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


def verify(destination: Path, *, transition_root: Path, repository: Path | None = None) -> dict:
    """Reperform the exact source chain and all fictional/real-world boundaries."""
    root = _private_path(destination, directory=True)
    paths = {
        "receipt": _private_path(root / "RECEIPT.json", directory=False),
        "manifest": _private_path(root / "MANIFEST.json", directory=False),
        "database": _private_path(root / "company.sqlite3", directory=False),
    }
    initial_snapshot = _frozen_snapshot(paths)
    initial_hashes = {k: value[-1] for k, value in initial_snapshot.items()}
    manifest = json.loads(paths["manifest"].read_text())
    receipt = json.loads(paths["receipt"].read_text())
    if (
        manifest.get("schema") != SCHEMA + "_MANIFEST"
        or manifest.get("receipt_sha256") != initial_hashes["receipt"]
        or manifest.get("company_db_sha256") != initial_hashes["database"]
        or manifest.get("module_sha256") != _digest(Path(__file__))
        or manifest.get("native_version_count") != 37
        or manifest.get("audit_task_credit") is not False
        or manifest.get("status") != receipt.get("status")
    ):
        raise CompanyStoreError("Fictional flow manifest/source pin differs")
    repository = Path(repository).resolve() if repository else Path(__file__).resolve().parents[2]
    source_pins = _source_context(repository)
    terms = _contract_terms(repository)
    transition = _transition_context(transition_root, REVIEWED_TRANSITION_PINS)
    if (
        receipt.get("schema") != SCHEMA
        or receipt.get("status") != "FICTIONAL_FUTURE_COMPANY_NATIVE_PHI_BA_FLOW_NO_AUDIT_CREDIT"
        or receipt.get("company") != COMPANY
        or receipt.get("qualification") != QUALIFICATION
        or receipt.get("source_pins") != source_pins
        or receipt.get("transition_pins") != transition["pins"]
        or receipt.get("transition_releases") != transition["releases"]
        or receipt.get("final_states") != {"CLEAN": "RECONCILED", "MESSY": "QUARANTINED"}
        or receipt.get("open_exception_ids") != {"CLEAN": [], "MESSY": [EXCEPTION_ID]}
        or receipt.get("open_exception_counts") != {"CLEAN": 0, "MESSY": 1}
        or receipt.get("exception_event_row_counts") != {"CLEAN": 0, "MESSY": 9}
        or set(receipt.get("branches", {})) != {"CLEAN", "MESSY"}
        or receipt["branches"]["CLEAN"] == receipt["branches"]["MESSY"]
    ):
        raise CompanyStoreError("Fictional flow scope/exception receipt differs")
    with closing(
        sqlite3.connect(paths["database"].as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Fictional flow source integrity failure")
        if (
            db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != 37
            or db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] != 0
            or db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] != 0
        ):
            raise CompanyStoreError("Fictional flow count or audit access differs")
        expected_systems = {
            (COMPANY, branch, system, owner)
            for branch in receipt["branches"].values()
            for system, owner in SYSTEM_OWNERS.items()
        }
        systems = {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        }
        if systems != expected_systems:
            raise CompanyStoreError("Fictional source system custody differs")
        for scenario in ("CLEAN", "MESSY"):
            branch = _id(receipt["branches"][scenario])
            refs = receipt["records"][scenario]
            releases = transition["releases"][scenario]
            base = _time(max(releases[site]["available_at"] for site in ("RENO", "BOISE")))
            steps = _plan(scenario, base)
            if len(refs) != 1 + len(steps):
                raise CompanyStoreError("Incomplete fictional source chain")
            state, prior_sha = "SCOPE_REGISTERED", None
            gate_refs = {}
            seen_exception_rows = []
            provenance = {
                "source_reference": "enterprise/audit_suite/company_phi_ba_2027_simulation.py",
                "source_pins": source_pins,
                "transition_pins": transition["pins"],
                "scenario": scenario,
                "qualification": QUALIFICATION,
            }
            for index, ref in enumerate(refs):
                if index == 0:
                    system, record, event_at = "scenario_scope", "SCOPE-01", _when(base, 1)
                    expected_body = _scope(scenario, branch, transition)
                    command = f"PB-{branch}-SCOPE"
                else:
                    step = steps[index - 1]
                    system, record, _action, event_at, available_at, before, after = step
                    if before != state:
                        raise CompanyStoreError("Causal fictional state differs")
                    _check_event_gate(scenario, record, event_at, gate_refs)
                    expected_body = _body(
                        scenario,
                        index,
                        step,
                        scope_sha=refs[0]["sha256"],
                        previous_sha=prior_sha,
                        gate_refs=gate_refs,
                        releases=releases,
                        terms=terms,
                    )
                    command = f"PB-{branch}-{record}"
                    state = after
                    if expected_body["exception_open"]:
                        seen_exception_rows.append(expected_body["exception_id"])
                if (
                    ref["company"],
                    ref["branch"],
                    ref["system"],
                    ref["record"],
                    ref["version"],
                ) != (COMPANY, branch, system, record, 1):
                    raise CompanyStoreError("Fictional native identity differs")
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=1",
                    (COMPANY, branch, system, record),
                ).fetchone()
                if (
                    row is None
                    or row["command_id"] != command
                    or row["sha256"] != ref["sha256"]
                    or sha(row["content"]) != ref["sha256"]
                    or json.loads(row["content"]) != expected_body
                    or row["event_at"] != event_at
                    or row["available_at"] != (event_at if index == 0 else available_at)
                    or row["available_at"] < row["event_at"]
                    or row["event_at"] <= base
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or json.loads(row["provenance"]) != provenance
                    or ref["provenance"] != provenance
                    or (ref["event_at"], ref["available_at"], ref["imported_at"])
                    != (row["event_at"], row["available_at"], row["imported_at"])
                    or _time(row["imported_at"]) != row["imported_at"]
                ):
                    raise CompanyStoreError("Fictional source row/provenance/clock differs")
                if record.startswith(("AP-CUST-", "AP-SUB-")) or record in {
                    "ROLE-01",
                    "DA-PHI-BA-2027",
                    "VA-CUST-01",
                    "BAA-CUST-01",
                    "VA-SUB-01",
                    "BAA-SUB-01",
                }:
                    gate_refs[record] = {
                        "sha256": row["sha256"],
                        "effective_at": event_at,
                        "available_at": row["available_at"],
                    }
                prior_sha = row["sha256"]
            if state != receipt["final_states"][scenario]:
                raise CompanyStoreError("Fictional final state differs")
            if (
                len(seen_exception_rows) != receipt["exception_event_row_counts"][scenario]
                or sorted(set(seen_exception_rows)) != receipt["open_exception_ids"][scenario]
            ):
                raise CompanyStoreError("Distinct exception/event-row counts differ")
    if _frozen_snapshot(paths) != initial_snapshot:
        raise CompanyStoreError("Fictional native source changed during verification")
    return manifest
