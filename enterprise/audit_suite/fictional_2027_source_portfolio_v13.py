"""V13 partial source roster with one reviewed SEC001 component-lifecycle cohort."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from . import company_sec001_component_lifecycle_2027 as component
from . import fictional_2027_source_portfolio_v12 as prior
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

SCHEMA = "SH_FICTIONAL_2027_REVIEWED_SOURCE_PORTFOLIO_DIAGNOSTIC_V13"
V12_FOLDER = "company-source-portfolio-v12-2026-09-30"
V12_REVIEW_SHA = "053dca8df77c5fb990daf7844a62a792276b89100dfef8df1d564f04df841400"
V12_REPORT_SHA = "c6d7205a9f2e6bc3a213a5eece4e0b1c28811d407850e31fd2bcb4a2eb382821"
V12_CANDIDATE_SHA = {
    "A.json": "2919a119ac97520f4026c6b9c25635857d1ff12e0308217864575d251a9443b2",
    "B.json": "6dbab1e7ef28f7ace549db73232d43b065ac1c6491f99152c4d5107ee763ca1a",
    "REPORT.json": "ee37e0e2d934ece1ba0f4d4c4cab5fce5dbabb4b0784044b6bca01a24fb529af",
}
COMPONENT_FOLDER = "company-sec001-component-lifecycle-2027-09-30"
COMPONENT_RUN = "main-run-v1"
COMPONENT_REVIEW_SHA = "c780366186a166071040c74f99c72b728b260daa9d4de5d84c8da682ddc59758"
COMPONENT_REVIEW_VERDICT = (
    "PASS_SELECTED_SYNTHETIC_SEC001_COMPONENT_LIFECYCLE_SOURCE_MAIN_LOCAL_NO_AUDIT_CREDIT"
)
COMPONENT_INTEGRATION_COMMIT = "17cb19c9e526dfd42aeb0968dbeb1f51b8ae8040"
COMPONENT_MANIFEST_SHA = "95a73ceb8c360acec49dbad3bcaded86396284be77f53e74cd2272fb612e1547"
COMPONENT_RECEIPT_SHA = "36374e1fa5ba18fd5d42ac6229da270b90bbed0aeeba9b39f3f2191d09aa36eb"
COMPONENT_DB_SHA = "f8aba6420ce8fbdd5582e95f98aefd3a056b088b2e47d172e5fb6b2e69bfb41f"
COMPONENT_MODULE_SHA = "8e6338dd060f5406828d1c6ccdf6cb14a2d5c846bbd1a9a5e2d64d8baaf5f52d"
COMPONENT_BRANCHES = ("SEC001-COMPONENT-CLEAN", "SEC001-COMPONENT-MESSY")
COMPONENT_COUNTS = (10, 15)
COMPONENT_SYSTEMS = 7
P1_FREEZE = prior.P1_FREEZE


def _v12_review(private: Path) -> tuple:
    """Pin every accepted V12 report and candidate byte before adding a cohort."""
    root = private / BASE / V12_FOLDER
    review = root / "independent-review-main-v1/REVIEW.json"
    report = root / "main-run-v1/REPORT.json"
    candidates = root / "main-candidate-v1"
    files = {name: candidates / name for name in V12_CANDIDATE_SHA}
    for directory in (root, review.parent, report.parent, candidates):
        _private(directory, directory=True)
    paths = {"review": review, "report": report, **files}
    before = {
        "review": _pin(review, V12_REVIEW_SHA),
        "report": _pin(report, V12_REPORT_SHA),
        **{name: _pin(path, V12_CANDIDATE_SHA[name]) for name, path in files.items()},
    }
    row = _read_json(review)
    report_row = _read_json(report)
    candidate_rows = {name: _read_json(path) for name, path in files.items()}
    if (
        row.get("verdict") != "PASS_PARTIAL_SEC001_PORTFOLIO_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or row.get("main_head") != "3d61d4e8b50ae09c3d0e214af9dba95a4ad32fd5"
        or row.get("integration_commits_in_order")
        != [
            "6d229a7d73946a556951f4d903e8f276373cdfe8",
            "3d61d4e8b50ae09c3d0e214af9dba95a4ad32fd5",
        ]
        or row.get("main_output_sha256")
        != {
            "portfolio_report": V12_REPORT_SHA,
            "candidate_A": V12_CANDIDATE_SHA["A.json"],
            "candidate_B": V12_CANDIDATE_SHA["B.json"],
            "candidate_report": V12_CANDIDATE_SHA["REPORT.json"],
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
        raise PortfolioVerificationError("Reviewed V12 main report/candidate boundary differs")
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("Reviewed V12 main files changed during read")
    return report_row, candidate_rows, before


def _component_source(repository: Path, private: Path) -> dict:
    """Qualify the accepted CC5.2 main source and its non-deployed limits."""
    module = repository / "enterprise/audit_suite/company_sec001_component_lifecycle_2027.py"
    if not module.is_file() or _digest(module) != COMPONENT_MODULE_SHA:
        raise PortfolioVerificationError("SEC001 component source module differs")
    folder = private / BASE / COMPONENT_FOLDER
    run = folder / COMPONENT_RUN
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
        "review": COMPONENT_REVIEW_SHA,
        "manifest": COMPONENT_MANIFEST_SHA,
        "receipt": COMPONENT_RECEIPT_SHA,
        "database": COMPONENT_DB_SHA,
    }
    before = {name: _pin(path, expected[name]) for name, path in paths.items()}
    review = _read_json(paths["review"])
    manifest = _read_json(paths["manifest"])
    receipt = _read_json(paths["receipt"])
    run_hashes = {
        "RUN-MANIFEST.json": COMPONENT_MANIFEST_SHA,
        "SOURCE_RECEIPT.json": COMPONENT_RECEIPT_SHA,
        "company.sqlite3": COMPONENT_DB_SHA,
    }
    if (
        review.get("verdict") != COMPONENT_REVIEW_VERDICT
        or review.get("integration_commit") != COMPONENT_INTEGRATION_COMMIT
        or review.get("main_run_sha256") != run_hashes
        or review.get("tracked_sha256", {}).get(
            "enterprise/audit_suite/company_sec001_component_lifecycle_2027.py"
        )
        != COMPONENT_MODULE_SHA
        or review.get("p1_freeze") != P1_FREEZE
        or review.get("task_id") != component.TASK
        or review.get("authored_clause") != component.CLAUSE
        or review.get("existing_limited_route_lead") != "SEC003_SELECTED_VULNERABILITY_V1"
        or review.get("main_or_atlas_tracked_written_by_review") is not False
        or review.get("active_pair_mutated") is not False
        or review.get("source_complete") is not False
        or review.get("audit_task_credit") is not False
    ):
        raise PortfolioVerificationError("SEC001 component main review/source join differs")
    if (
        manifest.get("module_sha256") != COMPONENT_MODULE_SHA
        or manifest.get("native_count") != 25
        or manifest.get("source_receipt_sha256") != COMPONENT_RECEIPT_SHA
        or manifest.get("native_db_sha256") != COMPONENT_DB_SHA
        or receipt.get("schema") != component.SCHEMA
        or receipt.get("branch_ids")
        != dict(zip(("CLEAN", "MESSY"), COMPONENT_BRANCHES, strict=True))
        or receipt.get("branch_counts") != {"CLEAN": 10, "MESSY": 15}
        or receipt.get("native_count") != 25
        or receipt.get("selected_component_count") != 2
        or receipt.get("selected_component_ids") != [component.CORE, component.OUTSOURCED]
        or receipt.get("control_id") != "SH-SEC-001"
        or receipt.get("task_id") != component.TASK
        or receipt.get("selected_authored_clause") != component.CLAUSE
        or receipt.get("actor_authority")
        != "CANON_LISTED_FICTIONAL_APPOINTMENTS_PENDING_ACCEPTANCE"
        or receipt.get("messy_false_close_corrected") is not True
        or receipt.get("messy_historical_exception_open") is not True
        or receipt.get("outsourced_component_challenged_and_blocked") is not True
        or any(
            receipt.get(key) is not False
            for key in (
                "actual_supplier_selected_or_contracted",
                "actual_deployed_component",
                "approved_enterprise_architecture",
                "independent_approval",
                "population_complete",
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
            or row.get("authored_test_clause") != component.CLAUSE
            or row.get("existing_targeted_integrated_source_ids")
            != ["SEC003_SELECTED_VULNERABILITY_V1"]
            or row.get("audit_task_credit") is not False
            for row in receipt["route_disposition"].values()
        )
    ):
        raise PortfolioVerificationError("SEC001 component receipt boundary differs")
    if component.verify(run, repository=repository, private_repository=private) != receipt:
        raise PortfolioVerificationError("SEC001 component native verifier differs")
    native, systems, journals = _frozen_rows(paths["database"])
    if (
        sorted(native)
        != sorted(
            ("SABLE-HARBOR-REFERENCE", branch, count)
            for branch, count in zip(COMPONENT_BRANCHES, COMPONENT_COUNTS, strict=True)
        )
        or sorted(systems)
        != sorted(
            ("SABLE-HARBOR-REFERENCE", branch, COMPONENT_SYSTEMS) for branch in COMPONENT_BRANCHES
        )
        or any(journals.values())
    ):
        raise PortfolioVerificationError("SEC001 component physical rows or journals differ")
    _no_sidecars(paths["database"])
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("SEC001 component source changed during read")
    return {
        "source": "sec001component",
        "run": f"{COMPONENT_FOLDER}/{COMPONENT_RUN}",
        "review_sha256": COMPONENT_REVIEW_SHA,
        "manifest_sha256": COMPONENT_MANIFEST_SHA,
        "receipt_sha256": COMPONENT_RECEIPT_SHA,
        "database_sha256": {"native": COMPONENT_DB_SHA},
        "native_versions": 25,
        "branch_versions": dict(zip(COMPONENT_BRANCHES, COMPONENT_COUNTS, strict=True)),
        "physical_company_ids": ["SABLE-HARBOR-REFERENCE"],
        "ledger_system_counts": {"native": COMPONENT_SYSTEMS},
        "inherited_audit_journals": {table: 0 for table in JOURNALS},
        "selected_component_count": 2,
        "selected_authored_clause": component.CLAUSE,
        "existing_limited_route_lead": "SEC003_SELECTED_VULNERABILITY_V1",
        "messy_false_close_corrected": True,
        "messy_historical_exception_open": True,
        "outsourced_component_challenged_and_blocked": True,
        "actual_supplier_selected_or_contracted": False,
        "actual_deployed_component": False,
        "approved_enterprise_architecture": False,
        "independent_approval": False,
        "population_complete": False,
        "audit_task_credit": False,
    }


def _compose_portfolio(previous: dict, source: dict) -> dict:
    """Append exactly one cohort while retaining the full reviewed V12 prefix."""
    if (
        previous.get("source_count"),
        previous.get("native_versions"),
        previous.get("source_component_count"),
        previous.get("source_complete"),
        previous.get("fresh_audit_pair_created"),
        previous.get("audit_task_credit"),
    ) != (33, 755, 34, False, False, False) or len(previous.get("sources", [])) != 33:
        raise PortfolioVerificationError("Reviewed V12 source count/claim boundary differs")
    if (
        source.get("source") != "sec001component"
        or source.get("native_versions") != 25
        or source.get("branch_versions")
        != dict(zip(COMPONENT_BRANCHES, COMPONENT_COUNTS, strict=True))
        or source.get("ledger_system_counts") != {"native": COMPONENT_SYSTEMS}
        or source.get("inherited_audit_journals") != {table: 0 for table in JOURNALS}
        or source.get("selected_component_count") != 2
        or source.get("existing_limited_route_lead") != "SEC003_SELECTED_VULNERABILITY_V1"
        or source.get("messy_historical_exception_open") is not True
        or source.get("actual_supplier_selected_or_contracted") is not False
        or source.get("actual_deployed_component") is not False
        or source.get("population_complete") is not False
        or source.get("audit_task_credit") is not False
    ):
        raise PortfolioVerificationError("SEC001 component source scope differs")
    sources = [*previous["sources"], source]
    if len(sources) != 34 or sum(row["native_versions"] for row in sources) != 780:
        raise PortfolioVerificationError("V13 selected-component roster differs")
    return {
        "schema": SCHEMA,
        "status": "PARTIAL_REVIEWED_NATIVE_SOURCES_NOT_AUDIT_READY",
        "as_of": "2026-09-30",
        "verifier_module_sha256": _digest(Path(__file__)),
        "v12_verifier_sha256": previous["verifier_module_sha256"],
        "v12_review_sha256": V12_REVIEW_SHA,
        "source_count": 34,
        "native_versions": 780,
        "source_component_count": 35,
        "sources": sources,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": [
            "Thirty-four selected fictional cohorts, not an enterprise evidence population.",
            "SEC001 adds two selected non-deployed component fixtures, including an unnamed "
            "outsourced dependency candidate without a vendor, contract or support proof.",
            "Messy omitted-component and false-completion history remain visible with an "
            "open exception; unsupported use is blocked in both scenarios.",
            "The exact CC5.2 authored route stays unsupported with its existing limited SEC003 "
            "lead; no route promotion or P1 task conclusion follows from this source roster.",
            "2027 events are authored prospective times; imported_at records 2026 insertion.",
            "REC003 inherited audit journals are excluded from business versions.",
            "No source-complete population, fresh pair, grant, collection, task, Key or grade.",
        ],
    }


def verify_all(repository: Path, *, private_repository: Path | None = None) -> dict:
    """Reperform accepted V12 and the selected CC5.2 main source."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository or repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise PortfolioVerificationError("Frozen P1 inventory differs")
    reviewed = _v12_review(private)
    previous = prior.verify_all(repository, private_repository=private)
    if previous != reviewed[0]:
        raise PortfolioVerificationError(
            "Recomputed V12 source prefix differs from reviewed report"
        )
    source = _component_source(repository, private)
    if _v12_review(private) != reviewed or _p1_inventory(private) != freeze:
        raise PortfolioVerificationError("Reviewed V12 prefix or P1 changed during source read")
    return _compose_portfolio(previous, source)


def write_report(repository: Path, private_repository: Path, destination: Path) -> dict:
    report = verify_all(repository, private_repository=private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise PortfolioVerificationError("Fresh V13 report destination required")
    _private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".portfolio-v13-", dir=destination.parent) as name:
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
        raise PortfolioVerificationError("Exact one-file V13 report required")
    path = root / "REPORT.json"
    before = _pin(path, _digest(path))
    actual = _read_json(path)
    expected = verify_all(repository, private_repository=private_repository)
    if actual != expected or _identity(path) != before:
        raise PortfolioVerificationError("V13 portfolio report differs")
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
