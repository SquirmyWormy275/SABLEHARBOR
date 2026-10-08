"""V15 partial roster adding one reviewed, payload-free emergency replay cohort."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from . import company_emergency_replay_2027 as replay
from . import fictional_2027_source_portfolio_v14 as prior
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

SCHEMA = "SH_FICTIONAL_2027_REVIEWED_SOURCE_PORTFOLIO_DIAGNOSTIC_V15"
V14_FOLDER = "company-source-portfolio-v14-2026-09-30"
V14_REVIEW_SHA = "30e152904322fa7e9d592087e58bf6e18f5555f4500f189cd3a7cc1988ba2fe4"
V14_REPORT_SHA = "73e5ad484017f87ec55d83acd61587cb8e656bb1bf92144da0d537ac6cc73853"
V14_CANDIDATE_SHA = {
    "A.json": "aa58f7f2291498aca3b97d017a0be20f432a90d11e1ecd5c433fb76bd4e38233",
    "B.json": "ce0759f9fab3ae0442865def6d9b53df627975d88496d7c3589cd9c062ed6c50",
    "REPORT.json": "d427131376aa8c43c051808410d856f35d0cb29ca8c001fd47efb12a3892d982",
}
REPLAY_FOLDER = "company-emergency-replay-2026-09-30"
REPLAY_RUN = "main-run-v1"
REPLAY_REVIEW_SHA = "2fd0f0d2f72f592c929dc1ae01d1c895a1c90cbdd6ebca776813f796cf4b0a36"
REPLAY_MANIFEST_SHA = "8552fbfe0ebd8487b7bda55e9577cf11b2f45bfa2835d6459cf3265aa3b3455b"
REPLAY_RECEIPT_SHA = "ffe8ee5f874a2581e9502c1b9cca9992fbf4602437ecede9005b50d098762e9c"
REPLAY_DB_SHA = "39dc7d18f22d064a007b42a3ce1f33391cb34aea226eaac9604915e8a73c259b"
REPLAY_MODULE_SHA = "991e10163322cff32ebe957b5d0b5101e1a9079925393d9c6a7b78a353a5deb9"
REPLAY_BRANCHES = tuple(replay.BRANCHES.values())
REPLAY_COUNTS = (8, 15)
REPLAY_SYSTEMS = 9
P1_FREEZE = prior.P1_FREEZE


def _v14_review(private: Path) -> tuple:
    """Pin the complete accepted V14 report and candidate before extension."""
    root = private / BASE / V14_FOLDER
    review = root / "independent-review-main-v1/REVIEW.json"
    report = root / "main-run-v1/REPORT.json"
    candidates = root / "main-candidate-v1"
    files = {name: candidates / name for name in V14_CANDIDATE_SHA}
    for directory in (root, review.parent, report.parent, candidates):
        _private(directory, directory=True)
    paths = {"review": review, "report": report, **files}
    before = {
        "review": _pin(review, V14_REVIEW_SHA),
        "report": _pin(report, V14_REPORT_SHA),
        **{name: _pin(path, V14_CANDIDATE_SHA[name]) for name, path in files.items()},
    }
    reviewed = _read_json(review)
    source_report = _read_json(report)
    candidate_rows = {name: _read_json(path) for name, path in files.items()}
    if (
        reviewed.get("verdict") != "PASS_PARTIAL_POL004_PORTFOLIO_V14_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or reviewed.get("integration_commit") != "3073081a"
        or reviewed.get("main_output_sha256")
        != {
            "portfolio_report": V14_REPORT_SHA,
            "candidate_A": V14_CANDIDATE_SHA["A.json"],
            "candidate_B": V14_CANDIDATE_SHA["B.json"],
            "candidate_report": V14_CANDIDATE_SHA["REPORT.json"],
        }
        or reviewed.get("p1_freeze") != P1_FREEZE
        or any(
            reviewed.get(key) is not False
            for key in (
                "source_complete",
                "fresh_audit_pair_created",
                "audit_task_credit",
                "active_pair_mutated",
                "main_or_atlas_external_write",
            )
        )
        or (
            source_report.get("source_count"),
            source_report.get("native_versions"),
            source_report.get("source_component_count"),
        )
        != (35, 796, 36)
        or source_report.get("source_complete") is not False
        or source_report.get("audit_task_credit") is not False
        or candidate_rows["REPORT.json"].get("reviewed_native_versions") != 796
        or candidate_rows["REPORT.json"].get("source_complete") is not False
        or candidate_rows["REPORT.json"].get("audit_task_credit") is not False
    ):
        raise PortfolioVerificationError("Reviewed V14 report/candidate boundary differs")
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("Reviewed V14 files changed during read")
    return source_report, candidate_rows, before


def _replay_source(repository: Path, private: Path) -> dict:
    """Qualify the main-reviewed local replay while retaining every open gate."""
    module = repository / "enterprise/audit_suite/company_emergency_replay_2027.py"
    if not module.is_file() or _digest(module) != REPLAY_MODULE_SHA:
        raise PortfolioVerificationError("Emergency replay source module differs")
    folder = private / BASE / REPLAY_FOLDER
    run = folder / REPLAY_RUN
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
        "review": REPLAY_REVIEW_SHA,
        "manifest": REPLAY_MANIFEST_SHA,
        "receipt": REPLAY_RECEIPT_SHA,
        "database": REPLAY_DB_SHA,
    }
    before = {name: _pin(path, expected[name]) for name, path in paths.items()}
    review = _read_json(paths["review"])
    manifest = _read_json(paths["manifest"])
    receipt = _read_json(paths["receipt"])
    if (
        review.get("verdict") != "PASS_SELECTED_EMERGENCY_REPLAY_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or review.get("integration_commit") != "6fe6326c9f9a1ff65b124bb0cbad3b37d1618455"
        or review.get("main_run_sha256")
        != {
            "MANIFEST.json": REPLAY_MANIFEST_SHA,
            "RECEIPT.json": REPLAY_RECEIPT_SHA,
            "company.sqlite3": REPLAY_DB_SHA,
        }
        or review.get("main_tracked_sha256", {}).get(
            "enterprise/audit_suite/company_emergency_replay_2027.py"
        )
        != REPLAY_MODULE_SHA
        or review.get("native_version_counts") != {"CLEAN": 8, "MESSY": 15}
        or review.get("p1_freeze") != P1_FREEZE
        or any(
            review.get(key) is not False
            for key in (
                "active_pair_mutated",
                "audit_task_credit",
                "fresh_pair_eligible",
                "main_or_atlas_external_write",
                "source_complete",
            )
        )
        or manifest.get("module_sha256") != REPLAY_MODULE_SHA
        or manifest.get("receipt_sha256") != REPLAY_RECEIPT_SHA
        or manifest.get("db_sha256") != REPLAY_DB_SHA
        or manifest.get("native_version_count") != 23
        or manifest.get("audit_task_credit") is not False
        or receipt.get("schema") != replay.SCHEMA
        or receipt.get("branches") != replay.BRANCHES
        or receipt.get("native_version_counts") != {"CLEAN": 8, "MESSY": 15}
        or receipt.get("local_open_exception_counts") != {"CLEAN": 0, "MESSY": 1}
        or receipt.get("messy_upstream_gates_remain_open") is not True
        or receipt.get("selected_population_count") != 1
        or receipt.get("external_bytes_or_packets") != 0
        or any(
            receipt.get(key) is not False
            for key in (
                "actual_phi_processing",
                "deployed_recovery_proven",
                "source_complete",
                "audit_task_credit",
            )
        )
    ):
        raise PortfolioVerificationError("Emergency replay reviewed source boundary differs")
    if replay.verify(run, repository=repository, private_repository=private)[
        "native_version_counts"
    ] != {"CLEAN": 8, "MESSY": 15}:
        raise PortfolioVerificationError("Emergency replay native verifier differs")
    native, systems, journals = _frozen_rows(paths["database"])
    if (
        sorted(native)
        != sorted(
            (replay.COMPANY, branch, count)
            for branch, count in zip(REPLAY_BRANCHES, REPLAY_COUNTS, strict=True)
        )
        or sorted(systems)
        != sorted((replay.COMPANY, branch, REPLAY_SYSTEMS) for branch in REPLAY_BRANCHES)
        or any(journals.values())
    ):
        raise PortfolioVerificationError("Emergency replay physical rows or journals differ")
    _no_sidecars(paths["database"])
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("Emergency replay source changed during read")
    return {
        "source": "emergencyreplay",
        "run": f"{REPLAY_FOLDER}/{REPLAY_RUN}",
        "review_sha256": REPLAY_REVIEW_SHA,
        "manifest_sha256": REPLAY_MANIFEST_SHA,
        "receipt_sha256": REPLAY_RECEIPT_SHA,
        "database_sha256": {"native": REPLAY_DB_SHA},
        "native_versions": 23,
        "branch_versions": dict(zip(REPLAY_BRANCHES, REPLAY_COUNTS, strict=True)),
        "physical_company_ids": [replay.COMPANY],
        "ledger_system_counts": {"native": REPLAY_SYSTEMS},
        "inherited_audit_journals": {table: 0 for table in JOURNALS},
        "selected_population_count": 1,
        "local_open_exception_counts": {"CLEAN": 0, "MESSY": 1},
        "messy_upstream_gates_remain_open": True,
        "external_bytes_or_packets": 0,
        "actual_phi_processing": False,
        "deployed_recovery_proven": False,
        "source_complete": False,
        "audit_task_credit": False,
    }


def _compose_portfolio(previous: dict, source: dict) -> dict:
    if (
        previous.get("source_count"),
        previous.get("native_versions"),
        previous.get("source_component_count"),
        previous.get("source_complete"),
        previous.get("fresh_audit_pair_created"),
        previous.get("audit_task_credit"),
    ) != (35, 796, 36, False, False, False) or len(previous.get("sources", [])) != 35:
        raise PortfolioVerificationError("Reviewed V14 source boundary differs")
    if (
        source.get("source") != "emergencyreplay"
        or source.get("native_versions") != 23
        or source.get("branch_versions") != dict(zip(REPLAY_BRANCHES, REPLAY_COUNTS, strict=True))
        or source.get("ledger_system_counts") != {"native": REPLAY_SYSTEMS}
        or source.get("inherited_audit_journals") != {table: 0 for table in JOURNALS}
        or source.get("local_open_exception_counts") != {"CLEAN": 0, "MESSY": 1}
        or source.get("messy_upstream_gates_remain_open") is not True
        or any(
            source.get(key) is not False
            for key in (
                "actual_phi_processing",
                "deployed_recovery_proven",
                "source_complete",
                "audit_task_credit",
            )
        )
    ):
        raise PortfolioVerificationError("Emergency replay source scope differs")
    sources = [*previous["sources"], source]
    if len(sources) != 36 or sum(row["native_versions"] for row in sources) != 819:
        raise PortfolioVerificationError("V15 source roster differs")
    return {
        "schema": SCHEMA,
        "status": "PARTIAL_REVIEWED_NATIVE_SOURCES_NOT_AUDIT_READY",
        "as_of": "2026-09-30",
        "verifier_module_sha256": _digest(Path(__file__)),
        "v14_verifier_sha256": previous["verifier_module_sha256"],
        "v14_review_sha256": V14_REVIEW_SHA,
        "source_count": 36,
        "native_versions": 819,
        "source_component_count": 37,
        "sources": sources,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": [
            "Thirty-six selected fictional cohorts, not an enterprise evidence population.",
            "Emergency replay is one payload-free marker and Boise local path, "
            "not actual ePHI or deployed recovery.",
            "The Messy local exception and BA, BCM, IAM and SEC005 historical gates remain open.",
            "2027 events are authored future training history; no full-period procedure follows.",
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
    reviewed = _v14_review(private)
    previous = prior.verify_all(repository, private_repository=private)
    if previous != reviewed[0]:
        raise PortfolioVerificationError(
            "Recomputed V14 source prefix differs from reviewed report"
        )
    source = _replay_source(repository, private)
    if _v14_review(private) != reviewed or _p1_inventory(private) != freeze:
        raise PortfolioVerificationError("Reviewed V14 prefix or P1 changed during source read")
    return _compose_portfolio(previous, source)


def write_report(repository: Path, private_repository: Path, destination: Path) -> dict:
    report = verify_all(repository, private_repository=private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise PortfolioVerificationError("Fresh V15 report destination required")
    _private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".portfolio-v15-", dir=destination.parent) as name:
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
        raise PortfolioVerificationError("Exact one-file V15 report required")
    path = root / "REPORT.json"
    before = _pin(path, _digest(path))
    actual = _read_json(path)
    expected = verify_all(repository, private_repository=private_repository)
    if actual != expected or _identity(path) != before:
        raise PortfolioVerificationError("V15 portfolio report differs")
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
