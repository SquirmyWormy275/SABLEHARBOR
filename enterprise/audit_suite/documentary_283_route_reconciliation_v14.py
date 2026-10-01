"""Add exact reviewed selected ENG005 operation to four unchanged discovery routes."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from . import company_eng005_operating_2027 as source
from . import documentary_283_route_reconciliation_v13 as prior
from .documentary_283_route_reconciliation_v6 import _p1_inventory

SCHEMA = "SH_DOCUMENTARY_283_PAIRED_ROUTE_CANDIDATE_RECONCILIATION_V14"
BASE = "enterprise/generated/audit-suite"
CONTROL = "SH-ENG-005"
SOURCE = "ENG005_OPERATED_SELECTED_V1"
AUTHORED = "TASK-SH-ENG-005-corporate-CHECK-SOC2:CC8.1"
GENERIC = (
    "TASK-SH-ENG-005-corporate-IMPLEMENTATION",
    "TASK-SH-ENG-005-corporate-TOD",
    "TASK-SH-ENG-005-corporate-TOE",
)
GENERIC_GATES = {
    "TASK-SH-ENG-005-corporate-IMPLEMENTATION": (
        "Locate deployed company-native configuration or decision records for the scoped "
        "service; reconcile owner and effective date to the population."
    ),
    "TASK-SH-ENG-005-corporate-TOD": (
        "Test design against the stated control objective, boundary, owner, frequency, "
        "inputs, decision criteria, outputs and exception path."
    ),
    "TASK-SH-ENG-005-corporate-TOE": (
        "Define the complete selected-period population and sample, reperform execution "
        "and exceptions, and retain exact native provenance and availability clocks."
    ),
}
TARGETS = {AUTHORED, *GENERIC}
CLAUSE = (
    "Select normal and emergency code, infrastructure and data changes; trace "
    "requirements, security tests, independent approval, deployment verification and rollback."
)
LIMIT = (
    "One selected fictional 2027 SVC-compute queue with one ordinary Reno and one "
    "emergency Boise request per branch, not a full-period change population. Clean "
    "completes bounded ordinary local gates and holds emergency execution because corporate "
    "emergency authority is not evidenced. Messy retains an invalid ordinary application, "
    "correction, unauthorized emergency bypass, rollbacks and two OPEN historical exceptions. "
    "Office identity and authored local decisions do not establish adopted corporate change "
    "policy or emergency delegation. No real deployment, PHI, complete population, "
    "independent audit test, clause satisfaction or task credit."
)
V13_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V13_2026-09-30.json"
V13_REVIEW = (
    f"{BASE}/documentary-283-route-reconciliation-v13-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
SOURCE_ROOT = f"{BASE}/company-eng005-operating-2026-09-30"
SOURCE_RUN = f"{SOURCE_ROOT}/main-run-v1"
SOURCE_REVIEW = f"{SOURCE_ROOT}/independent-review-main-v1/REVIEW.json"
PINS = {
    "v13_ledger": {
        "scope": "repo",
        "path": V13_LEDGER,
        "sha256": "042ad50cadeb9677d59045d0c263c3e87e320292fd51a7dd3ae484c87d9aba90",
    },
    "v13_review": {
        "scope": "private",
        "path": V13_REVIEW,
        "sha256": "609ffba4ad9dcdaa4ce370abdb32de995dd2f3f0664275692cf66d7da0e495ec",
    },
    "eng005_review": {
        "scope": "private",
        "path": SOURCE_REVIEW,
        "sha256": "03453687ff227cb6ef4376e6b1b313638e5a5841fc78f43cd09551fd62e44075",
    },
    "eng005_manifest": {
        "scope": "private",
        "path": f"{SOURCE_RUN}/MANIFEST.json",
        "sha256": "505be4531461c0d73e0466fb39540b5757512bf13b9d4ed8f44c13d86e90fc75",
    },
    "eng005_receipt": {
        "scope": "private",
        "path": f"{SOURCE_RUN}/RECEIPT.json",
        "sha256": "0d9209de464d0f4e9186eb41824ac66beba1b7f7e1e735364ba64cded20f02bd",
    },
    "eng005_db": {
        "scope": "private",
        "path": f"{SOURCE_RUN}/company.sqlite3",
        "sha256": "8696b55b03ec1df8597556d0b949f82a34c0e0cabc9d8130fae078e6b2812ee3",
    },
    "eng005_module": {
        "scope": "repo",
        "path": "enterprise/audit_suite/company_eng005_operating_2027.py",
        "sha256": "a9c7c2d373ec29bfa8c2c2606aec22de30c60c9f2cb0b4873d4d158e34968622",
    },
    "eng005_spec": {
        "scope": "repo",
        "path": "enterprise/audit_suite/eng005_operating_2027_spec_v1.json",
        "sha256": "a497fab4b3ca909f55b3376efec15c28f6195394d6f085d4aaf0b99d51043d6a",
    },
}
P1_FREEZE = prior.P1_FREEZE
IDENTITY = (
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
)
ROSTER = {
    "CLEAN": (
        "ORD-REQUEST",
        "ORD-RISK",
        "ORD-TEST-INITIAL",
        "ORD-SECURITY-DECISION",
        "ORD-RELEASE",
        "ORD-APPLY-APPROVED",
        "ORD-VERIFY",
        "ORD-ROLLBACK-REHEARSAL",
        "ORD-REVIEW",
        "EMG-REQUEST",
        "EMG-AUTHORITY-GATE",
        "EMG-BLOCKED-REVIEW",
    ),
    "MESSY": (
        "ORD-REQUEST",
        "ORD-RISK",
        "ORD-TEST-INITIAL",
        "ORD-SECURITY-DECISION",
        "ORD-INVALID-APPLY",
        "ORD-MISMATCH",
        "EXC-ENG005-ORD-01",
        "ORD-ROLLBACK",
        "ORD-TEST-CORRECTED",
        "ORD-CORRECTED-SECURITY",
        "ORD-RELEASE",
        "ORD-APPLY-APPROVED",
        "ORD-VERIFY",
        "ORD-ROLLBACK-REHEARSAL",
        "ORD-REVIEW",
        "EMG-REQUEST",
        "EMG-AUTHORITY-GATE",
        "EMG-INVALID-BYPASS",
        "EMG-ADVERSE-VERIFY",
        "EMG-ROLLBACK",
        "EMG-RETROSPECTIVE",
        "EXC-ENG005-EMG-01",
    ),
}
SYSTEM_BY_RECORD = {
    "ORD-REQUEST": "change_request",
    "ORD-RISK": "change_risk",
    "ORD-TEST-INITIAL": "change_test",
    "ORD-SECURITY-DECISION": "change_approval",
    "ORD-INVALID-APPLY": "change_application",
    "ORD-MISMATCH": "change_verification",
    "EXC-ENG005-ORD-01": "exception_register",
    "ORD-ROLLBACK": "change_recovery",
    "ORD-TEST-CORRECTED": "change_test",
    "ORD-CORRECTED-SECURITY": "change_approval",
    "ORD-RELEASE": "change_release",
    "ORD-APPLY-APPROVED": "change_application",
    "ORD-VERIFY": "change_verification",
    "ORD-ROLLBACK-REHEARSAL": "change_recovery",
    "ORD-REVIEW": "change_review",
    "EMG-REQUEST": "change_request",
    "EMG-AUTHORITY-GATE": "change_approval",
    "EMG-BLOCKED-REVIEW": "change_review",
    "EMG-INVALID-BYPASS": "change_application",
    "EMG-ADVERSE-VERIFY": "change_verification",
    "EMG-ROLLBACK": "change_recovery",
    "EMG-RETROSPECTIVE": "change_review",
    "EXC-ENG005-EMG-01": "exception_register",
}


class V14ReconciliationError(prior.V13ReconciliationError):
    """Reviewed ENG005 source, exact route prefix or no-credit gate changed."""


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _selected_refs(receipt: dict, previous: dict) -> dict[str, list[dict]]:
    if (
        receipt.get("schema") != source.SCHEMA
        or receipt.get("branches") != source.BRANCHES
        or receipt.get("selected_service_id") != "SVC-compute"
        or receipt.get("selected_population") != ["CHG-RNO-MARKER-2027-01", "CHG-BOI-GATE-2027-02"]
        or receipt.get("native_version_counts") != {"CLEAN": 12, "MESSY": 22}
        or receipt.get("open_exception_counts") != {"CLEAN": 0, "MESSY": 2}
        or receipt.get("open_exception_ids")
        != {"CLEAN": [], "MESSY": ["EXC-ENG005-ORD-01", "EXC-ENG005-EMG-01"]}
        or receipt.get("corporate_emergency_authority_status") != "NOT_EVIDENCED_OPEN"
        or receipt.get("historical_exercise_is_operating_source") is not False
        or receipt.get("historical_prospective_receipt_sha256") != source.HISTORICAL_SHA256
        or receipt.get("external_packets_or_writes") != 0
        or any(
            receipt.get(key) is not False
            for key in (
                "real_deployment",
                "actual_phi",
                "enterprise_policy_approved",
                "source_complete",
                "authored_eng005_clause_satisfied",
                "full_period_or_enterprise_change_population_complete",
                "audit_task_credit",
            )
        )
    ):
        raise V14ReconciliationError("ENG005 selected source scope or open gates differ")
    selected = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        rows = receipt.get("records", {}).get(scenario, [])
        if (
            not isinstance(rows, list)
            or len(rows) != len(ROSTER[scenario])
            or tuple((row.get("system"), row.get("record")) for row in rows)
            != tuple((SYSTEM_BY_RECORD[name], name) for name in ROSTER[scenario])
            or any(
                row.get("company") != source.COMPANY
                or row.get("branch") != source.BRANCHES[scenario]
                or row.get("version") != 1
                or row.get("origin") != "AUTHORED_TRAINING_SOURCE"
                or any(not row.get(key) for key in IDENTITY)
                for row in rows
            )
        ):
            raise V14ReconciliationError("ENG005 selected native original roster differs")
        routes = [
            row for row in previous["rows"] if row["side"] == side and row["control_id"] == CONTROL
        ]
        if len(routes) != 4 or {row["task_id"] for row in routes} != TARGETS:
            raise V14ReconciliationError("Exact four ENG005 route identities differ")
        for route in routes:
            authored = route["task_id"] == AUTHORED
            if (
                route["classification"]
                != ("UNSUPPORTED_EXACT_CLAUSE" if authored else "SOURCE_CANDIDATE_PARTIAL")
                or route["test_gate_basis"]
                != (
                    "AUTHORED_TASK_CLAUSE"
                    if authored
                    else "GENERIC_PROCEDURE_GATE_NOT_AN_AUTHORED_CLAUSE"
                )
                or route["authored_test_clause"] != (CLAUSE if authored else None)
                or route["remaining_test_gate"]
                != (CLAUSE if authored else GENERIC_GATES[route["task_id"]])
                or route["targeted_integrated_source_ids"] != ["ENG005_LOCAL_V1"]
                or route["candidate_or_design_source_ids"]
                != ([] if authored else ["ENG005_LOCAL_V1"])
                or route["current_status"] != "NOT_STARTED"
                or route["current_conclusion"] != "NOT_RUN"
                or route["audit_task_credit"] is not False
            ):
                raise V14ReconciliationError("Exact ENG005 authored/generic route gate differs")
        selected[side] = [{key: row[key] for key in IDENTITY} for row in rows]
    return selected


def _extend(previous: dict, receipt: dict, freeze: dict) -> dict:
    """Retain every V13 row field while appending one selected ENG005 lead."""
    if (
        previous.get("schema") != prior.SCHEMA
        or previous.get("p1_freeze") != freeze
        or previous.get("audit_task_credit") is not False
        or previous.get("active_pair_mutated") is not False
        or len(previous.get("rows", [])) != 566
        or previous.get("active_p1_tasks")
        != {
            side: {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"}
            for side in "AB"
        }
        or any(
            previous["counts"][side]["targeted_integrated_route_count"] != 175
            or previous["counts"][side]["classifications"]
            != {
                "DESIGN_CONTEXT_ONLY": 27,
                "SOURCE_CANDIDATE_PARTIAL": 135,
                "UNSUPPORTED_EXACT_CLAUSE": 121,
            }
            for side in "AB"
        )
    ):
        raise V14ReconciliationError("Reviewed V13 route prefix or frozen P1 differs")
    refs = _selected_refs(receipt, previous)
    rows = []
    for old in previous["rows"]:
        selected = old["task_id"] in TARGETS
        generic = old["task_id"] in GENERIC
        row = deepcopy(old)
        if selected:
            row["targeted_integrated_source_ids"].append(SOURCE)
        if generic:
            row["candidate_or_design_source_ids"].append(SOURCE)
        row["v14_reviewed_source_ids"] = [SOURCE] if selected else []
        row["v14_source_limits"] = {SOURCE: LIMIT} if selected else {}
        row["v14_source_record_refs"] = {SOURCE: refs[old["side"]]} if selected else {}
        allowed_append = {"targeted_integrated_source_ids"} if selected else set()
        if generic:
            allowed_append.add("candidate_or_design_source_ids")
        if any(row[key] != value for key, value in old.items() if key not in allowed_append):
            raise V14ReconciliationError("V13 row field changed")
        rows.append(row)
    counts = {}
    for side in "AB":
        subset = [row for row in rows if row["side"] == side]
        selected = [row for row in subset if row["v14_reviewed_source_ids"]]
        if (
            len(subset) != 283
            or len({row["task_id"] for row in subset}) != 283
            or len(selected) != 4
            or {row["task_id"] for row in selected} != TARGETS
            or sum(bool(row["targeted_integrated_source_ids"]) for row in subset) != 175
            or any(
                row["current_status"] != "NOT_STARTED"
                or row["current_conclusion"] != "NOT_RUN"
                or row["audit_task_credit"] is not False
                for row in subset
            )
        ):
            raise V14ReconciliationError("ENG005 selected route denominator differs")
        counts[side] = {
            **deepcopy(previous["counts"][side]),
            "v14_new_selected_eng005_authored_leads": 1,
            "v14_new_selected_eng005_generic_leads": 3,
            "v14_new_distinct_targeted_routes": 0,
            "v14_new_classification_promotions": 0,
        }
    if counts["A"] != counts["B"]:
        raise V14ReconciliationError("Paired ENG005 route counts differ")
    pins = {**previous["source_pins"], **PINS}
    return {
        **previous,
        "schema": SCHEMA,
        "v13_prefix_sha256": PINS["v13_ledger"]["sha256"],
        "source_pins": pins,
        "source_pins_sha256": hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest(),
        "reviewed_source_roster": {
            **previous["reviewed_source_roster"],
            "additional_selected_eng005_operating_cohort_versions": 34,
        },
        "counts": counts,
        "rows": rows,
        "limits": [
            *previous["limits"],
            "Only four exact SH-ENG-005 routes per side gain the selected operating lead. "
            "One authored clause stays unsupported; three generic routes stay partial; "
            "all 175 distinct targeted routes and 121 unsupported clauses per side persist.",
            LIMIT,
            "Corporate emergency authority remains NOT_EVIDENCED_OPEN. All 409 P1 tasks "
            "per side remain NOT_STARTED/NOT_RUN; no source completeness, task credit, "
            "fresh pair, Key, grade or Atlas write.",
        ],
        "audit_task_credit": False,
        "active_pair_mutated": False,
    }


def build(repository: Path, private_repository: Path) -> dict:
    """Reperform V13 and verified company source before selected discovery routing."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise V14ReconciliationError("Frozen P1 inventory differs")
    paths = {name: prior.prior._pin(repository, private, entry) for name, entry in PINS.items()}
    previous = prior.build(repository, private)
    if previous != json.loads(paths["v13_ledger"].read_text()):
        raise V14ReconciliationError("Reviewed V13 route replay differs")
    route_review = json.loads(paths["v13_review"].read_text())
    if (
        route_review.get("verdict") != "PASS_MAIN_SELECTED_EMERGENCY_LEAD_NO_CREDIT"
        or route_review.get("output_sha256", {}).get("LEDGER.json") != PINS["v13_ledger"]["sha256"]
        or route_review.get("p1_freeze") != freeze
        or route_review.get("audit_task_credit") is not False
    ):
        raise V14ReconciliationError("V13 independent route review join differs")
    review = json.loads(paths["eng005_review"].read_text())
    manifest = json.loads(paths["eng005_manifest"].read_text())
    source_hashes = {
        name: PINS[key]["sha256"]
        for name, key in (
            ("MANIFEST.json", "eng005_manifest"),
            ("RECEIPT.json", "eng005_receipt"),
            ("company.sqlite3", "eng005_db"),
        )
    }
    if (
        review.get("verdict") != "PASS_MAIN_SELECTED_SOURCE_NO_AUDIT_CREDIT"
        or review.get("main_run_sha256") != source_hashes
        or review.get("p1_freeze") != freeze
        or review.get("corporate_emergency_authority_status") != "NOT_EVIDENCED_OPEN"
        or review.get("real_deployment") is not False
        or review.get("source_complete") is not False
        or review.get("audit_task_credit") is not False
        or manifest.get("native_version_count") != 34
        or manifest.get("receipt_sha256") != PINS["eng005_receipt"]["sha256"]
        or manifest.get("db_sha256") != PINS["eng005_db"]["sha256"]
        or manifest.get("module_sha256") != PINS["eng005_module"]["sha256"]
        or manifest.get("audit_task_credit") is not False
    ):
        raise V14ReconciliationError("ENG005 independent source review join differs")
    source.verify(private / SOURCE_RUN, repository=repository, private_repository=private)
    receipt = json.loads(paths["eng005_receipt"].read_text())
    result = _extend(previous, receipt, freeze)
    if _p1_inventory(private) != freeze or any(
        _digest(path) != PINS[name]["sha256"] for name, path in paths.items()
    ):
        raise V14ReconciliationError("Pinned ENG005 input or P1 changed during build")
    return result


def markdown(result: dict) -> str:
    count = result["counts"]["A"]
    lines = [
        "# Paired 283-route ENG005 selected operating-source reconciliation V14",
        "",
        "Four exact SH-ENG-005 routes per side gain one reviewed fictional 2027 company "
        "change-queue lead: 12 Clean and 22 Messy immutable native versions. Every V13 row "
        "field persists except the named source-ID appends; no route classification changes.",
        "",
        "| Classification | Routes per side |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {name} | {number} |" for name, number in count["classifications"].items())
    lines += [
        "",
        "Clean completes a bounded ordinary local change and holds the emergency request "
        "without evidenced corporate authority. Messy retains invalid ordinary and emergency "
        "applications, correction/rollback, retrospective review and two OPEN exceptions. "
        "The earlier in-memory prospective exercise remains distinct.",
        "",
        "The CC8.1 authored normal/emergency clause remains UNSUPPORTED_EXACT_CLAUSE. "
        "The three generic ENG005 routes remain SOURCE_CANDIDATE_PARTIAL. "
        f"All 121 unsupported clauses and {count['targeted_integrated_route_count']} "
        "distinct targeted routes per side retain their classification.",
        "",
        "No corporate emergency delegation, full-period change population, real deployment, "
        "source completeness, task credit, fresh pair, Key, grade or Atlas write follows. "
        "The frozen P1 pair retains 409 NOT_STARTED/NOT_RUN tasks per side.",
        "",
    ]
    return "\n".join(lines)
