"""V14 partial source roster with one reviewed POL004 procedure-trace cohort."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from . import company_pol004_procedure_trace_2027 as procedure
from . import fictional_2027_source_portfolio_v13 as prior
from .documentary_283_route_reconciliation_v6 import _p1_inventory
from .fictional_2027_source_portfolio import BASE, PortfolioVerificationError, _digest, _identity
from .fictional_2027_source_portfolio_v4 import (
    JOURNALS,
    _frozen_rows,
    _no_sidecars,
    _pin,
    _private,
    _read_json,
)

SCHEMA = "SH_FICTIONAL_2027_REVIEWED_SOURCE_PORTFOLIO_DIAGNOSTIC_V14"
V13_FOLDER = "company-source-portfolio-v13-2026-09-30"
V13_REVIEW_SHA = "a035f34e1b530000395483dd2ae3b7eae9dc68fc0d881cca84373140a0c7f69f"
V13_REPORT_SHA = "f07da9b6a2aa261c63a2cad0c8bef31ecbb4d56c397e8ee1b0d0b261ff088954"
V13_CANDIDATE_SHA = {
    "A.json": "aa0750be8ee501ea7274d53f87196f7bf9fd0c49f3971a3359b244baaef93f16",
    "B.json": "7d39f207576d9d50373abe933d55004598a6dd1f83bb69b66325796636f1980e",
    "REPORT.json": "c9f726cb73002018bfc70c9d97d39a8b1fa02286f184cdb42f1448b73ede1f21",
}
PROCEDURE_FOLDER = "company-pol004-procedure-trace-2027-09-30"
PROCEDURE_RUN = "main-run-v1"
PROCEDURE_REVIEW_SHA = "2c0e96babf915c42d7d056de9ec87c30bc8966ddab126343ec444a1bad715143"
PROCEDURE_REVIEW_VERDICT = "PASS_SELECTED_POL004_PROCEDURE_TRACE_MAIN_LOCAL_NO_AUDIT_CREDIT"
PROCEDURE_INTEGRATION_COMMITS = [
    "83c2f3ea37aa63b3a1904cd10f74b724e207b7c6",
    "c92d43e0346921e31889baf4dfbea55ade09a765",
]
PROCEDURE_MANIFEST_SHA = "2d81554213354d8dc76d167fcc624bb1fb98b7ee5c44c0a75d4990ddf8e4f266"
PROCEDURE_RECEIPT_SHA = "442ddf2a36185460df20b04e00d63f12f877a3ef751f5f55cd9858fb9502af54"
PROCEDURE_DB_SHA = "62c71eca6b9186936e89c6569735a6ea74b8d4909d356d2fb794a9e437d2d4bb"
PROCEDURE_MODULE_SHA = "c418e73f5ce67398237a50814bca8ee48a0295f746b31dd2ab823828a8083a8e"
PROCEDURE_BRANCHES = tuple(procedure.BRANCHES.values())
PROCEDURE_COUNTS = (7, 9)
PROCEDURE_SYSTEMS = 8
P1_FREEZE = prior.P1_FREEZE


def _v13_review(private: Path) -> tuple:
    """Pin every accepted V13 report and candidate byte before adding a cohort."""
    root = private / BASE / V13_FOLDER
    review = root / "independent-review-main-v1/REVIEW.json"
    report = root / "main-run-v1/REPORT.json"
    candidates = root / "main-candidate-v1"
    files = {name: candidates / name for name in V13_CANDIDATE_SHA}
    for directory in (root, review.parent, report.parent, candidates):
        _private(directory, directory=True)
    paths = {"review": review, "report": report, **files}
    before = {
        "review": _pin(review, V13_REVIEW_SHA),
        "report": _pin(report, V13_REPORT_SHA),
        **{name: _pin(path, V13_CANDIDATE_SHA[name]) for name, path in files.items()},
    }
    row = _read_json(review)
    report_row = _read_json(report)
    candidate_rows = {name: _read_json(path) for name, path in files.items()}
    if (
        row.get("verdict") != "PASS_PARTIAL_SEC001_COMPONENT_PORTFOLIO_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or row.get("main_head") != "992d3b727fe31d3a5f3c46c88ffd84d36ef19d7d"
        or row.get("integration_commits_in_order")
        != [
            "476693f8d6a913bb5b5a215653804954756e1605",
            "992d3b727fe31d3a5f3c46c88ffd84d36ef19d7d",
        ]
        or row.get("main_output_sha256")
        != {
            "portfolio_report": V13_REPORT_SHA,
            "candidate_A": V13_CANDIDATE_SHA["A.json"],
            "candidate_B": V13_CANDIDATE_SHA["B.json"],
            "candidate_report": V13_CANDIDATE_SHA["REPORT.json"],
        }
        or row.get("p1_freeze") != P1_FREEZE
        or row.get("source_complete") is not False
        or row.get("fresh_audit_pair_created") is not False
        or row.get("audit_task_credit") is not False
        or row.get("main_or_atlas_tracked_written_by_review") is not False
        or report_row.get("source_complete") is not False
        or report_row.get("audit_task_credit") is not False
        or candidate_rows["REPORT.json"].get("source_complete") is not False
        or candidate_rows["REPORT.json"].get("audit_task_credit") is not False
    ):
        raise PortfolioVerificationError("Reviewed V13 main report/candidate boundary differs")
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("Reviewed V13 main files changed during read")
    return report_row, candidate_rows, before


def _procedure_source(repository: Path, private: Path) -> dict:
    """Qualify the reviewed POL004 source while retaining pending authority."""
    module = repository / "enterprise/audit_suite/company_pol004_procedure_trace_2027.py"
    if not module.is_file() or _digest(module) != PROCEDURE_MODULE_SHA:
        raise PortfolioVerificationError("POL004 procedure source module differs")
    folder = private / BASE / PROCEDURE_FOLDER
    run = folder / PROCEDURE_RUN
    review_folder = folder / "independent-review-main-v1"
    paths = {
        "review": review_folder / "REVIEW.json",
        "manifest": run / "RUN-MANIFEST.json",
        "receipt": run / "SOURCE_RECEIPT.json",
        "database": run / "company.sqlite3",
    }
    for directory in (folder, run, review_folder):
        _private(directory, directory=True)
    expected = {
        "review": PROCEDURE_REVIEW_SHA,
        "manifest": PROCEDURE_MANIFEST_SHA,
        "receipt": PROCEDURE_RECEIPT_SHA,
        "database": PROCEDURE_DB_SHA,
    }
    before = {name: _pin(path, expected[name]) for name, path in paths.items()}
    review = _read_json(paths["review"])
    manifest = _read_json(paths["manifest"])
    receipt = _read_json(paths["receipt"])
    run_hashes = {
        "RUN-MANIFEST.json": PROCEDURE_MANIFEST_SHA,
        "SOURCE_RECEIPT.json": PROCEDURE_RECEIPT_SHA,
        "company.sqlite3": PROCEDURE_DB_SHA,
    }
    if (
        review.get("verdict") != PROCEDURE_REVIEW_VERDICT
        or review.get("integration_commits_in_order") != PROCEDURE_INTEGRATION_COMMITS
        or review.get("main_run_sha256") != run_hashes
        or review.get("main_tracked_sha256", {}).get(
            "enterprise/audit_suite/company_pol004_procedure_trace_2027.py"
        )
        != PROCEDURE_MODULE_SHA
        or review.get("main_run_native_versions") != {"CLEAN": 7, "MESSY": 9}
        or review.get("p1_freeze") != P1_FREEZE
        or any(
            review.get(key) is not False
            for key in (
                "active_pair_mutated",
                "audit_task_credit",
                "fresh_pair_created",
                "main_or_atlas_external_write",
                "source_complete",
            )
        )
    ):
        raise PortfolioVerificationError("POL004 procedure main review/source join differs")
    if (
        manifest.get("module_sha256") != PROCEDURE_MODULE_SHA
        or manifest.get("native_count") != 16
        or manifest.get("source_receipt_sha256") != PROCEDURE_RECEIPT_SHA
        or manifest.get("native_db_sha256") != PROCEDURE_DB_SHA
        or receipt.get("schema") != procedure.SCHEMA
        or receipt.get("branch_ids") != procedure.BRANCHES
        or receipt.get("branch_counts") != {"CLEAN": 7, "MESSY": 9}
        or receipt.get("native_count") != 16
        or receipt.get("control_id") != procedure.CONTROL
        or receipt.get("task_id") != procedure.TASK
        or receipt.get("selected_authored_clause") != procedure.CLAUSE
        or receipt.get("enterprise_policy_status_2026") != "OPEN"
        or receipt.get("procedure_authority") != "PENDING_AUTHORIZED_DECISION"
        or receipt.get("design_standard_approved_only") is not True
        or receipt.get("clean_result") != "SELECTED_ON_TIME_NO_VARIATION_PENDING_PROCEDURE_APPROVAL"
        or receipt.get("messy_exception_open") is not True
        or receipt.get("messy_false_close_corrected") is not True
        or receipt.get("messy_missed_interval_retained") is not True
        or any(
            receipt.get(key) is not False
            for key in (
                "actual_operation",
                "full_policy_or_procedure_population",
                "source_complete",
                "audit_task_credit",
                "active_P1_mutated",
            )
        )
        or set(receipt.get("route_disposition", {})) != {"A", "B"}
        or any(
            row.get("classification") != "UNSUPPORTED_EXACT_CLAUSE"
            or row.get("current_status") != "NOT_STARTED"
            or row.get("current_conclusion") != "NOT_RUN"
            or row.get("authored_test_clause") != procedure.CLAUSE
            or row.get("audit_task_credit") is not False
            for row in receipt["route_disposition"].values()
        )
    ):
        raise PortfolioVerificationError("POL004 procedure receipt boundary differs")
    if procedure.verify(run, repository=repository, private_repository=private) != receipt:
        raise PortfolioVerificationError("POL004 procedure native verifier differs")
    native, systems, journals = _frozen_rows(paths["database"])
    if (
        sorted(native)
        != sorted(
            (procedure.COMPANY, branch, count)
            for branch, count in zip(PROCEDURE_BRANCHES, PROCEDURE_COUNTS, strict=True)
        )
        or sorted(systems)
        != sorted((procedure.COMPANY, branch, PROCEDURE_SYSTEMS) for branch in PROCEDURE_BRANCHES)
        or any(journals.values())
    ):
        raise PortfolioVerificationError("POL004 procedure physical rows or journals differ")
    _no_sidecars(paths["database"])
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("POL004 procedure source changed during read")
    return {
        "source": "pol004procedure",
        "run": f"{PROCEDURE_FOLDER}/{PROCEDURE_RUN}",
        "review_sha256": PROCEDURE_REVIEW_SHA,
        "manifest_sha256": PROCEDURE_MANIFEST_SHA,
        "receipt_sha256": PROCEDURE_RECEIPT_SHA,
        "database_sha256": {"native": PROCEDURE_DB_SHA},
        "native_versions": 16,
        "branch_versions": dict(zip(PROCEDURE_BRANCHES, PROCEDURE_COUNTS, strict=True)),
        "physical_company_ids": [procedure.COMPANY],
        "ledger_system_counts": {"native": PROCEDURE_SYSTEMS},
        "inherited_audit_journals": {table: 0 for table in JOURNALS},
        "selected_authored_clause": procedure.CLAUSE,
        "selected_trigger": receipt["selected_trigger"],
        "enterprise_policy_status_2026": "OPEN",
        "procedure_authority": "PENDING_AUTHORIZED_DECISION",
        "design_standard_approved_only": True,
        "clean_result": receipt["clean_result"],
        "messy_exception_open": True,
        "messy_false_close_corrected": True,
        "messy_missed_interval_retained": True,
        "actual_operation": False,
        "full_policy_or_procedure_population": False,
        "audit_task_credit": False,
    }


def _compose_portfolio(previous: dict, source: dict) -> dict:
    """Append one POL004 cohort while preserving the full reviewed V13 prefix."""
    if (
        previous.get("source_count"),
        previous.get("native_versions"),
        previous.get("source_component_count"),
        previous.get("source_complete"),
        previous.get("fresh_audit_pair_created"),
        previous.get("audit_task_credit"),
    ) != (34, 780, 35, False, False, False) or len(previous.get("sources", [])) != 34:
        raise PortfolioVerificationError("Reviewed V13 source count/claim boundary differs")
    if (
        source.get("source") != "pol004procedure"
        or source.get("native_versions") != 16
        or source.get("branch_versions")
        != dict(zip(PROCEDURE_BRANCHES, PROCEDURE_COUNTS, strict=True))
        or source.get("ledger_system_counts") != {"native": PROCEDURE_SYSTEMS}
        or source.get("inherited_audit_journals") != {table: 0 for table in JOURNALS}
        or source.get("enterprise_policy_status_2026") != "OPEN"
        or source.get("procedure_authority") != "PENDING_AUTHORIZED_DECISION"
        or source.get("design_standard_approved_only") is not True
        or source.get("messy_exception_open") is not True
        or source.get("actual_operation") is not False
        or source.get("full_policy_or_procedure_population") is not False
        or source.get("audit_task_credit") is not False
    ):
        raise PortfolioVerificationError("POL004 procedure source scope differs")
    sources = [*previous["sources"], source]
    if len(sources) != 35 or sum(row["native_versions"] for row in sources) != 796:
        raise PortfolioVerificationError("V14 selected-procedure roster differs")
    return {
        "schema": SCHEMA,
        "status": "PARTIAL_REVIEWED_NATIVE_SOURCES_NOT_AUDIT_READY",
        "as_of": "2026-09-30",
        "verifier_module_sha256": _digest(Path(__file__)),
        "v13_verifier_sha256": previous["verifier_module_sha256"],
        "v13_review_sha256": V13_REVIEW_SHA,
        "source_count": 35,
        "native_versions": 796,
        "source_component_count": 36,
        "sources": sources,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": [
            "Thirty-five selected fictional cohorts, not an enterprise evidence population.",
            "POL004 adds one selected local prospective procedure trial per side; the 2026 "
            "enterprise policy remains OPEN and only the document standard is design-approved.",
            "Procedure authority is pending, and the Messy missed interval, corrected false "
            "close and OPEN historical exception remain visible.",
            "The exact CC5.3 authored route stays unsupported and unrun; no P1 task "
            "conclusion follows from this source roster.",
            "2027 events are authored prospective times; imported_at records 2026 insertion.",
            "REC003 inherited audit journals are excluded from business versions.",
            "No complete policy/procedure population, fresh pair, grant, collection, "
            "task, Key or grade.",
        ],
    }


def verify_all(repository: Path, *, private_repository: Path | None = None) -> dict:
    """Reperform accepted V13 and the selected POL004 main source."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository or repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise PortfolioVerificationError("Frozen P1 inventory differs")
    reviewed = _v13_review(private)
    previous = prior.verify_all(repository, private_repository=private)
    if previous != reviewed[0]:
        raise PortfolioVerificationError(
            "Recomputed V13 source prefix differs from reviewed report"
        )
    source = _procedure_source(repository, private)
    if _v13_review(private) != reviewed or _p1_inventory(private) != freeze:
        raise PortfolioVerificationError("Reviewed V13 prefix or P1 changed during source read")
    return _compose_portfolio(previous, source)


def write_report(repository: Path, private_repository: Path, destination: Path) -> dict:
    report = verify_all(repository, private_repository=private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise PortfolioVerificationError("Fresh V14 report destination required")
    _private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".portfolio-v14-", dir=destination.parent) as name:
        stage = Path(name)
        path = stage / "REPORT.json"
        path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        path.chmod(0o600)
        os.rename(stage, destination)
    return verify_report(destination, repository, private_repository)


def verify_report(destination: Path, repository: Path, private_repository: Path) -> dict:
    root = Path(destination).absolute()
    _private(root, directory=True)
    if {path.name for path in root.iterdir()} != {"REPORT.json"}:
        raise PortfolioVerificationError("Exact one-file V14 report required")
    path = root / "REPORT.json"
    before = _pin(path, _digest(path))
    actual = _read_json(path)
    expected = verify_all(repository, private_repository=private_repository)
    if actual != expected or _identity(path) != before:
        raise PortfolioVerificationError("V14 portfolio report differs")
    return actual


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    result = (
        write_report(args.repository, args.private_repository, args.destination)
        if args.action == "create"
        else verify_report(args.destination, args.repository, args.private_repository)
    )
    print(json.dumps({key: result[key] for key in ("schema", "source_count", "native_versions")}))


if __name__ == "__main__":
    main()
