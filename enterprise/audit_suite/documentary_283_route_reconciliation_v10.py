"""Bind a selected fictional ETH001 conduct source to three exact generic routes."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

from . import company_eth001_conduct_attestation as conduct
from . import documentary_283_route_reconciliation_v3 as pinned
from . import documentary_283_route_reconciliation_v6 as frozen
from . import documentary_283_route_reconciliation_v9 as prior

SCHEMA = "SH_DOCUMENTARY_283_PAIRED_ROUTE_CANDIDATE_RECONCILIATION_V10"
BASE = "enterprise/generated/audit-suite"
SOURCE = "ETH001_SELECTED_FICTIONAL_CONDUCT_V1"
V9_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V9_2026-09-30.json"
V9_REVIEW = (
    f"{BASE}/documentary-283-route-reconciliation-v9-2026-09-30/"
    "independent-review-main-v1/REVIEW.json"
)
ETH_ROOT = f"{BASE}/company-eth001-conduct-2027-simulation-2026-09-30"
ETH_REVIEW = f"{ETH_ROOT}/independent-review-main-v1/REVIEW.json"
ETH_RUN = f"{ETH_ROOT}/main-run-v1"
V11_ROOT = f"{BASE}/company-source-portfolio-v11-2026-09-30"
# These isolated bytes are a test fixture, not an accepted main-local source pin.
PROSPECTIVE_V11 = {
    "isolated_commit": "d41d73470d2ae9610b67dcf3abac244710295971",
    "portfolio_report": "9011ff5ca02a41cd966179097b1663a1519ac4f91c446ae1b0bd3f6716cc59bf",
    "candidate_A": "43a86507b5d62d5e7348e7245426f8132b7eb6f5aea65e07511864baef3e6331",
    "candidate_B": "3f244b4b92f33740c6677b7a7166aab1aaef74067b3a4e90f741a5d8651aecc1",
    "candidate_report": "31dcabc95d102b3f9bdcd4f698c98e976d97eb9d1ae47948828825742dd5ae56",
}
# Final main-local review and replay hashes do not exist yet. Build fails closed
# until V11 has independent review, integration and a fresh main-local replay.
V11_ACCEPTED: dict | None = None
_ACCEPTED_TOKEN = object()
PINS = {
    "v9_ledger": {
        "scope": "repo",
        "path": V9_LEDGER,
        "sha256": "73483c9f47cdc58a6aae94f65cdaa1a2e1b038bc2d0e67061b1dd30ba0364c07",
    },
    "v9_review": {
        "scope": "private",
        "path": V9_REVIEW,
        "sha256": "c290249ae02caa147566e590abe79b3b56ac45d27953dc9133a123f8ba045156",
    },
    "eth_review": {
        "scope": "private",
        "path": ETH_REVIEW,
        "sha256": "fbeae6830cfd479c2c354c22dad99adc5b8b89b9f57f99a014cbd15a1d73308d",
    },
    "eth_receipt": {
        "scope": "private",
        "path": f"{ETH_RUN}/SOURCE_RECEIPT.json",
        "sha256": "876e78076e293a5432a34ec17a85497b9de91f20d27af6cf7d38bd9b3ad6ef5e",
    },
    "eth_manifest": {
        "scope": "private",
        "path": f"{ETH_RUN}/RUN-MANIFEST.json",
        "sha256": "320aad65c8ee0bd0d79f89460c80da00f5b52062ac2e20a3964f28951de552bc",
    },
    "eth_db": {
        "scope": "private",
        "path": f"{ETH_RUN}/company.sqlite3",
        "sha256": "0ecf3e6fa6eaa2af01839fb5577188bf786e2669101729c71a2cf5cb4e47a3b8",
    },
}
P1_FREEZE = prior.P1_FREEZE
GENERIC = {
    f"TASK-SH-ETH-001-corporate-{suffix}": suffix for suffix in ("IMPLEMENTATION", "TOD", "TOE")
}
SANCTIONS = "TASK-SH-ETH-001-corporate-ACTION-H-SANCTIONS"
LIMIT = (
    "Selected two-person, future fictional conduct exercise only. The 2026 enterprise "
    "code remains future/OPEN; local approval, delivery and attestation are not actual "
    "employee actions. This is not a workforce census, complete operating population, "
    "substantiated-case/no-case decision, sanctions or performance-review conclusion. "
    "Messy false-clean history and late acknowledgment remain visible and open. No "
    "source-complete status, test conclusion or audit task credit follows."
)
RECORDS = {
    "IMPLEMENTATION": ("FICTIONAL-LOCAL-APPROVAL", "SELECTED-ROSTER"),
    "TOD": ("DRAFT", "FICTIONAL-LOCAL-APPROVAL", "SELECTED-ROSTER"),
    "TOE": {
        "A": tuple(record for _, record, _, _ in conduct.PLAN["CLEAN"]),
        "B": tuple(record for _, record, _, _ in conduct.PLAN["MESSY"]),
    },
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


class V10ReconciliationError(prior.V9ReconciliationError):
    """A reviewed source, exact prior route or frozen audit boundary changed."""


def _accepted_v11(repository: Path, private: Path, freeze: dict) -> object:
    """Require a reviewed main-local V11 candidate before adding integrated leads."""
    if V11_ACCEPTED is None:
        raise V10ReconciliationError("V11 main-local review and output pins are pending")
    from . import fictional_2027_candidate_registry_v11 as candidate_v11
    from . import fictional_2027_source_portfolio_v11 as portfolio_v11

    pins = V11_ACCEPTED["pins"]
    expected = {
        "review": f"{V11_ROOT}/independent-review-main-v1/REVIEW.json",
        "portfolio": f"{V11_ROOT}/main-run-v1/REPORT.json",
        "candidate_a": f"{V11_ROOT}/main-candidate-v1/A.json",
        "candidate_b": f"{V11_ROOT}/main-candidate-v1/B.json",
        "candidate_report": f"{V11_ROOT}/main-candidate-v1/REPORT.json",
    }
    if set(pins) != set(expected) or any(
        pins[name]["path"] != path or pins[name]["scope"] != "private"
        for name, path in expected.items()
    ):
        raise V10ReconciliationError("V11 accepted main output pin roster differs")
    loaded = {
        name: pinned._pinned(repository, private, private, entry) for name, entry in pins.items()
    }
    review = loaded["review"]
    outputs = {
        "portfolio_report": pins["portfolio"]["sha256"],
        "candidate_A": pins["candidate_a"]["sha256"],
        "candidate_B": pins["candidate_b"]["sha256"],
        "candidate_report": pins["candidate_report"]["sha256"],
    }
    if (
        review.get("verdict") != V11_ACCEPTED["verdict"]
        or review.get("integration_commit") != V11_ACCEPTED["integration_commit"]
        or review.get("main_output_sha256") != outputs
        or review.get("p1_freeze") != freeze
        or review.get("checks", {}).get("audit_task_credit") is not False
        or review.get("checks", {}).get("fresh_audit_pair_created") is not False
        or review.get("checks", {}).get("main_or_atlas_tracked_written_by_review") is not False
    ):
        raise V10ReconciliationError("V11 independently reviewed main candidate differs")
    diagnostic = portfolio_v11.verify_report(
        private / V11_ROOT / "main-run-v1", repository, private
    )
    routed = candidate_v11.verify_candidate(
        private / V11_ROOT / "main-candidate-v1", repository, private
    )
    if (
        diagnostic != loaded["portfolio"]
        or routed != loaded["candidate_report"]
        or (diagnostic["source_count"], diagnostic["native_versions"]) != (32, 729)
        or diagnostic["sources"][-1]["source"] != "eth001conduct"
        or diagnostic["sources"][-1]["receipt_sha256"] != PINS["eth_receipt"]["sha256"]
        or diagnostic["sources"][-1]["review_sha256"] != PINS["eth_review"]["sha256"]
        or diagnostic["source_complete"] is not False
        or routed["source_complete"] is not False
        or routed["audit_task_credit"] is not False
        or any(
            routed["sides"][side]["source_pins"][-1]["source"] != "eth001conduct"
            or routed["sides"][side]["component_count"] != 46
            or routed["sides"][side]["system_alias_count"] != 285
            for side in "AB"
        )
    ):
        raise V10ReconciliationError("V11 selected ETH001 source/candidate replay differs")
    return _ACCEPTED_TOKEN


def _selected_refs(receipt: dict) -> dict[str, dict[str, list[dict]]]:
    """Select exact native tuples without turning the scenario into an audit population."""
    if (
        receipt.get("schema") != conduct.SCHEMA
        or receipt.get("native_count") != 19
        or receipt.get("branch_counts") != {"CLEAN": 8, "MESSY": 11}
        or receipt.get("selected_person_ids") != list(conduct.PEOPLE)
        or receipt.get("selected_population")
        != "TWO_FICTIONAL_PERSON_IDENTITIES_NOT_WORKFORCE_CENSUS"
        or receipt.get("canon_reconciliation") != conduct.CANON_RECONCILIATION
        or receipt.get("fictional_local_approval_only") is not True
        or receipt.get("clean_selected_on_time_count") != 2
        or receipt.get("messy_selected_late_count") != 1
        or receipt.get("messy_historical_false_clean_exception_open") is not True
        or any(
            receipt.get(key) is not False
            for key in (
                "real_enterprise_code_approved",
                "actual_workforce_population_complete",
                "substantiated_case_evidence_present",
                "no_case_population_decision",
                "sanctions_or_performance_review_conclusion",
                "actual_2027_operation",
                "actual_distribution_or_attestation",
                "source_complete",
                "audit_task_credit",
                "active_P1_mutated",
            )
        )
    ):
        raise V10ReconciliationError("Selected conduct authority boundary differs")
    originals = receipt.get("native_originals", [])
    if len(originals) != 19:
        raise V10ReconciliationError("Selected conduct native roster differs")
    selected = {}
    for side, scenario in (("A", "CLEAN"), ("B", "MESSY")):
        plan = conduct.PLAN[scenario]
        branch = conduct.BRANCHES[scenario]
        exact = [ref for ref in originals if ref["branch"] == branch]
        if (
            len(exact) != len(plan)
            or [(ref["system"], ref["record"]) for ref in exact]
            != [(system, record) for system, record, _, _ in plan]
            or any(ref["version"] != 1 for ref in exact)
        ):
            raise V10ReconciliationError("Selected conduct native roster differs")
        by_record = {ref["record"]: ref for ref in exact}
        selected[side] = {}
        for suffix in ("IMPLEMENTATION", "TOD", "TOE"):
            names = RECORDS[suffix][side] if suffix == "TOE" else RECORDS[suffix]
            selected[side][suffix] = [
                {key: by_record[name][key] for key in IDENTITY} for name in names
            ]
    return selected


def _extend(previous: dict, receipt: dict, freeze: dict, *, qualification: object | None) -> dict:
    """Promote only three generic SH-ETH-001 routes per side and retain all older fields."""
    if qualification is not _ACCEPTED_TOKEN:
        raise V10ReconciliationError("V11 accepted candidate verification required")
    if (
        previous.get("schema") != prior.SCHEMA
        or previous.get("p1_freeze") != freeze
        or previous.get("audit_task_credit") is not False
        or previous.get("active_pair_mutated") is not False
        or len(previous.get("rows", [])) != 566
        or previous["counts"]["A"] != previous["counts"]["B"]
        or previous["counts"]["A"]["classifications"]
        != {
            "DESIGN_CONTEXT_ONLY": 30,
            "SOURCE_CANDIDATE_PARTIAL": 132,
            "UNSUPPORTED_EXACT_CLAUSE": 121,
        }
        or previous["counts"]["A"]["targeted_integrated_route_count"] != 170
        or previous["active_p1_tasks"]
        != {
            side: {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"}
            for side in "AB"
        }
    ):
        raise V10ReconciliationError("Reviewed V9 route denominator or audit boundary differs")
    refs = _selected_refs(receipt)
    rows = []
    for old in previous["rows"]:
        row = dict(old)
        suffix = GENERIC.get(old["task_id"])
        if suffix:
            if (
                old["control_id"] != "SH-ETH-001"
                or old["classification"] != "DESIGN_CONTEXT_ONLY"
                or old["authored_test_clause"] is not None
                or old["test_gate_basis"] != "GENERIC_PROCEDURE_GATE_NOT_AN_AUTHORED_CLAUSE"
                or old["candidate_or_design_source_ids"]
                or old["targeted_integrated_source_ids"]
                or old["audit_task_credit"] is not False
            ):
                raise V10ReconciliationError("Generic ETH001 route boundary differs")
            row["classification"] = "SOURCE_CANDIDATE_PARTIAL"
            row["candidate_or_design_source_ids"] = [SOURCE]
            row["targeted_integrated_source_ids"] = [SOURCE]
        if old["task_id"] == SANCTIONS and (
            old["classification"] != "UNSUPPORTED_EXACT_CLAUSE"
            or old["authored_test_clause"] is None
            or old["remaining_test_gate"] != old["authored_test_clause"]
            or old["candidate_or_design_source_ids"]
            or old["targeted_integrated_source_ids"]
        ):
            raise V10ReconciliationError("Authored sanctions route boundary differs")
        row["v10_reviewed_source_ids"] = [SOURCE] if suffix else []
        row["v10_source_limits"] = {SOURCE: LIMIT} if suffix else {}
        row["v10_source_record_refs"] = {SOURCE: refs[old["side"]][suffix]} if suffix else {}
        if any(row[key] != old[key] for key in prior.prior.IMMUTABLE):
            raise V10ReconciliationError("Frozen authored route field changed")
        rows.append(row)
    counts = {}
    for side in "AB":
        subset = [row for row in rows if row["side"] == side]
        leads = [row for row in subset if row["v10_reviewed_source_ids"]]
        classes = dict(sorted(Counter(row["classification"] for row in subset).items()))
        targeted = sum(bool(row["targeted_integrated_source_ids"]) for row in subset)
        if (
            len(subset) != len({row["task_id"] for row in subset})
            or len(subset) != 283
            or {row["task_id"] for row in leads} != set(GENERIC)
            or classes
            != {
                "DESIGN_CONTEXT_ONLY": 27,
                "SOURCE_CANDIDATE_PARTIAL": 135,
                "UNSUPPORTED_EXACT_CLAUSE": 121,
            }
            or targeted != 173
            or sum(row["authored_test_clause"] is not None for row in subset) != 154
            or next(row for row in subset if row["task_id"] == SANCTIONS)["v10_reviewed_source_ids"]
        ):
            raise V10ReconciliationError("Exact three-lead 283-route denominator differs")
        count = deepcopy(previous["counts"][side])
        count["classifications"] = classes
        family = count["by_family"]["training_workforce_and_ethics"]
        family["DESIGN_CONTEXT_ONLY"] -= 3
        family["SOURCE_CANDIDATE_PARTIAL"] += 3
        count["targeted_integrated_route_count"] = targeted
        count["v10_new_selected_conduct_generic_leads"] = 3
        count["v10_authored_sanctions_leads"] = 0
        counts[side] = count
    if counts["A"] != counts["B"]:
        raise V10ReconciliationError("Paired ETH001 route delta differs")
    source_pins = {**PINS, **V11_ACCEPTED["pins"]}
    return {
        "schema": SCHEMA,
        "as_of": "2026-09-30",
        "v9_prefix_sha256": PINS["v9_ledger"]["sha256"],
        "source_pins": source_pins,
        "source_pins_sha256": hashlib.sha256(
            json.dumps(source_pins, sort_keys=True).encode()
        ).hexdigest(),
        "p1_freeze": freeze,
        "active_p1_tasks": previous["active_p1_tasks"],
        "reviewed_source_roster": {
            **previous["reviewed_source_roster"],
            "additional_selected_eth001_cohort_versions": 19,
        },
        "counts": counts,
        "rows": rows,
        "limits": [
            "Only three SH-ETH-001 generic procedure routes per side gain selected future "
            "fictional conduct leads; the 566-row denominator and prior fields are retained.",
            "The selected roster has two scenario identities, not an enterprise workforce census; "
            "fictional local approval and acknowledgment are not actual operation.",
            "The Messy false-clean original, late acknowledgment and historical "
            "exception remain open.",
            "ACTION-H-SANCTIONS and every authored clause retain prior classifications and open "
            "gates; no substantiated-case/no-case, sanction or performance-review "
            "conclusion exists.",
            "No source completeness, audit task credit, fresh pair, grade, Key or Atlas write.",
        ],
        "audit_task_credit": False,
        "active_pair_mutated": False,
    }


def build(repository: Path, private_repository: Path) -> dict:
    """Reperform both reviewed sources and freeze checks before returning route delta."""
    if V11_ACCEPTED is None:
        raise V10ReconciliationError("V11 main-local review and output pins are pending")
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    freeze = frozen._p1_inventory(private)
    if freeze != P1_FREEZE:
        raise V10ReconciliationError("Frozen P1 inventory differs")
    loaded = {
        name: pinned._pinned(repository, private, private, entry)
        for name, entry in PINS.items()
        if name != "eth_db"
    }
    frozen._pinned_db(private, PINS["eth_db"])
    previous = prior.build(repository, private)
    if previous != loaded["v9_ledger"]:
        raise V10ReconciliationError("Reviewed exact V9 route prefix differs")
    route_review = loaded["v9_review"]
    if (
        route_review.get("verdict")
        != "PASS_READ_ONLY_PENDING_ADDRESSABLE_ROUTE_RECONCILIATION_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or route_review.get("integrated_commit") != "bad51da80cd52a23015a7aa8cd3b62dd08b123ef"
        or route_review.get("main_tracked_sha256", {}).get(V9_LEDGER) != PINS["v9_ledger"]["sha256"]
        or route_review.get("p1_freeze") != freeze
        or route_review.get("audit_task_credit") is not False
        or route_review.get("active_pair_mutated") is not False
    ):
        raise V10ReconciliationError("V9 independent review/prefix join differs")
    source_review = loaded["eth_review"]
    source_hashes = {
        name: PINS[key]["sha256"]
        for name, key in (
            ("RUN-MANIFEST.json", "eth_manifest"),
            ("SOURCE_RECEIPT.json", "eth_receipt"),
            ("company.sqlite3", "eth_db"),
        )
    }
    if (
        source_review.get("verdict")
        != "PASS_SELECTED_FICTIONAL_ETH001_SOURCE_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or source_review.get("integrated_commit") != "ad636fc8df1af3b94a6d2dd208ac8992e4c53c51"
        or source_review.get("main_run_sha256") != source_hashes
        or source_review.get("p1_freeze") != freeze
        or source_review.get("source_complete") is not False
        or source_review.get("audit_task_credit") is not False
        or source_review.get("actual_enterprise_code_approved") is not False
        or source_review.get("actual_employee_distribution_or_attestation") is not False
    ):
        raise V10ReconciliationError("ETH001 independent review/source join differs")
    receipt = conduct.verify(private / ETH_RUN, repository=repository, private_repository=private)
    if receipt != loaded["eth_receipt"] or loaded["eth_manifest"]["native_count"] != 19:
        raise V10ReconciliationError("Reviewed ETH001 native source replay differs")
    qualification = _accepted_v11(repository, private, freeze)
    result = _extend(previous, receipt, freeze, qualification=qualification)
    if frozen._p1_inventory(private) != freeze:
        raise V10ReconciliationError("Frozen P1 changed during read-only route build")
    return result


def markdown(result: dict) -> str:
    """Render the selected conduct route limits for human review."""
    counts = result["counts"]["A"]
    lines = [
        "# Paired 283-route selected ETH001 conduct reconciliation V10",
        "",
        "The exact 566-row JSON retains every V9 field. Three generic SH-ETH-001 "
        "procedure routes per side gain bounded source leads from the reviewed 19-version "
        "fictional conduct exercise, outside the frozen P1 audit pair.",
        "",
        "| Classification | Routes per side |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {name} | {number} |" for name, number in counts["classifications"].items())
    lines += [
        "",
        "Implementation and design reference the fictional draft, local approval and "
        "two-person selected roster. Operating-test leads retain all Clean and Messy "
        "native records, including the Messy false-clean, discovery, late acknowledgment "
        "and correction sequence. This is not an actual workforce population or operation. "
        "The 2026 enterprise code remains future/OPEN and the Messy historical "
        "exception remains open.",
        "",
        "The authored ACTION-H-SANCTIONS route stays UNSUPPORTED_EXACT_CLAUSE with no "
        "new source lead. No substantiated-case or no-case population decision, reasoned "
        "sanction, follow-up or performance-review conclusion is present. All other authored "
        "routes and gates remain as V9 recorded them. Targeted routes total "
        f"{counts['targeted_integrated_route_count']} per side.",
        "",
        "No source-complete population, audit task credit, fresh pair, grade, Key or Atlas "
        "write was issued. The frozen A/B P1 tasks remain NOT_STARTED/NOT_RUN.",
        "",
    ]
    return "\n".join(lines)
