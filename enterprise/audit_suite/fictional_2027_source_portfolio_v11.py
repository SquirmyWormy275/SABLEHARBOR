"""Read-only partial V11 roster adding reviewed selected fictional ETH001 conduct."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from . import company_eth001_conduct_attestation as conduct
from . import fictional_2027_source_portfolio_v10 as prior
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

SCHEMA = "SH_FICTIONAL_2027_REVIEWED_SOURCE_PORTFOLIO_DIAGNOSTIC_V11"
V10_FOLDER = "company-source-portfolio-v10-2026-09-30"
V10_REVIEW_SHA = "395336ae7c9bdb68ceba5e3da19732e01fbc9b11c6c1bbed7d0438c02f6a3497"
V10_REPORT_SHA = "5e76c4be99824fade2fdc6c7a9b462090990aa3803a07b2e17ff8227c7eada0a"
V10_CANDIDATE_SHA = {
    "A.json": "9c74e512b5ac1a780d927c9ba1c7860cd0da4fc5fc6c4d4401bc60c92a7d6801",
    "B.json": "477fbed64bdebb7e1d91c2cdfb163d762d20f6127f6bd42f43edf4fc5debeecc",
    "REPORT.json": "9753f9af7236e1b014361596e6f24c1407c0c29dfacdab7248b093f6d76bdbdf",
}
ETH_FOLDER = "company-eth001-conduct-2027-simulation-2026-09-30"
ETH_RUN = "main-run-v1"
ETH_REVIEW_SHA = "fbeae6830cfd479c2c354c22dad99adc5b8b89b9f57f99a014cbd15a1d73308d"
ETH_REVIEW_VERDICT = "PASS_SELECTED_FICTIONAL_ETH001_SOURCE_MAIN_LOCAL_NO_AUDIT_CREDIT"
ETH_MANIFEST_SHA = "320aad65c8ee0bd0d79f89460c80da00f5b52062ac2e20a3964f28951de552bc"
ETH_RECEIPT_SHA = "876e78076e293a5432a34ec17a85497b9de91f20d27af6cf7d38bd9b3ad6ef5e"
ETH_DB_SHA = "0ecf3e6fa6eaa2af01839fb5577188bf786e2669101729c71a2cf5cb4e47a3b8"
ETH_MODULE_SHA = "902e08c90014752b8b69c75c98f8d685e7d159b02fbe591acb4d50cef8cf8ebb"
ETH_BRANCHES = ("ETH001-CLEAN", "ETH001-MESSY")
ETH_COUNTS = (8, 11)
ETH_SYSTEMS = 4
P1_FREEZE = {
    "file_count": 538,
    "inventory_sha256": "f266ef682b502b3b093170f8a7b64fcf5cbab722d5c8ddf6715a63c0e535360f",
}


def _v10_review(private: Path) -> tuple:
    """Pin reviewed V10 report and both exact candidate profiles."""
    root = private / BASE / V10_FOLDER
    review = root / "independent-review-main-v1/REVIEW.json"
    report = root / "main-run-v1/REPORT.json"
    candidates = root / "main-candidate-v1"
    files = {name: candidates / name for name in V10_CANDIDATE_SHA}
    for directory in (root, review.parent, report.parent, candidates):
        _private(directory, directory=True)
    paths = {"review": review, "report": report, **files}
    before = {
        "review": _pin(review, V10_REVIEW_SHA),
        "report": _pin(report, V10_REPORT_SHA),
        **{name: _pin(path, V10_CANDIDATE_SHA[name]) for name, path in files.items()},
    }
    row = _read_json(review)
    report_row = _read_json(report)
    candidate_rows = {name: _read_json(path) for name, path in files.items()}
    if (
        row.get("verdict") != "PASS_PARTIAL_PENDING_ADDRESSABLE_REGISTRY_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or row.get("integration_commit") != "2a4b7ecaaf62ef07550e1c9d366c7fa19cc8f6ef"
        or row.get("main_output_sha256")
        != {
            "portfolio_report": V10_REPORT_SHA,
            "candidate_A": V10_CANDIDATE_SHA["A.json"],
            "candidate_B": V10_CANDIDATE_SHA["B.json"],
            "candidate_report": V10_CANDIDATE_SHA["REPORT.json"],
        }
        or row.get("checks", {}).get("main_or_atlas_tracked_written_by_review") is not False
        or row.get("checks", {}).get("source_complete") is not False
        or row.get("checks", {}).get("audit_task_credit") is not False
        or report_row.get("source_complete") is not False
        or report_row.get("audit_task_credit") is not False
        or candidate_rows["REPORT.json"].get("source_complete") is not False
        or candidate_rows["REPORT.json"].get("audit_task_credit") is not False
    ):
        raise PortfolioVerificationError("Reviewed V10 main report/candidate boundary differs")
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("Reviewed V10 main files changed during read")
    return report_row, candidate_rows, before


def _eth_source(repository: Path, private: Path) -> dict:
    """Require the sealed future-only two-person source and all 19 native rows."""
    folder = private / BASE / ETH_FOLDER
    run = folder / ETH_RUN
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
        "review": ETH_REVIEW_SHA,
        "manifest": ETH_MANIFEST_SHA,
        "receipt": ETH_RECEIPT_SHA,
        "database": ETH_DB_SHA,
    }
    before = {name: _pin(path, expected[name]) for name, path in paths.items()}
    review = _read_json(paths["review"])
    manifest = _read_json(paths["manifest"])
    receipt = _read_json(paths["receipt"])
    if (
        review.get("verdict") != ETH_REVIEW_VERDICT
        or review.get("integrated_commit") != "ad636fc8df1af3b94a6d2dd208ac8992e4c53c51"
        or review.get("main_run_sha256")
        != {
            "RUN-MANIFEST.json": ETH_MANIFEST_SHA,
            "SOURCE_RECEIPT.json": ETH_RECEIPT_SHA,
            "company.sqlite3": ETH_DB_SHA,
        }
        or review.get("main_tracked_sha256", {}).get(
            "enterprise/audit_suite/company_eth001_conduct_attestation.py"
        )
        != ETH_MODULE_SHA
        or review.get("p1_freeze") != P1_FREEZE
        or review.get("checks", {}).get("main_or_atlas_tracked_written_by_review") is not False
        or review.get("source_complete") is not False
        or review.get("audit_task_credit") is not False
        or review.get("actual_enterprise_code_approved") is not False
        or review.get("actual_employee_distribution_or_attestation") is not False
    ):
        raise PortfolioVerificationError("ETH001 independently reviewed main source differs")
    if (
        _digest(repository / "enterprise/audit_suite/company_eth001_conduct_attestation.py")
        != ETH_MODULE_SHA
        or manifest.get("module_sha256") != ETH_MODULE_SHA
        or manifest.get("native_count") != 19
        or manifest.get("source_receipt_sha256") != ETH_RECEIPT_SHA
        or manifest.get("native_db_sha256") != ETH_DB_SHA
        or receipt.get("schema") != conduct.SCHEMA
        or receipt.get("branch_ids") != dict(zip(("CLEAN", "MESSY"), ETH_BRANCHES, strict=True))
        or receipt.get("branch_counts") != {"CLEAN": 8, "MESSY": 11}
        or receipt.get("native_count") != 19
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
        or conduct.verify(run, repository=repository, private_repository=private) != receipt
    ):
        raise PortfolioVerificationError("ETH001 future-only native source boundary differs")
    native, systems, journals = _frozen_rows(paths["database"])
    if (
        sorted(native)
        != sorted(
            ("SABLE-HARBOR-REFERENCE", branch, count)
            for branch, count in zip(ETH_BRANCHES, ETH_COUNTS, strict=True)
        )
        or sorted(systems)
        != sorted(("SABLE-HARBOR-REFERENCE", branch, ETH_SYSTEMS) for branch in ETH_BRANCHES)
        or any(journals.values())
    ):
        raise PortfolioVerificationError("ETH001 physical branches or journals differ")
    _no_sidecars(paths["database"])
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("ETH001 source changed during read")
    return {
        "source": "eth001conduct",
        "run": f"{ETH_FOLDER}/{ETH_RUN}",
        "review_sha256": ETH_REVIEW_SHA,
        "manifest_sha256": ETH_MANIFEST_SHA,
        "receipt_sha256": ETH_RECEIPT_SHA,
        "database_sha256": {"native": ETH_DB_SHA},
        "native_versions": 19,
        "branch_versions": dict(zip(ETH_BRANCHES, ETH_COUNTS, strict=True)),
        "physical_company_ids": ["SABLE-HARBOR-REFERENCE"],
        "ledger_system_counts": {"native": ETH_SYSTEMS},
        "inherited_audit_journals": {table: 0 for table in JOURNALS},
        "selected_person_count": 2,
        "fictional_local_approval_only": True,
        "messy_historical_false_clean_exception_open": True,
        "real_enterprise_code_approved": False,
        "actual_distribution_or_attestation": False,
        "workforce_population_complete": False,
        "sanctions_or_performance_review_conclusion": False,
        "audit_task_credit": False,
    }


def verify_all(repository: Path, *, private_repository: Path | None = None) -> dict:
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository or repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise PortfolioVerificationError("Frozen P1 inventory differs")
    reviewed = _v10_review(private)
    previous = prior.verify_all(repository, private_repository=private)
    if previous != reviewed[0]:
        raise PortfolioVerificationError(
            "Recomputed V10 source prefix differs from reviewed report"
        )
    if (
        previous.get("source_count"),
        previous.get("native_versions"),
        previous.get("source_component_count"),
        previous.get("source_complete"),
        previous.get("audit_task_credit"),
    ) != (31, 710, 32, False, False):
        raise PortfolioVerificationError("Reviewed V10 source count/claim boundary differs")
    sources = [*previous["sources"], _eth_source(repository, private)]
    if len(sources) != 32 or sum(row["native_versions"] for row in sources) != 729:
        raise PortfolioVerificationError("V11 selected conduct roster differs")
    if _v10_review(private) != reviewed or _p1_inventory(private) != freeze:
        raise PortfolioVerificationError("Reviewed V10 prefix or P1 changed during source read")
    return {
        "schema": SCHEMA,
        "status": "PARTIAL_REVIEWED_NATIVE_SOURCES_NOT_AUDIT_READY",
        "as_of": "2026-09-30",
        "verifier_module_sha256": _digest(Path(__file__)),
        "v10_verifier_sha256": previous["verifier_module_sha256"],
        "v10_review_sha256": V10_REVIEW_SHA,
        "source_count": 32,
        "native_versions": 729,
        "source_component_count": 33,
        "sources": sources,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": [
            "Thirty-two selected fictional cohorts, not an enterprise evidence population.",
            "ETH001 selected two-person scenario is not a workforce census; 2026 enterprise "
            "code remains future/OPEN and 2027 local approval is fictional only.",
            "Clean has two selected on-time acknowledgments; Messy has one late acknowledgment "
            "and its historical false-clean exception remains OPEN.",
            "No actual employee action, complete operating population, substantiated-case or "
            "no-case decision, sanctions or performance-review conclusion.",
            "2027 events are authored prospective times; imported_at records 2026 insertion.",
            "REC003 inherited audit journals are excluded from business versions.",
            "No source-complete population, fresh pair, grant, collection, task or grade claim.",
        ],
    }


def write_report(repository: Path, private_repository: Path, destination: Path) -> dict:
    report = verify_all(repository, private_repository=private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise PortfolioVerificationError("Fresh V11 report destination required")
    _private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".portfolio-v11-", dir=destination.parent) as name:
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
        raise PortfolioVerificationError("Exact one-file V11 report required")
    path = root / "REPORT.json"
    before = _pin(path, _digest(path))
    actual = _read_json(path)
    expected = verify_all(repository, private_repository=private_repository)
    if actual != expected or _identity(path) != before:
        raise PortfolioVerificationError("V11 portfolio report differs")
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
            {key: result[key] for key in ("schema", "source_count", "native_versions")},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
