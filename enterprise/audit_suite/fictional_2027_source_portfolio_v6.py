"""Read-only partial V6 roster adding the reviewed fictional IAM005 marker path."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from . import company_iam005_emergency_marker_2027 as iam
from . import fictional_2027_source_portfolio_v5 as prior
from .fictional_2027_source_portfolio import BASE, PortfolioVerificationError, _digest, _identity

SCHEMA = "SH_FICTIONAL_2027_REVIEWED_SOURCE_PORTFOLIO_DIAGNOSTIC_V6"
V5_FOLDER = "company-source-portfolio-v5-2026-09-30"
V5_REVIEW_SHA = "9c04b6e3b5208331e9a1a774295c9d0a195280f2fc8c703d515b5d741ece33ed"
V5_REPORT_SHA = "418166c593442760ad733dc8a7657e25b6365ae2e46a7e461a315b1f7ab4556e"
IAM_FOLDER = "company-iam005-emergency-marker-2026-09-30"
IAM_RUN = "main-run-v1"
IAM_REVIEW = "independent-review-main-v1/REVIEW.json"
IAM_REVIEW_SHA = "2d1d0f413e26388dd6f7abff9835bc3a3e80376cd8056f855da7e0d51ba35674"
IAM_MANIFEST_SHA = "d21c7aedd1d029ce596db7b158e4c23fd379bc225304c2959537ef8f4a9dba42"
IAM_RECEIPT_SHA = "95dcda39d7965d285a585afacadf869b4d7349556452d15051c29433fe5f9185"
IAM_DB_SHA = "bd40f886ccd53def3b1cfe716f93422a5aa686e15162b2f90b48e3af5920d433"
IAM_BRANCHES = ("IAM005-EMERGENCY-CLEAN", "IAM005-EMERGENCY-MESSY")
IAM_COUNTS = (9, 16)
IAM_SYSTEMS = 9


def _v5_review(private: Path) -> tuple:
    root = private / BASE / V5_FOLDER
    review = root / "independent-review-main-v1/REVIEW.json"
    report = root / "main-run-v1/REPORT.json"
    candidates = {
        name: root / "main-candidate-v1" / name for name in ("A.json", "B.json", "REPORT.json")
    }
    for directory in (review.parent, report.parent, root / "main-candidate-v1"):
        prior.prior._private(directory, directory=True)
    before = (prior.prior._pin(review, V5_REVIEW_SHA), prior.prior._pin(report, V5_REPORT_SHA))
    row = prior.prior._read_json(review)
    report_row = prior.prior._read_json(report)
    if (
        row.get("verdict") != "PASS_PARTIAL_READ_ONLY_V5_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or row.get("portfolio_report_sha256") != V5_REPORT_SHA
        or row.get("selected_portfolio_run") != "main-run-v1"
        or row.get("selected_candidate_run") != "main-candidate-v1"
        or row.get("active_pair_mutated") is not False
        or report_row.get("source_complete") is not False
        or set(row.get("candidate_sha256", {})) != set(candidates)
    ):
        raise PortfolioVerificationError("Reviewed V5 main baseline differs")
    candidate_before = tuple(
        prior.prior._pin(path, row["candidate_sha256"][name]) for name, path in candidates.items()
    )
    if (
        _identity(review) != before[0]
        or _identity(report) != before[1]
        or tuple(_identity(path) for path in candidates.values()) != candidate_before
    ):
        raise PortfolioVerificationError("Reviewed V5 main baseline changed during read")
    return (*before, candidate_before, report_row)


def _iam_source(repository: Path, private: Path) -> dict:
    folder = private / BASE / IAM_FOLDER
    run = folder / IAM_RUN
    review = folder / IAM_REVIEW
    paths = {
        "review": review,
        "manifest": run / "MANIFEST.json",
        "receipt": run / "RECEIPT.json",
        "database": run / "company.sqlite3",
    }
    for directory in (folder, run, review.parent):
        prior.prior._private(directory, directory=True)
    expected = {
        "review": IAM_REVIEW_SHA,
        "manifest": IAM_MANIFEST_SHA,
        "receipt": IAM_RECEIPT_SHA,
        "database": IAM_DB_SHA,
    }
    before = {name: prior.prior._pin(path, expected[name]) for name, path in paths.items()}
    review_row = prior.prior._read_json(review)
    if (
        review_row.get("selected_run", review_row.get("main_run")) != IAM_RUN
        or review_row.get("manifest_sha256") != IAM_MANIFEST_SHA
        or review_row.get("receipt_sha256") != IAM_RECEIPT_SHA
        or review_row.get("native_db_sha256") != IAM_DB_SHA
        or review_row.get("active_pair_mutated") is not False
        or review_row.get("verdict")
        != "PASS_SELECTED_FICTIONAL_NATIVE_SOURCE_MAIN_LOCAL_NO_AUDIT_CREDIT"
    ):
        raise PortfolioVerificationError("IAM005 independent review/source join differs")
    manifest = prior.prior._read_json(paths["manifest"])
    receipt = prior.prior._read_json(paths["receipt"])
    if (
        receipt.get("branches") != dict(zip(("CLEAN", "MESSY"), IAM_BRANCHES, strict=True))
        or receipt.get("company") != "SABLE-HARBOR-REFERENCE"
        or receipt.get("native_version_counts")
        != dict(zip(("CLEAN", "MESSY"), IAM_COUNTS, strict=True))
        or receipt.get("audit_task_credit") is not False
        or receipt.get("authored_iam005_clause_satisfied") is not False
        or manifest.get("audit_task_credit") is not False
        or manifest.get("native_version_count") != 25
        or manifest.get("receipt_sha256") != IAM_RECEIPT_SHA
        or manifest.get("db_sha256") != IAM_DB_SHA
    ):
        raise PortfolioVerificationError("IAM005 native manifest/receipt differs")
    own = iam.verify(run, repository=repository, private_repository=private)
    if own != {
        "status": "VERIFIED_FICTIONAL_SELECTED_IAM005_SOURCE_NO_AUDIT_CREDIT",
        "native_version_counts": {"CLEAN": 9, "MESSY": 16},
        "audit_task_credit": False,
    }:
        raise PortfolioVerificationError("IAM005 source verifier differs")
    native, systems, journals = prior.prior._frozen_rows(paths["database"])
    if (
        sorted(native)
        != sorted(
            ("SABLE-HARBOR-REFERENCE", branch, count)
            for branch, count in zip(IAM_BRANCHES, IAM_COUNTS, strict=True)
        )
        or sorted(systems)
        != sorted(("SABLE-HARBOR-REFERENCE", branch, IAM_SYSTEMS) for branch in IAM_BRANCHES)
        or any(journals.values())
    ):
        raise PortfolioVerificationError("IAM005 physical roster/journals differ")
    prior.prior._no_sidecars(paths["database"])
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("IAM005 source changed during verification")
    return {
        "source": "iam005emergency",
        "run": f"{IAM_FOLDER}/{IAM_RUN}",
        "review_sha256": IAM_REVIEW_SHA,
        "manifest_sha256": IAM_MANIFEST_SHA,
        "receipt_sha256": IAM_RECEIPT_SHA,
        "database_sha256": {"native": IAM_DB_SHA},
        "native_versions": 25,
        "branch_versions": dict(zip(IAM_BRANCHES, IAM_COUNTS, strict=True)),
        "physical_company_ids": ["SABLE-HARBOR-REFERENCE"],
        "ledger_system_counts": {"native": IAM_SYSTEMS},
        "inherited_audit_journals": {table: 0 for table in prior.prior.JOURNALS},
        "audit_task_credit": False,
    }


def verify_all(repository: Path, *, private_repository: Path | None = None) -> dict:
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository or repository).resolve(strict=True)
    before = _v5_review(private)
    previous = prior.verify_all(repository, private_repository=private)
    if previous != before[3]:
        raise PortfolioVerificationError("Recomputed V5 prefix differs from reviewed report")
    if (
        previous.get("source_count"),
        previous.get("native_versions"),
        previous.get("source_component_count"),
        previous.get("source_complete"),
        previous.get("audit_task_credit"),
    ) != (26, 475, 27, False, False):
        raise PortfolioVerificationError("Reviewed V5 source prefix differs")
    sources = [*previous["sources"], _iam_source(repository, private)]
    if len(sources) != 27 or sum(row["native_versions"] for row in sources) != 500:
        raise PortfolioVerificationError("V6 selected source roster differs")
    if _v5_review(private) != before:
        raise PortfolioVerificationError("Reviewed V5 baseline changed during V6 scan")
    return {
        "schema": SCHEMA,
        "status": "PARTIAL_REVIEWED_NATIVE_SOURCES_NOT_AUDIT_READY",
        "as_of": "2026-09-30",
        "verifier_module_sha256": _digest(Path(__file__)),
        "v5_verifier_sha256": previous["verifier_module_sha256"],
        "v5_review_sha256": V5_REVIEW_SHA,
        "source_count": 27,
        "native_versions": 500,
        "source_component_count": 28,
        "sources": sources,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": [
            "Twenty-seven selected cohorts, not an enterprise evidence population.",
            "IAM005 is fictional, not real emergency ePHI access or period assurance.",
            "Messy BCM failure, marker retest, denied closure and SEC005 exception remain open.",
            "AS-P008 self-review is not independent assurance.",
            "No source-complete, grant, collection, task, Key or grade claim.",
        ],
    }


def write_report(repository: Path, private_repository: Path, destination: Path) -> dict:
    report = verify_all(repository, private_repository=private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise PortfolioVerificationError("Fresh V6 report destination required")
    prior.prior._private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".portfolio-v6-", dir=destination.parent) as temp:
        stage = Path(temp)
        path = stage / "REPORT.json"
        path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        path.chmod(0o600)
        os.rename(stage, destination)
    return verify_report(destination, repository, private_repository)


def verify_report(destination: Path, repository: Path, private_repository: Path) -> dict:
    root = Path(destination).absolute()
    prior.prior._private(root, directory=True)
    if {path.name for path in root.iterdir()} != {"REPORT.json"}:
        raise PortfolioVerificationError("Exact one-file V6 report required")
    path = root / "REPORT.json"
    before = prior.prior._pin(path, _digest(path))
    actual = prior.prior._read_json(path)
    expected = verify_all(repository, private_repository=private_repository)
    if actual != expected or _identity(path) != before:
        raise PortfolioVerificationError("V6 portfolio report differs")
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
