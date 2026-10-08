"""Read-only partial V9 roster adding the reviewed fictional LEG001 docket."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from . import company_leg001_operating_docket_2027 as leg001
from . import fictional_2027_source_portfolio_v8 as prior
from .fictional_2027_source_portfolio import BASE, PortfolioVerificationError, _digest, _identity
from .fictional_2027_source_portfolio_v4 import (
    JOURNALS,
    _frozen_rows,
    _no_sidecars,
    _pin,
    _private,
    _read_json,
)

SCHEMA = "SH_FICTIONAL_2027_REVIEWED_SOURCE_PORTFOLIO_DIAGNOSTIC_V9"
V8_FOLDER = "company-source-portfolio-v8-2026-09-30"
V8_REVIEW_SHA = "58d696a4ba0cdd2f9e2245189544ed7d1be3d764bb6994fc1b1f43be44629e3d"
V8_REPORT_SHA = "bad1981628f6e72760ade785b01e589668fe6eed6e274018d175c15d48854953"
V8_CANDIDATE_SHA = {
    "A.json": "b8f2fafbee8c62d4dc2cd0ced5015d14debff1972e0f65d47283c8c6bb5d8c71",
    "B.json": "1f75372342081c161c001a644b0529295e80bbaca9180cf9d672a3b726343628",
    "REPORT.json": "7add4d7904ea7e79c50c6c79af3b7c6933b75896fef35dafeccf9662e0c4f79a",
}
LEG_FOLDER = "company-leg001-operating-docket-2027-09-30"
LEG_RUN = "main-run-v1"
LEG_REVIEW = "independent-review-main-v1/REVIEW.json"
LEG_REVIEW_SHA = "3bd03221aaa69b11ba5a484c402ee12e17b67290b3732f5aab97dd3b54632cc6"
LEG_REVIEW_VERDICT = "PASS_PRIVATE_FICTIONAL_SOURCE_MAIN_LOCAL_NO_AUDIT_CREDIT"
LEG_MANIFEST_SHA = "5d939d13644c2610198d8c15c75a8879a553d35b2e17f9f7730a8435f3127731"
LEG_RECEIPT_SHA = "1f445ea96df4f5cbb9505a575be25e779470368b44747bcd46ee0889f3fb7584"
LEG_DB_SHA = "89045558b86513fefa5791bf5ad4749279962758d05099139ae576f0025a7cd2"
LEG_BRANCHES = ("LEG-CLEAN", "LEG-MESSY")
LEG_COUNTS = (50, 50)
LEG_SYSTEMS = 6


def _v8_review(private: Path) -> tuple:
    """Pin the whole reviewed V8 report/candidate prefix, not just its totals."""
    root = private / BASE / V8_FOLDER
    review = root / "independent-review-main-v1/REVIEW.json"
    report = root / "main-run-v1/REPORT.json"
    candidate_root = root / "main-candidate-v1"
    files = {name: candidate_root / name for name in V8_CANDIDATE_SHA}
    for directory in (root, review.parent, report.parent, candidate_root):
        _private(directory, directory=True)
    before = {
        "review": _pin(review, V8_REVIEW_SHA),
        "report": _pin(report, V8_REPORT_SHA),
        **{name: _pin(path, V8_CANDIDATE_SHA[name]) for name, path in files.items()},
    }
    row = _read_json(review)
    report_row = _read_json(report)
    candidate_rows = {name: _read_json(path) for name, path in files.items()}
    if (
        row.get("verdict") != "PASS_PARTIAL_READ_ONLY_CANDIDATE_REGISTRY_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or row.get("main_output_sha256")
        != {
            "portfolio": V8_REPORT_SHA,
            "candidate_A": V8_CANDIDATE_SHA["A.json"],
            "candidate_B": V8_CANDIDATE_SHA["B.json"],
            "candidate_report": V8_CANDIDATE_SHA["REPORT.json"],
        }
        or row.get("checks", {}).get("tracked_code_or_p1_mutated_by_review") is not False
        or report_row.get("source_complete") is not False
        or report_row.get("audit_task_credit") is not False
        or candidate_rows["REPORT.json"].get("source_complete") is not False
        or candidate_rows["REPORT.json"].get("audit_task_credit") is not False
    ):
        raise PortfolioVerificationError("Reviewed V8 main report/candidate boundary differs")
    paths = {"review": review, "report": report, **files}
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("Reviewed V8 main files changed during read")
    return report_row, candidate_rows, before


def _leg_source(repository: Path, private: Path) -> dict:
    """Select only an independently reviewed and fully reverified LEG001 run."""
    if LEG_REVIEW_SHA == "PENDING_INDEPENDENT_MAIN_REVIEW":
        raise PortfolioVerificationError("LEG001 independent main review not yet pinned")
    folder = private / BASE / LEG_FOLDER
    run = folder / LEG_RUN
    review = folder / LEG_REVIEW
    paths = {
        "review": review,
        "manifest": run / "MANIFEST.json",
        "receipt": run / "RECEIPT.json",
        "database": run / "company.sqlite3",
    }
    for directory in (folder, run, review.parent):
        _private(directory, directory=True)
    expected = {
        "review": LEG_REVIEW_SHA,
        "manifest": LEG_MANIFEST_SHA,
        "receipt": LEG_RECEIPT_SHA,
        "database": LEG_DB_SHA,
    }
    before = {name: _pin(path, expected[name]) for name, path in paths.items()}
    review_row = _read_json(review)
    manifest = _read_json(paths["manifest"])
    receipt = _read_json(paths["receipt"])
    if (
        review_row.get("verdict") != LEG_REVIEW_VERDICT
        or review_row.get("main_run_sha256")
        != {
            "MANIFEST.json": LEG_MANIFEST_SHA,
            "RECEIPT.json": LEG_RECEIPT_SHA,
            "company.sqlite3": LEG_DB_SHA,
        }
        or review_row.get("audit_task_credit") is not False
        or review_row.get("actual_phi") is not False
        or review_row.get("outside_message_sent") is not False
        or review_row.get("real_hipaa_applicability") != "UNDETERMINED"
        or review_row.get("checks", {}).get("tracked_source_or_p1_mutated_by_review") is not False
    ):
        raise PortfolioVerificationError("LEG001 independent review/source join differs")
    if (
        receipt.get("branches") != dict(zip(("CLEAN", "MESSY"), LEG_BRANCHES, strict=True))
        or receipt.get("company") != "SABLE-HARBOR-REFERENCE"
        or receipt.get("selected_term_occurrences_per_branch") != 34
        or receipt.get("unsupported_authored_routes_per_side") != 66
        or receipt.get("selected_scope_complete") != {"CLEAN": True, "MESSY": False}
        or len(receipt.get("selected_source_refs", {}).get("CLEAN", {})) != 5
        or len(receipt.get("selected_source_refs", {}).get("MESSY", {})) != 5
        or len(receipt.get("records", {}).get("CLEAN", [])) != 50
        or len(receipt.get("records", {}).get("MESSY", [])) != 50
        or set(receipt.get("source_exception_refs", {}).get("MESSY", {}))
        != {"ba_flowdown", "provider_support_initial", "provider_support_current"}
        or receipt.get("real_hipaa_applicability") != "UNDETERMINED"
        or any(
            receipt.get(key) is not False
            for key in (
                "actual_phi",
                "outside_message_sent",
                "source_complete",
                "audit_task_credit",
            )
        )
        or manifest.get("receipt_sha256") != LEG_RECEIPT_SHA
        or manifest.get("company_db_sha256") != LEG_DB_SHA
        or manifest.get("native_version_count") != 100
        or manifest.get("audit_task_credit") is not False
    ):
        raise PortfolioVerificationError("LEG001 native claim/manifest boundary differs")
    if leg001.verify(run, repository=repository, private_repository=private) != receipt:
        raise PortfolioVerificationError("LEG001 own source verifier differs")
    native, systems, journals = _frozen_rows(paths["database"])
    if (
        sorted(native)
        != sorted(
            ("SABLE-HARBOR-REFERENCE", branch, count)
            for branch, count in zip(LEG_BRANCHES, LEG_COUNTS, strict=True)
        )
        or sorted(systems)
        != sorted(("SABLE-HARBOR-REFERENCE", branch, LEG_SYSTEMS) for branch in LEG_BRANCHES)
        or any(journals.values())
    ):
        raise PortfolioVerificationError("LEG001 physical branches/journals differ")
    _no_sidecars(paths["database"])
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("LEG001 source changed during read")
    return {
        "source": "leg001docket",
        "run": f"{LEG_FOLDER}/{LEG_RUN}",
        "review_sha256": LEG_REVIEW_SHA,
        "manifest_sha256": LEG_MANIFEST_SHA,
        "receipt_sha256": LEG_RECEIPT_SHA,
        "database_sha256": {"native": LEG_DB_SHA},
        "native_versions": 100,
        "branch_versions": dict(zip(LEG_BRANCHES, LEG_COUNTS, strict=True)),
        "physical_company_ids": ["SABLE-HARBOR-REFERENCE"],
        "ledger_system_counts": {"native": LEG_SYSTEMS},
        "inherited_audit_journals": {table: 0 for table in JOURNALS},
        "selected_term_occurrences_per_branch": 34,
        "unsupported_authored_routes_per_side": 66,
        "real_hipaa_applicability": "UNDETERMINED",
        "messy_historical_exceptions_open": True,
        "audit_task_credit": False,
    }


def verify_all(repository: Path, *, private_repository: Path | None = None) -> dict:
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository or repository).resolve(strict=True)
    reviewed = _v8_review(private)
    previous = prior.verify_all(repository, private_repository=private)
    if previous != reviewed[0]:
        raise PortfolioVerificationError("Recomputed V8 source prefix differs from reviewed report")
    if (
        previous.get("source_count"),
        previous.get("native_versions"),
        previous.get("source_component_count"),
        previous.get("source_complete"),
        previous.get("audit_task_credit"),
    ) != (29, 560, 30, False, False):
        raise PortfolioVerificationError("Reviewed V8 source count/claim boundary differs")
    sources = [*previous["sources"], _leg_source(repository, private)]
    if len(sources) != 30 or sum(row["native_versions"] for row in sources) != 660:
        raise PortfolioVerificationError("V9 selected LEG001 docket roster differs")
    if _v8_review(private) != reviewed:
        raise PortfolioVerificationError("Reviewed V8 source/candidate prefix changed")
    return {
        "schema": SCHEMA,
        "status": "PARTIAL_REVIEWED_NATIVE_SOURCES_NOT_AUDIT_READY",
        "as_of": "2026-09-30",
        "verifier_module_sha256": _digest(Path(__file__)),
        "v8_verifier_sha256": previous["verifier_module_sha256"],
        "v8_review_sha256": V8_REVIEW_SHA,
        "source_count": 30,
        "native_versions": 660,
        "source_component_count": 31,
        "sources": sources,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": [
            "Thirty selected fictional cohorts, not an enterprise evidence population.",
            "LEG001 is one synthetic chain and selected 34-term counsel docket per side.",
            "Real HIPAA/contract applicability remains undecided; 2027 law is not verified.",
            "Messy BA flowdown and provider support-omission histories remain OPEN.",
            "Sixty-six authored LEG001 routes per side remain unsupported and unaudited.",
            "REC003 inherited audit journals are excluded from business versions.",
            "No actual 2027 operation, source-complete, grant, collection, task or grade claim.",
        ],
    }


def write_report(repository: Path, private_repository: Path, destination: Path) -> dict:
    report = verify_all(repository, private_repository=private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise PortfolioVerificationError("Fresh V9 report destination required")
    _private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".portfolio-v9-", dir=destination.parent) as name:
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
        raise PortfolioVerificationError("Exact one-file V9 report required")
    path = root / "REPORT.json"
    before = _pin(path, _digest(path))
    actual = _read_json(path)
    expected = verify_all(repository, private_repository=private_repository)
    if actual != expected or _identity(path) != before:
        raise PortfolioVerificationError("V9 portfolio report differs")
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
