"""Read-only partial V7 roster adding reviewed SEC003 vulnerability history.

The SEC003 main-local review is a required input. Until it is sealed and pinned,
this successor deliberately cannot produce a selected portfolio report.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from . import company_sec003_selected_vulnerability_2027 as sec
from . import fictional_2027_source_portfolio_v6 as prior
from .fictional_2027_source_portfolio import BASE, PortfolioVerificationError, _digest, _identity
from .fictional_2027_source_portfolio_v4 import (
    _frozen_rows,
    _no_sidecars,
    _pin,
    _private,
    _read_json,
)

SCHEMA = "SH_FICTIONAL_2027_REVIEWED_SOURCE_PORTFOLIO_DIAGNOSTIC_V7"
V6_FOLDER = "company-source-portfolio-v6-2026-09-30"
V6_REVIEW_SHA = "7f067b8070d124be30dc4abc1653164ed6702b5601d0a4f90c6066a5ad9fde0b"
V6_REPORT_SHA = "b2f9eb833c58751fba740836daf722ed480e2063540c09d28bc6064aec802967"
V6_CANDIDATE_SHA = {
    "A.json": "e5f2674b439a1162d13d241578b278e755dafbaa2780ac93027eb9c3c5331fe2",
    "B.json": "5eb9b7baa234539a17631a13c3cb92983029824b45c1cc377b5a30d1d7082610",
    "REPORT.json": "25cae84f070457f50db4e067c689c254326702ae1c211c0cf29f5017f44a9072",
}
SEC_FOLDER = "company-sec003-selected-vulnerability-2026-09-30"
SEC_RUN = "main-run-v1"
SEC_REVIEW = "independent-review-main-v1/REVIEW.json"
SEC_REVIEW_SHA = "PENDING_INDEPENDENT_MAIN_REVIEW"
SEC_REVIEW_VERDICT = "PENDING_INDEPENDENT_MAIN_REVIEW"
SEC_MANIFEST_SHA = "4ae2200e8735ea60e4a85f1158782926fdd50eda96238fc15031d5d9eda69af3"
SEC_RECEIPT_SHA = "85233a1e785ffea73f32996bc3f410e9b5c381720b6cbe941ff8a2bbd5474ff8"
SEC_DB_SHA = "a94b9f0e2d18e06afd2c83ae2012cea8da72102f9bafcf0e3968959eb6f1539f"
SEC_BRANCHES = ("SEC003-SELECTED-CLEAN", "SEC003-SELECTED-MESSY")
SEC_COUNTS = (11, 18)
SEC_SYSTEMS = 10


def _v6_review(private: Path) -> tuple:
    """Pin reviewed report and every candidate byte, then expose exact objects."""
    root = private / BASE / V6_FOLDER
    review = root / "independent-review-main-v1/REVIEW.json"
    report = root / "main-run-v1/REPORT.json"
    candidate_root = root / "main-candidate-v1"
    files = {name: candidate_root / name for name in V6_CANDIDATE_SHA}
    for directory in (root, review.parent, report.parent, candidate_root):
        _private(directory, directory=True)
    before = {
        "review": _pin(review, V6_REVIEW_SHA),
        "report": _pin(report, V6_REPORT_SHA),
        **{name: _pin(path, V6_CANDIDATE_SHA[name]) for name, path in files.items()},
    }
    row = _read_json(review)
    report_row = _read_json(report)
    candidate_rows = {name: _read_json(path) for name, path in files.items()}
    if (
        row.get("verdict") != "PASS_PARTIAL_READ_ONLY_CANDIDATE_REGISTRY_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or row.get("main_output_sha256")
        != {
            "portfolio": V6_REPORT_SHA,
            "candidate_A": V6_CANDIDATE_SHA["A.json"],
            "candidate_B": V6_CANDIDATE_SHA["B.json"],
            "candidate_report": V6_CANDIDATE_SHA["REPORT.json"],
        }
        or row.get("checks", {}).get("tracked_code_or_p1_mutated_by_review") is not False
        or report_row.get("source_complete") is not False
        or report_row.get("audit_task_credit") is not False
        or candidate_rows["REPORT.json"].get("source_complete") is not False
        or candidate_rows["REPORT.json"].get("audit_task_credit") is not False
    ):
        raise PortfolioVerificationError("Reviewed V6 main report/candidate boundary differs")
    paths = {"review": review, "report": report, **files}
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("Reviewed V6 main files changed during read")
    return report_row, candidate_rows, before


def _sec_source(repository: Path, private: Path) -> dict:
    if SEC_REVIEW_SHA == "PENDING_INDEPENDENT_MAIN_REVIEW":
        raise PortfolioVerificationError("SEC003 independent main review not yet pinned")
    folder = private / BASE / SEC_FOLDER
    run = folder / SEC_RUN
    review = folder / SEC_REVIEW
    paths = {
        "review": review,
        "manifest": run / "MANIFEST.json",
        "receipt": run / "RECEIPT.json",
        "database": run / "company.sqlite3",
    }
    for directory in (folder, run, review.parent):
        _private(directory, directory=True)
    expected = {
        "review": SEC_REVIEW_SHA,
        "manifest": SEC_MANIFEST_SHA,
        "receipt": SEC_RECEIPT_SHA,
        "database": SEC_DB_SHA,
    }
    before = {name: _pin(path, expected[name]) for name, path in paths.items()}
    review_row = _read_json(review)
    manifest = _read_json(paths["manifest"])
    receipt = _read_json(paths["receipt"])
    if (
        review_row.get("verdict") != SEC_REVIEW_VERDICT
        or review_row.get("selected_main_run") != SEC_RUN
        or review_row.get("sha256", {}).get("main_manifest") != SEC_MANIFEST_SHA
        or review_row.get("sha256", {}).get("main_receipt") != SEC_RECEIPT_SHA
        or review_row.get("sha256", {}).get("main_native_db") != SEC_DB_SHA
        or review_row.get("sha256", {}).get("tracked_module") != manifest.get("module_sha256")
        or review_row.get("checks", {}).get("tracked_main_edits_by_review") is not False
        or review_row.get("checks", {}).get("authored_clause_or_task_credit") is not False
    ):
        raise PortfolioVerificationError("SEC003 independent main review/source join differs")
    if (
        receipt.get("branches") != dict(zip(("CLEAN", "MESSY"), SEC_BRANCHES, strict=True))
        or receipt.get("native_version_counts")
        != dict(zip(("CLEAN", "MESSY"), SEC_COUNTS, strict=True))
        or receipt.get("company") != "SABLE-HARBOR-REFERENCE"
        or receipt.get("selected_asset_ids")
        != ["SIM-RNO-EDGE-01", "SIM-RNO-OPS-01", "SIM-BOI-EDGE-01", "SIM-BOI-OPS-01"]
        or receipt.get("messy_october_false_clean_preserved") is not True
        or receipt.get("messy_historical_exception_status") != "OPEN"
        or receipt.get("independent_assurance_completed") is not False
        or receipt.get("enterprise_inventory_scan_baseline_population_complete") is not False
        or receipt.get("authored_sec003_cc71_or_sec001_cc52_clause_satisfied") is not False
        or receipt.get("actual_operation_eligibility_as_of_2026_09_30") is not False
        or receipt.get("source_complete") is not False
        or receipt.get("audit_task_credit") is not False
        or manifest.get("receipt_sha256") != SEC_RECEIPT_SHA
        or manifest.get("company_db_sha256") != SEC_DB_SHA
        or manifest.get("native_version_count") != 29
        or manifest.get("audit_task_credit") is not False
    ):
        raise PortfolioVerificationError("SEC003 native claim/manifest boundary differs")
    if sec.verify(run, repository=repository, private_repository=private) != receipt:
        raise PortfolioVerificationError("SEC003 own source verifier differs")
    native, systems, journals = _frozen_rows(paths["database"])
    if (
        sorted(native)
        != sorted(
            ("SABLE-HARBOR-REFERENCE", branch, count)
            for branch, count in zip(SEC_BRANCHES, SEC_COUNTS, strict=True)
        )
        or sorted(systems)
        != sorted(("SABLE-HARBOR-REFERENCE", branch, SEC_SYSTEMS) for branch in SEC_BRANCHES)
        or any(journals.values())
    ):
        raise PortfolioVerificationError("SEC003 physical branches/journals differ")
    _no_sidecars(paths["database"])
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("SEC003 source changed during read")
    return {
        "source": "sec003vuln",
        "run": f"{SEC_FOLDER}/{SEC_RUN}",
        "review_sha256": SEC_REVIEW_SHA,
        "manifest_sha256": SEC_MANIFEST_SHA,
        "receipt_sha256": SEC_RECEIPT_SHA,
        "database_sha256": {"native": SEC_DB_SHA},
        "native_versions": 29,
        "branch_versions": dict(zip(SEC_BRANCHES, SEC_COUNTS, strict=True)),
        "physical_company_ids": ["SABLE-HARBOR-REFERENCE"],
        "ledger_system_counts": {"native": SEC_SYSTEMS},
        "inherited_audit_journals": {table: 0 for table in prior.prior.prior.JOURNALS},
        "audit_task_credit": False,
    }


def verify_all(repository: Path, *, private_repository: Path | None = None) -> dict:
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository or repository).resolve(strict=True)
    reviewed = _v6_review(private)
    previous = prior.verify_all(repository, private_repository=private)
    if previous != reviewed[0]:
        raise PortfolioVerificationError("Recomputed V6 source prefix differs from reviewed report")
    if (
        previous.get("source_count"),
        previous.get("native_versions"),
        previous.get("source_component_count"),
        previous.get("source_complete"),
        previous.get("audit_task_credit"),
    ) != (27, 500, 28, False, False):
        raise PortfolioVerificationError("Reviewed V6 source count/claim boundary differs")
    sources = [*previous["sources"], _sec_source(repository, private)]
    if len(sources) != 28 or sum(row["native_versions"] for row in sources) != 529:
        raise PortfolioVerificationError("V7 selected SEC003 source roster differs")
    if _v6_review(private) != reviewed:
        raise PortfolioVerificationError("Reviewed V6 source/candidate prefix changed")
    return {
        "schema": SCHEMA,
        "status": "PARTIAL_REVIEWED_NATIVE_SOURCES_NOT_AUDIT_READY",
        "as_of": "2026-09-30",
        "verifier_module_sha256": _digest(Path(__file__)),
        "v6_verifier_sha256": previous["verifier_module_sha256"],
        "v6_review_sha256": V6_REVIEW_SHA,
        "source_count": 28,
        "native_versions": 529,
        "source_component_count": 29,
        "sources": sources,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": [
            "Twenty-eight selected fictional cohorts, not an enterprise evidence population.",
            "SEC003 is a selected four-asset data-only vulnerability lifecycle; its Messy "
            "false clean and open historical exception remain.",
            "AS-P008 November self-review is not independent assurance; CC7.1 and "
            "CC5.2 authored clauses remain unsupported.",
            "REC003 inherited audit journals are excluded from business versions.",
            "No actual 2027 operation, source-complete, grant, collection, task or grade claim.",
        ],
    }


def write_report(repository: Path, private_repository: Path, destination: Path) -> dict:
    report = verify_all(repository, private_repository=private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise PortfolioVerificationError("Fresh V7 report destination required")
    _private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".portfolio-v7-", dir=destination.parent) as name:
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
        raise PortfolioVerificationError("Exact one-file V7 report required")
    path = root / "REPORT.json"
    before = _pin(path, _digest(path))
    actual = _read_json(path)
    expected = verify_all(repository, private_repository=private_repository)
    if actual != expected or _identity(path) != before:
        raise PortfolioVerificationError("V7 portfolio report differs")
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
    print(
        json.dumps(
            {key: result[key] for key in ("schema", "source_count", "native_versions")}, indent=2
        )
    )


if __name__ == "__main__":
    main()
