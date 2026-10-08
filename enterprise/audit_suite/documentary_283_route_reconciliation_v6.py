"""Read-only exact V5 route successor for selected IAM005 and SEC003 sources."""

from __future__ import annotations

import hashlib
import json
import stat
from collections import Counter
from pathlib import Path

from . import company_iam005_emergency_marker_2027 as iam
from . import company_sec003_selected_vulnerability_2027 as sec
from . import documentary_283_route_reconciliation_v3 as pinned
from . import documentary_283_route_reconciliation_v5 as prior
from . import fictional_2027_candidate_registry_v6 as candidates
from . import fictional_2027_candidate_registry_v7 as candidates_v7
from . import fictional_2027_source_portfolio_v6 as portfolio
from . import fictional_2027_source_portfolio_v7 as portfolio_v7

SCHEMA = "SH_DOCUMENTARY_283_PAIRED_ROUTE_CANDIDATE_RECONCILIATION_V6"
PINS = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V6_PINS_2026-09-30.json"
BASE = "enterprise/generated/audit-suite"
V5_LEDGER = "enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V5_2026-09-30.json"
V5_REVIEW_SHA = "89d03c1b1b4a2450524c6093dbe5ab9c02452afde351da939c92e3f9c835497b"
V6_REVIEW_SHA = "7f067b8070d124be30dc4abc1653164ed6702b5601d0a4f90c6066a5ad9fde0b"
SEC_REVIEW_SHA = "f15bc7d94d04fa3599a0f852470e81ea53ce3dc1685d05d0fb15a65901013f36"
V7_REVIEW_SHA = "f49dd7f61a6afdda28ffd7ad366dde1e13269df229b70524d889ab1d85a68ea6"
IAM_SOURCE = "IAM005_EMERGENCY_MARKER_V1"
SEC_SOURCE = "SEC003_SELECTED_VULNERABILITY_V1"
LIMITS = {
    IAM_SOURCE: (
        "One fictional marker, human identity and inert service identity at Boise; "
        "no real ePHI access, complete trust-boundary population or independent assurance. "
        "Messy BCM and SEC005 exceptions remain open."
    ),
    SEC_SOURCE: (
        "Selected fictional four-asset vulnerability history; October false-clean "
        "sign-off and open missed-coverage exception remain. November AS-P008 "
        "recheck is self-review. No full inventory, scanner execution or authored "
        "CC7.1/CC5.2 support."
    ),
}


class V6ReconciliationError(prior.V5ReconciliationError):
    """A pinned review, source or exact frozen route changed."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pinned_db(private: Path, entry: dict) -> None:
    path = private / entry["path"]
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise V6ReconciliationError("Native database alias forbidden")
    before = path.stat()
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or stat.S_IMODE(before.st_mode) != 0o600
        or _sha(path) != entry["sha256"]
    ):
        raise V6ReconciliationError("Native database pin differs")
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_mode) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_mode,
    ) or _sha(path) != entry["sha256"]:
        raise V6ReconciliationError("Native database changed during read")


def _p1_inventory(private: Path) -> dict:
    """Hash the complete frozen P1 run without opening it for writing."""
    root = private / BASE / prior.P1_RUN
    if not root.is_dir() or root.is_symlink():
        raise V6ReconciliationError("P1 run root differs")
    entries = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise V6ReconciliationError("P1 alias forbidden")
        if path.is_file():
            info = path.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise V6ReconciliationError("P1 file identity differs")
            entries.append(
                (path.relative_to(root).as_posix(), stat.S_IMODE(info.st_mode), _sha(path))
            )
    encoded = json.dumps(entries, separators=(",", ":")).encode()
    return {"file_count": len(entries), "inventory_sha256": hashlib.sha256(encoded).hexdigest()}


def _selected_sec_routes(receipt: dict, previous: dict) -> dict[str, set[str]]:
    result = {}
    for side in "AB":
        expected = {
            row["task_id"]: row
            for row in previous["rows"]
            if row["side"] == side
            and (
                row["control_id"] == "SH-SEC-003"
                or (
                    row["control_id"] == "SH-SEC-001"
                    and row["task_id"].endswith("CHECK-SOC2:CC5.2")
                )
            )
        }
        source = receipt["selected_routes"][side]
        if (
            len(expected) != 5
            or len(source) != 5
            or {row["task_id"] for row in source} != set(expected)
        ):
            raise V6ReconciliationError(f"SEC003 selected route IDs differ: {side}")
        for row in source:
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
                raise V6ReconciliationError(f"SEC003 clause/gate differs: {side}")
        result[side] = set(expected)
    return result


def build(repository: Path, private_repository: Path) -> dict:
    """Reperform reviewed inputs and reconcile only the selected exact routes."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository).resolve(strict=True)
    pins = json.loads((repository / PINS).read_bytes())
    if pins.get("schema") != "SH_DOCUMENTARY_283_ROUTE_RECONCILIATION_V6_PINS_V1":
        raise V6ReconciliationError("V6 pins schema differs")
    p1_before = _p1_inventory(private)
    if p1_before != pins["p1_freeze"] or p1_before["file_count"] != 538:
        raise V6ReconciliationError("Frozen P1 run differs")
    loaded = {}
    for name, entry in pins["inputs"].items():
        if name.endswith("_db"):
            _pinned_db(private, entry)
        else:
            loaded[name] = pinned._pinned(repository, private, private, entry)
    old = prior.build(repository, private)
    if old != loaded["v5_ledger"]:
        raise V6ReconciliationError("Reviewed V5 ledger differs")
    v5_review = loaded["v5_review"]
    if (
        v5_review.get("verdict")
        != "PASS_READ_ONLY_PARTIAL_ROUTE_RECONCILIATION_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or v5_review.get("main_tracked_sha256", {}).get("ledger_json")
        != pins["inputs"]["v5_ledger"]["sha256"]
        or pins["inputs"]["v5_review"]["sha256"] != V5_REVIEW_SHA
    ):
        raise V6ReconciliationError("V5 independent review join differs")
    v6_review = loaded["v6_review"]
    if (
        pins["inputs"]["v6_review"]["sha256"] != V6_REVIEW_SHA
        or v6_review.get("verdict")
        != "PASS_PARTIAL_READ_ONLY_CANDIDATE_REGISTRY_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or v6_review.get("main_output_sha256")
        != {
            "portfolio": pins["inputs"]["v6_portfolio"]["sha256"],
            "candidate_A": pins["inputs"]["v6_candidate_a"]["sha256"],
            "candidate_B": pins["inputs"]["v6_candidate_b"]["sha256"],
            "candidate_report": pins["inputs"]["v6_candidate_report"]["sha256"],
        }
        or loaded["v6_portfolio"] != portfolio.verify_all(repository, private_repository=private)
        or loaded["v6_candidate_report"]
        != candidates.verify_candidate(
            private / BASE / "company-source-portfolio-v6-2026-09-30/main-candidate-v1",
            repository,
            private,
        )
    ):
        raise V6ReconciliationError("Reviewed V6 portfolio/candidate join differs")
    if (
        (loaded["v6_portfolio"]["source_count"], loaded["v6_portfolio"]["native_versions"])
        != (27, 500)
        or loaded["v6_portfolio"]["source_complete"] is not False
        or loaded["v6_portfolio"]["audit_task_credit"] is not False
        or loaded["v6_candidate_report"]["audit_task_credit"] is not False
    ):
        raise V6ReconciliationError("V6 partial source boundary differs")
    v7_review = loaded["v7_review"]
    if (
        pins["inputs"]["v7_review"]["sha256"] != V7_REVIEW_SHA
        or v7_review.get("verdict")
        != "PASS_PARTIAL_READ_ONLY_CANDIDATE_REGISTRY_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or v7_review.get("main_output_sha256")
        != {
            "portfolio": pins["inputs"]["v7_portfolio"]["sha256"],
            "candidate_A": pins["inputs"]["v7_candidate_a"]["sha256"],
            "candidate_B": pins["inputs"]["v7_candidate_b"]["sha256"],
            "candidate_report": pins["inputs"]["v7_candidate_report"]["sha256"],
        }
        or loaded["v7_portfolio"] != portfolio_v7.verify_all(repository, private_repository=private)
        or loaded["v7_candidate_report"]
        != candidates_v7.verify_candidate(
            private / BASE / "company-source-portfolio-v7-2026-09-30/main-candidate-v1",
            repository,
            private,
        )
    ):
        raise V6ReconciliationError("Reviewed V7 portfolio/candidate join differs")
    if (
        (
            loaded["v7_portfolio"].get("source_count"),
            loaded["v7_portfolio"].get("native_versions"),
            loaded["v7_portfolio"].get("source_component_count"),
        )
        != (28, 529, 29)
        or loaded["v7_portfolio"]["sources"][:27] != loaded["v6_portfolio"]["sources"]
        or loaded["v7_portfolio"]["source_complete"] is not False
        or loaded["v7_portfolio"]["audit_task_credit"] is not False
        or loaded["v7_candidate_report"]["audit_task_credit"] is not False
        or any(
            (
                loaded["v7_candidate_report"]["sides"][side]["component_count"],
                loaded["v7_candidate_report"]["sides"][side]["scenario_source_component_count"],
                loaded["v7_candidate_report"]["sides"][side]["system_alias_count"],
            )
            != (42, 29, 265)
            for side in "AB"
        )
    ):
        raise V6ReconciliationError("V7 selected source roster differs")
    iam_review = loaded["iam_review"]
    iam_receipt = loaded["iam_receipt"]
    iam_manifest = loaded["iam_manifest"]
    if (
        iam_review.get("verdict")
        != "PASS_SELECTED_FICTIONAL_NATIVE_SOURCE_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or iam_review.get("manifest_sha256") != pins["inputs"]["iam_manifest"]["sha256"]
        or iam_review.get("receipt_sha256") != pins["inputs"]["iam_receipt"]["sha256"]
        or iam_review.get("native_db_sha256") != pins["inputs"]["iam_db"]["sha256"]
        or iam_manifest.get("native_version_count") != 25
        or iam_receipt.get("native_version_counts") != {"CLEAN": 9, "MESSY": 16}
        or iam_receipt.get("authored_iam005_clause_satisfied") is not False
        or iam_receipt.get("source_complete") is not False
        or iam_receipt.get("audit_task_credit") is not False
        or iam.verify(
            private / BASE / "company-iam005-emergency-marker-2026-09-30/main-run-v1",
            repository=repository,
            private_repository=private,
        )["audit_task_credit"]
        is not False
    ):
        raise V6ReconciliationError("IAM005 reviewed source boundary differs")
    sec_review = loaded["sec_review"]
    sec_receipt = loaded["sec_receipt"]
    sec_manifest = loaded["sec_manifest"]
    if (
        pins["inputs"]["sec_review"]["sha256"] != SEC_REVIEW_SHA
        or sec_review.get("verdict")
        != "PASS_SELECTED_FICTIONAL_COMPANY_SOURCE_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or sec_review.get("sha256", {}).get("main_manifest")
        != pins["inputs"]["sec_manifest"]["sha256"]
        or sec_review.get("sha256", {}).get("main_receipt")
        != pins["inputs"]["sec_receipt"]["sha256"]
        or sec_review.get("sha256", {}).get("main_native_db") != pins["inputs"]["sec_db"]["sha256"]
        or sec_manifest.get("native_version_count") != 29
        or sec_receipt.get("native_version_counts") != {"CLEAN": 11, "MESSY": 18}
        or sec_receipt.get("messy_historical_exception_status") != "OPEN"
        or sec_receipt.get("messy_october_false_clean_preserved") is not True
        or sec_receipt.get("authored_sec003_cc71_or_sec001_cc52_clause_satisfied") is not False
        or sec_receipt.get("source_complete") is not False
        or sec_receipt.get("audit_task_credit") is not False
        or sec.verify(
            private / BASE / "company-sec003-selected-vulnerability-2026-09-30/main-run-v1",
            repository=repository,
            private_repository=private,
        )
        != sec_receipt
    ):
        raise V6ReconciliationError("SEC003 reviewed source boundary differs")
    selected_sec = _selected_sec_routes(sec_receipt, old)
    selected_iam = {
        side: {
            row["task_id"]
            for row in old["rows"]
            if row["side"] == side and row["control_id"] == "SH-IAM-005"
        }
        for side in "AB"
    }
    if any(len(selected_iam[side]) != 5 for side in "AB"):
        raise V6ReconciliationError("IAM005 route IDs differ")
    active, active_ids = prior._active_tasks(private)
    if active != old["active_p1_tasks"]:
        raise V6ReconciliationError("Active task state differs")
    rows = []
    for previous in old["rows"]:
        row = dict(previous)
        side, task_id = row["side"], row["task_id"]
        if task_id not in active_ids[side]:
            raise V6ReconciliationError("V5 route absent from active engagement")
        added = []
        if task_id in selected_iam[side]:
            added.append(IAM_SOURCE)
        if task_id in selected_sec[side]:
            added.append(SEC_SOURCE)
        row["v6_reviewed_source_ids"] = added
        row["v6_source_limits"] = {name: LIMITS[name] for name in added}
        if added:
            row["targeted_integrated_source_ids"] = sorted(
                set(row["targeted_integrated_source_ids"]) | set(added)
            )
            if row["classification"] == "DESIGN_CONTEXT_ONLY":
                if row["control_id"] != "SH-SEC-003" or row["authored_test_clause"] is not None:
                    raise V6ReconciliationError("Unexpected generic promotion")
                row["classification"] = "SOURCE_CANDIDATE_PARTIAL"
            if row["classification"] == "SOURCE_CANDIDATE_PARTIAL":
                row["candidate_or_design_source_ids"] = sorted(
                    set(row["candidate_or_design_source_ids"]) | set(added)
                )
        if any(
            row[key] != previous[key]
            for key in (
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
        ):
            raise V6ReconciliationError("Frozen task clause or status differs")
        rows.append(row)
    counts = {}
    for side in "AB":
        subset = [row for row in rows if row["side"] == side]
        classes = dict(sorted(Counter(row["classification"] for row in subset).items()))
        if (
            len(subset) != len({row["task_id"] for row in subset})
            or len(subset) != 283
            or classes
            != {
                "DESIGN_CONTEXT_ONLY": 33,
                "SOURCE_CANDIDATE_PARTIAL": 129,
                "UNSUPPORTED_EXACT_CLAUSE": 121,
            }
            or sum(row["authored_test_clause"] is not None for row in subset) != 154
        ):
            raise V6ReconciliationError("Exact 283-route classifications differ")
        counts[side] = {
            "classifications": classes,
            "targeted_integrated_route_count": sum(
                bool(row["targeted_integrated_source_ids"]) for row in subset
            ),
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
    if counts["A"] != counts["B"] or _p1_inventory(private) != p1_before:
        raise V6ReconciliationError("Paired result or frozen P1 run differs")
    return {
        "schema": SCHEMA,
        "as_of": "2026-09-30",
        "base_commit": pins["base_commit"],
        "v5_prefix_sha256": pins["inputs"]["v5_ledger"]["sha256"],
        "source_pins_sha256": _sha(repository / PINS),
        "source_pins": pins["inputs"],
        "p1_freeze": p1_before,
        "active_p1_tasks": active,
        "reviewed_source_roster": {
            "cohorts": 28,
            "native_versions": 529,
            "source_complete": False,
            "registry": "REVIEWED_MAIN_V7_PARTIAL_PORTFOLIO_AND_CANDIDATE",
        },
        "v6_portfolio_prefix": {"cohorts": 27, "native_versions": 500, "source_complete": False},
        "counts": counts,
        "rows": rows,
        "limits": [
            "Read-only fictional source-search triage; no task credit or clause satisfaction.",
            "IAM005 marker is one selected lead and its two authored clauses remain unsupported.",
            "SEC003 is selected vulnerability history; CC7.1 and CC5.2 remain unsupported.",
            "Messy historical exceptions and AS-P008 self-review limit any assurance inference.",
            "No source-complete population, collection, P1 change, Key, grade or Atlas write.",
        ],
        "audit_task_credit": False,
        "active_pair_mutated": False,
    }


def markdown(result: dict) -> str:
    counts = result["counts"]["A"]
    lines = [
        "# Paired 283-route source and clause reconciliation V6",
        "",
        "The exact 566-row JSON extends the independently reviewed V5 ledger with the "
        "main IAM005 emergency marker and SEC003 selected vulnerability sources. "
        "All 2027 events are fictional future history as of 2026-09-30.",
        "",
        "| Classification | Routes per side |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {name} | {number} |" for name, number in counts["classifications"].items())
    lines += [
        "",
        f"{counts['targeted_integrated_route_count']} distinct routes per side have named "
        "source leads. The three generic SH-SEC-003 gates move from design context "
        "to partial source leads. The 121 unsupported authored clauses remain "
        "unsupported; the 154 authored/129 inferred split is unchanged.",
        "",
        "IAM005 adds one fictional Boise marker exercise to five already targeted "
        "SH-IAM-005 routes. Its emergency-access and CC6.1 authored clauses remain "
        "unsupported. SEC003 adds a selected four-asset vulnerability history to "
        "four SH-SEC-003 routes and SH-SEC-001 CC5.2; CC7.1 and CC5.2 remain "
        "unsupported. The Messy October false-clean sign-off and open historical "
        "exception remain; November AS-P008 recheck is management self-review.",
        "",
        "The reviewed V6 prefix contains 27 cohorts and 500 native versions. "
        "The independently reviewed V7 portfolio joins SEC003 to reach 28 selected "
        "cohorts and 529 versions, with 42 components, 29 source pins and 265 "
        "aliases in each candidate. This is partial source routing, not a complete "
        "audit population. Both P1 engagements retain 409 `NOT_STARTED`/`NOT_RUN` "
        "tasks. The exact JSON retains every authored clause, remaining test gate, "
        "source pin and source limit.",
        "",
        "There is no audit task sufficiency, independent assurance, source completeness, "
        "actual 2027 deployment, collection, grade, Key or Atlas change.",
        "",
    ]
    return "\n".join(lines)
