"""Read-only 283-route successor for reviewed V4, governance and SEC005 sources.

This is source-search triage. It cannot start a task or certify an authored clause.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path

from . import company_gov_appetite_exercise as gov
from . import company_sec005_operated_2027 as operated
from . import documentary_283_route_reconciliation_v3 as prior
from . import fictional_2027_source_portfolio_v4 as portfolio

PINS = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V5_PINS_2026-09-30.json"
SCHEMA = "SH_DOCUMENTARY_283_PAIRED_ROUTE_CANDIDATE_RECONCILIATION_V5"
BASE = "enterprise/generated/audit-suite"
P1_RUN = "acceptance-audit-2026-09-22/aq06-aq07-integrated-full-portfolio-bootstrap-run-v1"
SOURCE_LABELS = {
    "rec003": "REC003_EXISTING_SNAPSHOT_V1",
    "sec005_symbolic": "SEC005_SYMBOLIC_LOCAL_V1",
    "ass001002": "ASS001002_OWNER_MONITOR_V1",
    "gov_appetite": "GOV_POL_ERM_APPETITE_V1",
    "sec005_operated": "SEC005_SELECTED_OPERATIONS_V2",
}
CONTROL_IDS = {
    "rec003": {"SH-REC-003"},
    "sec005_symbolic": {"SH-SEC-005"},
    "ass001002": {"SH-ASS-001", "SH-ASS-002"},
    "gov_appetite": {"SH-GOV-003", "SH-POL-002", "SH-ERM-002"},
    "sec005_operated": {"SH-SEC-005"},
}
ROUTE_COUNTS = {
    "rec003": 4,
    "sec005_symbolic": 5,
    "ass001002": 10,
    "gov_appetite": 16,
    "sec005_operated": 5,
}
LIMITS = {
    "rec003": (
        "Exact existing data-quality versions in independent A/B snapshots; inherited "
        "audit journals are excluded. No new operation, complete transformation "
        "lineage or design test."
    ),
    "sec005_symbolic": (
        "Data-only local boundary trace; no executable, network packet, deployed "
        "interface census, ePHI or authored CC6.6/CC6.8 support."
    ),
    "ass001002": (
        "One selected owner and monitoring quarter; Messy omission and open "
        "escalation remain. No complete duties, independent evaluation or certification."
    ),
    "gov_appetite": (
        "One fictional Board decision and bounded delegation; the Messy waiver "
        "remains denied/open. No real Board, HIPAA designation, legal applicability "
        "or full control population."
    ),
    "sec005_operated": (
        "Selected fictional four-asset/six-interface period; November source "
        "recheck is AS-P008 self-review, not independent assurance. October false "
        "pass and historical exception remain. No full-year census or authored "
        "CC6.6/CC6.8 support."
    ),
}


class V5ReconciliationError(prior.V3ReconciliationError):
    """A reviewed source, exact route, or frozen audit boundary changed."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _active_tasks(private: Path) -> tuple[dict[str, dict], dict[str, set[str]]]:
    """Read only the frozen active engagements; no task command is issued."""
    result = {}
    identities = {}
    for side in "AB":
        path = private / BASE / P1_RUN / "audit" / side / "audit-state" / "engagements.sqlite3"
        if path.is_symlink() or not path.is_file():
            raise V5ReconciliationError("Active P1 engagement input differs")
        with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
            db.execute("PRAGMA query_only=ON")
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise V5ReconciliationError("Active P1 engagement integrity differs")
            states = [json.loads(row[0]) for row in db.execute("SELECT state FROM engagements")]
        if len(states) != 1 or len(states[0].get("tasks", [])) != 409:
            raise V5ReconciliationError("Active P1 task denominator differs")
        tasks = states[0]["tasks"]
        if len({task["id"] for task in tasks}) != 409 or any(
            task.get("status") != "NOT_STARTED" or task.get("conclusion") != "NOT_RUN"
            for task in tasks
        ):
            raise V5ReconciliationError("Active P1 task status/conclusion differs")
        result[side] = {"task_count": 409, "status": "NOT_STARTED", "conclusion": "NOT_RUN"}
        identities[side] = {task["id"] for task in tasks}
    return result, identities


def _source_routes(name: str, receipt: dict, old: dict) -> dict[str, set[str]]:
    result = {}
    for side in "AB":
        if name == "rec003":
            selected = {
                row["task_id"]
                for row in old["rows"]
                if row["side"] == side and row["control_id"] == "SH-REC-003"
            }
            source = receipt["sides"][side]
            if (
                source["native_original_count"] != 11
                or source["candidate_only_no_new_company_operation"] is not True
            ):
                raise V5ReconciliationError("REC003 existing-original boundary differs")
        elif name in {"sec005_symbolic", "sec005_operated"}:
            authority = receipt["selected_route_authority"][side]
            selected = set(authority["task_ids"])
            if authority["authored_unsupported"] != 2 or authority["inferred"] != 3:
                raise V5ReconciliationError("SEC005 authored/inferred split differs")
        else:
            entries = receipt["selected_routes"][side]
            selected = {row["task_id"] for row in entries}
            if len(entries) != len(selected):
                raise V5ReconciliationError(f"Duplicate selected route: {name}/{side}")
            existing = {row["task_id"]: row for row in old["rows"] if row["side"] == side}
            if any(
                row["authored_test_clause"] != existing[row["task_id"]]["authored_test_clause"]
                or row["control_id"] != existing[row["task_id"]]["control_id"]
                or row["remaining_test_gate"] != existing[row["task_id"]]["remaining_test_gate"]
                for row in entries
            ):
                raise V5ReconciliationError(f"Exact selected clause/gate differs: {name}/{side}")
        expected = {
            row["task_id"]
            for row in old["rows"]
            if row["side"] == side and row["control_id"] in CONTROL_IDS[name]
        }
        if len(selected) != ROUTE_COUNTS[name] or selected != expected:
            raise V5ReconciliationError(f"Exact selected task IDs differ: {name}/{side}")
        result[side] = selected
    return result


def build(repository: Path, private_repository: Path) -> dict:
    """Reperform V3/V4 and source verifiers, then classify exact frozen routes."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    pins = json.loads((repository / PINS).read_bytes())
    if pins.get("schema") != "SH_DOCUMENTARY_283_ROUTE_RECONCILIATION_V5_PINS_V1":
        raise V5ReconciliationError("V5 pins schema differs")
    loaded = {
        name: prior._pinned(repository, private, private, entry)
        for name, entry in pins["inputs"].items()
        if not name.endswith("_db") and not name.endswith(("_db_a", "_db_b"))
    }
    # Database bytes are also independently pinned by the native source verifiers.
    for name, entry in pins["inputs"].items():
        if name not in loaded:
            path = private / entry["path"]
            if path.is_symlink() or _sha(path) != entry["sha256"]:
                raise V5ReconciliationError(f"Native database pin differs: {name}")
    old = prior.build(repository, private, private)
    if (
        old != loaded["v3_ledger"]
        or loaded["v3_review"].get("verdict") != "PASS_READ_ONLY_PARTIAL_ROUTE_RECONCILIATION"
        or loaded["v3_review"].get("tracked_sha256", {}).get("ledger_json")
        != pins["inputs"]["v3_ledger"]["sha256"]
    ):
        raise V5ReconciliationError("Reviewed V3 ledger join differs")
    v4 = portfolio.verify_all(repository, private_repository=private)
    review = loaded["v4_review"]
    if (
        v4 != loaded["v4_report"]
        or (v4["source_count"], v4["native_versions"], v4["source_component_count"])
        != (24, 401, 25)
        or v4["source_complete"] is not False
        or v4["audit_task_credit"] is not False
        or review.get("verdict") != "PASS_PARTIAL_READ_ONLY_CANDIDATE_REGISTRY_NO_AUDIT_CREDIT"
        or review.get("portfolio_report_sha256") != pins["inputs"]["v4_report"]["sha256"]
        or review.get("active_pair_mutated") is not False
    ):
        raise V5ReconciliationError("Reviewed V4 portfolio join differs")
    v4_sources = {row["source"]: row for row in v4["sources"]}
    selected = {}
    for name, descriptor in pins["sources"].items():
        receipt = loaded[name + "_receipt"]
        manifest = loaded[name + "_manifest"]
        source_review = loaded[name + "_review"]
        receipt_sha = pins["inputs"][name + "_receipt"]["sha256"]
        manifest_sha = pins["inputs"][name + "_manifest"]["sha256"]
        if (
            source_review.get("verdict") != descriptor["verdict"]
            or source_review.get("selected_run", source_review.get("main_run")) != descriptor["run"]
            or source_review.get("receipt_sha256") != receipt_sha
            or source_review.get("manifest_sha256") != manifest_sha
            or source_review.get("active_pair_mutated") is not False
            or manifest.get("receipt_sha256") != receipt_sha
            or manifest.get("audit_task_credit") is not False
            or receipt.get("audit_task_credit") is not False
        ):
            raise V5ReconciliationError(f"Independent source review/receipt join differs: {name}")
        if name == "rec003":
            if (
                receipt.get("new_company_operation") is not False
                or receipt.get("audit_collection") is not False
                or receipt.get("source_complete") is not False
                or manifest.get("routes_sha256") != pins["inputs"]["rec003_routes"]["sha256"]
                or v4_sources["rec003"]["native_versions"] != 22
            ):
                raise V5ReconciliationError("REC003 existing-source boundary differs")
        elif name == "sec005_symbolic":
            if (
                receipt.get("authored_sec005_clause_support") is not False
                or receipt.get("actual_operation_eligibility_as_of_2026_09_29") is not False
                or (receipt.get("network_packets_sent"), receipt.get("executables_created_or_run"))
                != (0, 0)
                or v4_sources["sec005"]["native_versions"] != 13
            ):
                raise V5ReconciliationError("SEC005 symbolic boundary differs")
        elif name == "ass001002":
            if (
                receipt.get("corporate_certification_accepted") is not False
                or receipt.get("independent_evaluation_completed") is not False
                or receipt.get("messy_exception_open") is not True
                or v4_sources["ass001002"]["native_versions"] != 8
            ):
                raise V5ReconciliationError("ASS001/002 selected boundary differs")
        elif name == "gov_appetite":
            run = private / BASE / descriptor["folder"] / descriptor["run"]
            if (
                gov.verify(run, repository=repository, private_repository=private) != receipt
                or receipt.get("real_board_approval") is not False
                or receipt.get("actual_hipaa_applicability") != "UNDETERMINED"
                or receipt.get("source_complete") is not False
                or receipt.get("messy_challenge_open") is not True
                or manifest.get("native_version_count") != 34
            ):
                raise V5ReconciliationError("GOV/POL/ERM selected boundary differs")
        elif name == "sec005_operated":
            run = private / BASE / descriptor["folder"] / descriptor["run"]
            transition = private / BASE / "company-runtime-transition-2026-09-29/run-v3"
            if (
                operated.verify(
                    run,
                    repository=repository,
                    private_repository=private,
                    transition_root=transition,
                )
                != {
                    "status": "VERIFIED_FICTIONAL_SELECTED_OPERATION_NO_AUDIT_CREDIT",
                    "native_version_counts": {"CLEAN": 17, "MESSY": 23},
                }
                or receipt.get("authored_sec005_clause_satisfied") is not False
                or receipt.get("full_year_or_enterprise_population_complete") is not False
                or receipt.get("actual_operation_eligibility_as_of_2026_09_30") is not False
                or receipt.get("november_review_independence")
                != "FRESH_NATIVE_SOURCE_AS_P008_SELF_REVIEW_NO_INDEPENDENT_ASSURANCE"
                or manifest.get("native_version_count") != 40
            ):
                raise V5ReconciliationError("SEC005 selected-operated boundary differs")
        if descriptor["native_versions"] not in (22, 13, 8, 34, 40):
            raise V5ReconciliationError("Source native denominator differs")
        selected[name] = _source_routes(name, receipt, old)
    if (
        sum(
            pins["sources"][name]["native_versions"] for name in ("gov_appetite", "sec005_operated")
        )
        != 74
    ):
        raise V5ReconciliationError("New native version denominator differs")
    active, active_ids = _active_tasks(private)
    rows = []
    for previous in old["rows"]:
        row = dict(previous)
        side, task_id = row["side"], row["task_id"]
        if task_id not in active_ids[side]:
            raise V5ReconciliationError("Reconciled task absent from active P1 engagement")
        added = [name for name in SOURCE_LABELS if task_id in selected[name][side]]
        row["v5_reviewed_source_ids"] = [SOURCE_LABELS[name] for name in added]
        row["v5_source_limits"] = {SOURCE_LABELS[name]: LIMITS[name] for name in added}
        if added:
            row["targeted_integrated_source_ids"] = sorted(
                set(row["targeted_integrated_source_ids"]) | set(row["v5_reviewed_source_ids"])
            )
            if row["authored_test_clause"] is None and row["control_id"] != "SH-REC-003":
                if row["classification"] != "DESIGN_CONTEXT_ONLY":
                    raise V5ReconciliationError("Unexpected prior generic classification")
                row["classification"] = "SOURCE_CANDIDATE_PARTIAL"
                row["candidate_or_design_source_ids"] = sorted(
                    set(row["candidate_or_design_source_ids"]) | set(row["v5_reviewed_source_ids"])
                )
            elif (
                row["authored_test_clause"] is not None
                and row["classification"] != "UNSUPPORTED_EXACT_CLAUSE"
                and row["control_id"] != "SH-REC-003"
            ):
                raise V5ReconciliationError("Authored successor clause cannot be credited")
        if (
            row["current_status"] != "NOT_STARTED"
            or row["current_conclusion"] != "NOT_RUN"
            or row["audit_task_credit"] is not False
            or row["actual_operation_eligibility_as_of_packet"] is not False
        ):
            raise V5ReconciliationError("Frozen task/no-credit boundary differs")
        rows.append(row)
    counts = {}
    for side in "AB":
        subset = [row for row in rows if row["side"] == side]
        classes = dict(sorted(Counter(row["classification"] for row in subset).items()))
        targeted = sum(bool(row["targeted_integrated_source_ids"]) for row in subset)
        if (
            len(subset) != 283
            or len({row["task_id"] for row in subset}) != 283
            or classes
            != {
                "DESIGN_CONTEXT_ONLY": 36,
                "SOURCE_CANDIDATE_PARTIAL": 126,
                "UNSUPPORTED_EXACT_CLAUSE": 121,
            }
            or targeted != 157
            or sum(row["authored_test_clause"] is not None for row in subset) != 154
        ):
            raise V5ReconciliationError("Exact successor route totals differ")
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
    if counts["A"] != counts["B"]:
        raise V5ReconciliationError("Paired successor classification differs")
    return {
        "schema": SCHEMA,
        "as_of": "2026-09-30",
        "base_commit": pins["base_commit"],
        "reviewed_source_roster": {"cohorts": 26, "native_versions": 475, "source_complete": False},
        "v4_prefix": {"cohorts": 24, "native_versions": 401, "source_complete": False},
        "source_pins_sha256": _sha(repository / PINS),
        "source_pins": pins["inputs"],
        "active_p1_tasks": active,
        "counts": counts,
        "rows": rows,
        "limits": [
            "Read-only future-fictional source-search triage, not procedure "
            "execution or task disposition.",
            "The same five SEC005 route IDs are counted once despite symbolic "
            "and selected-operated sources.",
            "REC003 copies eleven existing business versions per side; inherited "
            "audit journals are excluded and no new operation is asserted.",
            "Authored duties remain unsupported; actual HIPAA applicability, "
            "security-official designation, independent assurance, ePHI and "
            "operating-period completeness are not established.",
            "The active P1 pair, Key, workpapers, task commands and Atlas were not changed.",
        ],
        "audit_task_credit": False,
        "active_pair_mutated": False,
    }


def markdown(result: dict) -> str:
    counts = result["counts"]["A"]
    lines = [
        "# Paired 283-route source and clause reconciliation V5",
        "",
        "The exact 566-row JSON joins the reviewed 24-cohort/401-version V4 routing "
        "prefix to the separately reviewed governance and selected-operated SEC005 "
        "sources. The successor has 26 source cohorts and 475 reviewed native "
        "business versions. All 2027 events are fictional future history as of "
        "2026-09-30.",
        "",
        "| Classification | Routes per side |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {name} | {number} |" for name, number in counts["classifications"].items())
    lines += [
        "",
        f"{counts['targeted_integrated_route_count']} distinct task IDs per side have "
        "named source leads. Eighteen inferred gates per side move from design-only "
        "to partial-source context; the 121 unsupported authored clauses remain "
        "unsupported. The 154 authored/129 inferred split is unchanged. Both "
        "active engagements retain 409 `NOT_STARTED`/`NOT_RUN` tasks.",
        "",
        "REC003 contributes separate A/B byte-identical snapshots of eleven "
        "previously existing versions each, with historical access journals "
        "excluded. It adds no new operation, and its four routes were already "
        "targeted by earlier source context. Symbolic and selected-operated SEC005 "
        "sources share exactly five route IDs; those routes are counted once. The "
        "selected-operated source covers four fictional assets and six interfaces "
        "during a bounded period, preserves the Messy October false pass and open "
        "historical exception, and expressly discloses AS-P008 self-review in November.",
        "",
        "Governance provides one selected fictional decision and bounded delegation "
        "with a denied/open Messy waiver. ASS001/002 provides one selected owner-monitor "
        "quarter and an open Messy escalation. Neither is a complete or independently "
        "assured population. The exact JSON retains each task's authored clause, "
        "remaining test gate, source pins and limits.",
        "",
        "There is no real Board action, HIPAA legal designation, actual PHI or "
        "2027 deployment, full SOC 2 operating period, source completeness, audit "
        "collection or task credit. P1, workpapers, the Key and Atlas remain untouched.",
        "",
    ]
    return "\n".join(lines)
