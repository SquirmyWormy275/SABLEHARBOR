"""V16 partial roster adding only the main-reviewed held PRD concern cohort."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from . import company_prd_concern_intake_2027 as concern
from . import fictional_2027_source_portfolio_v15 as prior
from .documentary_283_route_reconciliation_v6 import _p1_inventory
from .fictional_2027_source_portfolio import PortfolioVerificationError, _digest, _identity
from .fictional_2027_source_portfolio_v4 import (
    JOURNALS,
    _frozen_rows,
    _no_sidecars,
    _pin,
    _private,
    _read_json,
)

SCHEMA = "SH_FICTIONAL_2027_REVIEWED_SOURCE_PORTFOLIO_DIAGNOSTIC_V16"
BASE = prior.BASE
V15_FOLDER = "company-source-portfolio-v15-2026-09-30"
V15_REVIEW_SHA = "2f2c76af486fb452858ca35b629e6852c3d963b85fe93c6ef76374ccbd2af972"
V15_REPORT_SHA = "9147a65b2f16f4244adbd368811e65171a819b8986ba8df5bd66846ee2090459"
V15_CANDIDATE_SHA = {
    "A.json": "fd6ed9cb57809628305ed9d8cbd4445e01ae8920092b88f63f7a7c6e58325fb6",
    "B.json": "994969e98bea3b0fd78d618e89f848308ba573f6768d1ed9cb4d2c7251042e50",
    "REPORT.json": "9f11bb33cef6b6d1d8f5a5e869bddcb42e7196882e4a25b587e506edb45c5054",
}
CONCERN_FOLDER = "company-prd-concern-intake-2026-09-30"
CONCERN_RUN = "main-run-v1"
CONCERN_REVIEW_SHA = "695aa780d6bfd952e2b161fe0b21b8b01ae62c8e3db101686237532e57072794"
CONCERN_MANIFEST_SHA = "a55481e58a8347d1539719ab02eff7f66b17ca7d87fb870935ccbe6b36898ff6"
CONCERN_RECEIPT_SHA = "8fc7f4a4518e918975a13bdaac006336e6ffbdb5f03770e43e37e0506ec2ffe1"
CONCERN_DB_SHA = "48b85f09899e5a74ef160e9bc10cd8c85ea128986086f1b73f1344d8739e4524"
CONCERN_MODULE_SHA = "e890f87f1fa9448ff94c18476b0904e6e89305a1390a2d1ea4eae57325a63b2e"
CONCERN_SPEC_SHA = "dde9f62c3de873bdf2ae8769f529e6bb43369f74038af1682ad94ff62caf5415"
CONCERN_BRANCHES = tuple(concern.BRANCHES.values())
CONCERN_COUNTS = (8, 13)
CONCERN_SYSTEMS = 10
P1_FREEZE = prior.P1_FREEZE


def _v15_review(private: Path) -> tuple:
    """Pin exact accepted V15 report, candidate bytes and independent verdict."""
    root = private / BASE / V15_FOLDER
    review = root / "independent-review-main-v1/REVIEW.json"
    report = root / "main-report-v1/REPORT.json"
    candidates = root / "main-candidate-v1"
    files = {name: candidates / name for name in V15_CANDIDATE_SHA}
    for directory in (root, review.parent, report.parent, candidates):
        _private(directory, directory=True)
    paths = {"review": review, "report": report, **files}
    before = {
        "review": _pin(review, V15_REVIEW_SHA),
        "report": _pin(report, V15_REPORT_SHA),
        **{name: _pin(path, V15_CANDIDATE_SHA[name]) for name, path in files.items()},
    }
    reviewed = _read_json(review)
    source_report = _read_json(report)
    candidate_rows = {name: _read_json(path) for name, path in files.items()}
    if (
        reviewed.get("verdict") != "PASS_MAIN_PARTIAL_CANDIDATE_NO_AUDIT_CREDIT"
        or reviewed.get("output_sha256")
        != {
            "main-report-v1/REPORT.json": V15_REPORT_SHA,
            "main-candidate-v1/A.json": V15_CANDIDATE_SHA["A.json"],
            "main-candidate-v1/B.json": V15_CANDIDATE_SHA["B.json"],
            "main-candidate-v1/REPORT.json": V15_CANDIDATE_SHA["REPORT.json"],
        }
        or "P1 freeze" not in reviewed.get("checks", [])
        or any(
            reviewed.get(key) is not False
            for key in ("source_complete", "fresh_audit_pair_created", "audit_task_credit")
        )
        or (
            source_report.get("source_count"),
            source_report.get("native_versions"),
            source_report.get("source_component_count"),
        )
        != (36, 819, 37)
        or source_report.get("source_complete") is not False
        or source_report.get("audit_task_credit") is not False
        or candidate_rows["REPORT.json"].get("reviewed_native_versions") != 819
        or candidate_rows["REPORT.json"].get("source_complete") is not False
        or candidate_rows["REPORT.json"].get("audit_task_credit") is not False
    ):
        raise PortfolioVerificationError("Reviewed V15 report/candidate boundary differs")
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("Reviewed V15 files changed during read")
    return source_report, candidate_rows, before


def _concern_source(repository: Path, private: Path) -> dict:
    """Qualify the separate main-reviewed held concern with no customer receipt."""
    module = repository / "enterprise/audit_suite/company_prd_concern_intake_2027.py"
    spec = repository / concern.SPEC
    if (
        not module.is_file()
        or module.is_symlink()
        or _digest(module) != CONCERN_MODULE_SHA
        or not spec.is_file()
        or spec.is_symlink()
        or _digest(spec) != CONCERN_SPEC_SHA
    ):
        raise PortfolioVerificationError("PRD concern tracked source/spec differs")
    folder = private / BASE / CONCERN_FOLDER
    run = folder / CONCERN_RUN
    review_folder = folder / "independent-review-main-v1"
    paths = {
        "review": review_folder / "REVIEW.json",
        "manifest": run / "MANIFEST.json",
        "receipt": run / "RECEIPT.json",
        "database": run / "company.sqlite3",
    }
    for directory in (folder, run, review_folder):
        _private(directory, directory=True)
    expected = {
        "review": CONCERN_REVIEW_SHA,
        "manifest": CONCERN_MANIFEST_SHA,
        "receipt": CONCERN_RECEIPT_SHA,
        "database": CONCERN_DB_SHA,
    }
    before = {name: _pin(path, expected[name]) for name, path in paths.items()}
    review = _read_json(paths["review"])
    manifest = _read_json(paths["manifest"])
    receipt = _read_json(paths["receipt"])
    if (
        review.get("verdict") != "PASS_MAIN_SELECTED_PRD_CONCERN_NO_AUDIT_CREDIT"
        or review.get("main_run_sha256")
        != {
            "MANIFEST.json": CONCERN_MANIFEST_SHA,
            "RECEIPT.json": CONCERN_RECEIPT_SHA,
            "company.sqlite3": CONCERN_DB_SHA,
        }
        or review.get("native_versions") != {"CLEAN": 8, "MESSY": 13}
        or review.get("p1_freeze") != P1_FREEZE
        or review.get("source_complete") is not False
        or review.get("audit_task_credit") is not False
        or manifest.get("module_sha256") != CONCERN_MODULE_SHA
        or manifest.get("receipt_sha256") != CONCERN_RECEIPT_SHA
        or manifest.get("db_sha256") != CONCERN_DB_SHA
        or manifest.get("native_version_count") != 21
        or manifest.get("audit_task_credit") is not False
        or receipt.get("schema") != concern.SCHEMA
        or receipt.get("branches") != concern.BRANCHES
        or receipt.get("native_version_counts") != {"CLEAN": 8, "MESSY": 13}
        or receipt.get("local_open_exception_counts") != {"CLEAN": 0, "MESSY": 1}
        or receipt.get("selected_concern_count") != 1
        or receipt.get("internal_draft_status")
        != {"CLEAN": "HELD", "MESSY": "HELD_AFTER_CORRECTION"}
        or any(
            receipt.get(key) != 0
            for key in (
                "real_external_messages_sent",
                "fictional_accepted_deliveries",
                "customer_acknowledgments",
            )
        )
        or any(
            receipt.get(key) is not False
            for key in (
                "selected_claimant_verified",
                "actual_phi_processing",
                "source_complete",
                "fresh_audit_pair_created",
                "audit_task_credit",
            )
        )
    ):
        raise PortfolioVerificationError("PRD concern reviewed source boundary differs")
    if concern.verify(run, repository=repository, private_repository=private)[
        "native_version_counts"
    ] != {"CLEAN": 8, "MESSY": 13}:
        raise PortfolioVerificationError("PRD concern native verifier differs")
    native, systems, journals = _frozen_rows(paths["database"])
    if (
        sorted(native)
        != sorted(
            (concern.COMPANY, branch, count)
            for branch, count in zip(CONCERN_BRANCHES, CONCERN_COUNTS, strict=True)
        )
        or sorted(systems)
        != sorted((concern.COMPANY, branch, CONCERN_SYSTEMS) for branch in CONCERN_BRANCHES)
        or any(journals.values())
        or any(
            row["event_at"] == row["imported_at"] or row["imported_at"] >= "2027-01-01"
            for branch_rows in receipt["records"].values()
            for row in branch_rows
        )
    ):
        raise PortfolioVerificationError("PRD concern physical rows, clocks or journals differ")
    _no_sidecars(paths["database"])
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("PRD concern source changed during read")
    return {
        "source": "prdconcern",
        "run": f"{CONCERN_FOLDER}/{CONCERN_RUN}",
        "review_sha256": CONCERN_REVIEW_SHA,
        "manifest_sha256": CONCERN_MANIFEST_SHA,
        "receipt_sha256": CONCERN_RECEIPT_SHA,
        "database_sha256": {"native": CONCERN_DB_SHA},
        "native_versions": 21,
        "branch_versions": dict(zip(CONCERN_BRANCHES, CONCERN_COUNTS, strict=True)),
        "physical_company_ids": [concern.COMPANY],
        "ledger_system_counts": {"native": CONCERN_SYSTEMS},
        "inherited_audit_journals": {table: 0 for table in JOURNALS},
        "selected_concern_count": 1,
        "local_open_exception_counts": {"CLEAN": 0, "MESSY": 1},
        "selected_claimant_verified": False,
        "real_external_messages_sent": 0,
        "fictional_accepted_deliveries": 0,
        "customer_acknowledgments": 0,
        "actual_phi_processing": False,
        "source_complete": False,
        "audit_task_credit": False,
    }


def _compose_portfolio(previous: dict, selected: dict) -> dict:
    if (
        previous.get("source_count"),
        previous.get("native_versions"),
        previous.get("source_component_count"),
        previous.get("source_complete"),
        previous.get("fresh_audit_pair_created"),
        previous.get("audit_task_credit"),
    ) != (36, 819, 37, False, False, False) or len(previous.get("sources", [])) != 36:
        raise PortfolioVerificationError("Reviewed V15 source boundary differs")
    if (
        selected.get("source") != "prdconcern"
        or selected.get("native_versions") != 21
        or selected.get("branch_versions")
        != dict(zip(CONCERN_BRANCHES, CONCERN_COUNTS, strict=True))
        or selected.get("ledger_system_counts") != {"native": CONCERN_SYSTEMS}
        or selected.get("inherited_audit_journals") != {table: 0 for table in JOURNALS}
        or selected.get("local_open_exception_counts") != {"CLEAN": 0, "MESSY": 1}
        or any(
            selected.get(key) != 0
            for key in (
                "real_external_messages_sent",
                "fictional_accepted_deliveries",
                "customer_acknowledgments",
            )
        )
        or any(
            selected.get(key) is not False
            for key in (
                "selected_claimant_verified",
                "actual_phi_processing",
                "source_complete",
                "audit_task_credit",
            )
        )
    ):
        raise PortfolioVerificationError("PRD concern source scope differs")
    sources = [*previous["sources"], selected]
    if len(sources) != 37 or sum(row["native_versions"] for row in sources) != 840:
        raise PortfolioVerificationError("V16 source roster differs")
    return {
        "schema": SCHEMA,
        "status": "PARTIAL_REVIEWED_NATIVE_SOURCES_NOT_AUDIT_READY",
        "as_of": "2026-09-30",
        "verifier_module_sha256": _digest(Path(__file__)),
        "v15_verifier_sha256": previous["verifier_module_sha256"],
        "v15_review_sha256": V15_REVIEW_SHA,
        "source_count": 37,
        "native_versions": 840,
        "source_component_count": 38,
        "sources": sources,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": [
            "Thirty-seven selected fictional cohorts, not an enterprise evidence population.",
            "PRD concern is one unverified claimant and held local company draft; "
            "no accepted delivery or acknowledgment.",
            "Messy denied dispatch attempt, false close, later matrix correction "
            "and OPEN historical exception remain.",
            "Customer authority and notice duty are unresolved; no complete "
            "customer/channel population or authored clause outcome.",
            "2027 event/availability clocks are authored; native import clocks "
            "record actual source creation separately.",
            "REC003 inherited audit journals are excluded from business versions.",
            "No complete source population, fresh pair, grant, collection, task, Key or grade.",
        ],
    }


def verify_all(repository: Path, *, private_repository: Path | None = None) -> dict:
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository or repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise PortfolioVerificationError("Frozen P1 inventory differs")
    reviewed = _v15_review(private)
    previous = prior.verify_all(repository, private_repository=private)
    if previous != reviewed[0]:
        raise PortfolioVerificationError(
            "Recomputed V15 source prefix differs from reviewed report"
        )
    selected = _concern_source(repository, private)
    if _v15_review(private) != reviewed or _p1_inventory(private) != freeze:
        raise PortfolioVerificationError("Reviewed V15 prefix or P1 changed during source read")
    return _compose_portfolio(previous, selected)


def write_report(repository: Path, private_repository: Path, destination: Path) -> dict:
    report = verify_all(repository, private_repository=private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise PortfolioVerificationError("Fresh V16 report destination required")
    _private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".portfolio-v16-", dir=destination.parent) as name:
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
        raise PortfolioVerificationError("Exact one-file V16 report required")
    path = root / "REPORT.json"
    before = _pin(path, _digest(path))
    actual = _read_json(path)
    expected = verify_all(repository, private_repository=private_repository)
    if actual != expected or _identity(path) != before:
        raise PortfolioVerificationError("V16 portfolio report differs")
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
