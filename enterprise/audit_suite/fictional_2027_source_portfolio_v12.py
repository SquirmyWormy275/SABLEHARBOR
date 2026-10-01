"""Bounded V12 roster pinned to the reviewed main SEC001 source."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from . import company_sec001_selected_transfer as transfer
from . import fictional_2027_source_portfolio_v11 as prior
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

SCHEMA = "SH_FICTIONAL_2027_REVIEWED_SOURCE_PORTFOLIO_DIAGNOSTIC_V12"
V11_FOLDER = "company-source-portfolio-v11-2026-09-30"
V11_REVIEW_SHA = "559cbd325ce84e736417576ece134c4f0959d849bd775af0761ad5bd6881b615"
V11_REPORT_SHA = "9011ff5ca02a41cd966179097b1663a1519ac4f91c446ae1b0bd3f6716cc59bf"
V11_CANDIDATE_SHA = {
    "A.json": "43a86507b5d62d5e7348e7245426f8132b7eb6f5aea65e07511864baef3e6331",
    "B.json": "3f244b4b92f33740c6677b7a7166aab1aaef74067b3a4e90f741a5d8651aecc1",
    "REPORT.json": "31dcabc95d102b3f9bdcd4f698c98e976d97eb9d1ae47948828825742dd5ae56",
}
SEC_FOLDER = "company-sec001-selected-transfer-2027-09-30"
SEC_RUN = "main-run-v1"
# Accepted main-local SEC001 source and independent review. Isolated source
# hashes deliberately do not qualify the V12 registry.
SEC_REVIEW_SHA = "9cf4d438d7b191f227f87f3dcb5cf6d36bcb3e7e490415d16cff11e72a33c196"
SEC_REVIEW_VERDICT = "PASS_SELECTED_SYNTHETIC_SEC001_TRANSFER_SOURCE_MAIN_LOCAL_NO_AUDIT_CREDIT"
SEC_INTEGRATION_COMMIT = "b286bbb9acef0c64e56b5170349546e74485f7b1"
SEC_MANIFEST_SHA = "d653285e748e7529557749445c0a3646b049237a1ff9888fed835f53fd185942"
SEC_RECEIPT_SHA = "73fa3ff1cb40f9e0e8196cd01bf18048c408427e0d10ade9003fd60d9c984d28"
SEC_DB_SHA = "3841366d17e3f072ef2ae303ec3bf010ab644e474a778d59f62263c6a8c86e7d"
SEC_MODULE_SHA = "430fa83ed5c3ac457132c4b10e02571e3921a21b70461e85cf6f2524bc73a7f2"
SEC_BRANCHES = ("SEC001-XFER-CLEAN", "SEC001-XFER-MESSY")
SEC_COUNTS = (10, 16)
SEC_SYSTEMS = 5
SEC_CLAUSE = (
    "Trace a transfer to purpose, recipient authorization, channel/endpoint protection "
    "and handling after receipt; transport encryption alone does not authorize the transfer."
)
P1_FREEZE = {
    "file_count": 538,
    "inventory_sha256": "f266ef682b502b3b093170f8a7b64fcf5cbab722d5c8ddf6715a63c0e535360f",
}


def _require_sec_pins() -> None:
    """Reject builds unless the accepted main source and PASS review are pinned."""
    hashes = (SEC_REVIEW_SHA, SEC_MANIFEST_SHA, SEC_RECEIPT_SHA, SEC_DB_SHA, SEC_MODULE_SHA)
    if (
        any(
            not isinstance(value, str)
            or len(value) != 64
            or any(char not in "0123456789abcdef" for char in value)
            or value == "0" * 64
            for value in hashes
        )
        or not isinstance(SEC_REVIEW_VERDICT, str)
        or not SEC_REVIEW_VERDICT.startswith("PASS_")
        or not isinstance(SEC_INTEGRATION_COMMIT, str)
        or len(SEC_INTEGRATION_COMMIT) != 40
        or any(char not in "0123456789abcdef" for char in SEC_INTEGRATION_COMMIT)
    ):
        raise PortfolioVerificationError("SEC001 accepted main source/review pins pending")


def _v11_review(private: Path) -> tuple:
    """Pin the full reviewed V11 report and exact candidate profiles."""
    root = private / BASE / V11_FOLDER
    review = root / "independent-review-main-v1/REVIEW.json"
    report = root / "main-run-v1/REPORT.json"
    candidates = root / "main-candidate-v1"
    files = {name: candidates / name for name in V11_CANDIDATE_SHA}
    for directory in (root, review.parent, report.parent, candidates):
        _private(directory, directory=True)
    paths = {"review": review, "report": report, **files}
    before = {
        "review": _pin(review, V11_REVIEW_SHA),
        "report": _pin(report, V11_REPORT_SHA),
        **{name: _pin(path, V11_CANDIDATE_SHA[name]) for name, path in files.items()},
    }
    row = _read_json(review)
    report_row = _read_json(report)
    candidate_rows = {name: _read_json(path) for name, path in files.items()}
    if (
        row.get("verdict") != "PASS_PARTIAL_ETH001_PORTFOLIO_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or row.get("integration_commit") != "6926e5a9d17a8e22cae41d3ca58cc9d03de6c404"
        or row.get("isolated_independent_review_sha256")
        != "69d09c57a04609f84dba52537936b600df96925277d5233af0a43bd9e3686e30"
        or row.get("p1_freeze") != P1_FREEZE
        or row.get("main_output_sha256")
        != {
            "portfolio_report": V11_REPORT_SHA,
            "candidate_A": V11_CANDIDATE_SHA["A.json"],
            "candidate_B": V11_CANDIDATE_SHA["B.json"],
            "candidate_report": V11_CANDIDATE_SHA["REPORT.json"],
        }
        or row.get("checks", {}).get("main_or_atlas_tracked_written_by_review") is not False
        or row.get("source_complete") is not False
        or row.get("audit_task_credit") is not False
        or report_row.get("source_complete") is not False
        or report_row.get("audit_task_credit") is not False
        or candidate_rows["REPORT.json"].get("source_complete") is not False
        or candidate_rows["REPORT.json"].get("audit_task_credit") is not False
    ):
        raise PortfolioVerificationError("Reviewed V11 main report/candidate boundary differs")
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("Reviewed V11 main files changed during read")
    return report_row, candidate_rows, before


def _sec_source(repository: Path, private: Path) -> dict:
    """Require the accepted main review, source originals and 26 native rows."""
    _require_sec_pins()
    module = repository / "enterprise/audit_suite/company_sec001_selected_transfer.py"
    if not module.is_file() or _digest(module) != SEC_MODULE_SHA:
        raise PortfolioVerificationError("SEC001 integrated source module differs")
    folder = private / BASE / SEC_FOLDER
    run = folder / SEC_RUN
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
        "review": SEC_REVIEW_SHA,
        "manifest": SEC_MANIFEST_SHA,
        "receipt": SEC_RECEIPT_SHA,
        "database": SEC_DB_SHA,
    }
    before = {name: _pin(path, expected[name]) for name, path in paths.items()}
    review = _read_json(paths["review"])
    manifest = _read_json(paths["manifest"])
    receipt = _read_json(paths["receipt"])
    if (
        review.get("verdict") != SEC_REVIEW_VERDICT
        or review.get("integration_commit") != SEC_INTEGRATION_COMMIT
        or review.get("main_run_sha256")
        != {
            "RUN-MANIFEST.json": SEC_MANIFEST_SHA,
            "SOURCE_RECEIPT.json": SEC_RECEIPT_SHA,
            "company.sqlite3": SEC_DB_SHA,
        }
        or review.get("tracked_sha256", {}).get(
            "enterprise/audit_suite/company_sec001_selected_transfer.py"
        )
        != SEC_MODULE_SHA
        or review.get("p1_freeze") != P1_FREEZE
        or review.get("selected_authored_clause") != SEC_CLAUSE
        or review.get("selected_task_id") != "TASK-SH-SEC-001-corporate-CHECK-SOC2:CC6.7"
        or review.get("main_or_atlas_tracked_written_by_review") is not False
        or review.get("active_pair_mutated") is not False
        or review.get("source_complete") is not False
        or review.get("audit_task_credit") is not False
    ):
        raise PortfolioVerificationError("SEC001 independently reviewed main source differs")
    if (
        manifest.get("module_sha256") != SEC_MODULE_SHA
        or manifest.get("native_count") != 26
        or manifest.get("source_receipt_sha256") != SEC_RECEIPT_SHA
        or manifest.get("native_db_sha256") != SEC_DB_SHA
        or receipt.get("branch_ids") != dict(zip(("CLEAN", "MESSY"), SEC_BRANCHES, strict=True))
        or receipt.get("branch_counts") != {"CLEAN": 10, "MESSY": 16}
        or receipt.get("native_count") != 26
        or receipt.get("selected_payload_count") != 1
        or receipt.get("control_id") != "SH-SEC-001"
        or receipt.get("selected_authored_clause") != SEC_CLAUSE
        or receipt.get("actor_authority")
        != "CANON_LISTED_FICTIONAL_APPOINTMENTS_PENDING_ACCEPTANCE"
        or receipt.get("messy_blocked_wrong_endpoint") is not True
        or receipt.get("messy_false_close_corrected") is not True
        or receipt.get("messy_historical_exception_open") is not True
        or any(
            receipt.get(key) is not False
            for key in (
                "actual_customer_or_phi_data",
                "actual_deployed_endpoint_or_channel",
                "actual_network_transmission",
                "enterprise_transfer_standard_approved",
                "independent_approval",
                "population_complete",
                "source_complete",
                "audit_task_credit",
                "active_P1_mutated",
            )
        )
        or any(
            row.get("classification") != "UNSUPPORTED_EXACT_CLAUSE"
            or row.get("current_status") != "NOT_STARTED"
            or row.get("current_conclusion") != "NOT_RUN"
            or row.get("authored_test_clause") != SEC_CLAUSE
            or row.get("audit_task_credit") is not False
            for row in receipt.get("route_disposition", {}).values()
        )
        or set(receipt.get("route_disposition", {})) != {"A", "B"}
    ):
        raise PortfolioVerificationError("SEC001 selected-transfer receipt boundary differs")
    if (
        receipt.get("schema") != transfer.SCHEMA
        or transfer.verify(run, repository=repository, private_repository=private) != receipt
    ):
        raise PortfolioVerificationError("SEC001 native source verifier differs")
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
        raise PortfolioVerificationError("SEC001 physical branches or journals differ")
    _no_sidecars(paths["database"])
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("SEC001 source changed during read")
    return {
        "source": "sec001transfer",
        "run": f"{SEC_FOLDER}/{SEC_RUN}",
        "review_sha256": SEC_REVIEW_SHA,
        "manifest_sha256": SEC_MANIFEST_SHA,
        "receipt_sha256": SEC_RECEIPT_SHA,
        "database_sha256": {"native": SEC_DB_SHA},
        "native_versions": 26,
        "branch_versions": dict(zip(SEC_BRANCHES, SEC_COUNTS, strict=True)),
        "physical_company_ids": ["SABLE-HARBOR-REFERENCE"],
        "ledger_system_counts": {"native": SEC_SYSTEMS},
        "inherited_audit_journals": {table: 0 for table in JOURNALS},
        "selected_payload_count": 1,
        "selected_authored_clause": SEC_CLAUSE,
        "messy_blocked_wrong_endpoint": True,
        "messy_false_close_corrected": True,
        "messy_historical_exception_open": True,
        "actual_customer_or_phi_data": False,
        "actual_deployed_endpoint_or_channel": False,
        "actual_network_transmission": False,
        "enterprise_transfer_standard_approved": False,
        "independent_approval": False,
        "population_complete": False,
        "audit_task_credit": False,
    }


def verify_all(repository: Path, *, private_repository: Path | None = None) -> dict:
    _require_sec_pins()
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository or repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise PortfolioVerificationError("Frozen P1 inventory differs")
    reviewed = _v11_review(private)
    previous = prior.verify_all(repository, private_repository=private)
    if previous != reviewed[0]:
        raise PortfolioVerificationError(
            "Recomputed V11 source prefix differs from reviewed report"
        )
    source = _sec_source(repository, private)
    if _v11_review(private) != reviewed or _p1_inventory(private) != freeze:
        raise PortfolioVerificationError("Reviewed V11 prefix or P1 changed during source read")
    return _compose_portfolio(previous, source)


def _compose_portfolio(previous: dict, source: dict) -> dict:
    """Shape the bounded successor only after its caller has qualified both inputs."""
    if (
        previous.get("source_count"),
        previous.get("native_versions"),
        previous.get("source_component_count"),
        previous.get("source_complete"),
        previous.get("fresh_audit_pair_created"),
        previous.get("audit_task_credit"),
    ) != (32, 729, 33, False, False, False) or len(previous.get("sources", [])) != 32:
        raise PortfolioVerificationError("Reviewed V11 source count/claim boundary differs")
    if (
        source.get("source") != "sec001transfer"
        or source.get("native_versions") != 26
        or source.get("branch_versions") != dict(zip(SEC_BRANCHES, SEC_COUNTS, strict=True))
        or source.get("ledger_system_counts") != {"native": SEC_SYSTEMS}
        or source.get("inherited_audit_journals") != {table: 0 for table in JOURNALS}
        or source.get("selected_payload_count") != 1
        or source.get("messy_historical_exception_open") is not True
        or source.get("actual_network_transmission") is not False
        or source.get("population_complete") is not False
        or source.get("audit_task_credit") is not False
    ):
        raise PortfolioVerificationError("SEC001 selected source scope differs")
    sources = [*previous["sources"], source]
    if len(sources) != 33 or sum(row["native_versions"] for row in sources) != 755:
        raise PortfolioVerificationError("V12 selected-transfer roster differs")
    return {
        "schema": SCHEMA,
        "status": "PARTIAL_REVIEWED_NATIVE_SOURCES_NOT_AUDIT_READY",
        "as_of": "2026-09-30",
        "verifier_module_sha256": _digest(Path(__file__)),
        "v11_verifier_sha256": previous["verifier_module_sha256"],
        "v11_review_sha256": V11_REVIEW_SHA,
        "source_count": 33,
        "native_versions": 755,
        "source_component_count": 34,
        "sources": sources,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": [
            "Thirty-three selected fictional cohorts, not an enterprise evidence population.",
            "SEC001 adds one synthetic non-PHI transfer custody fixture per branch, not an "
            "actual transmission, deployed channel, endpoint or enterprise transfer standard.",
            "Messy blocked wrong-endpoint attempt, false completion correction and open "
            "historical exception remain visible.",
            "The exact SH-SEC-001 authored clause remains unsupported and the P1 task unrun.",
            "2027 events are authored prospective times; imported_at records 2026 insertion.",
            "REC003 inherited audit journals are excluded from business versions.",
            "No source-complete population, fresh pair, grant, collection, task, Key or grade.",
        ],
    }


def write_report(repository: Path, private_repository: Path, destination: Path) -> dict:
    report = verify_all(repository, private_repository=private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise PortfolioVerificationError("Fresh V12 report destination required")
    _private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".portfolio-v12-", dir=destination.parent) as name:
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
        raise PortfolioVerificationError("Exact one-file V12 report required")
    path = root / "REPORT.json"
    before = _pin(path, _digest(path))
    actual = _read_json(path)
    expected = verify_all(repository, private_repository=private_repository)
    if actual != expected or _identity(path) != before:
        raise PortfolioVerificationError("V12 portfolio report differs")
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
