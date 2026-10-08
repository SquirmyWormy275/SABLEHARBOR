"""Read-only successor for 21 reviewed fictional cohorts and 283 routes per side.

This diagnostic records bounded native leads. It never grants audit task credit.
"""

from __future__ import annotations

import hashlib
import json
import stat
from collections import Counter
from pathlib import Path

from . import documentary_283_route_reconciliation as prior

PINS = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V3_PINS_2026-09-29.json"
SCHEMA = "SH_DOCUMENTARY_283_PAIRED_ROUTE_CANDIDATE_RECONCILIATION_V3"
NEW_SOURCES = {
    "eng005": ("SH-ENG-005", "ENG005_LOCAL_V1", 19),
    "prd": ("SH-PRD-002", "PRD_INTERNAL_V2", 15),
    "eth003": ("SH-ETH-003", "ETH003_SPEAKUP_V1", 14),
    "eth004": ("SH-ETH-004", "ETH004_CONFLICT_V1", 13),
    "ppl002": ("SH-PPL-002", "PPL002_SCREENING_V1", 12),
    "iam005": ("SH-IAM-005", "IAM005_LOCAL_V1", 29),
}
CONTROLS = {
    "eng005": {"SH-ENG-005"},
    "prd": {"SH-PRD-002", "SH-PRD-003", "SH-PRD-004"},
    "eth003": {"SH-ETH-003"},
    "eth004": {"SH-ETH-004"},
    "ppl002": {"SH-PPL-002"},
    "iam005": {"SH-IAM-005"},
}
EXPECTED_TASKS = {"eng005": 4, "prd": 12, "eth003": 5, "eth004": 4, "ppl002": 3, "iam005": 5}
LIMITS = [
    "Read-only source-search classification, not procedure execution, "
    "population completeness or audit credit.",
    "All simulated 2027 events remain future as of 2026-09-29 and are "
    "ineligible as actual operation.",
    "ENG005 has no authorized/deployed emergency change; PRD has no "
    "external send or customer response.",
    "ETH003 has no regulator case or sanctions; ETH004 no proved fraud "
    "or qualified disposition; PPL002 no screening result or employment; "
    "IAM005 no real trust boundary, usable secret, PHI or emergency access.",
    "External, legal, qualified-owner and historical operating facts cannot "
    "be inferred from scenario sources.",
    "The frozen paired audit state, Key, workpapers, task commands and Atlas are untouched.",
]
SOURCE_LIMITS = {
    "eng005": (
        "One local future in-memory emergency-change fixture with blocked authority; "
        "no normal or deployed change population, independent approval, security "
        "test or deployment verification."
    ),
    "prd": (
        "One fictional internal customer/service impact and concern path; no "
        "external message, receipt, customer response or executed commitment."
    ),
    "eth003": (
        "One payload-free internal routing marker; no regulator request, "
        "substantiated case, sanction, actual retaliation or committee disposition."
    ),
    "eth004": (
        "One synthetic procurement affiliation indicator and local hold/withdrawal; "
        "no override or dishonest-reporting scenario, fraud finding, award or "
        "qualified disposition."
    ),
    "ppl002": (
        "One synthetic requisition negative gate; no person, screening outcome, "
        "employment assignment, access or qualified applicability decision."
    ),
    "iam005": (
        "One 59-byte nonpersonal object in separate local human and inert-service "
        "ledgers; no enterprise trust boundary, credential/secret, PHI emergency "
        "exercise or deployment."
    ),
}


class V3ReconciliationError(prior.ReconciliationError):
    """A reviewed roster, native source or exact route boundary changed."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pinned(repository: Path, private: Path, portfolio: Path, entry: dict) -> dict:
    root = {"repo": repository, "private": private, "portfolio": portfolio}[entry["scope"]]
    path = root / entry["path"]
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise V3ReconciliationError("Input alias forbidden")
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise V3ReconciliationError("Ordinary single-link input required")
    if entry["scope"] != "repo" and stat.S_IMODE(before.st_mode) != 0o600:
        raise V3ReconciliationError("Private input mode differs")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
        raise V3ReconciliationError(f"Pinned input differs: {entry['path']}")
    after = path.stat()

    def identity(info) -> tuple[int, int, int, int, int]:
        return (
            info.st_dev,
            info.st_ino,
            info.st_size,
            info.st_mtime_ns,
            stat.S_IMODE(info.st_mode),
        )

    if identity(before) != identity(after) or _sha(path) != entry["sha256"]:
        raise V3ReconciliationError("Input changed during read")
    return json.loads(raw)


def _nested(obj: dict, path: str) -> object:
    value = obj
    for key in path.split("/"):
        value = value[key]
    return value


def _route_rows(source: str, receipt: dict, side: str, report: dict | None) -> list[dict] | None:
    if source == "eng005":
        return report["route_disposition"][side]
    if source in {"eth003", "eth004", "ppl002"}:
        return receipt["routes"][side]
    return None


def _selected_ids(source: str, receipt: dict, side: str, report: dict | None) -> set[str]:
    rows = _route_rows(source, receipt, side, report)
    if rows is not None:
        return {row["task_id"] for row in rows}
    return set(receipt["selected_route_authority"][side]["task_ids"])


def _check_source(source: str, loaded: dict, pins: dict, old: dict) -> None:
    descriptor = pins["new_sources"][source]
    receipt = loaded[source + "_receipt"]
    review = loaded[source + "_review"]
    if not str(review.get("verdict", "")).startswith("PASS"):
        raise V3ReconciliationError(f"Independent review not PASS: {source}")
    reviewed = _nested(review, descriptor["review_join_field"])
    if reviewed != pins["inputs"][descriptor["reviewed_input"]]["sha256"]:
        raise V3ReconciliationError(f"Review/source byte join differs: {source}")
    if receipt.get("audit_task_credit") is not False:
        raise V3ReconciliationError(f"Source grants credit: {source}")
    if receipt.get("actual_2027_operation", False) is True:
        raise V3ReconciliationError(f"Source claims actual operation: {source}")
    if (
        source in {"prd", "iam005"}
        and receipt["actual_operation_eligibility_as_of_2026_09_29"] is not False
    ):
        raise V3ReconciliationError(f"Future operation eligibility differs: {source}")
    if source == "prd" and (
        receipt["authored_external_communication_clause_support"] is not False
        or receipt["external_send_counts"] != {"CLEAN": 0, "MESSY": 0}
    ):
        raise V3ReconciliationError("External PRD communication boundary differs")
    if source == "iam005" and (
        receipt["authored_iam005_clause_support"] is not False
        or receipt["object_byte_count"] != 59
        or receipt["separate_native_ledgers"] != ["human", "service"]
    ):
        raise V3ReconciliationError("IAM005 local identity boundary differs")
    if source == "eng005" and (
        loaded["eng005_report"]["corporate_emergency_approval"] is not False
        or loaded["eng005_report"]["deployed_change"] is not False
    ):
        raise V3ReconciliationError("ENG005 authority boundary differs")
    expected_rows = {
        side: {
            row["task_id"]: row
            for row in old["rows"]
            if row["side"] == side and row["control_id"] in CONTROLS[source]
        }
        for side in "AB"
    }
    for side in "AB":
        expected = expected_rows[side]
        if len(expected) != EXPECTED_TASKS[source] or _selected_ids(
            source, receipt, side, loaded.get("eng005_report")
        ) != set(expected):
            raise V3ReconciliationError(f"Exact selected task IDs differ: {source}/{side}")
        rows = _route_rows(source, receipt, side, loaded.get("eng005_report"))
        if rows is None:
            authority = receipt["selected_route_authority"][side]
            if authority["authored_clause_count"] != sum(
                row["authored_test_clause"] is not None for row in expected.values()
            ) or authority["inferred_gate_count"] != sum(
                row["authored_test_clause"] is None for row in expected.values()
            ):
                raise V3ReconciliationError(f"Authored/inferred task split differs: {source}")
            continue
        if len(rows) != len(expected):
            raise V3ReconciliationError(f"Duplicate or missing source route: {source}")
        for row in rows:
            old_row = expected[row["task_id"]]
            if (
                row["procedure_type"] != old_row["procedure_type"]
                or row["authored_test_clause"] != old_row["authored_test_clause"]
                or row.get("current_status", row.get("status")) != "NOT_STARTED"
                or row.get("current_conclusion", row.get("conclusion")) != "NOT_RUN"
                or row["task_credit"] is not False
            ):
                raise V3ReconciliationError(f"Exact source clause/status differs: {source}")


def build(
    repository: Path, private_repository: Path, portfolio_repository: Path | None = None
) -> dict:
    """Reperform V2 then join six more reviewed native cohorts, without task writes."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    portfolio_root = Path(portfolio_repository or private).resolve(strict=True)
    pins = json.loads((repository / PINS).read_text())
    if pins["schema"] != "SH_DOCUMENTARY_283_ROUTE_RECONCILIATION_V3_PINS_V1":
        raise V3ReconciliationError("V3 pin schema differs")
    loaded = {
        name: _pinned(repository, private, portfolio_root, entry)
        for name, entry in pins["inputs"].items()
    }
    old = prior.build(repository, private)
    if old != loaded["v2_ledger"]:
        raise V3ReconciliationError("Independently reviewed V2 baseline differs")
    v2_review = loaded["v2_review"]
    if (
        v2_review.get("verdict") != "PASS_READ_ONLY_PARTIAL_ROUTE_RECONCILIATION"
        or v2_review.get("tracked_sha256", {}).get("ledger_json")
        != pins["inputs"]["v2_ledger"]["sha256"]
    ):
        raise V3ReconciliationError("V2 review/ledger join differs")
    for source in NEW_SOURCES:
        _check_source(source, loaded, pins, old)
    portfolio = loaded["portfolio_report"]
    portfolio_review = loaded["portfolio_review"]
    portfolio_v2 = loaded["portfolio_v2_report"]
    portfolio_v2_review = loaded["portfolio_v2_review"]
    if (
        portfolio["source_count"] != 21
        or portfolio["native_versions"] != 358
        or portfolio["source_complete"] is not False
        or portfolio["audit_task_credit"] is not False
        or not str(portfolio_review.get("verdict", "")).startswith("PASS")
        or _nested(portfolio_review, pins["portfolio_review_join_field"])
        != pins["inputs"]["portfolio_report"]["sha256"]
    ):
        raise V3ReconciliationError("Reviewed 21/358 portfolio boundary differs")
    if (
        portfolio_v2.get("source_count") != 15
        or portfolio_v2.get("native_versions") != 256
        or portfolio_v2_review.get("verdict") != "PASS_PARTIAL_DIAGNOSTIC_FOR_INTEGRATION_REVIEW"
        or portfolio_v2_review.get("portfolio_report_sha256")
        != pins["inputs"]["portfolio_v2_report"]["sha256"]
        or portfolio["sources"][:15] != portfolio_v2["sources"]
    ):
        raise V3ReconciliationError("Reviewed V2 portfolio prefix differs")
    portfolio_sources = {row["source"]: row for row in portfolio["sources"]}
    if len(portfolio_sources) != 21:
        raise V3ReconciliationError("Portfolio source identity duplicates or omits cohorts")
    for source, descriptor in pins["new_sources"].items():
        row = portfolio_sources[descriptor["portfolio_key"]]
        if (
            row["native_versions"] != NEW_SOURCES[source][2]
            or row["review_sha256"] != pins["inputs"][source + "_review"]["sha256"]
            or row["receipt_sha256"] != pins["inputs"][source + "_receipt"]["sha256"]
            or row["audit_task_credit"] is not False
        ):
            raise V3ReconciliationError(f"Portfolio/source join differs: {source}")
    rows = []
    for old_row in old["rows"]:
        row = dict(old_row)
        for source, controls in CONTROLS.items():
            if row["control_id"] not in controls:
                continue
            label = NEW_SOURCES[source][1]
            if row["classification"] not in {
                "DESIGN_CONTEXT_ONLY",
                "UNSUPPORTED_EXACT_CLAUSE",
            }:
                raise V3ReconciliationError(f"Unexpected V2 classification: {source}")
            row["targeted_integrated_source_ids"] = sorted(
                set(row["targeted_integrated_source_ids"]) | {label}
            )
            if row["authored_test_clause"] is None:
                if row["classification"] != "DESIGN_CONTEXT_ONLY":
                    raise V3ReconciliationError("Generic V2 gate differs")
                row["classification"] = "SOURCE_CANDIDATE_PARTIAL"
                row["candidate_or_design_source_ids"] = sorted(
                    set(row["candidate_or_design_source_ids"]) | {label}
                )
            elif row["classification"] != "UNSUPPORTED_EXACT_CLAUSE":
                raise V3ReconciliationError("Authored V2 clause differs")
            row["source_limit"] = SOURCE_LIMITS[source]
            break
        rows.append(row)
    if len(rows) != 566:
        raise V3ReconciliationError("Exact paired task denominator differs")
    counts = {}
    for side in "AB":
        selected = [row for row in rows if row["side"] == side]
        classes = dict(sorted(Counter(row["classification"] for row in selected).items()))
        targeted = sum(bool(row["targeted_integrated_source_ids"]) for row in selected)
        if (
            classes
            != {
                "DESIGN_CONTEXT_ONLY": 54,
                "SOURCE_CANDIDATE_PARTIAL": 108,
                "UNSUPPORTED_EXACT_CLAUSE": 121,
            }
            or targeted != 126
        ):
            raise V3ReconciliationError("V3 expected classification/target totals differ")
        counts[side] = {
            "classifications": classes,
            "targeted_integrated_route_count": targeted,
            "authored_clause_count": sum(
                row["authored_test_clause"] is not None for row in selected
            ),
            "inferred_gate_count": sum(row["authored_test_clause"] is None for row in selected),
            "by_family": {
                family: dict(
                    sorted(
                        Counter(
                            row["classification"] for row in selected if row["family"] == family
                        ).items()
                    )
                )
                for family in sorted({row["family"] for row in selected})
            },
        }
    if counts["A"] != counts["B"] or counts["A"]["authored_clause_count"] != 154:
        raise V3ReconciliationError("Paired/authored task split differs")
    return {
        "schema": SCHEMA,
        "as_of": "2026-09-29",
        "base_commit": pins["base_commit"],
        "reviewed_source_roster": {"cohorts": 21, "native_versions": 358, "source_complete": False},
        "source_pins_sha256": _sha(repository / PINS),
        "source_pins": pins["inputs"],
        "counts": counts,
        "rows": rows,
        "limits": LIMITS,
        "audit_task_credit": False,
        "active_pair_mutated": False,
    }


def markdown(result: dict) -> str:
    """Render concise counts and authority limits; JSON retains exact route clauses."""
    count = result["counts"]["A"]
    lines = [
        "# Paired 283-route source and clause reconciliation V3",
        "",
        "This read-only successor joins the independently reviewed 15-source V2 "
        "baseline to six additional bounded fictional cohorts. The exact 566-row "
        "JSON keeps every task ID, authored clause or inferred gate, source target, "
        "missing gate and no-credit status. V2 remains historical.",
        "",
        "The reviewed portfolio contains 21 selected source cohorts and 358 native "
        "versions. It is source-incomplete; all 2027 activity is fictional and "
        "future as of 2026-09-29. No audit task has started or run.",
        "",
        "| Candidate classification | Routes per side |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {name} | {number} |" for name, number in count["classifications"].items())
    lines += [
        "",
        f"{count['targeted_integrated_route_count']} distinct routes per side are "
        "named by the reviewed cohorts. Targeting is not clause sufficiency: "
        "nine newly targeted authored duties remain unsupported, while 24 "
        "inferred/generic gates move from design-only to partial native-source "
        "leads. The 154 authored and 129 inferred route split is unchanged.",
        "",
        "| Family | Partial native | Design only | Unsupported clause |",
        "| --- | ---: | ---: | ---: |",
    ]
    for family, classes in count["by_family"].items():
        lines.append(
            f"| {family} | {classes.get('SOURCE_CANDIDATE_PARTIAL', 0)} | "
            f"{classes.get('DESIGN_CONTEXT_ONLY', 0)} | "
            f"{classes.get('UNSUPPORTED_EXACT_CLAUSE', 0)} |"
        )
    lines += [
        "",
        "ENG005 contributes a blocked local emergency-change history, not an "
        "authorized deployment. PRD covers only internal routing and cannot "
        "support the three external communication duties. ETH003 has no regulator "
        "case or sanctions; ETH004 has no override/dishonest-reporting or qualified "
        "fraud disposition. PPL002 lacks actual screening and employment facts. "
        "IAM005 is a local nonpersonal two-ledger trace with no deployed trust "
        "boundary, usable credential or ePHI emergency exercise. Each source's "
        "exact task limits remain in the JSON.",
        "",
        "External customer/provider responses, contract/legal status, qualified "
        "owner decisions, actual PHI processing, enterprise populations, real "
        "historical 2027 operation and ordinary audit procedures remain separate "
        "gates. The frozen A/B pair, task commands, workpapers, Key and Atlas "
        "were not changed.",
        "",
    ]
    return "\n".join(lines)
