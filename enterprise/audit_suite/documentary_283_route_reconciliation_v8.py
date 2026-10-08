"""Exact LEG001 source-lead successor to the reviewed 283-route V7 ledger."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from . import company_leg001_operating_docket_2027 as legal
from . import documentary_283_route_reconciliation_v3 as pinned
from . import documentary_283_route_reconciliation_v7 as prior

SCHEMA = "SH_DOCUMENTARY_283_PAIRED_ROUTE_CANDIDATE_RECONCILIATION_V8"
BASE = "enterprise/generated/audit-suite"
SOURCE = "LEG001_SELECTED_DOCKET_V1"
LIMIT = (
    "One fictional customer/service/BA/subcontractor chain and selected internal "
    "matter watch. Real HIPAA applicability and 2027 law are unverified; no complete "
    "company or external matter population, triggered proceeding, legal opinion, "
    "authored-clause satisfaction or audit credit. Messy flowdown and support "
    "omission remain historical exceptions."
)
V7_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V7_2026-09-30.json"
V7_REVIEW = (
    f"{BASE}/documentary-283-route-reconciliation-v7-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
LEGAL_ROOT = f"{BASE}/company-leg001-operating-docket-2027-09-30"
LEGAL_RUN = f"{LEGAL_ROOT}/main-run-v1"
LEGAL_REVIEW = f"{LEGAL_ROOT}/independent-review-main-v1/REVIEW.json"
PINS = {
    "v7_ledger": {
        "scope": "repo",
        "path": V7_LEDGER,
        "sha256": "a72d462a7b677bea6be6463b7fc91f48359c2c4b2abf878c9e92f3e7a52197c9",
    },
    "v7_review": {
        "scope": "private",
        "path": V7_REVIEW,
        "sha256": "c4405c5e5a5daa73c5d6936ce2b55327b65b3b0bcaad608bd0b9ab1a49108d90",
    },
    "legal_review": {
        "scope": "private",
        "path": LEGAL_REVIEW,
        "sha256": "3bd03221aaa69b11ba5a484c402ee12e17b67290b3732f5aab97dd3b54632cc6",
    },
    "legal_receipt": {
        "scope": "private",
        "path": f"{LEGAL_RUN}/RECEIPT.json",
        "sha256": "1f445ea96df4f5cbb9505a575be25e779470368b44747bcd46ee0889f3fb7584",
    },
    "legal_manifest": {
        "scope": "private",
        "path": f"{LEGAL_RUN}/MANIFEST.json",
        "sha256": "5d939d13644c2610198d8c15c75a8879a553d35b2e17f9f7730a8435f3127731",
    },
    "legal_db": {
        "scope": "private",
        "path": f"{LEGAL_RUN}/company.sqlite3",
        "sha256": "89045558b86513fefa5791bf5ad4749279962758d05099139ae576f0025a7cd2",
    },
}
IMMUTABLE = prior.IMMUTABLE
ROUTE_SUFFIXES = (
    "IMPLEMENTATION",
    "TOD",
    "TOE",
    "CHECK-HIPAA:160.102",
    "CHECK-HIPAA:160.103",
    "CHECK-HIPAA:164.104",
    "CHECK-HIPAA:160.306",
    "CHECK-HIPAA:160.504",
)
EXPECTED_CLASS = {
    "IMPLEMENTATION": "SOURCE_CANDIDATE_PARTIAL",
    "TOD": "SOURCE_CANDIDATE_PARTIAL",
    "TOE": "SOURCE_CANDIDATE_PARTIAL",
    "CHECK-HIPAA:160.102": "DESIGN_CONTEXT_ONLY",
    "CHECK-HIPAA:160.103": "DESIGN_CONTEXT_ONLY",
    "CHECK-HIPAA:164.104": "DESIGN_CONTEXT_ONLY",
    "CHECK-HIPAA:160.306": "UNSUPPORTED_EXACT_CLAUSE",
    "CHECK-HIPAA:160.504": "UNSUPPORTED_EXACT_CLAUSE",
}
LEAD_RECORDS = {
    "IMPLEMENTATION": (
        ("scope_decision", "LEG001-SCOPE-01"),
        ("reconciliation", "LEG001-SELECTED-RECON"),
    ),
    "TOD": (("scope_decision", "LEG001-SCOPE-01"), ("reconciliation", "LEG001-SELECTED-RECON")),
    "TOE": (("scope_decision", "LEG001-SCOPE-01"), ("reconciliation", "LEG001-SELECTED-RECON")),
    "CHECK-HIPAA:160.102": (("provision_status", "PROVISION-01"),),
    "CHECK-HIPAA:160.103": (("provision_status", "PROVISION-02"),),
    "CHECK-HIPAA:164.104": (("scope_decision", "LEG001-SCOPE-01"),),
    "CHECK-HIPAA:160.306": (
        ("provision_status", "PROVISION-07"),
        ("matter_watch", "MATTER-2027-12-31"),
    ),
    "CHECK-HIPAA:160.504": (
        ("provision_status", "PROVISION-08"),
        ("matter_watch", "MATTER-2027-12-31"),
    ),
}


class V8ReconciliationError(prior.V7ReconciliationError):
    """A reviewed source, exact lead or frozen audit task changed."""


def _selected_routes(previous: dict, receipt: dict) -> dict[str, set[str]]:
    """Select only source-matched LEG001 leads, never all 66 authored gaps."""
    if (
        receipt.get("selected_term_occurrences_per_branch") != 34
        or receipt.get("unsupported_authored_routes_per_side") != 66
        or receipt.get("selected_scope_complete") != {"CLEAN": True, "MESSY": False}
        or receipt.get("real_hipaa_applicability") != "UNDETERMINED"
        or receipt.get("source_complete") is not False
        or receipt.get("audit_task_credit") is not False
        or receipt.get("outside_message_sent") is not False
        or receipt.get("actual_phi") is not False
    ):
        raise V8ReconciliationError("Selected legal source boundary differs")
    selected = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        native = receipt["records"][scenario]
        if len(native) != 50 or Counter(row["system"] for row in native) != {
            "term_status": 34,
            "provision_status": 8,
            "matter_watch": 3,
            "change_watch": 3,
            "scope_decision": 1,
            "reconciliation": 1,
        }:
            raise V8ReconciliationError(f"Selected legal native population differs: {side}")
        rows = [
            row
            for row in previous["rows"]
            if row["side"] == side and row["control_id"] == "SH-LEG-001"
        ]
        by_suffix = {row["task_id"].split("-corporate-", 1)[1]: row for row in rows}
        if len(rows) != len(by_suffix) or any(s not in by_suffix for s in ROUTE_SUFFIXES):
            raise V8ReconciliationError(f"Selected legal route IDs differ: {side}")
        for suffix in ROUTE_SUFFIXES:
            row = by_suffix[suffix]
            if (
                row["classification"] != EXPECTED_CLASS[suffix]
                or (suffix in {"IMPLEMENTATION", "TOD", "TOE"})
                != (row["authored_test_clause"] is None)
                or (
                    row["authored_test_clause"] is not None
                    and row["remaining_test_gate"] != row["authored_test_clause"]
                )
            ):
                raise V8ReconciliationError(f"Selected legal clause differs: {side}/{suffix}")
        selected[side] = {by_suffix[s]["task_id"] for s in ROUTE_SUFFIXES}
    return selected


def build(repository: Path, private_repository: Path) -> dict:
    """Reperform reviewed V7 and attach eight exact legal leads per side."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    freeze = prior.prior._p1_inventory(private)
    if freeze != {
        "file_count": 538,
        "inventory_sha256": "f266ef682b502b3b093170f8a7b64fcf5cbab722d5c8ddf6715a63c0e535360f",
    }:
        raise V8ReconciliationError("Frozen active P1 inventory differs")
    loaded = {
        name: pinned._pinned(repository, private, private, entry)
        for name, entry in PINS.items()
        if name != "legal_db"
    }
    prior.prior._pinned_db(private, PINS["legal_db"])
    previous = prior.build(repository, private)
    if previous != loaded["v7_ledger"]:
        raise V8ReconciliationError("Reviewed exact V7 route prefix differs")
    review_v7 = loaded["v7_review"]
    if (
        review_v7.get("verdict")
        != "PASS_READ_ONLY_PARTIAL_PHYSICAL_ROUTE_RECONCILIATION_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or review_v7.get("main_tracked_sha256", {}).get(V7_LEDGER) != PINS["v7_ledger"]["sha256"]
        or review_v7.get("audit_task_credit") is not False
        or review_v7.get("active_pair_mutated") is not False
    ):
        raise V8ReconciliationError("V7 independent review boundary differs")
    review, receipt, manifest = (
        loaded[name] for name in ("legal_review", "legal_receipt", "legal_manifest")
    )
    if (
        review.get("verdict") != "PASS_PRIVATE_FICTIONAL_SOURCE_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or review.get("main_run_sha256")
        != {
            "RECEIPT.json": PINS["legal_receipt"]["sha256"],
            "MANIFEST.json": PINS["legal_manifest"]["sha256"],
            "company.sqlite3": PINS["legal_db"]["sha256"],
        }
        or review.get("real_hipaa_applicability") != "UNDETERMINED"
        or review.get("audit_task_credit") is not False
        or manifest.get("receipt_sha256") != PINS["legal_receipt"]["sha256"]
        or manifest.get("company_db_sha256") != PINS["legal_db"]["sha256"]
        or manifest.get("native_version_count") != 100
        or legal.verify(private / LEGAL_RUN, repository=repository, private_repository=private)
        != receipt
    ):
        raise V8ReconciliationError("Reviewed legal source boundary differs")
    selected = _selected_routes(previous, receipt)
    lead_refs = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        native = {(r["system"], r["record"]): r for r in receipt["records"][scenario]}
        if len(native) != 50:
            raise V8ReconciliationError(f"Selected legal native keys differ: {side}")
        lead_refs[side] = {}
        for suffix, keys in LEAD_RECORDS.items():
            if any(key not in native for key in keys):
                raise V8ReconciliationError(f"Selected legal source refs differ: {side}/{suffix}")
            lead_refs[side][suffix] = [
                {
                    key: native[record_key][key]
                    for key in (
                        "branch",
                        "system",
                        "record",
                        "version",
                        "sha256",
                        "event_at",
                        "available_at",
                    )
                }
                for record_key in keys
            ]
    rows = []
    for old in previous["rows"]:
        row = dict(old)
        added = old["task_id"] in selected[old["side"]]
        row["v8_reviewed_source_ids"] = [SOURCE] if added else []
        row["v8_source_limits"] = {SOURCE: LIMIT} if added else {}
        row["v8_source_record_refs"] = (
            {SOURCE: lead_refs[old["side"]][old["task_id"].split("-corporate-", 1)[1]]}
            if added
            else {}
        )
        if added:
            row["targeted_integrated_source_ids"] = sorted(
                set(old["targeted_integrated_source_ids"]) | {SOURCE}
            )
            if row["classification"] == "SOURCE_CANDIDATE_PARTIAL":
                row["candidate_or_design_source_ids"] = sorted(
                    set(old["candidate_or_design_source_ids"]) | {SOURCE}
                )
        if (
            any(row[key] != old[key] for key in IMMUTABLE)
            or row["classification"] != old["classification"]
        ):
            raise V8ReconciliationError("Frozen authored task, route class or result changed")
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
            or targeted != 169
            or sum(row["authored_test_clause"] is not None for row in subset) != 154
        ):
            raise V8ReconciliationError("Exact legal route denominator differs")
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
    if counts["A"] != counts["B"] or prior.prior._p1_inventory(private) != freeze:
        raise V8ReconciliationError("Paired result or frozen active pair differs")
    return {
        "schema": SCHEMA,
        "as_of": "2026-09-30",
        "v7_prefix_sha256": PINS["v7_ledger"]["sha256"],
        "source_pins": PINS,
        "source_pins_sha256": hashlib.sha256(json.dumps(PINS, sort_keys=True).encode()).hexdigest(),
        "p1_freeze": freeze,
        "active_p1_tasks": previous["active_p1_tasks"],
        "reviewed_source_roster": {
            **previous["reviewed_source_roster"],
            "additional_legal_docket_cohort_versions": 100,
        },
        "counts": counts,
        "rows": rows,
        "limits": [
            "Selected fictional source-search triage, not task or authored-clause satisfaction.",
            "Legal docket is one selected synthetic chain and internal matter watch; "
            "real HIPAA applicability remains undetermined.",
            "No all-company or external-matter nonoccurrence, 2027 law assertion, "
            "N/A acceptance or conditional-hearing credit.",
            "Messy BA flowdown and provider-support historical exceptions remain open.",
            "No actual operation, independent assurance, fresh pair, Key, grade or Atlas write.",
        ],
        "audit_task_credit": False,
        "active_pair_mutated": False,
    }


def markdown(result: dict) -> str:
    count = result["counts"]["A"]
    lines = [
        "# Paired 283-route LEG001 selected-docket reconciliation V8",
        "",
        "The exact 566-row JSON extends the independently reviewed V7 ledger with one "
        "selected fictional legal operating docket. Its 100 company-native versions "
        "remain outside the frozen P1 audit pair.",
        "",
        "| Classification | Routes per side |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {name} | {number} |" for name, number in count["classifications"].items())
    lines += [
        "",
        "169 distinct routes per side now have named source leads. Eight exact SH-LEG-001 "
        "routes per side gain this selected source: three generic partial gates, three "
        "role/applicability design rows and two conditional complaint/hearing authored "
        "clauses that remain unsupported. The ACTION-H-LEGAL-STATUS overlay clause "
        "and the other 64 unsupported LEG001 authored clauses gain no lead. All 121 "
        "unsupported authored clauses per side remain open.",
        "",
        "Real HIPAA applicability remains UNDETERMINED. The internal matter watch is "
        "not a full population or proof that no complaint or hearing occurred; "
        "2027 law and actual contracts require verification. Clean selected fictional "
        "scope is complete only within the synthetic chain. Messy historical BA "
        "flowdown and provider-support exceptions remain open. Both P1 sides remain "
        "409 NOT_STARTED/NOT_RUN tasks.",
        "",
        "No actual 2027 deployment, complete registry, collection, task credit, "
        "independent assurance, Key, grade or Atlas change.",
        "",
    ]
    return "\n".join(lines)
