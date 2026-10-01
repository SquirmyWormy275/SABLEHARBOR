"""Route one reviewed, selected governance cycle without committee or audit credit."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

from . import company_gov_selected_oversight_2027 as source
from . import documentary_283_route_reconciliation_v15 as prior
from .documentary_283_route_reconciliation_v6 import _p1_inventory
from .documentary_283_route_reconciliation_v12 import _pin

SCHEMA = "SH_DOCUMENTARY_283_PAIRED_ROUTE_CANDIDATE_RECONCILIATION_V16"
BASE = "enterprise/generated/audit-suite"
SOURCE = "GOV_SELECTED_OVERSIGHT_V1"
CONTROLS = ("SH-GOV-001", "SH-GOV-004")
AUTHORED = tuple(f"TASK-{control}-corporate-CHECK-SOC2:CC1.2" for control in CONTROLS)
GENERIC = tuple(
    f"TASK-{control}-corporate-{procedure}"
    for control in CONTROLS
    for procedure in ("IMPLEMENTATION", "TOD", "TOE")
)
TARGETS = set(AUTHORED + GENERIC)
CLAUSE = (
    "Inspect governing-body composition, conflicts and minutes challenging a control "
    "failure; a meeting calendar alone cannot demonstrate oversight."
)
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
    "One fictional 2027 selected Corporate Secretary/committee cycle, not a full "
    "governance population. Clean references only its SEC003 selected finding and closure. "
    "Messy references only its false-clean, self-review and OPEN exception; it preserves "
    "the omitted first packet, missing questionnaire, false close, later correction and "
    "OPEN historical governance exception. The 2026 locked charters are references, not "
    "newly adopted instruments. No actual Board meeting, legal quorum, adopted committee "
    "minutes, collective approval, independent assurance, full-period oversight, authored "
    "CC1.2 clause satisfaction, real deployment or PHI, source completeness or audit credit."
)
V15_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V15_2026-09-30.json"
V15_REVIEW = (
    f"{BASE}/documentary-283-route-reconciliation-v15-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
SOURCE_ROOT = f"{BASE}/company-gov-selected-oversight-2026-10-01"
SOURCE_RUN = f"{SOURCE_ROOT}/main-run-v1"
SOURCE_REVIEW = f"{SOURCE_ROOT}/independent-review-main-v1/REVIEW.json"
PINS = {
    "v15_ledger": {
        "scope": "repo",
        "path": V15_LEDGER,
        "sha256": "bb3b74930b256f5396d2393438236e2bd9a3dd654d829080d0927129954a535c",
    },
    "v15_review": {
        "scope": "private",
        "path": V15_REVIEW,
        "sha256": "b9c20621f2512aeb66b8b7d02ba87a5fcc64f705a13208f610209cfabf950ff7",
    },
    "gov_review": {
        "scope": "private",
        "path": SOURCE_REVIEW,
        "sha256": "54f59bd5a7db74ab29ead5d322908f4ad9e844c746c2f1b6f0cf3b0731bbcb01",
    },
    "gov_manifest": {
        "scope": "private",
        "path": f"{SOURCE_RUN}/MANIFEST.json",
        "sha256": "09cee311aac8f62cc5aee39626fccf67b6bbb5a8be4a1c218f533a7c7c7cbad4",
    },
    "gov_receipt": {
        "scope": "private",
        "path": f"{SOURCE_RUN}/RECEIPT.json",
        "sha256": "6c4b5a9c56e930e7875667fc3cd85e7825f69a5e4901f9d940c2f10ab29c40bd",
    },
    "gov_db": {
        "scope": "private",
        "path": f"{SOURCE_RUN}/company.sqlite3",
        "sha256": "81aef24a796a07e4daf2fc32f1dcfec10712a944b6d58f757eae2a73ef03228e",
    },
    "gov_module": {
        "scope": "repo",
        "path": "enterprise/audit_suite/company_gov_selected_oversight_2027.py",
        "sha256": "e1b747263b419de84b949c9014a2368921a8a07f8948761896f9e82f85b152ab",
    },
    "gov_spec": {
        "scope": "repo",
        "path": "enterprise/audit_suite/gov_selected_oversight_2027_spec_v1.json",
        "sha256": "ff5151cc7e788f502d0324b1aa859750284d36c80a7558817fd38aff923e23a6",
    },
}
P1_FREEZE = prior.P1_FREEZE
IDENTITY = source.SOURCE_FIELDS
ROSTER = {
    side: tuple((system, record) for _, system, record, *_ in source._plan(side))
    for side in source.BRANCHES
}


class V16ReconciliationError(prior.V15ReconciliationError):
    """The reviewed GOV source, V15 prefix, or no-credit boundary changed."""


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _selected_refs(receipt: dict, previous: dict) -> dict[str, list[dict]]:
    if (
        receipt.get("schema") != source.SCHEMA
        or receipt.get("branches") != source.BRANCHES
        or receipt.get("native_version_counts") != {"CLEAN": 9, "MESSY": 14}
        or receipt.get("selected_case_count") != 1
        or receipt.get("target_task_ids") != list(source.TARGETS)
        or receipt.get("spec_sha256") != PINS["gov_spec"]["sha256"]
        or receipt.get("source_pins") != {**source.TRACKED_PINS, **source.PRIVATE_PINS}
        or receipt.get("clean_selected_finding_status") != "CLOSED_SELECTED_ONLY"
        or receipt.get("messy_historical_sec003_exception_status") != "OPEN"
        or receipt.get("messy_historical_governance_exception_status") != "OPEN"
        or receipt.get("real_external_messages_sent") != 0
        or any(
            receipt.get(key) is not False
            for key in (
                "actual_board_meeting",
                "legal_quorum_established",
                "adopted_minutes",
                "complete_oversight_population",
                "authored_cc12_clause_satisfied",
                "independent_assurance_completed",
                "actual_phi_processing",
                "source_complete",
                "fresh_audit_pair_created",
                "audit_task_credit",
            )
        )
    ):
        raise V16ReconciliationError("GOV selected source scope or authority differs")
    refs = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        rows = receipt.get("records", {}).get(scenario, [])
        upstream = receipt.get("upstream_original_refs", {}).get(scenario, [])
        if (
            not isinstance(rows, list)
            or len(rows) != len(ROSTER[scenario])
            or tuple((row.get("system"), row.get("record")) for row in rows) != ROSTER[scenario]
            or not isinstance(upstream, list)
            or len(upstream) != (2 if scenario == "CLEAN" else 3)
            or any(item.get("branch") != source.sec3.BRANCHES[scenario] for item in upstream)
            or any(
                row.get("company") != source.COMPANY
                or row.get("branch") != source.BRANCHES[scenario]
                or row.get("version") != 1
                or row.get("origin") != "AUTHORED_TRAINING_SOURCE"
                or any(not row.get(key) for key in IDENTITY)
                for row in rows
            )
        ):
            raise V16ReconciliationError("GOV exact branch native roster differs")
        selected = [
            row for row in previous["rows"] if row["side"] == side and row["control_id"] in CONTROLS
        ]
        if len(selected) != 8 or {row["task_id"] for row in selected} != TARGETS:
            raise V16ReconciliationError("Eight exact GOV task identities differ")
        for row in selected:
            authored = row["task_id"] in AUTHORED
            procedure = row["task_id"].rsplit("-", 1)[1]
            if (
                row["classification"]
                != ("UNSUPPORTED_EXACT_CLAUSE" if authored else "DESIGN_CONTEXT_ONLY")
                or row["test_gate_basis"]
                != (
                    "AUTHORED_TASK_CLAUSE"
                    if authored
                    else "GENERIC_PROCEDURE_GATE_NOT_AN_AUTHORED_CLAUSE"
                )
                or row["authored_test_clause"] != (CLAUSE if authored else None)
                or row["remaining_test_gate"] != (CLAUSE if authored else GENERIC_GATES[procedure])
                or row["targeted_integrated_source_ids"] != []
                or row["candidate_or_design_source_ids"] != []
                or row["current_status"] != "NOT_STARTED"
                or row["current_conclusion"] != "NOT_RUN"
                or row["audit_task_credit"] is not False
            ):
                raise V16ReconciliationError("GOV exact authored/generic route gate differs")
        refs[side] = [{key: row[key] for key in IDENTITY} for row in rows]
    return refs


def _extend(previous: dict, receipt: dict, freeze: dict) -> dict:
    """Preserve V15 row fields and add only the eight specified GOV leads per side."""
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
        raise V16ReconciliationError("Reviewed V15 route prefix or frozen P1 differs")
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
            row["classification"] = "SOURCE_CANDIDATE_PARTIAL"
        row["v16_reviewed_source_ids"] = [SOURCE] if selected else []
        row["v16_source_limits"] = {SOURCE: LIMIT} if selected else {}
        row["v16_source_record_refs"] = {SOURCE: refs[old["side"]]} if selected else {}
        allowed = {"targeted_integrated_source_ids"} if selected else set()
        if generic:
            allowed.update(("candidate_or_design_source_ids", "classification"))
        if any(row[key] != value for key, value in old.items() if key not in allowed):
            raise V16ReconciliationError("V15 row field changed")
        rows.append(row)
    counts = {}
    for side in "AB":
        subset = [row for row in rows if row["side"] == side]
        selected = [row for row in subset if row["v16_reviewed_source_ids"]]
        classes = dict(sorted(Counter(row["classification"] for row in subset).items()))
        old_families = previous["counts"][side]["by_family"]
        families = {
            family: dict(
                sorted(
                    {
                        **{name: 0 for name in old_families[family]},
                        **Counter(
                            row["classification"] for row in subset if row["family"] == family
                        ),
                    }.items()
                )
            )
            for family in sorted({row["family"] for row in subset})
        }
        if (
            len(subset) != 283
            or len({row["task_id"] for row in subset}) != 283
            or len(selected) != 8
            or {row["task_id"] for row in selected} != TARGETS
            or sum(bool(row["targeted_integrated_source_ids"]) for row in subset) != 183
            or classes
            != {
                "DESIGN_CONTEXT_ONLY": 21,
                "SOURCE_CANDIDATE_PARTIAL": 141,
                "UNSUPPORTED_EXACT_CLAUSE": 121,
            }
            or any(
                row["current_status"] != "NOT_STARTED"
                or row["current_conclusion"] != "NOT_RUN"
                or row["audit_task_credit"] is not False
                for row in subset
            )
        ):
            raise V16ReconciliationError("GOV route denominator or no-credit boundary differs")
        if any(
            families[name] != value
            for name, value in old_families.items()
            if name != "risk_assurance_governance"
        ):
            raise V16ReconciliationError("Unrelated family count changed")
        risk_old = old_families["risk_assurance_governance"]
        if families["risk_assurance_governance"] != {
            "DESIGN_CONTEXT_ONLY": risk_old["DESIGN_CONTEXT_ONLY"] - 6,
            "SOURCE_CANDIDATE_PARTIAL": risk_old["SOURCE_CANDIDATE_PARTIAL"] + 6,
            "UNSUPPORTED_EXACT_CLAUSE": risk_old["UNSUPPORTED_EXACT_CLAUSE"],
        }:
            raise V16ReconciliationError("Only six GOV generic classifications may promote")
        counts[side] = {
            **deepcopy(previous["counts"][side]),
            "classifications": classes,
            "by_family": families,
            "targeted_integrated_route_count": 183,
            "v16_new_selected_gov_authored_leads": 2,
            "v16_new_selected_gov_generic_leads": 6,
            "v16_new_distinct_targeted_routes": 8,
            "v16_new_classification_promotions": 6,
        }
    if counts["A"] != counts["B"]:
        raise V16ReconciliationError("Paired GOV counts differ")
    pins = {**previous["source_pins"], **PINS}
    return {
        **previous,
        "schema": SCHEMA,
        "v15_prefix_sha256": PINS["v15_ledger"]["sha256"],
        "source_pins": pins,
        "source_pins_sha256": hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest(),
        "reviewed_source_roster": {
            **previous["reviewed_source_roster"],
            "additional_selected_gov_oversight_versions": 23,
        },
        "counts": counts,
        "rows": rows,
        "limits": [
            *previous["limits"],
            "Eight previously untargeted GOV-001/GOV-004 routes per side gain a selected "
            "company-native lead. Two authored CC1.2 clauses stay unsupported and six "
            "generic gates become partial; 183 targeted routes and 121 unsupported clauses "
            "per side remain unrun.",
            LIMIT,
            "The frozen P1 pair retains 409 NOT_STARTED/NOT_RUN tasks per side. No "
            "source completeness, collective approval, task credit, fresh pair, Key, grade "
            "or Atlas write.",
        ],
        "audit_task_credit": False,
        "active_pair_mutated": False,
    }


def build(repository: Path, private_repository: Path) -> dict:
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise V16ReconciliationError("Frozen P1 inventory differs")
    paths = {name: _pin(repository, private, entry) for name, entry in PINS.items()}
    previous = prior.build(repository, private)
    if previous != json.loads(paths["v15_ledger"].read_text()):
        raise V16ReconciliationError("Reviewed V15 route replay differs")
    route_review = json.loads(paths["v15_review"].read_text())
    if (
        route_review.get("verdict") != "PASS_MAIN_HELD_CONCERN_LEAD_NO_CREDIT"
        or route_review.get("output_sha256", {}).get("LEDGER.json") != PINS["v15_ledger"]["sha256"]
        or route_review.get("p1_freeze") != freeze
        or route_review.get("audit_task_credit") is not False
        or route_review.get("source_complete") is not False
    ):
        raise V16ReconciliationError("V15 independent route review join differs")
    review = json.loads(paths["gov_review"].read_text())
    manifest = json.loads(paths["gov_manifest"].read_text())
    source_hashes = {
        name: PINS[key]["sha256"]
        for name, key in (
            ("MANIFEST.json", "gov_manifest"),
            ("RECEIPT.json", "gov_receipt"),
            ("company.sqlite3", "gov_db"),
        )
    }
    if (
        review.get("verdict") != "PASS_MAIN_SELECTED_GOV_SOURCE_NO_AUDIT_CREDIT"
        or review.get("main_run_sha256") != source_hashes
        or review.get("p1_freeze") != freeze
        or review.get("native_versions") != {"CLEAN": 9, "MESSY": 14}
        or review.get("source_complete") is not False
        or review.get("fresh_audit_pair_created") is not False
        or review.get("audit_task_credit") is not False
        or manifest.get("native_version_count") != 23
        or manifest.get("receipt_sha256") != PINS["gov_receipt"]["sha256"]
        or manifest.get("db_sha256") != PINS["gov_db"]["sha256"]
        or manifest.get("module_sha256") != PINS["gov_module"]["sha256"]
        or manifest.get("audit_task_credit") is not False
    ):
        raise V16ReconciliationError("GOV independent source review join differs")
    source.verify(private / SOURCE_RUN, repository=repository, private_repository=private)
    receipt = json.loads(paths["gov_receipt"].read_text())
    result = _extend(previous, receipt, freeze)
    if _p1_inventory(private) != freeze or any(
        _digest(path) != PINS[name]["sha256"] for name, path in paths.items()
    ):
        raise V16ReconciliationError("Pinned GOV input or P1 changed during build")
    return result


def markdown(result: dict) -> str:
    count = result["counts"]["A"]
    lines = [
        "# Paired 283-route selected governance reconciliation V16",
        "",
        "Eight previously untargeted SH-GOV-001/004 routes per side gain one reviewed "
        "fictional 2027 company-native committee-cycle lead: 9 Clean and 14 Messy "
        "versions. Every V15 row field persists except the named source-ID appends and six "
        "generic classification promotions.",
        "",
        "| Classification | Routes per side |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {name} | {number} |" for name, number in count["classifications"].items())
    lines += [
        "",
        "Clean uses only branch-matched SEC003 selected finding/closure originals. Messy "
        "uses only branch-matched false-clean, self-review and OPEN exception originals. "
        "Its omitted first packet, missing questionnaire and false close remain visible after "
        "later correction; both SEC003 and governance historical exceptions remain OPEN.",
        "",
        "The two authored CC1.2 clauses remain UNSUPPORTED_EXACT_CLAUSE. The six generic "
        "GOV routes become SOURCE_CANDIDATE_PARTIAL discovery leads. "
        f"All 121 unsupported clauses and {count['targeted_integrated_route_count']} "
        "distinct targeted routes per side remain unrun.",
        "",
        "No actual Board meeting, legal quorum, adopted minutes, collective committee "
        "approval, independent assurance, complete oversight period, clause satisfaction, "
        "source completeness, task credit, fresh pair, Key, grade or Atlas write follows. "
        "The frozen P1 pair retains 409 NOT_STARTED/NOT_RUN tasks per side.",
        "",
    ]
    return "\n".join(lines)
