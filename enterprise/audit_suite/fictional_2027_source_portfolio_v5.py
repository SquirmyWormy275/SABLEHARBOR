"""Read-only partial V5 roster: reviewed governance and selected security operations."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import company_gov_appetite_exercise as gov
from . import company_sec005_operated_2027 as operated
from . import fictional_2027_source_portfolio_v4 as prior
from .fictional_2027_source_portfolio import BASE, PortfolioVerificationError, _digest, _identity

SCHEMA = "SH_FICTIONAL_2027_REVIEWED_SOURCE_PORTFOLIO_DIAGNOSTIC_V5"
V4_REVIEW = "company-source-portfolio-v4-2026-09-30/independent-review-main-v1/REVIEW.json"
V4_REVIEW_SHA = "804e7c58ee437d4b7f2e87106c1e893cc155c2c0043e07b7205d4204d1a81264"
V4_REPORT = "company-source-portfolio-v4-2026-09-30/main-run-v1/REPORT.json"
V4_REPORT_SHA = "fa8474dfe68370b1fda382b03615c15a11d644edbbcd6b988f7c283b7f1221c4"
V4_CANDIDATE = "company-source-portfolio-v4-2026-09-30/main-candidate-v1"


@dataclass(frozen=True)
class AddedSource:
    key: str
    folder: str
    review: str
    review_sha256: str
    verdict: str
    manifest_sha256: str
    receipt_sha256: str
    database_sha256: str
    branches: tuple[str, str]
    counts: tuple[int, int]
    systems: int

    run: str = "main-run-v1"


STANDARD = (
    AddedSource(
        "govapp",
        "company-gov-appetite-2026-09-30",
        "independent-review-main-v1/REVIEW.json",
        "293ff3ba7d368398d22a5008204173a9b22ed0d78686e00d7ad6b692f30a7c0e",
        "PASS_FICTIONAL_SELECTED_GOVERNANCE_MAIN_LOCAL_NO_AUDIT_CREDIT",
        "31c78f79bc0a533758ed7778c6c5a43d2256c5705ec425f26fd73e7d6623ce39",
        "0b4d879e0536c404de2492bfa0b4388cc6e7f330c230764c4486766f247d54f1",
        "b925f9bb3bc955fe0bcc107ac5ae5612b7a44227bd350fbe5d076b4480eb09d7",
        ("GOVAPP-CLEAN", "GOVAPP-MESSY"),
        (16, 18),
        10,
    ),
    AddedSource(
        "sec005operated",
        "company-sec005-operated-2026-09-30",
        "independent-review-main-v2/REVIEW.json",
        "4c163ff06dda410b05a83a45f0135d9b3a80e8fd38801704df481d999b2772b6",
        "PASS_SELECTED_FICTIONAL_COMPANY_SOURCE_MAIN_LOCAL_NO_AUDIT_CREDIT",
        "37b170a7e6688d1bbab4022ff8a239eb3b2e5c44fff76af381a9872c0b84aa32",
        "157495f5e98d9475f2c88b01954b6e192049183105fe35475350c20885681968",
        "4c258e73de8084b20c65fcad24a96e7f0e3fbb771de431c6e079fc6500d7fd1f",
        ("SEC005-OPERATED-CLEAN", "SEC005-OPERATED-MESSY"),
        (17, 23),
        9,
    ),
)


def _v4_review(private: Path) -> tuple:
    root = private / BASE
    review = root / V4_REVIEW
    report = root / V4_REPORT
    candidates = {name: root / V4_CANDIDATE / name for name in ("A.json", "B.json", "REPORT.json")}
    for directory in (review.parent, report.parent, root / V4_CANDIDATE):
        prior._private(directory, directory=True)
    review_before = prior._pin(review, V4_REVIEW_SHA)
    report_before = prior._pin(report, V4_REPORT_SHA)
    row = prior._read_json(review)
    if (
        row.get("verdict") != "PASS_PARTIAL_READ_ONLY_CANDIDATE_REGISTRY_NO_AUDIT_CREDIT"
        or row.get("portfolio_report_sha256") != V4_REPORT_SHA
        or row.get("selected_portfolio_run") != "main-run-v1"
        or row.get("selected_candidate_run") != "main-candidate-v1"
        or row.get("active_pair_mutated") is not False
        or prior._read_json(report).get("source_complete") is not False
        or set(row.get("candidate_sha256", {})) != set(candidates)
    ):
        raise PortfolioVerificationError("Reviewed V4 main baseline differs")
    candidate_before = tuple(
        prior._pin(path, row["candidate_sha256"][name]) for name, path in candidates.items()
    )
    if (
        _identity(review) != review_before
        or _identity(report) != report_before
        or tuple(_identity(path) for path in candidates.values()) != candidate_before
    ):
        raise PortfolioVerificationError("Reviewed V4 main baseline changed during read")
    return review_before, report_before, candidate_before


def _standard(source: AddedSource, repository: Path, private: Path) -> dict:
    folder = private / BASE / source.folder
    run = folder / source.run
    review = folder / source.review
    paths = {
        "review": review,
        "manifest": run / "MANIFEST.json",
        "receipt": run / "RECEIPT.json",
        "database": run / "company.sqlite3",
    }
    for directory in (folder, run, review.parent):
        prior._private(directory, directory=True)
    before = {
        name: prior._pin(path, sha)
        for name, (path, sha) in {
            "review": (review, source.review_sha256),
            "manifest": (paths["manifest"], source.manifest_sha256),
            "receipt": (paths["receipt"], source.receipt_sha256),
            "database": (paths["database"], source.database_sha256),
        }.items()
    }
    review_row = prior._read_json(review)
    if (
        review_row.get("verdict") != source.verdict
        or review_row.get("selected_run", review_row.get("main_run")) != source.run
        or review_row.get("manifest_sha256") != source.manifest_sha256
        or review_row.get("receipt_sha256") != source.receipt_sha256
        or review_row.get("native_db_sha256") != source.database_sha256
        or review_row.get("active_pair_mutated") is not False
    ):
        raise PortfolioVerificationError(f"{source.key} independent review/source join differs")
    manifest, receipt = prior._read_json(paths["manifest"]), prior._read_json(paths["receipt"])
    if (
        receipt.get("branches") != dict(zip(("CLEAN", "MESSY"), source.branches, strict=True))
        or receipt.get("company") != "SABLE-HARBOR-REFERENCE"
        or receipt.get("audit_task_credit") is not False
        or manifest.get("audit_task_credit") is not False
        or manifest.get("native_version_count") != sum(source.counts)
        or manifest.get("receipt_sha256") != source.receipt_sha256
        or manifest.get("company_db_sha256", manifest.get("db_sha256")) != source.database_sha256
    ):
        raise PortfolioVerificationError(f"{source.key} native manifest/receipt differs")
    if source.key == "govapp":
        own = gov.verify(run, repository=repository, private_repository=private)
        if own.get("audit_task_credit") is not False or own.get("real_board_approval") is not False:
            raise PortfolioVerificationError("Governance source claim limit differs")
    else:
        transition = private / BASE / "company-runtime-transition-2026-09-29/run-v3"
        own = operated.verify(
            run, repository=repository, private_repository=private, transition_root=transition
        )
        if own != {
            "status": "VERIFIED_FICTIONAL_SELECTED_OPERATION_NO_AUDIT_CREDIT",
            "native_version_counts": {"CLEAN": 17, "MESSY": 23},
        }:
            raise PortfolioVerificationError("Selected security source verifier differs")
    native, systems, journals = prior._frozen_rows(paths["database"])
    if (
        sorted(native)
        != sorted(
            ("SABLE-HARBOR-REFERENCE", branch, count)
            for branch, count in zip(source.branches, source.counts, strict=True)
        )
        or sorted(systems)
        != sorted(("SABLE-HARBOR-REFERENCE", branch, source.systems) for branch in source.branches)
        or any(journals.values())
    ):
        raise PortfolioVerificationError(f"{source.key} physical roster/journals differ")
    prior._no_sidecars(paths["database"])
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError(f"{source.key} changed during verification")
    return {
        "source": source.key,
        "run": f"{source.folder}/{source.run}",
        "review_sha256": source.review_sha256,
        "manifest_sha256": source.manifest_sha256,
        "receipt_sha256": source.receipt_sha256,
        "database_sha256": {"native": source.database_sha256},
        "native_versions": sum(source.counts),
        "branch_versions": dict(zip(source.branches, source.counts, strict=True)),
        "physical_company_ids": ["SABLE-HARBOR-REFERENCE"],
        "ledger_system_counts": {"native": source.systems},
        "inherited_audit_journals": {table: 0 for table in prior.JOURNALS},
        "audit_task_credit": False,
    }


def verify_all(repository: Path, *, private_repository: Path | None = None) -> dict:
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository or repository).resolve(strict=True)
    before = _v4_review(private)
    previous = prior.verify_all(repository, private_repository=private)
    if (
        previous.get("source_count"),
        previous.get("native_versions"),
        previous.get("source_component_count"),
        previous.get("source_complete"),
        previous.get("audit_task_credit"),
    ) != (24, 401, 25, False, False):
        raise PortfolioVerificationError("Reviewed V4 source prefix differs")
    sources = [*previous["sources"]]
    sources.extend(_standard(source, repository, private) for source in STANDARD)
    if len(sources) != 26 or sum(row["native_versions"] for row in sources) != 475:
        raise PortfolioVerificationError("V5 selected source roster differs")
    if _v4_review(private) != before:
        raise PortfolioVerificationError("Reviewed V4 baseline changed during V5 scan")
    return {
        "schema": SCHEMA,
        "status": "PARTIAL_REVIEWED_NATIVE_SOURCES_NOT_AUDIT_READY",
        "as_of": "2026-09-30",
        "verifier_module_sha256": _digest(Path(__file__)),
        "v4_verifier_sha256": previous["verifier_module_sha256"],
        "v4_review_sha256": V4_REVIEW_SHA,
        "source_count": 26,
        "native_versions": 475,
        "source_component_count": 27,
        "sources": sources,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": [
            "Twenty-six selected cohorts, not an enterprise evidence population.",
            "GOVAPP and SEC005-operated are future fictional selected company histories; "
            "no real Board approval, device deployment or independent security assurance.",
            "V4 REC003 inherited journals are excluded from company business versions.",
            "A/B are routing profiles, not new engagements or collected evidence.",
            "No source-complete, grant, collection, task, Key or grade claim.",
        ],
    }


def write_report(repository: Path, private_repository: Path, destination: Path) -> dict:
    report = verify_all(repository, private_repository=private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise PortfolioVerificationError("Fresh V5 report destination required")
    prior._private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".portfolio-v5-", dir=destination.parent) as temp:
        stage = Path(temp)
        path = stage / "REPORT.json"
        path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        path.chmod(0o600)
        os.rename(stage, destination)
    return verify_report(destination, repository, private_repository)


def verify_report(destination: Path, repository: Path, private_repository: Path) -> dict:
    root = Path(destination).absolute()
    prior._private(root, directory=True)
    if {path.name for path in root.iterdir()} != {"REPORT.json"}:
        raise PortfolioVerificationError("Exact one-file V5 report required")
    path = root / "REPORT.json"
    before = prior._pin(path, _digest(path))
    actual = prior._read_json(path)
    expected = verify_all(repository, private_repository=private_repository)
    if actual != expected or _identity(path) != before:
        raise PortfolioVerificationError("V5 portfolio report differs")
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
    summary = {k: result[k] for k in ("schema", "source_count", "native_versions")}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
