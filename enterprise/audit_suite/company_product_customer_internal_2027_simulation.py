"""One fictional customer/service internal commitment and concern history."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import stat
import tempfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from . import company_phi_ba_2027_simulation as phi_ba
from . import company_provider_lifecycle_2027_simulation as provider
from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .private_publication import publish

SCHEMA = "SH_FICTIONAL_2027_SELECTED_INTERNAL_CUSTOMER_CASE_V2"
COMPANY = "SABLE-HARBOR-REFERENCE"
BRANCHES = {"CLEAN": "PRD-CLEAN", "MESSY": "PRD-MESSY"}
CUSTOMER = "SIM-COVERED-CUSTOMER-01"
SERVICE = "SIM-RESTRICTED-HOSTING-01"
SUPPORT = "SIM-RECOVERY-SUPPORT-01"
CHANGE = "SIM-PRD-SUPPORT-ROUTE-CHANGE-01"
EXCEPTION = "EXC-SIM-PRD-DEPENDENCY-OMISSION-01"
SOURCE_REFERENCE = "enterprise/audit_suite/company_product_customer_internal_2027_simulation.py"
PRIVATE_ROOT = "enterprise/generated/audit-suite"
TRANSITION = PRIVATE_ROOT + "/company-runtime-transition-2026-09-29/run-v3"
PHI = PRIVATE_ROOT + "/company-phi-ba-2027-simulation-2026-09-29"
PROVIDER = PRIVATE_ROOT + "/company-provider-lifecycle-2026-09-29"
ROUTE_AUTHORITY = {
    "matrix_path": PRIVATE_ROOT + "/documentary-discovery-routes-2026-09-29/run-v2/MATRIX.json",
    "matrix_sha256": "e9477d2074bebce185e412a3ee7c424ded395c1a1128a7c918a94f6acbd1e327",
    "review_path": PRIVATE_ROOT
    + "/documentary-discovery-routes-2026-09-29/independent-review-v2/REVIEW.json",
    "review_sha256": "c4064f6217c0e7f69276adc71004d6da7971867ccf3d844a3e198145cec31ace",
}
SOURCE_PINS = {
    "docs/internal/development/audit-suite/FICTIONAL_2027_SCENARIO_DECISIONS_2026-09-29.md": (
        "15198cd0bcc1de1c8872d4310ff7f1eef8fc89a5250d24af15f4ec19f8e78496"
    ),
    "docs/canon/DECISION_REGISTER_ADDENDUM_2026-09-09_ADVISORY_TIER1.md": (
        "9e5c2c9849f903ac945d2f1668aa2703e2d95a0de7cca94ad4a330731d3cf7a5"
    ),
    "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md": (
        "6bc27636355eb21204471672bd04377ee12cf5530feadf9ec7049a5983015433"
    ),
    "enterprise/ccf/assurance/completion_data/control_procedures.json": (
        "cb5d2729e555156b3fc9845031c00c445b5d37f7bc4c0536f275ceebecabf1f6"
    ),
    "docs/organization/source/chartbook.json": (
        "6ba4f1ed1a14581455a62c3e79a29ca59dbaf1270dfb0db850c0376c15507b49"
    ),
    "enterprise/audit_suite/phi_ba_2027_contract_spec_v1.json": (
        "557cd3ddf09195207de93be2441710f38be9aa8693de729c07d8cf45e45a081f"
    ),
}
UPSTREAM = {
    "PHI": {
        "relative": PHI,
        "run": "run-v1",
        "review": "independent-review-v1/REVIEW.json",
        "schema": "SH_FICTIONAL_2027_PHI_BA_FLOW_V1",
        "manifest": "8226ac2031cafe581289afb4c25088c8dfe603e75ac11fc1ababfe2590f2a5f2",
        "receipt": "20e3762aabb45fcfa3107d695da37e7eeb677f6c5e98f1bb767fa463fe857d9d",
        "database": "ad252e8cb6b1309b238fbe50daac541d67b5fa89051a0b3d8eab7993d4010449",
        "review_sha256": "39bb9b071179ed672c5cf07c2867285d36b2f3e8cdce2106dc4472d17047911e",
        "branches": {"CLEAN": "PHI-CLEAN", "MESSY": "PHI-MESSY"},
    },
    "PROVIDER": {
        "relative": PROVIDER,
        "run": "run-v2",
        "review": "independent-review-v1/REVIEW.json",
        "schema": "SH_FICTIONAL_2027_PROVIDER_LIFECYCLE_V1",
        "manifest": "e8a91c7cd2a426acf78155ffe6dc644048280e592c92ff5e3f63d7b46185f851",
        "receipt": "ab530dfffb00574fe446b20b07bb80bcf89f5fbdc23d61a676ac0a4e4cce6025",
        "database": "b92da45fc00db915cf24bef166c5a092cd6ca5bcc33887998e6b6b414e4e0d0f",
        "review_sha256": "bde642fd35fd4412bda49867b4d7961289bc97deae216bb56e325a19f371b634",
        "branches": {"CLEAN": "LIFE-CLEAN", "MESSY": "LIFE-MESSY"},
    },
}
SYSTEM_OWNERS = {
    "commitment_scope": "P004",
    "change_request": "P002",
    "impact_assessment": "P004",
    "notice_decision": "AS-P003",
    "dependency_discovery": "P004",
    "internal_concern": "P004",
    "internal_escalation": "P002",
    "reconciliation": "P004",
}
GENERIC_ROUTE_IDS = [
    f"TASK-{control}-corporate-{procedure}"
    for control in ("SH-PRD-002", "SH-PRD-003", "SH-PRD-004")
    for procedure in ("IMPLEMENTATION", "TOD", "TOE")
]
UNSUPPORTED_AUTHORED_ROUTE_IDS = [
    f"TASK-{control}-corporate-ACTION-S-COMMUNICATION"
    for control in ("SH-PRD-002", "SH-PRD-003", "SH-PRD-004")
]
LIMITS = [
    "Future 2027 fictional selected-service history; imported_at is actual creation time.",
    "P002 and P004 are source-pinned functional contacts, not accepted executive titles; "
    "AS-P003 performs scenario-only Legal review, not real notice authorization.",
    "No real external message, customer concern or acknowledgment, broad customer population, "
    "executed real contract, PHI, legal status or operation assertion.",
    "All three authored external-communication clauses remain unsupported; no task credit.",
    "No active P1 grant, collection, task, workpaper, Key or Atlas mutation.",
]
AUTHORED_COMMUNICATION_CLAUSE = (
    "Trace a changed service responsibility and an external concern through receipt, "
    "response and the appropriate audience. Test contact accuracy and incomplete recipient lists."
)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _private(path: Path, *, directory: bool) -> Path:
    path = Path(path).absolute()
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise CompanyStoreError("Private source aliases forbidden")
    info = path.stat()
    if directory:
        if not path.is_dir() or stat.S_IMODE(info.st_mode) != 0o700:
            raise CompanyStoreError("Private 0700 source directory required")
    elif (
        not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600
    ):
        raise CompanyStoreError("Private 0600 regular source file required")
    return path


def _frozen(paths: dict[str, Path]) -> dict[str, tuple]:
    database = paths["database"]
    if any(
        Path(str(database) + suffix).exists() or Path(str(database) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise CompanyStoreError("Frozen source database has a sidecar")
    result = {}
    for name, path in paths.items():
        _private(path, directory=False)
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


def _validate_route_family(matrix: dict) -> dict:
    if (
        matrix.get("counts", {}).get("controls_per_side") != 43
        or matrix.get("counts", {}).get("tasks_per_side") != 283
    ):
        raise CompanyStoreError("Reviewed route denominator differs")
    selected = {}
    for side in "AB":
        families = [
            family
            for family in matrix["sides"][side]["families"]
            if family["family"] == "product_customer_commitments"
        ]
        if len(families) != 1:
            raise CompanyStoreError("Selected product route family differs")
        controls = families[0]["controls"]
        if {control["control_id"] for control in controls} != {
            "SH-PRD-002",
            "SH-PRD-003",
            "SH-PRD-004",
        }:
            raise CompanyStoreError("Selected product controls differ")
        rows = {
            task["task_id"]: (control["control_id"], task)
            for control in controls
            for task in control["tasks"]
        }
        if len(rows) != 12 or set(rows) != set(GENERIC_ROUTE_IDS + UNSUPPORTED_AUTHORED_ROUTE_IDS):
            raise CompanyStoreError("Exact twelve selected product task IDs differ")
        for task_id, (control_id, task) in rows.items():
            authored = task_id in UNSUPPORTED_AUTHORED_ROUTE_IDS
            expected_type = "ADDITIONAL_DUTY" if authored else task_id.rsplit("-", 1)[1]
            if (
                not task_id.startswith(f"TASK-{control_id}-corporate-")
                or task["procedure_type"] != expected_type
                or task["authored_test_clause"]
                != (AUTHORED_COMMUNICATION_CLAUSE if authored else None)
                or task["requirement_ids"] != (["SOC2:CC2.2", "SOC2:CC2.3"] if authored else [])
                or (authored and task["remaining_test_gate"] != AUTHORED_COMMUNICATION_CLAUSE)
                or task["test_gate_basis"]
                != (
                    "AUTHORED_TASK_CLAUSE"
                    if authored
                    else "GENERIC_PROCEDURE_GATE_NOT_AN_AUTHORED_CLAUSE"
                )
                or task["current_status"] != "NOT_STARTED"
                or task["current_conclusion"] != "NOT_RUN"
                or task["task_credit"] is not False
            ):
                raise CompanyStoreError("Selected product task clause/status/credit differs")
        selected[side] = {
            "task_count": 12,
            "authored_clause_count": 3,
            "inferred_gate_count": 9,
            "task_ids": sorted(rows),
            "selected_task_rows_sha256": sha(
                encoded({key: value[1] for key, value in sorted(rows.items())})
            ),
        }
    if selected["A"] != selected["B"]:
        raise CompanyStoreError("Paired selected product route authority diverged")
    return selected


def _route_context(private_repository: Path) -> dict:
    paths = {
        "matrix": private_repository / ROUTE_AUTHORITY["matrix_path"],
        "review": private_repository / ROUTE_AUTHORITY["review_path"],
    }
    before = {}
    for name, path in paths.items():
        _private(path, directory=False)
        info = path.stat()
        before[name] = (
            info.st_dev,
            info.st_ino,
            stat.S_IMODE(info.st_mode),
            info.st_size,
            info.st_mtime_ns,
            _digest(path),
        )
    if (
        before["matrix"][-1] != ROUTE_AUTHORITY["matrix_sha256"]
        or before["review"][-1] != ROUTE_AUTHORITY["review_sha256"]
    ):
        raise CompanyStoreError("Reviewed route matrix/review byte pin differs")
    matrix = json.loads(paths["matrix"].read_text())
    review = json.loads(paths["review"].read_text())
    if (
        review.get("verdict") != "PASS_READ_ONLY_CANDIDATE_MATRIX_FOR_INTEGRATION"
        or review.get("matrix_sha256") != ROUTE_AUTHORITY["matrix_sha256"]
        or review.get("audit_task_credit") is not False
        or review.get("active_P1_mutated") is not False
    ):
        raise CompanyStoreError("Reviewed route authority differs")
    selected = _validate_route_family(matrix)
    for name, path in paths.items():
        info = path.stat()
        after = (
            info.st_dev,
            info.st_ino,
            stat.S_IMODE(info.st_mode),
            info.st_size,
            info.st_mtime_ns,
            _digest(path),
        )
        if after != before[name]:
            raise CompanyStoreError("Reviewed route authority changed during read")
    return selected


def _native(private_repository: Path, key: str) -> dict:
    config = UPSTREAM[key]
    parent = _private(private_repository / config["relative"], directory=True)
    run = _private(parent / config["run"], directory=True)
    paths = {
        "manifest": run / "MANIFEST.json",
        "receipt": run / "RECEIPT.json",
        "database": run / "company.sqlite3",
        "review_sha256": parent / config["review"],
    }
    before = _frozen(paths)
    if any(before[name][-1] != config[name] for name in paths):
        raise CompanyStoreError("Reviewed upstream byte pin differs")
    manifest = json.loads(paths["manifest"].read_text())
    receipt = json.loads(paths["receipt"].read_text())
    review = json.loads(paths["review_sha256"].read_text())
    reviewed_hashes = review.get("run_sha256", {})
    if (
        manifest.get("schema") != config["schema"] + "_MANIFEST"
        or manifest.get("receipt_sha256") != config["receipt"]
        or manifest.get("company_db_sha256") != config["database"]
        or manifest.get("audit_task_credit") is not False
        or receipt.get("schema") != config["schema"]
        or receipt.get("branches") != config["branches"]
        or not str(review.get("verdict", "")).startswith("PASS")
        or (
            review.get("run_receipt_sha256", reviewed_hashes.get("RECEIPT.json"))
            != config["receipt"]
        )
    ):
        raise CompanyStoreError("Reviewed upstream scope differs")
    wanted = {
        "PHI": {
            "CLEAN": {
                ("scenario_scope", "SCOPE-01", 1),
                ("contract_register", "BAA-CUST-01", 1),
                ("flow_register", "FLOW-RECON-01", 1),
            },
            "MESSY": {
                ("scenario_scope", "SCOPE-01", 1),
                ("contract_register", "BAA-CUST-01", 1),
                ("flow_register", "FLOW-RECON-01", 1),
            },
        },
        "PROVIDER": {
            "CLEAN": {
                ("relationship_register", f"REL-{part}", 1) for part in ("RENO", "BOISE", "SUPPORT")
            }
            | {("population_reconcile", "POP-Q3-01", 1), ("review_register", "RV-SUPPORT-Q4", 1)},
            "MESSY": {
                ("relationship_register", f"REL-{part}", 1) for part in ("RENO", "BOISE", "SUPPORT")
            }
            | {
                ("population_reconcile", "POP-Q3-01", 1),
                ("review_register", "RV-SUPPORT-Q4", 1),
                ("exception_register", "EXC-SUPPORT-OMISSION", 1),
                ("exception_register", "EXC-SUPPORT-OMISSION", 2),
            },
        },
    }[key]
    selected = {}
    with closing(
        sqlite3.connect(paths["database"].as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Upstream database integrity differs")
        for scenario, branch in config["branches"].items():
            refs = {
                (r["system"], r["record"], r["version"]): r for r in receipt["records"][scenario]
            }
            if not wanted[scenario] <= set(refs):
                raise CompanyStoreError("Required upstream source tuple absent")
            selected[scenario] = {}
            for system, record, version in wanted[scenario]:
                ref = refs[system, record, version]
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    (COMPANY, branch, system, record, version),
                ).fetchone()
                if (
                    row is None
                    or ref["company"] != COMPANY
                    or ref["branch"] != branch
                    or row["sha256"] != ref["sha256"]
                    or sha(row["content"]) != ref["sha256"]
                    or (row["event_at"], row["available_at"], row["imported_at"])
                    != (ref["event_at"], ref["available_at"], ref["imported_at"])
                ):
                    raise CompanyStoreError("Upstream receipt/native tuple differs")
                selected[scenario][system, record, version] = {
                    "ref": ref,
                    "body": json.loads(row["content"]),
                }
    if _frozen(paths) != before:
        raise CompanyStoreError("Upstream source changed during read")
    return selected


def _context(repository: Path, private_repository: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    private_repository = Path(private_repository).resolve(strict=True)
    selected_routes = _route_context(private_repository)
    for name, expected in SOURCE_PINS.items():
        path = repository / name
        if path.is_symlink() or not path.is_file() or _digest(path) != expected:
            raise CompanyStoreError("Canon/role/term source pin differs")
    chart = json.loads((repository / "docs/organization/source/chartbook.json").read_text())
    nodes = {
        node["id"]: node for node in chart["nodes"] if node.get("id") in {"P002", "P004", "AS-P003"}
    }
    if (
        set(nodes) != {"P002", "P004", "AS-P003"}
        or nodes["P002"]["person_id"] != "P002"
        or nodes["P002"]["title_state"] != "PROPOSED_EXECUTIVE_TITLE; founder/director locked"
        or nodes["P004"]["person_id"] != "P004"
        or nodes["P004"]["title_state"] != "PROPOSED_PLAIN_TITLE"
        or nodes["AS-P003"]["person_id"] != "AS-P003"
        or nodes["AS-P003"]["title_state"] != "DELEGATED_FICTIONAL_APPOINTMENT_PENDING_ACCEPTANCE"
    ):
        raise CompanyStoreError("Selected source-contact/Legal role state differs")
    transition = private_repository / TRANSITION
    phi_root = private_repository / PHI / "run-v1"
    provider_root = private_repository / PROVIDER / "run-v2"
    phi_ba.verify(phi_root, transition_root=transition, repository=repository)
    provider.verify(
        provider_root, repository=repository, transition_root=transition, phi_root=phi_root
    )
    phi, lifecycle = _native(private_repository, "PHI"), _native(private_repository, "PROVIDER")
    terms = json.loads(
        (repository / "enterprise/audit_suite/phi_ba_2027_contract_spec_v1.json").read_text()
    )["synthetic_terms"]["SIM-BAA-CUST-01"]
    for scenario in BRANCHES:
        scope = phi[scenario]["scenario_scope", "SCOPE-01", 1]["body"]
        contract = phi[scenario]["contract_register", "BAA-CUST-01", 1]["body"]
        flow = phi[scenario]["flow_register", "FLOW-RECON-01", 1]["body"]
        pop = lifecycle[scenario]["population_reconcile", "POP-Q3-01", 1]["body"]
        if (
            scope["sim_customer_id"] != CUSTOMER
            or scope["sim_service_id"] != SERVICE
            or scope["sim_subcontractor_id"] != SUPPORT
            or contract["contract_id"] != "SIM-BAA-CUST-01"
            or contract["synthetic_terms"] != terms
            or contract["reviewed_synthetic_terms_sha256"] != sha(encoded(terms))
            or contract["contract_executed_in_simulation"] is not True
            or contract["real_signature_or_agreement"] is not False
            or contract["actual_legal_applicability"] != "UNDETERMINED"
            or flow["payload_bytes"] != 0
            or flow["sim_customer_id"] != CUSTOMER
            or flow["sim_service_id"] != SERVICE
            or pop["expected_provider_ids"] != ["CP-SWITCH", "CP-IDACORE", SUPPORT]
            or lifecycle[scenario]["relationship_register", "REL-SUPPORT", 1]["body"]["provider_id"]
            != SUPPORT
        ):
            raise CompanyStoreError("Selected fictional customer/relationship facts differ")
        if scenario == "CLEAN":
            if pop["missing_provider_ids"] or flow["after"] != "RECONCILED":
                raise CompanyStoreError("Clean upstream relationship/flow differs")
        else:
            exception = lifecycle[scenario]["exception_register", "EXC-SUPPORT-OMISSION", 2]["body"]
            if (
                pop["missing_provider_ids"] != [SUPPORT]
                or exception["exception_id"] != provider.EXCEPTION_ID
                or exception["status"] != "OPEN"
                or flow["after"] != "QUARANTINED"
            ):
                raise CompanyStoreError("Messy historical omission/flow differs")
    return {
        "phi": phi,
        "provider": lifecycle,
        "terms_sha256": sha(encoded(terms)),
        "role_nodes": nodes,
        "selected_routes": selected_routes,
    }


def _ref(source: dict, scenario: str, system: str, record: str, version: int = 1) -> dict:
    ref = source[scenario][system, record, version]["ref"]
    return {
        k: ref[k]
        for k in (
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


def _expected_rows(context: dict, scenario: str) -> list[dict]:
    if scenario not in BRANCHES:
        raise CompanyStoreError("Unknown customer-case branch")
    messy = scenario == "MESSY"
    phi, life = context["phi"], context["provider"]
    scope_refs = {
        "scenario_scope": _ref(phi, scenario, "scenario_scope", "SCOPE-01"),
        "customer_baa": _ref(phi, scenario, "contract_register", "BAA-CUST-01"),
        "selected_flow": _ref(phi, scenario, "flow_register", "FLOW-RECON-01"),
    }
    initial_dependencies = {
        part: _ref(life, scenario, "relationship_register", f"REL-{part}")
        for part in (("RENO", "BOISE") if messy else ("RENO", "BOISE", "SUPPORT"))
    }
    common = {
        "schema": SCHEMA,
        "scenario": scenario,
        "truth_class": "FUTURE_FICTIONAL_SELECTED_SERVICE_ONLY",
        "company": COMPANY,
        "customer_id": CUSTOMER,
        "service_id": SERVICE,
        "change_id": CHANGE,
        "payload_bytes": 0,
        "actual_phi_processed": False,
        "actual_customer_or_contract_status": "UNDETERMINED",
        "actual_legal_applicability": "UNDETERMINED",
        "real_external_message_sent": False,
        "fictional_external_message_sent": False,
        "customer_receipt_or_acknowledgment": False,
        "real_world_operation": False,
        "audit_task_credit": False,
        "actor_authority_limit": "SOURCE_CONTACT_OR_SCENARIO_REVIEW_ONLY_NO_REAL_NOTICE_AUTHORITY",
    }
    items = [
        (
            "commitment_scope",
            "CASE-01",
            1,
            "2027-09-16T10:00:00+00:00",
            {
                "action": "SELECTED_INTERNAL_COMMITMENT_MAP",
                "upstream_refs": scope_refs,
                "synthetic_customer_contract_terms_sha256": context["terms_sha256"],
                "commitment": "PAYLOAD_FREE_MARKER_HOSTING_AND_RECOVERY_ONLY",
                "delivery_contacts": {
                    "product": "P002",
                    "customer_delivery": "P004",
                    "legal_review": "AS-P003",
                },
                "role_title_states": {
                    k: context["role_nodes"][k]["title_state"] for k in ("P002", "P004", "AS-P003")
                },
                "nonstandard_product_promises_approved": False,
                "customer_wide_commitment_population_established": False,
            },
        ),
        (
            "change_request",
            "CHANGE-01",
            1,
            "2027-09-17T09:00:00+00:00",
            {
                "action": "INTERNAL_SUPPORT_RECOVERY_ROUTING_CHANGE_PROPOSED",
                "change_execution_state": "PROPOSED_NOT_APPLIED",
                "selected_service_only": True,
                "external_notice_duty": "UNDETERMINED_PENDING_LEGAL_AND_CUSTOMER_TERMS",
            },
        ),
        (
            "impact_assessment",
            "IMPACT-01",
            1,
            "2027-09-17T10:00:00+00:00",
            {
                "action": "INITIAL_INTERNAL_IMPACT_ASSESSMENT",
                "dependency_refs": initial_dependencies,
                "internal_dependency_ids": ["CP-SWITCH", "CP-IDACORE"]
                + ([] if messy else [SUPPORT]),
                "original_recipient_matrix": ["P002", "P004", "AS-P003"]
                + ([] if messy else ["AS-P013"]),
                "customer_recipient_list_established": False,
                "support_dependency_omitted": messy,
                "change_execution_state": "BLOCKED_PENDING_IMPACT_AND_NOTICE_DECISION",
            },
        ),
        (
            "notice_decision",
            "NOTICE-01",
            1,
            "2027-09-17T11:00:00+00:00",
            {
                "action": "INTERNAL_NOTICE_GATE_REVIEW",
                "legal_reviewer_id": "AS-P003",
                "customer_delivery_contact_id": "P004",
                "external_notice_duty": "UNDETERMINED_PENDING_CUSTOMER_TERMS",
                "send_gate": "BLOCKED_NO_EXTERNAL_DELIVERY",
                "recipient_matrix_complete_for_selected_dependencies": not messy,
            },
        ),
    ]
    if messy:
        items += [
            (
                "dependency_discovery",
                "DISC-01",
                1,
                "2027-09-18T11:00:00+00:00",
                {
                    "action": "INDEPENDENT_PROVIDER_POPULATION_RECONCILIATION_DISCOVERED_OMISSION",
                    "upstream_refs": {
                        "provider_population": _ref(
                            life, scenario, "population_reconcile", "POP-Q3-01"
                        ),
                        "provider_exception_original": _ref(
                            life, scenario, "exception_register", "EXC-SUPPORT-OMISSION"
                        ),
                    },
                    "omitted_dependency_id": SUPPORT,
                    "original_impact_sha256": "__IMPACT_V1__",
                    "historical_exception_id": EXCEPTION,
                },
            ),
            (
                "internal_concern",
                "CONCERN-01",
                1,
                "2027-09-18T12:00:00+00:00",
                {
                    "action": "INTERNAL_CONCERN_OPENED_NOT_CUSTOMER_REPORTED",
                    "concern_origin": "INTERNAL_PROVIDER_RECONCILIATION",
                    "historical_exception_id": EXCEPTION,
                    "status": "OPEN",
                    "external_support_case_or_customer_response": False,
                },
            ),
            (
                "internal_escalation",
                "ESC-01",
                1,
                "2027-09-18T13:00:00+00:00",
                {
                    "action": "INTERNAL_PRODUCT_AND_LEGAL_ESCALATION",
                    "escalated_to_contact_ids": ["P002", "P004", "AS-P003"],
                    "historical_exception_id": EXCEPTION,
                    "remediation_gate": "CORRECT_DEPENDENCY_MATRIX_AND_REVIEW_NOTICE_DUTY",
                    "external_response_or_notice": False,
                },
            ),
            (
                "impact_assessment",
                "IMPACT-01",
                2,
                "2027-09-23T10:00:00+00:00",
                {
                    "action": "CORRECTED_INTERNAL_IMPACT_ASSESSMENT",
                    "upstream_refs": {
                        "backfilled_support_relationship": _ref(
                            life, scenario, "relationship_register", "REL-SUPPORT"
                        ),
                        "provider_exception_original": _ref(
                            life, scenario, "exception_register", "EXC-SUPPORT-OMISSION"
                        ),
                    },
                    "internal_dependency_ids": ["CP-SWITCH", "CP-IDACORE", SUPPORT],
                    "corrected_recipient_matrix": ["P002", "P004", "AS-P003", "AS-P013"],
                    "original_impact_sha256": "__IMPACT_V1__",
                    "historical_exception_id": EXCEPTION,
                    "historical_omission_not_retroactively_cured": True,
                    "customer_recipient_list_established": False,
                },
            ),
            (
                "notice_decision",
                "NOTICE-01",
                2,
                "2027-09-23T11:00:00+00:00",
                {
                    "action": "REVIEW_CORRECTED_MATRIX_NO_EXTERNAL_SEND",
                    "external_notice_duty": "UNDETERMINED_PENDING_CUSTOMER_TERMS",
                    "send_gate": "BLOCKED_NO_EXTERNAL_DELIVERY",
                    "historical_exception_id": EXCEPTION,
                    "customer_recipient_list_established": False,
                },
            ),
        ]
    q4_refs = {
        "provider_support_q4_review": _ref(life, scenario, "review_register", "RV-SUPPORT-Q4")
    }
    if messy:
        q4_refs["open_provider_exception_v2"] = _ref(
            life, scenario, "exception_register", "EXC-SUPPORT-OMISSION", 2
        )
    items.append(
        (
            "reconciliation",
            "RECON-01",
            1,
            "2027-10-21T12:00:00+00:00",
            {
                "action": "SELECTED_INTERNAL_CASE_RECONCILIATION",
                "upstream_refs": q4_refs,
                "selected_customer_count": 1,
                "selected_change_count": 1,
                "internal_concern_count": int(messy),
                "historical_open_exception_ids": [EXCEPTION] if messy else [],
                "external_messages_sent": 0,
                "external_customer_receipts": 0,
                "change_executed": False,
                "notice_duty_resolved": False,
                "enterprise_customer_or_channel_population_complete": False,
            },
        )
    )
    rows = []
    prior = None
    impact_v1 = None
    for system, record, version, at, fields in items:
        event = _time(at)
        available = _time((datetime.fromisoformat(at) + timedelta(minutes=10)).isoformat())
        for ref in (
            *fields.get("upstream_refs", {}).values(),
            *fields.get("dependency_refs", {}).values(),
        ):
            if ref["available_at"] > event:
                raise CompanyStoreError("Internal event predates an upstream available source")
        if prior is not None and prior["available_at"] > event:
            raise CompanyStoreError("Internal event predates its available predecessor")
        if fields.get("original_impact_sha256") == "__IMPACT_V1__":
            if impact_v1 is None:
                raise CompanyStoreError("Original impact history absent")
            fields["original_impact_sha256"] = impact_v1
        body = {
            **common,
            "system": system,
            "record": record,
            "version": version,
            "actor_person_id": SYSTEM_OWNERS[system],
            "event_at": event,
            "available_at": available,
            "source_previous": prior,
            **fields,
        }
        item = {
            "system": system,
            "record": record,
            "version": version,
            "event_at": event,
            "available_at": available,
            "body": body,
            "sha256": sha(encoded(body)),
        }
        rows.append(item)
        if system == "impact_assessment" and version == 1:
            impact_v1 = item["sha256"]
        prior = {
            k: item[k]
            for k in ("system", "record", "version", "sha256", "event_at", "available_at")
        }
    return rows


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
    path.chmod(0o600)


def create(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    destination = Path(destination).absolute()
    _private(destination.parent, directory=True)
    if destination.exists() or destination.is_symlink() or destination != destination.resolve():
        raise CompanyStoreError("New private customer-source destination required")
    context = _context(repository, private_repository)
    with tempfile.TemporaryDirectory(prefix=".prd-stage-", dir=destination.parent) as name:
        stage = Path(name)
        store = CompanyStore(stage)
        records = {}
        for scenario, branch in BRANCHES.items():
            records[scenario] = []
            for system, owner in SYSTEM_OWNERS.items():
                store.register_system(COMPANY, branch, system, owner)
            for item in _expected_rows(context, scenario):
                ref = store.append_version(
                    COMPANY,
                    branch,
                    item["system"],
                    item["record"],
                    expected_version=item["version"] - 1,
                    command_id=f"PRD-{branch}-{item['system']}-{item['record']}-V{item['version']}",
                    event_at=item["event_at"],
                    available_at=item["available_at"],
                    content=encoded(item["body"]),
                    provenance={
                        "source_reference": SOURCE_REFERENCE,
                        "scenario": scenario,
                        "source_pins": SOURCE_PINS,
                        "upstream_pins": UPSTREAM,
                        "route_authority_pins": ROUTE_AUTHORITY,
                        "qualification": "FUTURE_FICTIONAL_INTERNAL_CASE_NO_AUDIT_CREDIT",
                    },
                )
                if ref["sha256"] != item["sha256"]:
                    raise CompanyStoreError("Customer-case source serialization differs")
                records[scenario].append(ref)
        receipt = {
            "schema": SCHEMA,
            "company": COMPANY,
            "branches": BRANCHES,
            "records": records,
            "source_pins": SOURCE_PINS,
            "upstream_pins": UPSTREAM,
            "route_authority_pins": ROUTE_AUTHORITY,
            "selected_route_authority": context["selected_routes"],
            "selected_customer_count_per_branch": 1,
            "selected_change_count_per_branch": 1,
            "internal_concern_counts": {"CLEAN": 0, "MESSY": 1},
            "open_historical_exception_ids": {"CLEAN": [], "MESSY": [EXCEPTION]},
            "external_send_counts": {"CLEAN": 0, "MESSY": 0},
            "selected_generic_candidate_route_ids_per_side": GENERIC_ROUTE_IDS,
            "unsupported_authored_route_ids_per_side": UNSUPPORTED_AUTHORED_ROUTE_IDS,
            "authored_external_communication_clause_support": False,
            "actual_operation_eligibility_as_of_2026_09_29": False,
            "audit_task_credit": False,
            "limits": LIMITS,
        }
        _write(stage / "RECEIPT.json", receipt)
        manifest = {
            "schema": SCHEMA + "_MANIFEST",
            "receipt_sha256": _digest(stage / "RECEIPT.json"),
            "company_db_sha256": _digest(stage / "company.sqlite3"),
            "module_sha256": _digest(Path(__file__)),
            "native_version_count": sum(len(v) for v in records.values()),
            "audit_task_credit": False,
        }
        _write(stage / "MANIFEST.json", manifest)
        publish(stage, destination)
    return manifest


def verify(destination: Path, *, repository: Path, private_repository: Path) -> dict:
    root = _private(destination, directory=True)
    paths = {
        "manifest": root / "MANIFEST.json",
        "receipt": root / "RECEIPT.json",
        "database": root / "company.sqlite3",
    }
    before = _frozen(paths)
    manifest = json.loads(paths["manifest"].read_text())
    receipt = json.loads(paths["receipt"].read_text())
    context = _context(repository, private_repository)
    expected_count = sum(len(_expected_rows(context, side)) for side in BRANCHES)
    if (
        manifest.get("schema") != SCHEMA + "_MANIFEST"
        or manifest.get("receipt_sha256") != before["receipt"][-1]
        or manifest.get("company_db_sha256") != before["database"][-1]
        or manifest.get("module_sha256") != _digest(Path(__file__))
        or manifest.get("native_version_count") != expected_count
        or manifest.get("audit_task_credit") is not False
        or receipt.get("schema") != SCHEMA
        or receipt.get("company") != COMPANY
        or receipt.get("branches") != BRANCHES
        or receipt.get("source_pins") != SOURCE_PINS
        or receipt.get("upstream_pins") != UPSTREAM
        or receipt.get("route_authority_pins") != ROUTE_AUTHORITY
        or receipt.get("selected_route_authority") != context["selected_routes"]
        or receipt.get("selected_customer_count_per_branch") != 1
        or receipt.get("selected_change_count_per_branch") != 1
        or receipt.get("internal_concern_counts") != {"CLEAN": 0, "MESSY": 1}
        or receipt.get("open_historical_exception_ids") != {"CLEAN": [], "MESSY": [EXCEPTION]}
        or receipt.get("external_send_counts") != {"CLEAN": 0, "MESSY": 0}
        or receipt.get("selected_generic_candidate_route_ids_per_side") != GENERIC_ROUTE_IDS
        or receipt.get("unsupported_authored_route_ids_per_side") != UNSUPPORTED_AUTHORED_ROUTE_IDS
        or receipt.get("authored_external_communication_clause_support") is not False
        or receipt.get("actual_operation_eligibility_as_of_2026_09_29") is not False
        or receipt.get("audit_task_credit") is not False
        or receipt.get("limits") != LIMITS
        or set(receipt.get("records", {})) != set(BRANCHES)
    ):
        raise CompanyStoreError("Customer-case receipt/manifest scope differs")
    with closing(
        sqlite3.connect(paths["database"].as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CompanyStoreError("Customer-case database integrity differs")
        if db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] != expected_count or any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "collections", "access_events")
        ):
            raise CompanyStoreError("Customer-case source/audit-access count differs")
        expected_systems = {
            (COMPANY, branch, system, owner)
            for branch in BRANCHES.values()
            for system, owner in SYSTEM_OWNERS.items()
        }
        if {
            tuple(r) for r in db.execute("SELECT company,branch,system,owner FROM systems")
        } != expected_systems:
            raise CompanyStoreError("Customer-case source custody differs")
        for scenario, branch in BRANCHES.items():
            expected = _expected_rows(context, scenario)
            refs = receipt["records"][scenario]
            if len(refs) != len(expected):
                raise CompanyStoreError("Customer-case branch row count differs")
            provenance = {
                "source_reference": SOURCE_REFERENCE,
                "scenario": scenario,
                "source_pins": SOURCE_PINS,
                "upstream_pins": UPSTREAM,
                "route_authority_pins": ROUTE_AUTHORITY,
                "qualification": "FUTURE_FICTIONAL_INTERNAL_CASE_NO_AUDIT_CREDIT",
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
                    or any(
                        ref[k] != item[k]
                        for k in (
                            "system",
                            "record",
                            "version",
                            "sha256",
                            "event_at",
                            "available_at",
                        )
                    )
                    or ref["imported_at"] != row["imported_at"]
                    or ref["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or ref["provenance"] != provenance
                    or row["sha256"] != item["sha256"]
                    or row["content"] != encoded(item["body"])
                    or json.loads(row["provenance"]) != provenance
                    or (row["event_at"], row["available_at"])
                    != (item["event_at"], item["available_at"])
                    or row["available_at"] < row["event_at"]
                    or row["imported_at"] >= row["event_at"]
                ):
                    raise CompanyStoreError("Customer-case native row differs")
    if _frozen(paths) != before:
        raise CompanyStoreError("Customer-case source changed during verify")
    return manifest
