"""Bind one reviewed SEC001 transfer fixture to its exact unsupported route."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from . import company_sec001_selected_transfer as transfer
from . import documentary_283_route_reconciliation_v3 as pinned
from . import documentary_283_route_reconciliation_v6 as frozen
from . import documentary_283_route_reconciliation_v10 as prior

SCHEMA = "SH_DOCUMENTARY_283_PAIRED_ROUTE_CANDIDATE_RECONCILIATION_V11"
BASE = "enterprise/generated/audit-suite"
SOURCE = "SEC001_SELECTED_SYNTHETIC_TRANSFER_V1"
TASK = "TASK-SH-SEC-001-corporate-CHECK-SOC2:CC6.7"
CLAUSE = (
    "Trace a transfer to purpose, recipient authorization, channel/endpoint protection "
    "and handling after receipt; transport encryption alone does not authorize the transfer."
)
LIMIT = (
    "One selected future fictional non-PHI transfer fixture only. Purpose and recipient "
    "decisions are training-only; AS-P007/008/014 appointments remain pending acceptance, "
    "and CRYPTO-TRANSFER is a proposed design supplement. Simulated channel and endpoint "
    "do not show deployed protection, actual transmission, independent approval, a full "
    "transfer population or receipt-handling operation. Messy wrong-endpoint attempt was "
    "blocked before send; unauthorized false close was corrected but its historical "
    "exception remains open. The authored CC6.7 gate is unsatisfied; no audit task credit."
)
V10_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V10_2026-09-30.json"
V10_REVIEW = (
    f"{BASE}/documentary-283-route-reconciliation-v10-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
SEC_ROOT = f"{BASE}/company-sec001-selected-transfer-2027-09-30"
SEC_RUN = f"{SEC_ROOT}/main-run-v1"
SEC_REVIEW = f"{SEC_ROOT}/independent-review-main-v1/REVIEW.json"
V12_ROOT = f"{BASE}/company-source-portfolio-v12-2026-09-30"
PINS = {
    "v10_ledger": {
        "scope": "repo",
        "path": V10_LEDGER,
        "sha256": "d7904fe36b8307e31071a24086d71b2500910e88e5243256a1d5bf4b4f050324",
    },
    "v10_review": {
        "scope": "private",
        "path": V10_REVIEW,
        "sha256": "b702667f9f480774c07d160c31939250c7ad76a65661a1f7c8c41f23e068b674",
    },
    "sec_review": {
        "scope": "private",
        "path": SEC_REVIEW,
        "sha256": "9cf4d438d7b191f227f87f3dcb5cf6d36bcb3e7e490415d16cff11e72a33c196",
    },
    "sec_receipt": {
        "scope": "private",
        "path": f"{SEC_RUN}/SOURCE_RECEIPT.json",
        "sha256": "73fa3ff1cb40f9e0e8196cd01bf18048c408427e0d10ade9003fd60d9c984d28",
    },
    "sec_manifest": {
        "scope": "private",
        "path": f"{SEC_RUN}/RUN-MANIFEST.json",
        "sha256": "d653285e748e7529557749445c0a3646b049237a1ff9888fed835f53fd185942",
    },
    "sec_db": {
        "scope": "private",
        "path": f"{SEC_RUN}/company.sqlite3",
        "sha256": "3841366d17e3f072ef2ae303ec3bf010ab644e474a778d59f62263c6a8c86e7d",
    },
}
V12_ACCEPTED = {
    "verdict": "PASS_PARTIAL_SEC001_PORTFOLIO_MAIN_LOCAL_NO_AUDIT_CREDIT",
    "integration_commits_in_order": [
        "6d229a7d73946a556951f4d903e8f276373cdfe8",
        "3d61d4e8b50ae09c3d0e214af9dba95a4ad32fd5",
    ],
    "main_head": "3d61d4e8b50ae09c3d0e214af9dba95a4ad32fd5",
    "tracked_sha256": {
        "enterprise/audit_suite/SEC001_SELECTED_TRANSFER_PORTFOLIO_V12_PROPOSAL.md": (
            "decfa771f4d8a297c76c46aa9227f8f52b31de015f2c3f4d99a5df47c10f9c01"
        ),
        "enterprise/audit_suite/fictional_2027_candidate_registry_v12.py": (
            "67a28d070d8ab82d06dbc29a69c3def9967646080dbe5ffcc7168d94192fbbfe"
        ),
        "enterprise/audit_suite/fictional_2027_source_portfolio_v12.py": (
            "92756c5c29e21d5fdce1e79704917fea021ea18e5e2285c994801139789094c4"
        ),
        "tests/audit_suite/test_fictional_2027_portfolio_v12.py": (
            "f423b51fa1b7efc15a83f7707ee630e81933da28b3fae395f7f14c0430f0f42b"
        ),
    },
    "pins": {
        "v12_review": {
            "scope": "private",
            "path": f"{V12_ROOT}/independent-review-main-v1/REVIEW.json",
            "sha256": "053dca8df77c5fb990daf7844a62a792276b89100dfef8df1d564f04df841400",
        },
        "v12_portfolio": {
            "scope": "private",
            "path": f"{V12_ROOT}/main-run-v1/REPORT.json",
            "sha256": "c6d7205a9f2e6bc3a213a5eece4e0b1c28811d407850e31fd2bcb4a2eb382821",
        },
        "v12_candidate_a": {
            "scope": "private",
            "path": f"{V12_ROOT}/main-candidate-v1/A.json",
            "sha256": "2919a119ac97520f4026c6b9c25635857d1ff12e0308217864575d251a9443b2",
        },
        "v12_candidate_b": {
            "scope": "private",
            "path": f"{V12_ROOT}/main-candidate-v1/B.json",
            "sha256": "6dbab1e7ef28f7ace549db73232d43b065ac1c6491f99152c4d5107ee763ca1a",
        },
        "v12_candidate_report": {
            "scope": "private",
            "path": f"{V12_ROOT}/main-candidate-v1/REPORT.json",
            "sha256": "ee37e0e2d934ece1ba0f4d4c4cab5fce5dbabb4b0784044b6bca01a24fb529af",
        },
    },
}
_ACCEPTED_TOKEN = object()
P1_FREEZE = prior.P1_FREEZE
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


class V11ReconciliationError(prior.V10ReconciliationError):
    """A reviewed prefix, source or acceptance boundary changed."""


def _accepted_v12(repository: Path, private: Path, freeze: dict) -> object:
    """Accept integrated targeting only after a reviewed main-local V12 replay."""
    if V12_ACCEPTED is None:
        raise V11ReconciliationError("V12 main-local review and output pins are pending")
    from . import fictional_2027_candidate_registry_v12 as candidate_v12
    from . import fictional_2027_source_portfolio_v12 as portfolio_v12

    pins = V12_ACCEPTED["pins"]
    expected = {
        "v12_review": f"{V12_ROOT}/independent-review-main-v1/REVIEW.json",
        "v12_portfolio": f"{V12_ROOT}/main-run-v1/REPORT.json",
        "v12_candidate_a": f"{V12_ROOT}/main-candidate-v1/A.json",
        "v12_candidate_b": f"{V12_ROOT}/main-candidate-v1/B.json",
        "v12_candidate_report": f"{V12_ROOT}/main-candidate-v1/REPORT.json",
    }
    if set(pins) != set(expected) or any(
        pins[name]["path"] != path or pins[name]["scope"] != "private"
        for name, path in expected.items()
    ):
        raise V11ReconciliationError("V12 accepted main output pin roster differs")
    loaded = {
        name: pinned._pinned(repository, private, private, entry) for name, entry in pins.items()
    }
    outputs = {
        "portfolio_report": pins["v12_portfolio"]["sha256"],
        "candidate_A": pins["v12_candidate_a"]["sha256"],
        "candidate_B": pins["v12_candidate_b"]["sha256"],
        "candidate_report": pins["v12_candidate_report"]["sha256"],
    }
    review = loaded["v12_review"]
    if (
        review.get("schema")
        != "SH_FICTIONAL_2027_SEC001_PARTIAL_PORTFOLIO_V12_MAIN_LOCAL_INDEPENDENT_REVIEW_V1"
        or review.get("verdict") != V12_ACCEPTED["verdict"]
        or review.get("main_head") != V12_ACCEPTED["main_head"]
        or review.get("integration_commits_in_order")
        != V12_ACCEPTED["integration_commits_in_order"]
        or review.get("main_output_sha256") != outputs
        or review.get("main_tracked_sha256") != V12_ACCEPTED["tracked_sha256"]
        or review.get("sec001_main_review_sha256") != PINS["sec_review"]["sha256"]
        or review.get("sec001_main_run_sha256")
        != {
            "RUN-MANIFEST.json": PINS["sec_manifest"]["sha256"],
            "SOURCE_RECEIPT.json": PINS["sec_receipt"]["sha256"],
            "company.sqlite3": PINS["sec_db"]["sha256"],
        }
        or review.get("counts")
        != {
            "candidate_components_per_side": 47,
            "candidate_pins_per_side": 34,
            "native_business_versions": 755,
            "sec001_clean_versions": 10,
            "sec001_messy_versions": 16,
            "sec001_native_versions": 26,
            "source_cohorts": 33,
            "source_components": 34,
            "system_aliases_per_side": 290,
        }
        or review.get("p1_freeze") != freeze
        or review.get("source_complete") is not False
        or review.get("fresh_audit_pair_created") is not False
        or review.get("audit_task_credit") is not False
        or review.get("main_or_atlas_tracked_written_by_review") is not False
    ):
        raise V11ReconciliationError("V12 independently reviewed main candidate differs")
    diagnostic = portfolio_v12.verify_report(
        private / V12_ROOT / "main-run-v1", repository, private
    )
    routed = candidate_v12.verify_candidate(
        private / V12_ROOT / "main-candidate-v1", repository, private
    )
    if (
        diagnostic != loaded["v12_portfolio"]
        or routed != loaded["v12_candidate_report"]
        or (diagnostic["source_count"], diagnostic["native_versions"]) != (33, 755)
        or diagnostic["sources"][-1]["source"] != "sec001transfer"
        or diagnostic["sources"][-1]["receipt_sha256"] != PINS["sec_receipt"]["sha256"]
        or diagnostic["sources"][-1]["review_sha256"] != PINS["sec_review"]["sha256"]
        or diagnostic["source_complete"] is not False
        or routed["source_complete"] is not False
        or routed["audit_task_credit"] is not False
        or any(
            routed["sides"][side]["source_pins"][-1]["source"] != "sec001transfer"
            or routed["sides"][side]["component_count"] != 47
            or routed["sides"][side]["system_alias_count"] != 290
            for side in "AB"
        )
    ):
        raise V11ReconciliationError("V12 selected SEC001 source/candidate replay differs")
    return _ACCEPTED_TOKEN


def _selected_refs(receipt: dict) -> dict[str, list[dict]]:
    """Select full native causal chains without implying clause satisfaction."""
    if (
        receipt.get("schema") != transfer.SCHEMA
        or receipt.get("control_id") != "SH-SEC-001"
        or receipt.get("task_id") != TASK
        or receipt.get("selected_authored_clause") != CLAUSE
        or receipt.get("native_count") != 26
        or receipt.get("branch_counts") != {"CLEAN": 10, "MESSY": 16}
        or receipt.get("branch_ids") != transfer.BRANCHES
        or receipt.get("selected_payload_count") != 1
        or receipt.get("actor_authority")
        != "CANON_LISTED_FICTIONAL_APPOINTMENTS_PENDING_ACCEPTANCE"
        or receipt.get("messy_blocked_wrong_endpoint") is not True
        or receipt.get("messy_false_close_corrected") is not True
        or receipt.get("messy_historical_exception_open") is not True
        or any(
            receipt.get(key) is not False
            for key in (
                "independent_approval",
                "actual_network_transmission",
                "actual_customer_or_phi_data",
                "actual_deployed_endpoint_or_channel",
                "enterprise_transfer_standard_approved",
                "population_complete",
                "source_complete",
                "audit_task_credit",
                "active_P1_mutated",
            )
        )
        or any(
            receipt.get("route_disposition", {}).get(side, {}).get(key) != value
            for side in "AB"
            for key, value in (
                ("classification", "UNSUPPORTED_EXACT_CLAUSE"),
                ("remaining_test_gate", CLAUSE),
                ("current_status", "NOT_STARTED"),
                ("current_conclusion", "NOT_RUN"),
                ("audit_task_credit", False),
            )
        )
    ):
        raise V11ReconciliationError("Selected SEC001 authority or route boundary differs")
    originals = receipt.get("native_originals", [])
    if len(originals) != 26:
        raise V11ReconciliationError("Selected SEC001 native roster differs")
    selected = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        plan = transfer.PLAN[scenario]
        branch = transfer.BRANCHES[scenario]
        refs = [ref for ref in originals if ref["branch"] == branch]
        if (
            len(refs) != len(plan)
            or [(ref["system"], ref["record"]) for ref in refs]
            != [(system, record) for system, record, _, _ in plan]
            or any(ref["version"] != 1 for ref in refs)
        ):
            raise V11ReconciliationError("Selected SEC001 native roster differs")
        selected[side] = [{key: ref[key] for key in IDENTITY} for ref in refs]
    return selected


def _extend(previous: dict, receipt: dict, freeze: dict, *, qualification: object | None) -> dict:
    """Add one unsupported exact-clause lead per side; preserve the entire V10 prefix."""
    if qualification is not _ACCEPTED_TOKEN:
        raise V11ReconciliationError("V12 accepted candidate verification required")
    if (
        previous.get("schema") != prior.SCHEMA
        or previous.get("p1_freeze") != freeze
        or previous.get("audit_task_credit") is not False
        or previous.get("active_pair_mutated") is not False
        or len(previous.get("rows", [])) != 566
        or previous["counts"]["A"] != previous["counts"]["B"]
        or previous["counts"]["A"]["classifications"]
        != {
            "DESIGN_CONTEXT_ONLY": 27,
            "SOURCE_CANDIDATE_PARTIAL": 135,
            "UNSUPPORTED_EXACT_CLAUSE": 121,
        }
        or previous["counts"]["A"]["targeted_integrated_route_count"] != 173
        or previous["active_p1_tasks"]
        != {
            side: {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"}
            for side in "AB"
        }
    ):
        raise V11ReconciliationError("Reviewed V10 route denominator or audit boundary differs")
    refs = _selected_refs(receipt)
    rows = []
    for old in previous["rows"]:
        row = dict(old)
        selected = old["task_id"] == TASK
        if selected:
            if (
                old["control_id"] != "SH-SEC-001"
                or old["classification"] != "UNSUPPORTED_EXACT_CLAUSE"
                or old["authored_test_clause"] != CLAUSE
                or old["remaining_test_gate"] != CLAUSE
                or old["test_gate_basis"] != "AUTHORED_TASK_CLAUSE"
                or old["candidate_or_design_source_ids"]
                or old["targeted_integrated_source_ids"]
                or old["audit_task_credit"] is not False
            ):
                raise V11ReconciliationError("Authored SEC001 route boundary differs")
            row["targeted_integrated_source_ids"] = [SOURCE]
        row["v11_reviewed_source_ids"] = [SOURCE] if selected else []
        row["v11_source_limits"] = {SOURCE: LIMIT} if selected else {}
        row["v11_source_record_refs"] = {SOURCE: refs[old["side"]]} if selected else {}
        if any(row[key] != old[key] for key in prior.prior.prior.IMMUTABLE):
            raise V11ReconciliationError("Frozen authored route field changed")
        rows.append(row)
    counts = {}
    for side in "AB":
        subset = [row for row in rows if row["side"] == side]
        leads = [row for row in subset if row["v11_reviewed_source_ids"]]
        targeted = sum(bool(row["targeted_integrated_source_ids"]) for row in subset)
        if (
            len(subset) != len({row["task_id"] for row in subset})
            or len(subset) != 283
            or len(leads) != 1
            or leads[0]["task_id"] != TASK
            or leads[0]["classification"] != "UNSUPPORTED_EXACT_CLAUSE"
            or leads[0]["remaining_test_gate"] != CLAUSE
            or leads[0]["candidate_or_design_source_ids"]
            or targeted != 174
            or sum(row["authored_test_clause"] is not None for row in subset) != 154
        ):
            raise V11ReconciliationError("Exact one-lead 283-route denominator differs")
        count = deepcopy(previous["counts"][side])
        count["targeted_integrated_route_count"] = targeted
        count["v11_new_selected_sec001_authored_leads"] = 1
        count["v11_new_generic_promotions"] = 0
        counts[side] = count
    if counts["A"] != counts["B"]:
        raise V11ReconciliationError("Paired SEC001 route delta differs")
    source_pins = {**PINS, **V12_ACCEPTED["pins"]}
    return {
        "schema": SCHEMA,
        "as_of": "2026-09-30",
        "v10_prefix_sha256": PINS["v10_ledger"]["sha256"],
        "source_pins": source_pins,
        "source_pins_sha256": hashlib.sha256(
            json.dumps(source_pins, sort_keys=True).encode()
        ).hexdigest(),
        "p1_freeze": freeze,
        "active_p1_tasks": previous["active_p1_tasks"],
        "reviewed_source_roster": {
            **previous["reviewed_source_roster"],
            "additional_selected_sec001_cohort_versions": 26,
        },
        "counts": counts,
        "rows": rows,
        "limits": [
            "Only the exact SH-SEC-001 SOC2:CC6.7 authored route per side gains a selected "
            "fictional source lead; all 566 prior rows and classifications persist.",
            LIMIT,
            "All 121 unsupported authored clauses per side remain unsupported, including "
            "CC6.7; no generic route is promoted.",
            "No source completeness, audit task credit, fresh pair, grade, Key or Atlas write.",
        ],
        "audit_task_credit": False,
        "active_pair_mutated": False,
    }


def build(repository: Path, private_repository: Path) -> dict:
    """Reperform the reviewed sources and V12 acceptance before adding a route lead."""
    if V12_ACCEPTED is None:
        raise V11ReconciliationError("V12 main-local review and output pins are pending")
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    freeze = frozen._p1_inventory(private)
    if freeze != P1_FREEZE:
        raise V11ReconciliationError("Frozen P1 inventory differs")
    loaded = {
        name: pinned._pinned(repository, private, private, entry)
        for name, entry in PINS.items()
        if name != "sec_db"
    }
    frozen._pinned_db(private, PINS["sec_db"])
    previous = prior.build(repository, private)
    if previous != loaded["v10_ledger"]:
        raise V11ReconciliationError("Reviewed exact V10 route prefix differs")
    route_review = loaded["v10_review"]
    if (
        route_review.get("verdict")
        != "PASS_READ_ONLY_SELECTED_ETH001_ROUTE_RECONCILIATION_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or route_review.get("integration_commit") != "a65e0d8070906553db6028dd75831ccfa6683ad2"
        or route_review.get("main_tracked_sha256", {}).get(V10_LEDGER)
        != PINS["v10_ledger"]["sha256"]
        or route_review.get("p1_freeze") != freeze
        or route_review.get("audit_task_credit") is not False
        or route_review.get("active_pair_mutated") is not False
    ):
        raise V11ReconciliationError("V10 independent review/prefix join differs")
    source_review = loaded["sec_review"]
    source_hashes = {
        name: PINS[key]["sha256"]
        for name, key in (
            ("RUN-MANIFEST.json", "sec_manifest"),
            ("SOURCE_RECEIPT.json", "sec_receipt"),
            ("company.sqlite3", "sec_db"),
        )
    }
    if (
        source_review.get("verdict")
        != "PASS_SELECTED_SYNTHETIC_SEC001_TRANSFER_SOURCE_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or source_review.get("integration_commit") != "b286bbb9acef0c64e56b5170349546e74485f7b1"
        or source_review.get("main_run_sha256") != source_hashes
        or source_review.get("p1_freeze") != freeze
        or source_review.get("selected_task_id") != TASK
        or source_review.get("selected_authored_clause") != CLAUSE
        or source_review.get("source_complete") is not False
        or source_review.get("audit_task_credit") is not False
        or source_review.get("active_pair_mutated") is not False
        or source_review.get("main_or_atlas_tracked_written_by_review") is not False
    ):
        raise V11ReconciliationError("SEC001 independent review/source join differs")
    receipt = transfer.verify(private / SEC_RUN, repository=repository, private_repository=private)
    if receipt != loaded["sec_receipt"] or loaded["sec_manifest"]["native_count"] != 26:
        raise V11ReconciliationError("Reviewed SEC001 native source replay differs")
    qualification = _accepted_v12(repository, private, freeze)
    result = _extend(previous, receipt, freeze, qualification=qualification)
    if frozen._p1_inventory(private) != freeze:
        raise V11ReconciliationError("Frozen P1 changed during read-only route build")
    return result


def markdown(result: dict) -> str:
    """Render the exact unsupported clause and its limited selected source."""
    count = result["counts"]["A"]
    lines = [
        "# Paired 283-route SEC001 selected-transfer reconciliation V11",
        "",
        "The exact 566-row JSON retains every V10 row and earlier field. The authored "
        "SH-SEC-001 SOC2:CC6.7 route per side gains one bounded source lead from a "
        "reviewed 26-version synthetic non-PHI transfer fixture, outside frozen P1.",
        "",
        "| Classification | Routes per side |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {name} | {number} |" for name, number in count["classifications"].items())
    lines += [
        "",
        "The selected Clean trace joins purpose, recipient, simulated channel and endpoint, "
        "fictional receipt and handling. Messy retains a blocked wrong-endpoint attempt, "
        "an unauthorized false close, correction and open historical exception. The "
        "appointees are pending acceptance and CRYPTO-TRANSFER remains a proposed design. "
        "There was no real network transmission or deployed safeguard.",
        "",
        "CC6.7 and all 121 authored unsupported clauses per side remain "
        "UNSUPPORTED_EXACT_CLAUSE, with the full authored test gate open. No generic "
        "route promotion occurred. Named targeted leads total "
        f"{count['targeted_integrated_route_count']} "
        "distinct routes per side.",
        "",
        "No source-complete population, audit task credit, fresh pair, grade, Key or Atlas "
        "write was issued. The frozen A/B P1 tasks remain 409 NOT_STARTED/NOT_RUN.",
        "",
    ]
    return "\n".join(lines)
