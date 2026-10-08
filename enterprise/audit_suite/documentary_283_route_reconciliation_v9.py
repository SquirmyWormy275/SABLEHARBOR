"""One pending addressable-docket design lead on the exact reviewed V8 route ledger."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path

from . import company_addressable_docket_exercise as addressable
from . import documentary_283_route_reconciliation_v3 as pinned
from . import documentary_283_route_reconciliation_v6 as frozen
from . import documentary_283_route_reconciliation_v8 as prior
from . import fictional_2027_candidate_registry_v10 as candidate_v10
from . import fictional_2027_source_portfolio_v10 as portfolio_v10

SCHEMA = "SH_DOCUMENTARY_283_PAIRED_ROUTE_CANDIDATE_RECONCILIATION_V9"
BASE = "enterprise/generated/audit-suite"
SOURCE = "ADDRESSABLE_PENDING_DOCKET_V1"
LIMIT = (
    "Twenty-two prospective source-locator cases per side are pending, not addressable "
    "decisions. No actual service/ePHI environment, qualified applicability, selected "
    "specification, reasoned alternative, approval, implemented safeguard or waiver is "
    "established. Messy blanket-waiver history remains open; SH-POL-003 source gap remains open."
)
V8_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V8_2026-09-30.json"
V8_REVIEW = (
    f"{BASE}/documentary-283-route-reconciliation-v8-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
V10_ROOT = f"{BASE}/company-source-portfolio-v10-2026-09-30"
V10_REVIEW = f"{V10_ROOT}/independent-review-main-v1/REVIEW.json"
V10_PORTFOLIO = f"{V10_ROOT}/main-run-v1/REPORT.json"
V10_CANDIDATE = f"{V10_ROOT}/main-candidate-v1"
ADDR_ROOT = f"{BASE}/{portfolio_v10.ADDR_FOLDER}"
ADDR_REVIEW = f"{BASE}/{portfolio_v10.ADDR_REVIEW_FOLDER}/REVIEW.json"
ADDR_RUN = f"{ADDR_ROOT}/{portfolio_v10.ADDR_RUN}"
PINS = {
    "v8_ledger": {
        "scope": "repo",
        "path": V8_LEDGER,
        "sha256": "6e92adbfeeda9b43f525036e43f978f6d3653ff314ec4fd8a44ffc57f1b56ec9",
    },
    "v8_review": {
        "scope": "private",
        "path": V8_REVIEW,
        "sha256": "3587f7ec4fe0082a8f93d6e0565f6758a1f7b4bc0d6e43c8bd47cb7b012f86ea",
    },
    "v10_review": {
        "scope": "private",
        "path": V10_REVIEW,
        "sha256": "395336ae7c9bdb68ceba5e3da19732e01fbc9b11c6c1bbed7d0438c02f6a3497",
    },
    "v10_portfolio": {
        "scope": "private",
        "path": V10_PORTFOLIO,
        "sha256": "5e76c4be99824fade2fdc6c7a9b462090990aa3803a07b2e17ff8227c7eada0a",
    },
    "v10_candidate_a": {
        "scope": "private",
        "path": f"{V10_CANDIDATE}/A.json",
        "sha256": "9c74e512b5ac1a780d927c9ba1c7860cd0da4fc5fc6c4d4401bc60c92a7d6801",
    },
    "v10_candidate_b": {
        "scope": "private",
        "path": f"{V10_CANDIDATE}/B.json",
        "sha256": "477fbed64bdebb7e1d91c2cdfb163d762d20f6127f6bd42f43edf4fc5debeecc",
    },
    "v10_candidate_report": {
        "scope": "private",
        "path": f"{V10_CANDIDATE}/REPORT.json",
        "sha256": "9753f9af7236e1b014361596e6f24c1407c0c29dfacdab7248b093f6d76bdbdf",
    },
    "addressable_review": {
        "scope": "private",
        "path": ADDR_REVIEW,
        "sha256": portfolio_v10.ADDR_REVIEW_SHA,
    },
    "addressable_manifest": {
        "scope": "private",
        "path": f"{ADDR_RUN}/MANIFEST.json",
        "sha256": portfolio_v10.ADDR_MANIFEST_SHA,
    },
    "addressable_receipt": {
        "scope": "private",
        "path": f"{ADDR_RUN}/RECEIPT.json",
        "sha256": portfolio_v10.ADDR_RECEIPT_SHA,
    },
    "addressable_db": {
        "scope": "private",
        "path": f"{ADDR_RUN}/company.sqlite3",
        "sha256": portfolio_v10.ADDR_DB_SHA,
    },
}
P1_FREEZE = {
    "file_count": 538,
    "inventory_sha256": "f266ef682b502b3b093170f8a7b64fcf5cbab722d5c8ddf6715a63c0e535360f",
}
ACTION = "TASK-SH-POL-003-corporate-ACTION-H-ADDRESSABLE"
GENERIC = {
    "TASK-SH-POL-003-corporate-IMPLEMENTATION",
    "TASK-SH-POL-003-corporate-TOD",
    "TASK-SH-POL-003-corporate-TOE",
}
IDENTITY = (
    "branch",
    "system",
    "record",
    "version",
    "sha256",
    "event_at",
    "available_at",
    "imported_at",
)


class V9ReconciliationError(prior.V8ReconciliationError):
    """A reviewed pending docket, exact route, or frozen audit task changed."""


def _selected_refs(receipt: dict, database: Path) -> dict[str, list[dict]]:
    """Require all 22 cases to remain pending and bind them to native content."""
    if (
        receipt.get("source_locator_count") != 22
        or receipt.get("final_docket_counts") != {"CLEAN": 22, "MESSY": 22}
        or receipt.get("final_states") != {"CLEAN": "PENDING_REVIEW", "MESSY": "QUARANTINED"}
        or receipt.get("open_exception_counts") != {"CLEAN": 0, "MESSY": 1}
        or receipt.get("related_sh_pol003_gap") != "OPEN_INSUFFICIENT_SOURCE_UNCHANGED"
        or receipt.get("qualification") != addressable.QUALIFICATION
    ):
        raise V9ReconciliationError("Pending addressable docket boundary differs")
    selected = {}
    with sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise V9ReconciliationError("Addressable native database integrity differs")
        for scenario, branch, count, gate in (
            ("CLEAN", "ADDR-CLEAN", 24, "GATE-02"),
            ("MESSY", "ADDR-MESSY", 26, "GATE-04"),
        ):
            refs = receipt["records"][scenario]
            candidates = [ref for ref in refs if ref["system"] == "addressable_candidate"]
            events = [ref for ref in refs if ref["system"] == "docket_event"]
            if (
                len(refs) != count
                or len(candidates) != 22
                or len(events) != count - 22
                or {ref["record"] for ref in candidates}
                != {f"SPEC-{index:02d}" for index in range(1, 23)}
                or {ref["record"] for ref in events}
                != {f"GATE-{index:02d}" for index in range(1, count - 21)}
                or any(ref["branch"] != branch or ref["version"] != 1 for ref in refs)
            ):
                raise V9ReconciliationError("Exact pending native case roster differs")
            locators = set()
            for ref in candidates + [next(ref for ref in events if ref["record"] == gate)]:
                rows = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    tuple(ref[key] for key in ("company", "branch", "system", "record", "version")),
                ).fetchall()
                if len(rows) != 1:
                    raise V9ReconciliationError("Selected addressable native version missing")
                native = rows[0]
                if (
                    native["sha256"] != ref["sha256"]
                    or hashlib.sha256(native["content"]).hexdigest() != ref["sha256"]
                    or any(
                        native[key] != ref[key]
                        for key in ("event_at", "available_at", "imported_at")
                    )
                ):
                    raise V9ReconciliationError("Selected addressable native tuple differs")
                body = json.loads(native["content"])
                if ref["system"] == "addressable_candidate":
                    locators.add(body["source_locator"])
                    if (
                        body.get("docket_state") != "PENDING_ENVIRONMENT_AND_QUALIFIED_LEGAL_REVIEW"
                        or body.get("entity_role_and_hipaa_applicability") != "UNDETERMINED"
                        or body.get("source_disposition") != "ENVIRONMENTAL_DECISION_REQUIRED"
                        or body.get("generic_waiver_effect") != "NONE"
                        or body.get("related_generic_exception_control_id") != "SH-POL-003"
                        or any(
                            body.get(key) is not None
                            for key in (
                                "actual_service_environment",
                                "actual_ephi_systems",
                                "selected_specification",
                                "reasonableness_analysis",
                                "equivalent_alternative_analysis",
                                "nonimplementation_rationale",
                                "implemented_safeguard_evidence",
                                "approver_id",
                                "approval_at",
                            )
                        )
                    ):
                        raise V9ReconciliationError("Addressable case promoted beyond pending")
                elif (
                    body.get("after")
                    != ("PENDING_REVIEW" if scenario == "CLEAN" else "QUARANTINED")
                    or body.get("actual_hipaa_applicability") != "UNDETERMINED"
                    or body.get("candidate_decision_status")
                    != "ALL_PENDING_NO_IMPLEMENTATION_SELECTION"
                    or body.get("actual_legal_approval") is not False
                    or body.get("actual_owner_approval") is not False
                    or body.get("approved_substitution") is not False
                    or body.get("implemented_safeguards_claimed") is not False
                    or body.get("exception_open") is not (scenario == "MESSY")
                ):
                    raise V9ReconciliationError("Final addressable gate promoted beyond pending")
            if len(locators) != 22:
                raise V9ReconciliationError("Duplicate addressable source locator")
            selected["A" if scenario == "CLEAN" else "B"] = [
                {key: ref[key] for key in IDENTITY}
                for ref in [*candidates, next(ref for ref in events if ref["record"] == gate)]
            ]
    return selected


def _extend(previous: dict, receipt: dict, database: Path, freeze: dict) -> dict:
    """Append one design-context lead per side and keep every V8 field exact."""
    if (
        previous.get("schema") != prior.SCHEMA
        or previous.get("p1_freeze") != freeze
        or previous.get("audit_task_credit") is not False
        or previous.get("active_pair_mutated") is not False
        or len(previous.get("rows", [])) != 566
        or previous.get("counts", {}).get("A") != previous.get("counts", {}).get("B")
        or previous["counts"]["A"]["classifications"]
        != {
            "DESIGN_CONTEXT_ONLY": 30,
            "SOURCE_CANDIDATE_PARTIAL": 132,
            "UNSUPPORTED_EXACT_CLAUSE": 121,
        }
        or previous["counts"]["A"]["targeted_integrated_route_count"] != 169
    ):
        raise V9ReconciliationError("Reviewed V8 route prefix/denominator differs")
    refs = _selected_refs(receipt, database)
    rows = []
    for old in previous["rows"]:
        row = dict(old)
        selected = old["task_id"] == ACTION
        if selected:
            if (
                old["control_id"] != "SH-POL-003"
                or old["classification"] != "DESIGN_CONTEXT_ONLY"
                or old["authored_test_clause"] is None
                or old["remaining_test_gate"] != old["authored_test_clause"]
                or old["current_status"] != "NOT_STARTED"
                or old["current_conclusion"] != "NOT_RUN"
                or old["audit_task_credit"] is not False
                or old["actual_operation_eligibility_as_of_packet"] is not False
            ):
                raise V9ReconciliationError("Addressable authored action boundary differs")
            row["targeted_integrated_source_ids"] = sorted(
                set(old["targeted_integrated_source_ids"]) | {SOURCE}
            )
        if old["task_id"] in GENERIC and (
            old["control_id"] != "SH-POL-003"
            or old["classification"] != "SOURCE_CANDIDATE_PARTIAL"
            or old["authored_test_clause"] is not None
        ):
            raise V9ReconciliationError("Generic SH-POL-003 source gate differs")
        row["v9_reviewed_source_ids"] = [SOURCE] if selected else []
        row["v9_source_limits"] = {SOURCE: LIMIT} if selected else {}
        row["v9_source_record_refs"] = {SOURCE: refs[old["side"]]} if selected else {}
        if (
            any(row[key] != old[key] for key in prior.IMMUTABLE)
            or row["classification"] != old["classification"]
        ):
            raise V9ReconciliationError("Frozen authored route/classification changed")
        rows.append(row)
    counts = {}
    for side in "AB":
        subset = [row for row in rows if row["side"] == side]
        lead = [row for row in subset if row["v9_reviewed_source_ids"]]
        generic = [row for row in subset if row["task_id"] in GENERIC]
        classes = dict(sorted(Counter(row["classification"] for row in subset).items()))
        targeted = sum(bool(row["targeted_integrated_source_ids"]) for row in subset)
        if (
            len(subset) != len({row["task_id"] for row in subset})
            or len(subset) != 283
            or len(lead) != 1
            or lead[0]["task_id"] != ACTION
            or len(generic) != 3
            or any(row["v9_reviewed_source_ids"] for row in generic)
            or classes != previous["counts"][side]["classifications"]
            or targeted != 170
            or sum(row["authored_test_clause"] is not None for row in subset) != 154
        ):
            raise V9ReconciliationError("Exact one-lead 283-route denominator differs")
        counts[side] = {
            **previous["counts"][side],
            "targeted_integrated_route_count": targeted,
            "v9_new_pending_design_context_leads": 1,
            "v9_generic_gate_leads": 0,
            "v9_addressable_decisions": 0,
        }
    if counts["A"] != counts["B"]:
        raise V9ReconciliationError("Paired route delta differs")
    return {
        "schema": SCHEMA,
        "as_of": "2026-09-30",
        "v8_prefix_sha256": PINS["v8_ledger"]["sha256"],
        "source_pins": PINS,
        "source_pins_sha256": hashlib.sha256(json.dumps(PINS, sort_keys=True).encode()).hexdigest(),
        "p1_freeze": freeze,
        "active_p1_tasks": previous["active_p1_tasks"],
        "reviewed_source_roster": {
            **previous["reviewed_source_roster"],
            "additional_pending_addressable_cohort_versions": 50,
        },
        "counts": counts,
        "rows": rows,
        "limits": [
            "One SH-POL-003 authored action gains pending design context, not clause satisfaction.",
            "Generic implementation, TOD and TOE gates gain no lead without a deployed "
            "decision or operating source.",
            "Twenty-two locator cases per side remain PENDING; no actual environment, "
            "HIPAA applicability, alternative, waiver, approval or safeguard is established.",
            "Messy blanket-waiver exception and SH-POL-003 gap remain OPEN/INSUFFICIENT_SOURCE.",
            "All 566 prior route fields and 132/30/121 classes remain exact; P1 is frozen.",
            "No source-complete population, procedure, task credit, Key, grade or Atlas write.",
        ],
        "audit_task_credit": False,
        "active_pair_mutated": False,
    }


def build(repository: Path, private_repository: Path) -> dict:
    """Reperform reviewed V8 and V10, then bind one exact pending native lead."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    freeze = frozen._p1_inventory(private)
    if freeze != P1_FREEZE:
        raise V9ReconciliationError("Frozen P1 inventory differs")
    loaded = {
        name: pinned._pinned(repository, private, private, entry)
        for name, entry in PINS.items()
        if name != "addressable_db"
    }
    frozen._pinned_db(private, PINS["addressable_db"])
    previous = prior.build(repository, private)
    if previous != loaded["v8_ledger"]:
        raise V9ReconciliationError("Reviewed exact V8 route prefix differs")
    v8_review = loaded["v8_review"]
    if (
        v8_review.get("verdict")
        != "PASS_READ_ONLY_SELECTED_LEG001_ROUTE_RECONCILIATION_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or v8_review.get("main_tracked_sha256", {}).get(V8_LEDGER) != PINS["v8_ledger"]["sha256"]
        or v8_review.get("p1_freeze") != freeze
        or v8_review.get("audit_task_credit") is not False
        or v8_review.get("active_pair_mutated") is not False
    ):
        raise V9ReconciliationError("V8 independent review/prefix join differs")
    review = loaded["v10_review"]
    outputs = {
        "portfolio_report": PINS["v10_portfolio"]["sha256"],
        "candidate_A": PINS["v10_candidate_a"]["sha256"],
        "candidate_B": PINS["v10_candidate_b"]["sha256"],
        "candidate_report": PINS["v10_candidate_report"]["sha256"],
    }
    if (
        review.get("verdict")
        != "PASS_PARTIAL_PENDING_ADDRESSABLE_REGISTRY_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or review.get("main_output_sha256") != outputs
        or review.get("integration_commit") != "2a4b7ecaaf62ef07550e1c9d366c7fa19cc8f6ef"
        or review.get("checks", {}).get("audit_task_credit") is not False
        or review.get("checks", {}).get("fresh_audit_pair_created") is not False
        or review.get("checks", {}).get("main_or_atlas_tracked_written_by_review") is not False
    ):
        raise V9ReconciliationError("V10 independently reviewed package differs")
    diagnostic = portfolio_v10.verify_report(
        private / V10_ROOT / "main-run-v1", repository, private
    )
    routed = candidate_v10.verify_candidate(private / V10_CANDIDATE, repository, private)
    if (
        diagnostic != loaded["v10_portfolio"]
        or routed != loaded["v10_candidate_report"]
        or (diagnostic["source_count"], diagnostic["native_versions"]) != (31, 710)
        or diagnostic["sources"][-1]["source"] != "addressabledocket"
        or routed["audit_task_credit"] is not False
        or routed["source_complete"] is not False
    ):
        raise V9ReconciliationError("Reviewed V10 source/candidate replay differs")
    source_review = loaded["addressable_review"]
    manifest = loaded["addressable_manifest"]
    receipt = loaded["addressable_receipt"]
    if (
        source_review.get("verdict") != portfolio_v10.ADDR_REVIEW_VERDICT
        or source_review.get("run_receipt_sha256") != PINS["addressable_receipt"]["sha256"]
        or source_review.get("run_manifest_sha256") != PINS["addressable_manifest"]["sha256"]
        or source_review.get("native_db_sha256") != PINS["addressable_db"]["sha256"]
        or manifest.get("native_version_count") != 50
        or addressable.verify(private / ADDR_RUN, repository=repository) != manifest
    ):
        raise V9ReconciliationError("Reviewed addressable native source differs")
    result = _extend(
        receipt=receipt,
        previous=previous,
        database=private / ADDR_RUN / "company.sqlite3",
        freeze=freeze,
    )
    if frozen._p1_inventory(private) != freeze:
        raise V9ReconciliationError("Frozen P1 changed during read-only route build")
    return result


def markdown(result: dict) -> str:
    """Render the bounded pending-docket route delta."""
    counts = result["counts"]["A"]
    lines = [
        "# Paired 283-route pending addressable-docket reconciliation V9",
        "",
        "The exact 566-row JSON preserves every V8 route field and adds one selected "
        "SH-POL-003 ACTION-H-ADDRESSABLE design-context lead per side. The prospective "
        "50-version native docket remains outside the frozen P1 audit pair.",
        "",
        "| Classification | Routes per side |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {name} | {number} |" for name, number in counts["classifications"].items())
    lines += [
        "",
        "The selected docket contains 22 pending source-locator cases per side, not 22 "
        "environmental or safeguard decisions. Clean remains PENDING_REVIEW; Messy "
        "remains QUARANTINED with its blanket-waiver exception open. No source supports "
        "an actual ePHI environment, applicable role, implemented measure, approved "
        "alternative or waiver. SH-POL-003's authored action stays DESIGN_CONTEXT_ONLY "
        "and its exact test gate remains open.",
        "",
        "The generic implementation, TOD and TOE routes receive no new lead because "
        "the docket does not establish a deployed decision or operating source. The "
        "132 partial, 30 design-context and 121 unsupported classes per side are unchanged. "
        "Only one additional route per side has a targeted source lead, bringing the "
        f"total to {counts['targeted_integrated_route_count']}.",
        "",
        "No audit task command or credit, fresh pair, grade, Key or Atlas write was issued. "
        "The frozen A/B P1 tasks remain NOT_STARTED/NOT_RUN.",
        "",
    ]
    return "\n".join(lines)
