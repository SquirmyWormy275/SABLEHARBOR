"""Fictional 2027 company-owned provider register; no vendor or audit assertion."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import tempfile
from contextlib import closing
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _id, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_PROVIDER_LIFECYCLE_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
QUALIFICATION = "FUTURE_TRAINING_WORLD_INTERNAL_PROVIDER_RECORD_NO_REAL_OPERATION"
STATUS = "FICTIONAL_FUTURE_PROVIDER_LIFECYCLE_NO_AUDIT_CREDIT"
LIMITS = [
    "All 2027 source events are future training-world chronology; "
    "imported_at is actual authoring time.",
    "No real provider operation, signature, external request/response, PHI "
    "or legal applicability asserted.",
    "Messy support omission remains open after backfill and is distinct from BA late flowdown.",
    "No audit grant, collection, workpaper, task credit, Key, Atlas or active-pair change.",
]
EXCEPTION_ID = "EXC-SIM-PROVIDER-SUPPORT-OMISSION-01"
BA_EXCEPTION_ID = "EXC-SIM-BA-FLOWDOWN-01"
SOURCE_REFERENCE = "enterprise/audit_suite/company_provider_lifecycle_2027_simulation.py"
SOURCE_PINS = {
    ("docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md"): (
        "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496"
    ),
    ("enterprise/services/source/runtime_sites_2026-09-11.json"): (
        "fa216f629762503865fd9f1a3207e87691cd484cec9885bf25ce045b4525519c"
    ),
    ("enterprise/audit_suite/PROVIDER_BA_85_ROUTE_DELTA_PLAN.md"): (
        "7fae68a26ebc650f05ac8af1430f3e4949dcb7c372049c20e05d68c182999d5d"
    ),
    ("enterprise/audit_suite/provider_ba_85_candidate_routes_v1.json"): (
        "789f0a747255b63abe170403db06f6a1770f73888a44501d4434d305999f803f"
    ),
}
UPSTREAM = {
    "TRANSITION_V3": {
        "schema": "SH_FICTIONAL_2027_RUNTIME_TRANSITION_V3",
        "receipt": "0a0a448f619e490870f69959d196eb6d5ca3747af0d4fb68056195910ce6cc11",
        "manifest": "f7c6ec3ab460f204f69cf6b50df66399687034b3b63cb38aaee84841daedcbd4",
        "database": "428b5c740cb8fc627b38f2aa6847e450fd166e62be52a6309d4f5a7b284988fd",
        "independent_review": "f1acaeaea963055f99b0de120fd1b0347ee984edf085d353e7af1e427234d5a9",
    },
    "PHI_BA_V1": {
        "schema": "SH_FICTIONAL_2027_PHI_BA_FLOW_V1",
        "receipt": "20e3762aabb45fcfa3107d695da37e7eeb677f6c5e98f1bb767fa463fe857d9d",
        "manifest": "8226ac2031cafe581289afb4c25088c8dfe603e75ac11fc1ababfe2590f2a5f2",
        "database": "ad252e8cb6b1309b238fbe50daac541d67b5fa89051a0b3d8eab7993d4010449",
        "independent_review": "39bb9b071179ed672c5cf07c2867285d36b2f3e8cdce2106dc4472d17047911e",
    },
}
SYSTEM_OWNERS = {
    "scenario_scope": "AS-P013",
    "relationship_register": "AS-P013",
    "obligation_calendar": "AS-P013",
    "population_reconcile": "AS-P014",
    "exception_register": "AS-P013",
    "review_register": "AS-P013",
}
RELATIONSHIPS = {
    "RENO": {
        "provider_id": "CP-SWITCH",
        "role": "SIMULATED_PRIMARY_FACILITY_PROVIDER",
        "tier": "SCENARIO_CRITICAL_PRIMARY_SITE_DEPENDENCY",
        "data_boundary": (
            "FACILITY_POWER_COOLING_PHYSICAL_ACCESS_NO_EPHI_PROCESSING_BY_SITE_CONTRACT"
        ),
        "review_owner": "AS-P013",
        "canon_site_id": "RUNTIME-RENO-COLO",
    },
    "BOISE": {
        "provider_id": "CP-IDACORE",
        "role": "SIMULATED_RECOVERY_FACILITY_PROVIDER",
        "tier": "SCENARIO_CRITICAL_RECOVERY_SITE_DEPENDENCY",
        "data_boundary": (
            "FACILITY_POWER_COOLING_PHYSICAL_ACCESS_NO_EPHI_PROCESSING_BY_SITE_CONTRACT"
        ),
        "review_owner": "AS-P013",
        "canon_site_id": "RUNTIME-BOISE-DR",
    },
    "SUPPORT": {
        "provider_id": "SIM-RECOVERY-SUPPORT-01",
        "role": "FICTIONAL_BA_SUBCONTRACTOR_RECOVERY_MARKER_ONLY",
        "tier": "SCENARIO_SENSITIVE_SUPPORT_DEPENDENCY",
        "data_boundary": "PAYLOAD_FREE_SYNTHETIC_MARKER_ONLY_ACTUAL_PHI_UNASSERTED",
        "review_owner": "AS-P003",
        "canon_site_id": None,
    },
}
INITIAL_AT = "2027-09-15T08:00:00+00:00"
RECON_AT = "2027-09-16T09:00:00+00:00"
REVIEW_DUE = "2027-10-31T23:00:00+00:00"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private(path: Path, *, directory: bool) -> Path:
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise CompanyStoreError("Private nonsymlink source path required")
    info = path.stat()
    if directory:
        if not path.is_dir() or info.st_mode & 0o077:
            raise CompanyStoreError("Private directory required")
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077:
        raise CompanyStoreError("Private regular source file required")
    return path


def _frozen(paths: dict[str, Path]) -> dict[str, tuple]:
    database = paths["database"]
    if any(
        Path(str(database) + suffix).exists() or Path(str(database) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Frozen company source must have no sidecars")
    snapshot = {}
    for name, path in paths.items():
        _private(path, directory=False)
        info = path.stat()
        snapshot[name] = (
            info.st_dev,
            info.st_ino,
            stat.S_IMODE(info.st_mode),
            info.st_size,
            info.st_mtime_ns,
            _digest(path),
        )
    return snapshot


def _read_upstream(root: Path, expected: dict) -> dict:
    root = _private(root, directory=True)
    paths = {
        key: root / name
        for key, name in {
            "receipt": "RECEIPT.json",
            "manifest": "MANIFEST.json",
            "database": "company.sqlite3",
        }.items()
    }
    before = _frozen(paths)
    if any(before[key][-1] != expected[key] for key in paths):
        raise CompanyStoreError("Independently reviewed upstream bytes differ")
    receipt = json.loads(paths["receipt"].read_text())
    manifest = json.loads(paths["manifest"].read_text())
    if (
        receipt.get("schema") != expected["schema"]
        or manifest.get("schema") != expected["schema"] + "_MANIFEST"
        or manifest.get("receipt_sha256") != expected["receipt"]
        or manifest.get("company_db_sha256") != expected["database"]
        or manifest.get("audit_task_credit") is not False
        or receipt.get("company") != COMPANY
        or set(receipt.get("branches", {})) != {"CLEAN", "MESSY"}
        or receipt.get("source_pins", {}).get(
            "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md"
        )
        != SOURCE_PINS[
            "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md"
        ]
    ):
        raise CompanyStoreError("Reviewed upstream schema/scope differs")
    selected = {}
    with closing(
        sqlite3.connect(paths["database"].as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Upstream database integrity differs")
        if any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections")
        ):
            raise CompanyStoreError("Upstream source contains audit access or collection")
        for scenario in ("CLEAN", "MESSY"):
            branch = _id(receipt["branches"][scenario])
            selected[scenario] = {}
            for ref in receipt["records"][scenario]:
                key = (ref["system"], ref["record"], ref["version"])
                if key in selected[scenario]:
                    raise CompanyStoreError("Duplicate upstream native tuple")
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    (COMPANY, branch, *key),
                ).fetchone()
                if (
                    row is None
                    or ref["company"] != COMPANY
                    or ref["branch"] != branch
                    or row["sha256"] != ref["sha256"]
                    or sha(row["content"]) != ref["sha256"]
                    or (row["event_at"], row["available_at"], row["imported_at"])
                    != (ref["event_at"], ref["available_at"], ref["imported_at"])
                    or row["available_at"] < row["event_at"]
                ):
                    raise CompanyStoreError("Reviewed upstream receipt/native tuple differs")
                selected[scenario][key] = {"ref": ref, "body": json.loads(row["content"])}
    if _frozen(paths) != before:
        raise CompanyStoreError("Reviewed upstream changed during read")
    return {
        "receipt": receipt,
        "selected": selected,
        "pins": {k: expected[k] for k in ("receipt", "manifest", "database")},
    }


def _at(source: dict, scenario: str, system: str, record: str) -> dict:
    try:
        return source["selected"][scenario][(system, record, 1)]
    except KeyError as error:
        raise CompanyStoreError("Required upstream native source tuple missing") from error


def _source_context(repository: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    for name, expected in SOURCE_PINS.items():
        path = repository / name
        if not path.is_file() or path.is_symlink() or _digest(path) != expected:
            raise CompanyStoreError("Canon or reviewed provider plan pin differs")
    sites = json.loads(
        (repository / "enterprise/services/source/runtime_sites_2026-09-11.json").read_text()
    )["sites"]
    for key in ("RENO", "BOISE"):
        rel = RELATIONSHIPS[key]
        matching = [x for x in sites if x["id"] == rel["canon_site_id"]]
        if len(matching) != 1 or (
            matching[0]["provider_id"] != rel["provider_id"]
            or matching[0]["status"] != "PROVIDER_SELECTED_PROCUREMENT_PENDING"
            or matching[0]["contract_executed"] is not False
            or matching[0]["operating"] is not False
        ):
            raise CompanyStoreError("2026 planned site/provider boundary differs")
    plan = json.loads(
        (repository / "enterprise/audit_suite/provider_ba_85_candidate_routes_v1.json").read_text()
    )
    if (
        plan.get("schema") != "SH_PROVIDER_BA_85_CANDIDATE_ROUTE_MAP_V1"
        or plan.get("counts", {}).get("per_side") != 85
    ):
        raise CompanyStoreError("Reviewed provider plan scope differs")
    return SOURCE_PINS.copy()


def _input_context(repository: Path, transition_root: Path, phi_root: Path) -> dict:
    pins = _source_context(repository)
    trans = _read_upstream(transition_root, UPSTREAM["TRANSITION_V3"])
    phi = _read_upstream(phi_root, UPSTREAM["PHI_BA_V1"])
    if phi["receipt"].get("transition_pins") != trans["pins"] or phi["receipt"].get(
        "open_exception_ids"
    ) != {"CLEAN": [], "MESSY": [BA_EXCEPTION_ID]}:
        raise CompanyStoreError("BA flow/transition dependency or distinct BA exception differs")
    chosen = {}
    for scenario in ("CLEAN", "MESSY"):
        chosen[scenario] = {}
        for key in ("RENO", "BOISE"):
            contract = _at(trans, scenario, "provider_contract", f"C-{key}")
            release = _at(trans, scenario, "site_release", f"RL-{key}")
            provider_id = RELATIONSHIPS[key]["provider_id"]
            cb, rb = contract["body"], release["body"]
            if (
                cb.get("status") != "EXECUTED_SIMULATED"
                or cb.get("site", {}).get("provider_id") != provider_id
                or cb.get("fictional_executed_terms", {})
                .get("master_terms", {})
                .get("ephi_processing")
                != "NOT_AUTHORIZED_BY_THIS_CONTRACT"
                or cb.get("real_external_signature") is not False
                or cb.get("real_world_provider_operation") is not False
                or rb.get("site", {}).get("provider_id") != provider_id
                or rb.get("fictional_in_universe_operating_release") is not True
                or rb.get("real_world_provider_operation") is not False
                or rb.get("actual_real_world_phi_processing") is not False
                or release["ref"]["available_at"] < contract["ref"]["available_at"]
            ):
                raise CompanyStoreError("Site contract/release boundary differs")
            chosen[scenario][key] = {"contract": contract, "release": release}
        scope = _at(phi, scenario, "scenario_scope", "SCOPE-01")
        role = _at(phi, scenario, "legal_decision", "ROLE-01")
        upstream_baa = _at(phi, scenario, "contract_register", "BAA-CUST-01")
        downstream_baa = _at(phi, scenario, "contract_register", "BAA-SUB-01")
        flow = _at(phi, scenario, "flow_register", "FLOW-BOISE-01")
        if (
            scope["body"].get("sim_subcontractor_id") != RELATIONSHIPS["SUPPORT"]["provider_id"]
            or scope["body"].get("actual_legal_applicability") != "UNDETERMINED"
            or scope["body"].get("fixture_contains_real_phi") is not False
            or role["body"].get("legal_role_decision") != "BA_AND_SUBCONTRACTOR_FOR_TRAINING_ONLY"
            or role["body"].get("real_world_legal_approval") is not False
            or downstream_baa["body"].get("contract_id") != "SIM-BAA-SUB-01"
            or upstream_baa["body"].get("contract_id") != "SIM-BAA-CUST-01"
            or any(
                x["body"].get("real_signature_or_agreement") is not False
                for x in (upstream_baa, downstream_baa)
            )
            or any(
                x["body"].get("contract_executed_in_simulation") is not True
                for x in (upstream_baa, downstream_baa)
            )
            or flow["body"].get("sim_subcontractor_id") != RELATIONSHIPS["SUPPORT"]["provider_id"]
            or flow["body"].get("payload_bytes") != 0
            or flow["body"].get("fixture_contains_real_phi") is not False
            or flow["body"].get("simulated_copy_reached_support")
            != ("SIMULATED_ACK_ONLY" if scenario == "CLEAN" else "UNDETERMINED")
        ):
            raise CompanyStoreError("Synthetic BA role/terms/flow boundary differs")
        chosen[scenario]["SUPPORT"] = {
            "scope": scope,
            "role": role,
            "upstream_baa": upstream_baa,
            "contract": downstream_baa,
            "flow": flow,
        }
        if scenario == "MESSY":
            exception = _at(phi, scenario, "exception_register", "EXC-01")
            if (
                exception["body"].get("exception_id") != BA_EXCEPTION_ID
                or exception["body"].get("exception_open") is not True
            ):
                raise CompanyStoreError("Upstream BA flowdown exception differs")
            chosen[scenario]["SUPPORT"]["ba_exception"] = exception
        selected_refs = [
            item["ref"] for relation in chosen[scenario].values() for item in relation.values()
        ]
        if any(ref["available_at"] >= _time(INITIAL_AT) for ref in selected_refs):
            raise CompanyStoreError("Provider lifecycle must follow all reviewed upstream sources")
        for site in ("RENO", "BOISE"):
            if (
                phi["receipt"]["transition_releases"][scenario][site]["sha256"]
                != chosen[scenario][site]["release"]["ref"]["sha256"]
            ):
                raise CompanyStoreError("BA flow does not pin selected native site release")
    return {
        "source_pins": pins,
        "upstream_pins": {"TRANSITION_V3": trans["pins"], "PHI_BA_V1": phi["pins"]},
        "upstream_branches": {
            "TRANSITION_V3": trans["receipt"]["branches"],
            "PHI_BA_V1": phi["receipt"]["branches"],
        },
        "chosen": chosen,
    }


def _ref(item: dict) -> dict:
    ref = item["ref"]
    return {
        key: ref[key]
        for key in (
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
    }


def _obligations(key: str, relation: dict) -> list[dict]:
    body = relation["contract"]["body"]
    if key == "SUPPORT":
        return [
            {
                "id": x["clause_candidate_id"],
                "source_obligation": x["scenario_obligation"],
                "source_contract_sha256": relation["contract"]["ref"]["sha256"],
            }
            for x in body["synthetic_terms"]
        ]
    terms = body["fictional_executed_terms"]["master_terms"]
    return [
        {
            "id": "facility_service",
            "source_obligation": terms["service"],
            "source_contract_sha256": relation["contract"]["ref"]["sha256"],
        },
        {
            "id": "site_incident_notice_hours",
            "source_obligation": terms["provider_incident_notice_hours"],
            "source_contract_sha256": relation["contract"]["ref"]["sha256"],
        },
        {
            "id": "security_report_frequency",
            "source_obligation": terms["provider_security_report_frequency"],
            "source_contract_sha256": relation["contract"]["ref"]["sha256"],
        },
        {
            "id": "exit_notice_days",
            "source_obligation": terms["exit_notice_days"],
            "source_contract_sha256": relation["contract"]["ref"]["sha256"],
        },
        {
            "id": "ephi_processing",
            "source_obligation": terms["ephi_processing"],
            "source_contract_sha256": relation["contract"]["ref"]["sha256"],
        },
    ]


def _expected_rows(context: dict, scenario: str, branch: str) -> list[dict]:
    chosen = context["chosen"][scenario]
    rows: list[dict] = []
    previous_sha = None
    relationship_sha = {}
    calendar_sha = {}
    exception_sha = None

    def emit(
        system: str, record: str, version: int, event: str, available: str, fields: dict
    ) -> str:
        nonlocal previous_sha
        event, available = _time(event), _time(available)
        if available < event or (rows and event < rows[-1]["event_at"]):
            raise CompanyStoreError("Provider lifecycle event/availability chronology invalid")
        body = {
            "schema": SCHEMA,
            "truth_class": "TRAINING_SCENARIO_ONLY",
            "scenario": scenario,
            "branch": branch,
            "system": system,
            "record": record,
            "version": version,
            "event_at": event,
            "available_at": available,
            "previous_sha256": previous_sha,
            "source_pins": context["source_pins"],
            "upstream_pins": context["upstream_pins"],
            "real_world_provider_operation": False,
            "actual_real_world_phi_processing": False,
            "actual_legal_applicability": "UNDETERMINED",
            "real_external_representation": False,
            "external_request_sent": False,
            "external_response_received": False,
            "audit_task_credit": False,
            "qualification": QUALIFICATION,
            **fields,
        }
        content = encoded(body)
        digest = sha(content)
        rows.append(
            {
                "system": system,
                "record": record,
                "version": version,
                "event_at": event,
                "available_at": available,
                "body": body,
                "sha256": digest,
            }
        )
        previous_sha = digest
        return digest

    emit(
        "scenario_scope",
        "SCOPE-01",
        1,
        INITIAL_AT,
        INITIAL_AT,
        {
            "declared_relationship_ids": [
                RELATIONSHIPS[k]["provider_id"] for k in ("RENO", "BOISE", "SUPPORT")
            ],
            "upstream_branch_ids": {
                k: v[scenario] for k, v in context["upstream_branches"].items()
            },
            "provider_population_basis": "INDEPENDENT_SITE_CONTRACTS_AND_BA_FLOW_NOT_VENDOR_LIST",
            "simulated_selected_period": "2027-01-01_TO_2027-12-31",
            "actual_2027_operation_as_of_authoring": False,
        },
    )
    first = ("RENO", "BOISE", "SUPPORT") if scenario == "CLEAN" else ("RENO", "BOISE")

    def relationship(key: str, event: str, available: str, *, backfill: bool = False) -> None:
        rel = RELATIONSHIPS[key]
        upstream = chosen[key]
        refs = {name: _ref(item) for name, item in upstream.items()}
        relationship_sha[key] = emit(
            "relationship_register",
            f"REL-{key}",
            1,
            event,
            available,
            {
                "provider_id": rel["provider_id"],
                "scenario_role": rel["role"],
                "scenario_tier": rel["tier"],
                "tier_rationale": "PRIMARY_OR_RECOVERY_SITE_DEPENDENCY"
                if key != "SUPPORT"
                else "DISTINCT_RECOVERY_MARKER_SUPPORT_CHAIN",
                "data_access_boundary": rel["data_boundary"],
                "review_owner_id": rel["review_owner"],
                "canon_2026_site_status": "PROVIDER_SELECTED_PROCUREMENT_PENDING"
                if key != "SUPPORT"
                else "NOT_IN_2026_SITE_CANON",
                "canon_site_id": rel["canon_site_id"],
                "upstream_native_refs": refs,
                "entry_reason": "LATE_BACKFILL_FROM_INDEPENDENT_FLOW_RECONCILIATION"
                if backfill
                else "INITIAL_INTERNAL_REGISTER",
                "population_exception_id": EXCEPTION_ID if backfill else None,
                "actual_provider_assurance_received": False,
            },
        )
        calendar_sha[key] = emit(
            "obligation_calendar",
            f"CAL-{key}",
            1,
            event,
            available,
            {
                "provider_id": rel["provider_id"],
                "relationship_sha256": relationship_sha[key],
                "source_contract_ref": _ref(upstream["contract"]),
                "obligations": _obligations(key, upstream),
                "internal_review_due_at": _time(REVIEW_DUE),
                "external_assurance_status": "NOT_REQUESTED_NOT_RECEIVED",
                "offboarding_status": "TERMS_INDEXED_NO_OFFBOARDING_EVENT",
            },
        )

    relationship("RENO", "2027-09-15T09:00:00+00:00", "2027-09-15T09:00:00+00:00")
    relationship("BOISE", "2027-09-15T10:00:00+00:00", "2027-09-15T10:00:00+00:00")
    if scenario == "CLEAN":
        relationship("SUPPORT", "2027-09-15T11:00:00+00:00", "2027-09-15T11:00:00+00:00")
    observed = [RELATIONSHIPS[k]["provider_id"] for k in first]
    expected = [RELATIONSHIPS[k]["provider_id"] for k in ("RENO", "BOISE", "SUPPORT")]
    reconcile_sha = emit(
        "population_reconcile",
        "POP-Q3-01",
        1,
        RECON_AT,
        RECON_AT if scenario == "CLEAN" else "2027-09-18T09:00:00+00:00",
        {
            "expected_provider_ids": expected,
            "initial_registered_provider_ids": observed,
            "missing_provider_ids": sorted(set(expected) - set(observed)),
            "independent_expected_source_refs": {
                "RENO": _ref(chosen["RENO"]["contract"]),
                "BOISE": _ref(chosen["BOISE"]["contract"]),
                "SUPPORT_SCOPE": _ref(chosen["SUPPORT"]["scope"]),
                "SUPPORT_FLOW": _ref(chosen["SUPPORT"]["flow"]),
            },
            "discovery_method": "SOURCE_CONTRACT_AND_FLOW_JOIN_INDEPENDENT_OF_REGISTER",
            "population_exception_id": EXCEPTION_ID if scenario == "MESSY" else None,
            "ba_late_flowdown_exception_id": BA_EXCEPTION_ID if scenario == "MESSY" else None,
            "ba_exception_is_distinct": True,
        },
    )
    if scenario == "MESSY":
        exception_sha = emit(
            "exception_register",
            "EXC-SUPPORT-OMISSION",
            1,
            "2027-09-18T10:00:00+00:00",
            "2027-09-18T10:00:00+00:00",
            {
                "exception_id": EXCEPTION_ID,
                "status": "OPEN",
                "detected_at": _time(RECON_AT),
                "detected_available_at": _time("2027-09-18T09:00:00+00:00"),
                "reconcile_sha256": reconcile_sha,
                "missing_provider_id": RELATIONSHIPS["SUPPORT"]["provider_id"],
                "independent_flow_ref": _ref(chosen["SUPPORT"]["flow"]),
                "ba_late_flowdown_exception_id": BA_EXCEPTION_ID,
                "distinct_from_ba_exception": True,
                "cure_plan": (
                    "BACKFILL_REGISTER_AND_CALENDAR_PRESERVE_HISTORICAL_OMISSION_REVIEW_ROOT_CAUSE"
                ),
                "external_assurance_status": "NOT_REQUESTED_NOT_RECEIVED",
            },
        )
        relationship(
            "SUPPORT", "2027-09-20T09:00:00+00:00", "2027-09-22T09:00:00+00:00", backfill=True
        )
    for index, key in enumerate(("RENO", "BOISE", "SUPPORT")):
        event = f"2027-10-15T{12 + index:02d}:00:00+00:00"
        rel = RELATIONSHIPS[key]
        emit(
            "review_register",
            f"RV-{key}-Q4",
            1,
            event,
            event,
            {
                "provider_id": rel["provider_id"],
                "quarter": "2027-Q4",
                "relationship_sha256": relationship_sha[key],
                "calendar_sha256": calendar_sha[key],
                "review_owner_id": rel["review_owner"],
                "review_due_at": _time(REVIEW_DUE),
                "internal_checks": [
                    {"id": "relationship_population", "result": "SCENARIO_SOURCE_JOIN_CHECKED"},
                    {"id": "contract_scope_and_role", "result": "SCENARIO_SOURCE_JOIN_CHECKED"},
                    {"id": "obligation_calendar", "result": "SCENARIO_SOURCE_JOIN_CHECKED"},
                ],
                "obligation_checks": [
                    {
                        "obligation_id": obligation["id"],
                        "source_contract_sha256": obligation["source_contract_sha256"],
                        "internal_result": "SOURCE_TERM_INDEXED_ONLY",
                        "external_performance_state": "NOT_VERIFIED",
                    }
                    for obligation in _obligations(key, chosen[key])
                ],
                "external_assurance_request_status": "NOT_SENT_NOT_RECEIVED",
                "vendor_report_or_representation": "NONE",
                "real_world_review_approval": False,
                "offboarding_readiness": "TERMS_INDEXED_ONLY_NO_ACTUAL_OFFBOARDING",
                "historical_population_exception_id": EXCEPTION_ID
                if scenario == "MESSY" and key == "SUPPORT"
                else None,
                "upstream_ba_exception_id": BA_EXCEPTION_ID
                if scenario == "MESSY" and key == "SUPPORT"
                else None,
                "review_disposition": (
                    "INTERNAL_SCENARIO_CHECK_ONLY_EXTERNAL_AND_REAL_WORLD_GAPS_OPEN"
                ),
            },
        )
    if scenario == "MESSY":
        emit(
            "exception_register",
            "EXC-SUPPORT-OMISSION",
            2,
            "2027-10-20T10:00:00+00:00",
            "2027-10-20T10:00:00+00:00",
            {
                "exception_id": EXCEPTION_ID,
                "status": "OPEN",
                "prior_exception_sha256": exception_sha,
                "support_relationship_sha256": relationship_sha["SUPPORT"],
                "backfill_available_at": _time("2027-09-22T09:00:00+00:00"),
                "historical_omission_not_retroactively_cured": True,
                "ba_late_flowdown_exception_id": BA_EXCEPTION_ID,
                "distinct_from_ba_exception": True,
                "external_assurance_status": "NOT_REQUESTED_NOT_RECEIVED",
            },
        )
    return rows


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
    phi_root: Path,
    clean_branch: str,
    messy_branch: str,
) -> dict:
    destination = Path(destination).absolute()
    _private(destination.parent, directory=True)
    if destination.exists() or destination.is_symlink() or destination != destination.resolve():
        raise CompanyStoreError("New canonical destination required")
    branches = {"CLEAN": _id(clean_branch), "MESSY": _id(messy_branch)}
    if branches["CLEAN"] == branches["MESSY"]:
        raise CompanyStoreError("Distinct lifecycle branches required")
    context = _input_context(repository, transition_root, phi_root)
    with tempfile.TemporaryDirectory(
        prefix=".provider-lifecycle-stage-", dir=destination.parent
    ) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records = {"CLEAN": [], "MESSY": []}
        for scenario in ("CLEAN", "MESSY"):
            branch = branches[scenario]
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            provenance = {
                "source_reference": SOURCE_REFERENCE,
                "source_pins": context["source_pins"],
                "upstream_pins": context["upstream_pins"],
                "scenario": scenario,
                "qualification": QUALIFICATION,
            }
            for item in _expected_rows(context, scenario, branch):
                ref = store.append_version(
                    COMPANY,
                    branch,
                    item["system"],
                    item["record"],
                    expected_version=item["version"] - 1,
                    command_id=f"PL-{branch}-{item['system']}-{item['record']}-V{item['version']}",
                    event_at=item["event_at"],
                    available_at=item["available_at"],
                    content=encoded(item["body"]),
                    provenance=provenance,
                )
                if ref["sha256"] != item["sha256"]:
                    raise CompanyStoreError("Lifecycle source serialization differs")
                records[scenario].append(ref)
        receipt = {
            "schema": SCHEMA,
            "status": STATUS,
            "company": COMPANY,
            "branches": branches,
            "records": records,
            "source_pins": context["source_pins"],
            "upstream_pins": context["upstream_pins"],
            "upstream_branches": context["upstream_branches"],
            "expected_relationship_ids": [
                RELATIONSHIPS[k]["provider_id"] for k in ("RENO", "BOISE", "SUPPORT")
            ],
            "initial_relationship_counts": {"CLEAN": 3, "MESSY": 2},
            "final_relationship_counts": {"CLEAN": 3, "MESSY": 3},
            "q4_internal_review_counts": {"CLEAN": 3, "MESSY": 3},
            "open_exception_ids": {"CLEAN": [], "MESSY": [EXCEPTION_ID]},
            "open_exception_counts": {"CLEAN": 0, "MESSY": 1},
            "exception_event_row_counts": {"CLEAN": 0, "MESSY": 2},
            "separate_upstream_ba_exception_id": BA_EXCEPTION_ID,
            "qualification": QUALIFICATION,
            "limits": LIMITS,
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


def verify(destination: Path, *, repository: Path, transition_root: Path, phi_root: Path) -> dict:
    root = _private(destination, directory=True)
    paths = {
        key: root / name
        for key, name in {
            "receipt": "RECEIPT.json",
            "manifest": "MANIFEST.json",
            "database": "company.sqlite3",
        }.items()
    }
    before = _frozen(paths)
    receipt = json.loads(paths["receipt"].read_text())
    manifest = json.loads(paths["manifest"].read_text())
    context = _input_context(repository, transition_root, phi_root)
    if (
        manifest.get("schema") != SCHEMA + "_MANIFEST"
        or manifest.get("status") != STATUS
        or manifest.get("receipt_sha256") != before["receipt"][-1]
        or manifest.get("company_db_sha256") != before["database"][-1]
        or manifest.get("module_sha256") != _digest(Path(__file__))
        or manifest.get("audit_task_credit") is not False
        or manifest.get("native_version_count") != 24
        or receipt.get("schema") != SCHEMA
        or receipt.get("status") != STATUS
        or receipt.get("company") != COMPANY
        or receipt.get("source_pins") != context["source_pins"]
        or receipt.get("upstream_pins") != context["upstream_pins"]
        or receipt.get("upstream_branches") != context["upstream_branches"]
        or receipt.get("expected_relationship_ids")
        != [RELATIONSHIPS[k]["provider_id"] for k in ("RENO", "BOISE", "SUPPORT")]
        or receipt.get("initial_relationship_counts") != {"CLEAN": 3, "MESSY": 2}
        or receipt.get("final_relationship_counts") != {"CLEAN": 3, "MESSY": 3}
        or receipt.get("q4_internal_review_counts") != {"CLEAN": 3, "MESSY": 3}
        or receipt.get("open_exception_ids") != {"CLEAN": [], "MESSY": [EXCEPTION_ID]}
        or receipt.get("open_exception_counts") != {"CLEAN": 0, "MESSY": 1}
        or receipt.get("exception_event_row_counts") != {"CLEAN": 0, "MESSY": 2}
        or receipt.get("separate_upstream_ba_exception_id") != BA_EXCEPTION_ID
        or receipt.get("qualification") != QUALIFICATION
        or receipt.get("limits") != LIMITS
        or set(receipt.get("branches", {})) != {"CLEAN", "MESSY"}
        or set(receipt.get("records", {})) != {"CLEAN", "MESSY"}
        or receipt["branches"]["CLEAN"] == receipt["branches"]["MESSY"]
    ):
        raise CompanyStoreError("Lifecycle receipt/manifest scope differs")
    with closing(
        sqlite3.connect(paths["database"].as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Lifecycle database integrity differs")
        if (
            db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != 24
            or db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] != 0
            or db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] != 0
        ):
            raise CompanyStoreError("Lifecycle source count or audit access differs")
        expected_systems = {
            (COMPANY, branch, system, owner)
            for branch in receipt["branches"].values()
            for system, owner in SYSTEM_OWNERS.items()
        }
        if {
            tuple(row) for row in db.execute("SELECT company,branch,system,owner FROM systems")
        } != expected_systems:
            raise CompanyStoreError("Lifecycle source custody differs")
        for scenario in ("CLEAN", "MESSY"):
            branch = _id(receipt["branches"][scenario])
            refs = receipt["records"][scenario]
            expected = _expected_rows(context, scenario, branch)
            if len(refs) != len(expected):
                raise CompanyStoreError("Incomplete lifecycle source chain")
            provenance = {
                "source_reference": SOURCE_REFERENCE,
                "source_pins": context["source_pins"],
                "upstream_pins": context["upstream_pins"],
                "scenario": scenario,
                "qualification": QUALIFICATION,
            }
            for ref, item in zip(refs, expected, strict=True):
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    (COMPANY, branch, item["system"], item["record"], item["version"]),
                ).fetchone()
                if (
                    row is None
                    or ref["company"] != COMPANY
                    or ref["branch"] != branch
                    or (ref["system"], ref["record"], ref["version"])
                    != (item["system"], item["record"], item["version"])
                    or row["command_id"]
                    != f"PL-{branch}-{item['system']}-{item['record']}-V{item['version']}"
                    or row["sha256"] != item["sha256"]
                    or ref["sha256"] != item["sha256"]
                    or sha(row["content"]) != item["sha256"]
                    or json.loads(row["content"]) != item["body"]
                    or (row["event_at"], row["available_at"])
                    != (item["event_at"], item["available_at"])
                    or row["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or json.loads(row["provenance"]) != provenance
                    or ref["provenance"] != provenance
                    or (ref["event_at"], ref["available_at"], ref["imported_at"])
                    != (row["event_at"], row["available_at"], row["imported_at"])
                    or _time(row["imported_at"]) != row["imported_at"]
                ):
                    raise CompanyStoreError("Lifecycle native row/provenance/clock differs")
    if _frozen(paths) != before:
        raise CompanyStoreError("Lifecycle source changed during verification")
    return manifest
