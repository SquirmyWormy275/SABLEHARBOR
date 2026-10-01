"""Read-only partial V8 roster adding reviewed fictional physical-site history."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from . import company_physical_site_2027 as physical
from . import fictional_2027_source_portfolio_v7 as prior
from .fictional_2027_source_portfolio import BASE, PortfolioVerificationError, _digest, _identity
from .fictional_2027_source_portfolio_v4 import (
    JOURNALS,
    _frozen_rows,
    _no_sidecars,
    _pin,
    _private,
    _read_json,
)

SCHEMA = "SH_FICTIONAL_2027_REVIEWED_SOURCE_PORTFOLIO_DIAGNOSTIC_V8"
V7_FOLDER = "company-source-portfolio-v7-2026-09-30"
V7_REVIEW_SHA = "f49dd7f61a6afdda28ffd7ad366dde1e13269df229b70524d889ab1d85a68ea6"
V7_REPORT_SHA = "179030de0a438f2f3e05937a3a660e1da5e2072f0293c53d0ffe131804945015"
V7_CANDIDATE_SHA = {
    "A.json": "64a4a35ab535629752d257ed4f7e83c20ed30f512bf4ca9d11a8860f3f94e244",
    "B.json": "c0a9255defe093d94274b02891516f3fe4c323147b4a112c3edfb98fb61c0cd1",
    "REPORT.json": "3a3ce5354f78138863a13c4b42e2556a520b950f040546b3a54b976a75fcbbd5",
}
PHYS_FOLDER = "company-physical-site-selected-2026-09-30"
PHYS_RUN = "main-run-v1"
PHYS_REVIEW = "independent-review-main-v1/REVIEW.json"
PHYS_REVIEW_SHA = "1c7ccc1ce9abeab01f265238e63f84df4defa70948a46c99047d138a449fa0f3"
PHYS_REVIEW_VERDICT = "PASS_PRIVATE_FICTIONAL_SOURCE_FOR_INTEGRATION_REVIEW_NO_AUDIT_CREDIT"
PHYS_MANIFEST_SHA = "5c8cf04de73f987d3555efe54f6d6fd238e005b0574bff61b90c251e46f2e7a5"
PHYS_RECEIPT_SHA = "fd82fbbfa3c5d03a35c935673fe9ec973ccb905d57e09df52fb943522ba6e485"
PHYS_DB_SHA = "19a358a258a8da7054f9f1946cb9e49e98dfe4def3da06d33e635ff2fe6ca816"
PHYS_BRANCHES = ("PHYSICAL-CLEAN", "PHYSICAL-MESSY")
PHYS_COUNTS = (13, 18)
PHYS_SYSTEMS = 8


def _v7_review(private: Path) -> tuple:
    """Pin reviewed report and every candidate byte, then expose exact objects."""
    root = private / BASE / V7_FOLDER
    review = root / "independent-review-main-v1/REVIEW.json"
    report = root / "main-run-v1/REPORT.json"
    candidate_root = root / "main-candidate-v1"
    files = {name: candidate_root / name for name in V7_CANDIDATE_SHA}
    for directory in (root, review.parent, report.parent, candidate_root):
        _private(directory, directory=True)
    before = {
        "review": _pin(review, V7_REVIEW_SHA),
        "report": _pin(report, V7_REPORT_SHA),
        **{name: _pin(path, V7_CANDIDATE_SHA[name]) for name, path in files.items()},
    }
    row = _read_json(review)
    report_row = _read_json(report)
    candidate_rows = {name: _read_json(path) for name, path in files.items()}
    if (
        row.get("verdict") != "PASS_PARTIAL_READ_ONLY_CANDIDATE_REGISTRY_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or row.get("main_output_sha256")
        != {
            "portfolio": V7_REPORT_SHA,
            "candidate_A": V7_CANDIDATE_SHA["A.json"],
            "candidate_B": V7_CANDIDATE_SHA["B.json"],
            "candidate_report": V7_CANDIDATE_SHA["REPORT.json"],
        }
        or row.get("checks", {}).get("tracked_code_or_p1_mutated_by_review") is not False
        or report_row.get("source_complete") is not False
        or report_row.get("audit_task_credit") is not False
        or candidate_rows["REPORT.json"].get("source_complete") is not False
        or candidate_rows["REPORT.json"].get("audit_task_credit") is not False
    ):
        raise PortfolioVerificationError("Reviewed V7 main report/candidate boundary differs")
    paths = {"review": review, "report": report, **files}
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("Reviewed V7 main files changed during read")
    return report_row, candidate_rows, before


def _physical_source(repository: Path, private: Path) -> dict:
    """Check the independently reviewed three-file source and its claim limits."""
    if PHYS_REVIEW_SHA == "PENDING_INDEPENDENT_MAIN_REVIEW":
        raise PortfolioVerificationError("Physical-site independent main review not yet pinned")
    folder = private / BASE / PHYS_FOLDER
    run = folder / PHYS_RUN
    review = folder / PHYS_REVIEW
    paths = {
        "review": review,
        "manifest": run / "MANIFEST.json",
        "receipt": run / "RECEIPT.json",
        "database": run / "company.sqlite3",
    }
    for directory in (folder, run, review.parent):
        _private(directory, directory=True)
    expected = {
        "review": PHYS_REVIEW_SHA,
        "manifest": PHYS_MANIFEST_SHA,
        "receipt": PHYS_RECEIPT_SHA,
        "database": PHYS_DB_SHA,
    }
    before = {name: _pin(path, expected[name]) for name, path in paths.items()}
    review_row = _read_json(review)
    manifest = _read_json(paths["manifest"])
    receipt = _read_json(paths["receipt"])
    if (
        review_row.get("verdict") != PHYS_REVIEW_VERDICT
        or review_row.get("main_run_v1_sha256")
        != {
            "MANIFEST.json": PHYS_MANIFEST_SHA,
            "RECEIPT.json": PHYS_RECEIPT_SHA,
            "company.sqlite3": PHYS_DB_SHA,
        }
        or review_row.get("active_p1_mutated") is not False
        or review_row.get("actual_operation_eligibility_as_of_2026_09_30") is not False
        or review_row.get("audit_task_credit") is not False
    ):
        raise PortfolioVerificationError("Physical-site independent review/source join differs")
    if (
        receipt.get("branches") != dict(zip(("CLEAN", "MESSY"), PHYS_BRANCHES, strict=True))
        or receipt.get("native_version_counts")
        != dict(zip(("CLEAN", "MESSY"), PHYS_COUNTS, strict=True))
        or receipt.get("company") != "SABLE-HARBOR-REFERENCE"
        or receipt.get("selected_sites")
        != {"BOISE": "RUNTIME-BOISE-DR", "RENO": "RUNTIME-RENO-COLO"}
        or receipt.get("selected_zones") != ["RNO-CAGE-A", "BOI-CAGE-R"]
        or receipt.get("selected_badges") != ["BADGE-FAC-01", "BADGE-BOI-TECH-01"]
        or receipt.get("selected_environment_point") != "BOI-CAGE-R-TEMP-01"
        or receipt.get("messy_false_close_preserved") is not True
        or receipt.get("messy_unescorted_entry_preserved") is not True
        or receipt.get("messy_historical_exception_status") != "OPEN"
        or any(
            receipt.get(key) is not False
            for key in (
                "provider_and_enterprise_population_complete",
                "authored_clauses_satisfied",
                "independent_assurance_completed",
                "actual_operation_eligibility_as_of_2026_09_30",
                "real_site_action",
                "actual_personal_data",
                "actual_phi",
                "audit_task_credit",
            )
        )
        or receipt.get("network_packets") != 0
        or manifest.get("receipt_sha256") != PHYS_RECEIPT_SHA
        or manifest.get("company_db_sha256") != PHYS_DB_SHA
        or manifest.get("native_version_count") != 31
        or manifest.get("audit_task_credit") is not False
    ):
        raise PortfolioVerificationError("Physical-site native claim/manifest boundary differs")
    if physical.verify(run, repository=repository, private_repository=private) != receipt:
        raise PortfolioVerificationError("Physical-site own source verifier differs")
    native, systems, journals = _frozen_rows(paths["database"])
    if (
        sorted(native)
        != sorted(
            ("SABLE-HARBOR-REFERENCE", branch, count)
            for branch, count in zip(PHYS_BRANCHES, PHYS_COUNTS, strict=True)
        )
        or sorted(systems)
        != sorted(("SABLE-HARBOR-REFERENCE", branch, PHYS_SYSTEMS) for branch in PHYS_BRANCHES)
        or any(journals.values())
    ):
        raise PortfolioVerificationError("Physical-site physical branches/journals differ")
    _no_sidecars(paths["database"])
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("Physical-site source changed during read")
    return {
        "source": "physicalsite",
        "run": f"{PHYS_FOLDER}/{PHYS_RUN}",
        "review_sha256": PHYS_REVIEW_SHA,
        "manifest_sha256": PHYS_MANIFEST_SHA,
        "receipt_sha256": PHYS_RECEIPT_SHA,
        "database_sha256": {"native": PHYS_DB_SHA},
        "native_versions": 31,
        "branch_versions": dict(zip(PHYS_BRANCHES, PHYS_COUNTS, strict=True)),
        "physical_company_ids": ["SABLE-HARBOR-REFERENCE"],
        "ledger_system_counts": {"native": PHYS_SYSTEMS},
        "inherited_audit_journals": {table: 0 for table in JOURNALS},
        "audit_task_credit": False,
    }


def verify_all(repository: Path, *, private_repository: Path | None = None) -> dict:
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository or repository).resolve(strict=True)
    reviewed = _v7_review(private)
    previous = prior.verify_all(repository, private_repository=private)
    if previous != reviewed[0]:
        raise PortfolioVerificationError("Recomputed V7 source prefix differs from reviewed report")
    if (
        previous.get("source_count"),
        previous.get("native_versions"),
        previous.get("source_component_count"),
        previous.get("source_complete"),
        previous.get("audit_task_credit"),
    ) != (28, 529, 29, False, False):
        raise PortfolioVerificationError("Reviewed V7 source count/claim boundary differs")
    sources = [*previous["sources"], _physical_source(repository, private)]
    if len(sources) != 29 or sum(row["native_versions"] for row in sources) != 560:
        raise PortfolioVerificationError("V8 selected physical-site roster differs")
    if _v7_review(private) != reviewed:
        raise PortfolioVerificationError("Reviewed V7 source/candidate prefix changed")
    return {
        "schema": SCHEMA,
        "status": "PARTIAL_REVIEWED_NATIVE_SOURCES_NOT_AUDIT_READY",
        "as_of": "2026-09-30",
        "verifier_module_sha256": _digest(Path(__file__)),
        "v7_verifier_sha256": previous["verifier_module_sha256"],
        "v7_review_sha256": V7_REVIEW_SHA,
        "source_count": 29,
        "native_versions": 560,
        "source_component_count": 30,
        "sources": sources,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": [
            "Twenty-nine selected fictional cohorts, not an enterprise evidence population.",
            "Physical-site source is a selected two-cage fictional history; 2026 provider sites "
            "remain procurement-pending.",
            "Provider building perimeters, complete access/environmental populations and "
            "annual operation remain untested.",
            "Messy false closure and unescorted entry remain; historical exception stays OPEN.",
            "REC003 inherited audit journals are excluded from business versions.",
            "No actual 2027 operation, source-complete, grant, collection, task or grade claim.",
        ],
    }


def write_report(repository: Path, private_repository: Path, destination: Path) -> dict:
    report = verify_all(repository, private_repository=private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise PortfolioVerificationError("Fresh V8 report destination required")
    _private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".portfolio-v8-", dir=destination.parent) as name:
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
        raise PortfolioVerificationError("Exact one-file V8 report required")
    path = root / "REPORT.json"
    before = _pin(path, _digest(path))
    actual = _read_json(path)
    expected = verify_all(repository, private_repository=private_repository)
    if actual != expected or _identity(path) != before:
        raise PortfolioVerificationError("V8 portfolio report differs")
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
