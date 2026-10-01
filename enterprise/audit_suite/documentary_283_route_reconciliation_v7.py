"""Exact physical-site source successor to the reviewed 283-route V6 ledger."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from . import company_physical_site_2027 as physical
from . import documentary_283_route_reconciliation_v3 as pinned
from . import documentary_283_route_reconciliation_v6 as prior

SCHEMA = "SH_DOCUMENTARY_283_PAIRED_ROUTE_CANDIDATE_RECONCILIATION_V7"
BASE = "enterprise/generated/audit-suite"
SOURCE = "PHYSICAL_SITE_SELECTED_V1"
LIMIT = (
    "One fictional two-cage Reno/Boise source: no provider building perimeter, "
    "complete access/environmental population, site-failure recovery proof or "
    "independent assurance. Messy false closure, unescorted entry and historical "
    "open exception remain."
)
V6_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V6_2026-09-30.json"
V6_REVIEW = (
    f"{BASE}/documentary-283-route-reconciliation-v6-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
PHYSICAL_ROOT = f"{BASE}/company-physical-site-selected-2026-09-30"
PHYSICAL_RUN = f"{PHYSICAL_ROOT}/main-run-v1"
PHYSICAL_REVIEW = f"{PHYSICAL_ROOT}/independent-review-main-v1/REVIEW.json"
PINS = {
    "v6_ledger": {
        "scope": "repo",
        "path": V6_LEDGER,
        "sha256": "45a88eb3b82a20d2be417a1f301f6103087748d721c392edcc24a476a77e5dfe",
    },
    "v6_review": {
        "scope": "private",
        "path": V6_REVIEW,
        "sha256": "fe373c67bc5938a3263a1bcc85b51b1be55352748a1c3bee379d0b01a233d751",
    },
    "physical_review": {
        "scope": "private",
        "path": PHYSICAL_REVIEW,
        "sha256": "1c7ccc1ce9abeab01f265238e63f84df4defa70948a46c99047d138a449fa0f3",
    },
    "physical_receipt": {
        "scope": "private",
        "path": f"{PHYSICAL_RUN}/RECEIPT.json",
        "sha256": "fd82fbbfa3c5d03a35c935673fe9ec973ccb905d57e09df52fb943522ba6e485",
    },
    "physical_manifest": {
        "scope": "private",
        "path": f"{PHYSICAL_RUN}/MANIFEST.json",
        "sha256": "5c8cf04de73f987d3555efe54f6d6fd238e005b0574bff61b90c251e46f2e7a5",
    },
    "physical_db": {
        "scope": "private",
        "path": f"{PHYSICAL_RUN}/company.sqlite3",
        "sha256": "19a358a258a8da7054f9f1946cb9e49e98dfe4def3da06d33e635ff2fe6ca816",
    },
}
IMMUTABLE = (
    "side",
    "task_id",
    "family",
    "control_id",
    "procedure_type",
    "authored_test_clause",
    "test_gate_basis",
    "requirement_ids",
    "screen_row_sha256",
    "remaining_test_gate",
    "current_status",
    "current_conclusion",
    "actual_operation_eligibility_as_of_packet",
    "audit_task_credit",
)


class V7ReconciliationError(prior.V6ReconciliationError):
    """A reviewed source, route, or frozen audit task changed."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _selected_routes(receipt: dict, previous: dict) -> dict[str, set[str]]:
    selected: dict[str, set[str]] = {}
    for side in "AB":
        expected = {
            row["task_id"]: row
            for row in previous["rows"]
            if row["side"] == side
            and (
                (
                    row["control_id"] == "SH-BCM-004"
                    and (
                        row["procedure_type"] in {"IMPLEMENTATION", "TOD", "TOE"}
                        or row["task_id"].endswith("CHECK-SOC2:CC9.1")
                    )
                )
                or (
                    row["control_id"] == "SH-SEC-001"
                    and (
                        row["procedure_type"] in {"IMPLEMENTATION", "TOD", "TOE"}
                        or row["task_id"].endswith(("CHECK-SOC2:CC6.4", "CHECK-SOC2:A1.2"))
                    )
                )
            )
        }
        supplied = receipt["selected_routes"][side]
        if (
            len(expected) != 9
            or len(supplied) != 9
            or {r["task_id"] for r in supplied} != set(expected)
        ):
            raise V7ReconciliationError(f"Exact nine physical route IDs differ: {side}")
        for row in supplied:
            old = expected[row["task_id"]]
            if any(
                row[key] != old[key]
                for key in (
                    "control_id",
                    "authored_test_clause",
                    "remaining_test_gate",
                    "classification",
                )
            ):
                raise V7ReconciliationError(
                    f"Physical route clause or classification differs: {side}"
                )
        selected[side] = set(expected)
    return selected


def build(repository: Path, private_repository: Path) -> dict:
    """Reperform both reviewed histories and classify only nine exact routes per side."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    freeze = prior._p1_inventory(private)
    if freeze != {
        "file_count": 538,
        "inventory_sha256": "f266ef682b502b3b093170f8a7b64fcf5cbab722d5c8ddf6715a63c0e535360f",
    }:
        raise V7ReconciliationError("Frozen active P1 inventory differs")
    loaded = {
        name: pinned._pinned(repository, private, private, entry)
        for name, entry in PINS.items()
        if name != "physical_db"
    }
    prior._pinned_db(private, PINS["physical_db"])
    previous = prior.build(repository, private)
    if previous != loaded["v6_ledger"]:
        raise V7ReconciliationError("Reviewed exact V6 route prefix differs")
    v6_review = loaded["v6_review"]
    if (
        v6_review.get("verdict")
        != "PASS_READ_ONLY_PARTIAL_ROUTE_RECONCILIATION_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or v6_review.get("main_tracked_sha256", {}).get(V6_LEDGER) != PINS["v6_ledger"]["sha256"]
        or v6_review.get("audit_task_credit") is not False
        or v6_review.get("active_pair_mutated") is not False
    ):
        raise V7ReconciliationError("V6 independent review boundary differs")
    review, receipt, manifest = (
        loaded[name] for name in ("physical_review", "physical_receipt", "physical_manifest")
    )
    if (
        review.get("verdict")
        != "PASS_PRIVATE_FICTIONAL_SOURCE_FOR_INTEGRATION_REVIEW_NO_AUDIT_CREDIT"
        or review.get("main_run_v1_sha256")
        != {
            "RECEIPT.json": PINS["physical_receipt"]["sha256"],
            "MANIFEST.json": PINS["physical_manifest"]["sha256"],
            "company.sqlite3": PINS["physical_db"]["sha256"],
        }
        or review.get("active_p1_mutated") is not False
        or review.get("audit_task_credit") is not False
        or manifest.get("receipt_sha256") != PINS["physical_receipt"]["sha256"]
        or manifest.get("company_db_sha256") != PINS["physical_db"]["sha256"]
        or manifest.get("native_version_count") != 31
        or receipt.get("native_version_counts") != {"CLEAN": 13, "MESSY": 18}
        or receipt.get("messy_false_close_preserved") is not True
        or receipt.get("messy_unescorted_entry_preserved") is not True
        or receipt.get("messy_historical_exception_status") != "OPEN"
        or receipt.get("authored_clauses_satisfied") is not False
        or receipt.get("provider_and_enterprise_population_complete") is not False
        or receipt.get("actual_operation_eligibility_as_of_2026_09_30") is not False
        or receipt.get("audit_task_credit") is not False
        or physical.verify(
            private / PHYSICAL_RUN, repository=repository, private_repository=private
        )
        != receipt
    ):
        raise V7ReconciliationError("Reviewed physical source boundary differs")
    selected = _selected_routes(receipt, previous)
    rows = []
    for old in previous["rows"]:
        row = dict(old)
        added = old["task_id"] in selected[old["side"]]
        row["v7_reviewed_source_ids"] = [SOURCE] if added else []
        row["v7_source_limits"] = {SOURCE: LIMIT} if added else {}
        if added:
            row["targeted_integrated_source_ids"] = sorted(
                set(old["targeted_integrated_source_ids"]) | {SOURCE}
            )
            if row["classification"] == "DESIGN_CONTEXT_ONLY":
                if row["control_id"] != "SH-SEC-001" or row["authored_test_clause"] is not None:
                    raise V7ReconciliationError("Unexpected physical generic promotion")
                row["classification"] = "SOURCE_CANDIDATE_PARTIAL"
            if row["classification"] == "SOURCE_CANDIDATE_PARTIAL":
                row["candidate_or_design_source_ids"] = sorted(
                    set(old["candidate_or_design_source_ids"]) | {SOURCE}
                )
        if any(row[key] != old[key] for key in IMMUTABLE):
            raise V7ReconciliationError("Frozen authored task or result changed")
        rows.append(row)
    counts = {}
    for side in "AB":
        subset = [row for row in rows if row["side"] == side]
        classes = dict(sorted(Counter(row["classification"] for row in subset).items()))
        targeted = sum(bool(row["targeted_integrated_source_ids"]) for row in subset)
        if (
            len(subset) != len({row["task_id"] for row in subset})
            or len(subset) != 283
            or len({row["control_id"] for row in subset}) != 43
            or classes
            != {
                "DESIGN_CONTEXT_ONLY": 30,
                "SOURCE_CANDIDATE_PARTIAL": 132,
                "UNSUPPORTED_EXACT_CLAUSE": 121,
            }
            or targeted != 167
            or sum(row["authored_test_clause"] is not None for row in subset) != 154
        ):
            raise V7ReconciliationError("Exact physical route denominator differs")
        counts[side] = {
            "classifications": classes,
            "targeted_integrated_route_count": targeted,
            "authored_clause_count": 154,
            "inferred_gate_count": 129,
            "by_family": {
                family: dict(
                    sorted(
                        Counter(
                            row["classification"] for row in subset if row["family"] == family
                        ).items()
                    )
                )
                for family in sorted({row["family"] for row in subset})
            },
        }
    if counts["A"] != counts["B"] or prior._p1_inventory(private) != freeze:
        raise V7ReconciliationError("Paired result or frozen active pair differs")
    return {
        "schema": SCHEMA,
        "as_of": "2026-09-30",
        "v6_prefix_sha256": PINS["v6_ledger"]["sha256"],
        "source_pins": PINS,
        "source_pins_sha256": hashlib.sha256(json.dumps(PINS, sort_keys=True).encode()).hexdigest(),
        "p1_freeze": freeze,
        "active_p1_tasks": previous["active_p1_tasks"],
        "reviewed_source_roster": {
            "v7_portfolio_cohorts": 28,
            "v7_portfolio_native_versions": 529,
            "additional_physical_site_cohort_versions": 31,
            "source_complete": False,
        },
        "counts": counts,
        "rows": rows,
        "limits": [
            "Selected fictional source-search triage, not task or authored-clause satisfaction.",
            "Physical site covers only two cages; provider perimeters and full "
            "populations remain open.",
            "Messy false close, unescorted entry and historical exception remain open.",
            "No actual site operation, independent assurance, fresh pair, collection, "
            "Key, grade or Atlas write.",
        ],
        "audit_task_credit": False,
        "active_pair_mutated": False,
    }


def markdown(result: dict) -> str:
    count = result["counts"]["A"]
    lines = [
        "# Paired 283-route physical-site source reconciliation V7",
        "",
        "The exact 566-row JSON extends the independently reviewed V6 ledger with "
        "one selected fictional Reno/Boise physical-site source. Its 31 native "
        "versions remain company records, outside the frozen P1 audit pair.",
        "",
        "| Classification | Routes per side |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {name} | {number} |" for name, number in count["classifications"].items())
    lines += [
        "",
        "167 distinct routes per side now have named source leads. The three "
        "generic SH-SEC-001 discovery gates move from design context to partial "
        "source leads. SH-SEC-001 CC6.4 and A1.2 remain unsupported exact "
        "clauses despite the selected site source; SH-BCM-004 CC9.1 remains "
        "partial. All 121 unsupported authored clauses per side remain open.",
        "",
        "The Messy October false badge/visitor closure, unescorted expired entry, "
        "November self-recheck and open historical exception are retained. "
        "Provider building perimeters, full period populations and site-failure "
        "recovery capacity still require source and procedures. Both P1 sides "
        "remain 409 NOT_STARTED/NOT_RUN tasks.",
        "",
        "No actual 2027 deployment, complete registry, collection, task credit, "
        "independent assurance, Key, grade or Atlas change.",
        "",
    ]
    return "\n".join(lines)
