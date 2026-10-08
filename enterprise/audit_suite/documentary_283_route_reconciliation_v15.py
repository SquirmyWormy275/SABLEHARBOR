"""Append one reviewed, held PRD concern lead to exact existing discovery rows."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from . import company_prd_concern_intake_2027 as source
from . import documentary_283_route_reconciliation_v14 as prior
from .documentary_283_route_reconciliation_v6 import _p1_inventory
from .documentary_283_route_reconciliation_v12 import _pin

SCHEMA = "SH_DOCUMENTARY_283_PAIRED_ROUTE_CANDIDATE_RECONCILIATION_V15"
BASE = "enterprise/generated/audit-suite"
SOURCE = "PRD_CONCERN_HELD_V1"
CONTROLS = ("SH-PRD-002", "SH-PRD-003", "SH-PRD-004")
AUTHORED = tuple(f"TASK-{control}-corporate-ACTION-S-COMMUNICATION" for control in CONTROLS)
GENERIC = tuple(
    f"TASK-{control}-corporate-{procedure}"
    for control in CONTROLS
    for procedure in ("IMPLEMENTATION", "TOD", "TOE")
)
TARGETS = set(AUTHORED + GENERIC)
CLAUSE = source.prior.AUTHORED_COMMUNICATION_CLAUSE
GENERIC_GATES = {
    "IMPLEMENTATION": (
        "Locate deployed company-native configuration or decision records for the scoped "
        "service; reconcile owner and effective date to the population."
    ),
    "TOD": (
        "Test design against the stated control objective, boundary, owner, frequency, "
        "inputs, decision criteria, outputs and exception path."
    ),
    "TOE": (
        "Define the complete selected-period population and sample, reperform execution "
        "and exceptions, and retain exact native provenance and availability clocks."
    ),
}
LIMIT = (
    "One future-fictional selected service and local simulated concern inbox with an "
    "unverified claimant, not a customer/channel population. Clean lists selected internal "
    "roles but holds the response draft at unresolved authority. Messy preserves the omitted "
    "support role, denied local dispatch attempt, false completion, later matrix correction "
    "and OPEN historical exception. The earlier PRD notice duty remains undetermined; "
    "P004 and AS-P003 are scenario contacts, not accepted signatories. No accepted fictional "
    "outbound delivery, separate customer acknowledgment, real send, actual customer/contract "
    "or ePHI, deployed service, clause satisfaction, complete population or audit credit."
)
V14_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V14_2026-09-30.json"
V14_REVIEW = (
    f"{BASE}/documentary-283-route-reconciliation-v14-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
SOURCE_ROOT = f"{BASE}/company-prd-concern-intake-2026-09-30"
SOURCE_RUN = f"{SOURCE_ROOT}/main-run-v1"
SOURCE_REVIEW = f"{SOURCE_ROOT}/independent-review-main-v1/REVIEW.json"
PINS = {
    "v14_ledger": {
        "scope": "repo",
        "path": V14_LEDGER,
        "sha256": "e43e644eecd53a2111c247d16466627ad8d4d63b14012b78fead47c48a23877a",
    },
    "v14_review": {
        "scope": "private",
        "path": V14_REVIEW,
        "sha256": "4cebb2939e5dacf308757640f3643c0f3de4ebd78fbaf77e385c1f883ee8ceee",
    },
    "prd_review": {
        "scope": "private",
        "path": SOURCE_REVIEW,
        "sha256": "695aa780d6bfd952e2b161fe0b21b8b01ae62c8e3db101686237532e57072794",
    },
    "prd_manifest": {
        "scope": "private",
        "path": f"{SOURCE_RUN}/MANIFEST.json",
        "sha256": "a55481e58a8347d1539719ab02eff7f66b17ca7d87fb870935ccbe6b36898ff6",
    },
    "prd_receipt": {
        "scope": "private",
        "path": f"{SOURCE_RUN}/RECEIPT.json",
        "sha256": "8fc7f4a4518e918975a13bdaac006336e6ffbdb5f03770e43e37e0506ec2ffe1",
    },
    "prd_db": {
        "scope": "private",
        "path": f"{SOURCE_RUN}/company.sqlite3",
        "sha256": "48b85f09899e5a74ef160e9bc10cd8c85ea128986086f1b73f1344d8739e4524",
    },
    "prd_module": {
        "scope": "repo",
        "path": "enterprise/audit_suite/company_prd_concern_intake_2027.py",
        "sha256": "e890f87f1fa9448ff94c18476b0904e6e89305a1390a2d1ea4eae57325a63b2e",
    },
    "prd_spec": {
        "scope": "repo",
        "path": "enterprise/audit_suite/prd_concern_intake_2027_spec_v1.json",
        "sha256": "dde9f62c3de873bdf2ae8769f529e6bb43369f74038af1682ad94ff62caf5415",
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
        ("simulated_inbox", "CLAIM-01"),
        ("case_intake", "INTAKE-01"),
        ("recipient_matrix", "MATRIX-01"),
        ("concern_assessment", "ASSESS-01"),
        ("legal_gate", "LEGAL-01"),
        ("response_draft", "DRAFT-01"),
        ("dispatch_gate", "GATE-01"),
        ("reconciliation", "RECON-01"),
    ),
    "MESSY": (
        ("simulated_inbox", "CLAIM-01"),
        ("case_intake", "INTAKE-01"),
        ("recipient_matrix", "MATRIX-INITIAL"),
        ("response_draft", "DRAFT-INITIAL"),
        ("dispatch_attempt", "ATTEMPT-01"),
        ("dispatch_gate", "DENY-01"),
        ("reconciliation", "FALSE-CLOSE"),
        ("concern_assessment", "DISCOVERY-01"),
        ("exception_register", "EXCEPTION-OPEN"),
        ("recipient_matrix", "MATRIX-CORRECTED"),
        ("legal_gate", "LEGAL-01"),
        ("response_draft", "DRAFT-CORRECTED"),
        ("reconciliation", "RECON-01"),
    ),
}


class V15ReconciliationError(prior.V14ReconciliationError):
    """The reviewed concern, V14 row prefix, or no-credit boundary changed."""


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _selected_refs(receipt: dict, previous: dict) -> dict[str, list[dict]]:
    if (
        receipt.get("schema") != source.SCHEMA
        or receipt.get("branches") != source.BRANCHES
        or receipt.get("native_version_counts") != {"CLEAN": 8, "MESSY": 13}
        or receipt.get("local_open_exception_counts") != {"CLEAN": 0, "MESSY": 1}
        or receipt.get("internal_draft_status")
        != {"CLEAN": "HELD", "MESSY": "HELD_AFTER_CORRECTION"}
        or receipt.get("selected_concern_count") != 1
        or receipt.get("real_external_messages_sent") != 0
        or receipt.get("fictional_accepted_deliveries") != 0
        or receipt.get("customer_acknowledgments") != 0
        or receipt.get("spec_sha256") != PINS["prd_spec"]["sha256"]
        or receipt.get("reviewed_prd_source_sha256") != source.UPSTREAM_HASHES
        or any(
            receipt.get(key) is not False
            for key in (
                "selected_claimant_verified",
                "actual_phi_processing",
                "source_complete",
                "fresh_audit_pair_created",
                "audit_task_credit",
            )
        )
    ):
        raise V15ReconciliationError("PRD concern source scope or held gate differs")
    selected = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        rows = receipt.get("records", {}).get(scenario, [])
        if (
            not isinstance(rows, list)
            or len(rows) != len(ROSTER[scenario])
            or tuple((row.get("system"), row.get("record")) for row in rows) != ROSTER[scenario]
            or any(
                row.get("company") != source.COMPANY
                or row.get("branch") != source.BRANCHES[scenario]
                or row.get("version") != 1
                or row.get("origin") != "AUTHORED_TRAINING_SOURCE"
                or any(not row.get(key) for key in IDENTITY)
                for row in rows
            )
        ):
            raise V15ReconciliationError("PRD concern native original roster differs")
        routes = [
            row for row in previous["rows"] if row["side"] == side and row["control_id"] in CONTROLS
        ]
        if len(routes) != 12 or {row["task_id"] for row in routes} != TARGETS:
            raise V15ReconciliationError("Exact PRD task identities differ")
        for row in routes:
            authored = row["task_id"] in AUTHORED
            procedure = row["task_id"].rsplit("-", 1)[1]
            if (
                row["classification"]
                != ("UNSUPPORTED_EXACT_CLAUSE" if authored else "SOURCE_CANDIDATE_PARTIAL")
                or row["test_gate_basis"]
                != (
                    "AUTHORED_TASK_CLAUSE"
                    if authored
                    else "GENERIC_PROCEDURE_GATE_NOT_AN_AUTHORED_CLAUSE"
                )
                or row["authored_test_clause"] != (CLAUSE if authored else None)
                or row["remaining_test_gate"] != (CLAUSE if authored else GENERIC_GATES[procedure])
                or row["targeted_integrated_source_ids"] != ["PRD_INTERNAL_V2"]
                or row["candidate_or_design_source_ids"]
                != ([] if authored else ["PRD_INTERNAL_V2"])
                or row["current_status"] != "NOT_STARTED"
                or row["current_conclusion"] != "NOT_RUN"
                or row["audit_task_credit"] is not False
            ):
                raise V15ReconciliationError("Exact PRD authored/generic route gate differs")
        selected[side] = [{key: row[key] for key in IDENTITY} for row in rows]
    return selected


def _extend(previous: dict, receipt: dict, freeze: dict) -> dict:
    """Keep the full V14 row prefix and append only selected source fields."""
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
        raise V15ReconciliationError("Reviewed V14 route prefix or frozen P1 differs")
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
        row["v15_reviewed_source_ids"] = [SOURCE] if selected else []
        row["v15_source_limits"] = {SOURCE: LIMIT} if selected else {}
        row["v15_source_record_refs"] = {SOURCE: refs[old["side"]]} if selected else {}
        allowed = {"targeted_integrated_source_ids"} if selected else set()
        if generic:
            allowed.add("candidate_or_design_source_ids")
        if any(row[key] != value for key, value in old.items() if key not in allowed):
            raise V15ReconciliationError("V14 row field changed")
        rows.append(row)
    counts = {}
    for side in "AB":
        subset = [row for row in rows if row["side"] == side]
        selected = [row for row in subset if row["v15_reviewed_source_ids"]]
        if (
            len(subset) != 283
            or len({row["task_id"] for row in subset}) != 283
            or len(selected) != 12
            or {row["task_id"] for row in selected} != TARGETS
            or sum(bool(row["targeted_integrated_source_ids"]) for row in subset) != 175
            or any(
                row["current_status"] != "NOT_STARTED"
                or row["current_conclusion"] != "NOT_RUN"
                or row["audit_task_credit"] is not False
                for row in subset
            )
        ):
            raise V15ReconciliationError("PRD concern route denominator differs")
        counts[side] = {
            **deepcopy(previous["counts"][side]),
            "v15_new_selected_prd_authored_leads": 3,
            "v15_new_selected_prd_generic_leads": 9,
            "v15_new_distinct_targeted_routes": 0,
            "v15_new_classification_promotions": 0,
        }
    if counts["A"] != counts["B"]:
        raise V15ReconciliationError("Paired PRD concern counts differ")
    pins = {**previous["source_pins"], **PINS}
    return {
        **previous,
        "schema": SCHEMA,
        "v14_prefix_sha256": PINS["v14_ledger"]["sha256"],
        "source_pins": pins,
        "source_pins_sha256": hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest(),
        "reviewed_source_roster": {
            **previous["reviewed_source_roster"],
            "additional_selected_prd_concern_versions": 21,
        },
        "counts": counts,
        "rows": rows,
        "limits": [
            *previous["limits"],
            "Only the twelve already-targeted PRD routes per side gain a bounded concern-intake "
            "source lead. Three authored clauses stay unsupported; nine generic routes stay "
            "partial. All 175 distinct targeted routes and 121 unsupported clauses persist.",
            LIMIT,
            "The frozen P1 pair remains at 409 NOT_STARTED/NOT_RUN tasks per side. No "
            "source completeness, accepted customer delivery, task credit, fresh pair, Key, "
            "grade or Atlas write.",
        ],
        "audit_task_credit": False,
        "active_pair_mutated": False,
    }


def build(repository: Path, private_repository: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise V15ReconciliationError("Frozen P1 inventory differs")
    paths = {name: _pin(repository, private, entry) for name, entry in PINS.items()}
    previous = prior.build(repository, private)
    if previous != json.loads(paths["v14_ledger"].read_text()):
        raise V15ReconciliationError("Reviewed V14 route replay differs")
    route_review = json.loads(paths["v14_review"].read_text())
    if (
        route_review.get("verdict") != "PASS_MAIN_SELECTED_OPERATING_LEAD_NO_CREDIT"
        or route_review.get("output_sha256", {}).get("LEDGER.json") != PINS["v14_ledger"]["sha256"]
        or route_review.get("p1_freeze") != freeze
        or route_review.get("audit_task_credit") is not False
        or route_review.get("source_complete") is not False
    ):
        raise V15ReconciliationError("V14 independent route review join differs")
    review = json.loads(paths["prd_review"].read_text())
    manifest = json.loads(paths["prd_manifest"].read_text())
    source_hashes = {
        name: PINS[key]["sha256"]
        for name, key in (
            ("MANIFEST.json", "prd_manifest"),
            ("RECEIPT.json", "prd_receipt"),
            ("company.sqlite3", "prd_db"),
        )
    }
    if (
        review.get("verdict") != "PASS_MAIN_SELECTED_PRD_CONCERN_NO_AUDIT_CREDIT"
        or review.get("main_run_sha256") != source_hashes
        or review.get("p1_freeze") != freeze
        or review.get("native_versions") != {"CLEAN": 8, "MESSY": 13}
        or review.get("source_complete") is not False
        or review.get("audit_task_credit") is not False
        or manifest.get("native_version_count") != 21
        or manifest.get("receipt_sha256") != PINS["prd_receipt"]["sha256"]
        or manifest.get("db_sha256") != PINS["prd_db"]["sha256"]
        or manifest.get("module_sha256") != PINS["prd_module"]["sha256"]
        or manifest.get("audit_task_credit") is not False
    ):
        raise V15ReconciliationError("PRD concern independent source review join differs")
    source.verify(private / SOURCE_RUN, repository=repository, private_repository=private)
    receipt = json.loads(paths["prd_receipt"].read_text())
    result = _extend(previous, receipt, freeze)
    if _p1_inventory(private) != freeze or any(
        _digest(path) != PINS[name]["sha256"] for name, path in paths.items()
    ):
        raise V15ReconciliationError("Pinned PRD input or P1 changed during build")
    return result


def markdown(result: dict) -> str:
    count = result["counts"]["A"]
    lines = [
        "# Paired 283-route PRD concern-intake reconciliation V15",
        "",
        "Twelve already-targeted SH-PRD-002/003/004 routes per side gain one reviewed "
        "fictional company-native concern-intake lead: 8 Clean and 13 Messy versions. "
        "Every V14 row field persists except the named source-ID appends.",
        "",
        "| Classification | Routes per side |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {name} | {number} |" for name, number in count["classifications"].items())
    lines += [
        "",
        "The claimant remains unverified. Clean holds its response draft at the unresolved "
        "contact/Legal gate. Messy preserves the omitted support role, denied dispatch "
        "attempt, false completion, correction and OPEN historical exception. There is no "
        "accepted fictional delivery or separate customer acknowledgment, and no real send.",
        "",
        "All three authored external-communication clauses remain UNSUPPORTED_EXACT_CLAUSE; "
        "the nine generic PRD routes remain SOURCE_CANDIDATE_PARTIAL. "
        f"All 121 unsupported clauses and {count['targeted_integrated_route_count']} "
        "distinct targeted routes per side retain their classification.",
        "",
        "No verified customer identity, notice authority, actual contract/ePHI/deployment, "
        "full population, source completeness, task credit, fresh pair, Key, grade or Atlas "
        "write follows. The frozen P1 pair retains 409 NOT_STARTED/NOT_RUN tasks per side.",
        "",
    ]
    return "\n".join(lines)
