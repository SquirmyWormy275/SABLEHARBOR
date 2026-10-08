"""Read-only partial V10 roster adding the reviewed prospective addressable docket."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from . import company_addressable_docket_exercise as addressable
from . import fictional_2027_source_portfolio_v9 as prior
from .fictional_2027_source_portfolio import BASE, PortfolioVerificationError, _digest, _identity
from .fictional_2027_source_portfolio_v4 import (
    JOURNALS,
    _frozen_rows,
    _no_sidecars,
    _pin,
    _private,
    _read_json,
)

SCHEMA = "SH_FICTIONAL_2027_REVIEWED_SOURCE_PORTFOLIO_DIAGNOSTIC_V10"
V9_FOLDER = "company-source-portfolio-v9-2026-09-30"
V9_REVIEW_SHA = "50a5c6a881bdb703fb5e00b7bf24a5515c713827b8f09eb6c423b81d0649028e"
V9_REPORT_SHA = "f382fdbbc1eaae8f41ecfa573d3ef4b856e93e10b65a173019ef37de53ad0ed5"
V9_CANDIDATE_SHA = {
    "A.json": "893986851b49d1dde951285e23dba663cc88f22bfe967ae9db330c1ab385c722",
    "B.json": "fcf91a7cc14b5299ce2fb7717e0c2f7d05e457236bf58b2084709d9f5b720f28",
    "REPORT.json": "b63615600ad5164bea763eb7d25ff2ab119a0a48241b2e0612d70844aca30644",
}
ADDR_FOLDER = "company-addressable-docket-2026-09-29"
ADDR_RUN = "run-v1"
ADDR_REVIEW_FOLDER = "company-addressable-docket-independent-review-2026-09-29-v1"
ADDR_REVIEW_SHA = "5796cf3bee5075defb743401dad3831448cb5687c7f06d5df9dcba3021143c7d"
ADDR_REVIEW_VERDICT = "PASS_PROSPECTIVE_PENDING_DOCKET_ONLY"
ADDR_CHECKS_SHA = "f643519220d10c8cf44a24893af1888e5e2a7a899dacf12068d318321dc794f5"
ADDR_HANDOFF_SHA = "3a41ce41b307be313bb4bd2f92558703a36941b664e74747013bc07ab4c4f010"
ADDR_MANIFEST_SHA = "41f3b1c783c3c84217f86edd03febad42da00a25e22fcc38c41e6bf61aa910e1"
ADDR_RECEIPT_SHA = "7ef4cb845b14259acd7ecfb015ff8d0626c3b0a4a9a3052b485764f6a164e0f0"
ADDR_DB_SHA = "50d9fe4f9a49c72b72537a8a3d7a5dbf0b9eb3e3171d8072ffd63748bc750305"
ADDR_MODULE_SHA = "05cb35d247c5efc5b1dc93f4ed03cfa69ba373a40ef292a640c2bcb34f468a5b"
ADDR_BRANCHES = ("ADDR-CLEAN", "ADDR-MESSY")
ADDR_COUNTS = (24, 26)
ADDR_SYSTEMS = 2


def _v9_review(private: Path) -> tuple:
    """Pin the whole reviewed V9 report/candidate prefix, including every route."""
    root = private / BASE / V9_FOLDER
    review = root / "independent-review-main-v1/REVIEW.json"
    report = root / "main-run-v1/REPORT.json"
    candidate_root = root / "main-candidate-v1"
    files = {name: candidate_root / name for name in V9_CANDIDATE_SHA}
    for directory in (root, review.parent, report.parent, candidate_root):
        _private(directory, directory=True)
    before = {
        "review": _pin(review, V9_REVIEW_SHA),
        "report": _pin(report, V9_REPORT_SHA),
        **{name: _pin(path, V9_CANDIDATE_SHA[name]) for name, path in files.items()},
    }
    row = _read_json(review)
    report_row = _read_json(report)
    candidate_rows = {name: _read_json(path) for name, path in files.items()}
    if (
        row.get("verdict") != "PASS_PARTIAL_READ_ONLY_CANDIDATE_REGISTRY_MAIN_LOCAL_NO_AUDIT_CREDIT"
        or row.get("main_output_sha256")
        != {
            "portfolio_report": V9_REPORT_SHA,
            "candidate_A": V9_CANDIDATE_SHA["A.json"],
            "candidate_B": V9_CANDIDATE_SHA["B.json"],
            "candidate_report": V9_CANDIDATE_SHA["REPORT.json"],
        }
        or row.get("checks", {}).get("main_or_atlas_tracked_written_by_review") is not False
        or report_row.get("source_complete") is not False
        or report_row.get("audit_task_credit") is not False
        or candidate_rows["REPORT.json"].get("source_complete") is not False
        or candidate_rows["REPORT.json"].get("audit_task_credit") is not False
    ):
        raise PortfolioVerificationError("Reviewed V9 main report/candidate boundary differs")
    paths = {"review": review, "report": report, **files}
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("Reviewed V9 main files changed during read")
    return report_row, candidate_rows, before


def _addressable_source(repository: Path, private: Path) -> dict:
    """Select only the independently reviewed pending docket, with no decision credit."""
    root = private / BASE
    folder = root / ADDR_FOLDER
    run = folder / ADDR_RUN
    review_folder = root / ADDR_REVIEW_FOLDER
    paths = {
        "review": review_folder / "REVIEW.json",
        "checks": review_folder / "CHECKS.json",
        "handoff": folder / "HANDOFF-V2.json",
        "manifest": run / "MANIFEST.json",
        "receipt": run / "RECEIPT.json",
        "database": run / "company.sqlite3",
    }
    for directory in (folder, run, review_folder):
        _private(directory, directory=True)
    expected = {
        "review": ADDR_REVIEW_SHA,
        "checks": ADDR_CHECKS_SHA,
        "handoff": ADDR_HANDOFF_SHA,
        "manifest": ADDR_MANIFEST_SHA,
        "receipt": ADDR_RECEIPT_SHA,
        "database": ADDR_DB_SHA,
    }
    before = {name: _pin(path, expected[name]) for name, path in paths.items()}
    review = _read_json(paths["review"])
    handoff = _read_json(paths["handoff"])
    manifest = _read_json(paths["manifest"])
    receipt = _read_json(paths["receipt"])
    if (
        review.get("verdict") != ADDR_REVIEW_VERDICT
        or review.get("reviewed_commit") != "80def7bbd8d567133ab989cb11165f30dd40e655"
        or review.get("handoff_v2_sha256") != ADDR_HANDOFF_SHA
        or review.get("checks_sha256") != ADDR_CHECKS_SHA
        or review.get("run_manifest_sha256") != ADDR_MANIFEST_SHA
        or review.get("run_receipt_sha256") != ADDR_RECEIPT_SHA
        or review.get("native_db_sha256") != ADDR_DB_SHA
        or handoff.get("module_sha256") != ADDR_MODULE_SHA
        or handoff.get("actual_hipaa_applicability") != "UNDETERMINED"
        or any(
            handoff.get(key) is not False
            for key in (
                "actual_hipaa_applicability_asserted",
                "approved_substitutions",
                "implemented_safeguard_claims",
                "audit_collection",
                "audit_task_credit",
            )
        )
    ):
        raise PortfolioVerificationError("Addressable independent review/handoff boundary differs")
    if (
        manifest.get("module_sha256") != ADDR_MODULE_SHA
        or _digest(repository / "enterprise/audit_suite/company_addressable_docket_exercise.py")
        != ADDR_MODULE_SHA
        or manifest.get("receipt_sha256") != ADDR_RECEIPT_SHA
        or manifest.get("company_db_sha256") != ADDR_DB_SHA
        or manifest.get("native_version_count") != 50
        or manifest.get("audit_task_credit") is not False
        or receipt.get("branches") != dict(zip(("CLEAN", "MESSY"), ADDR_BRANCHES, strict=True))
        or receipt.get("company") != "SABLE-HARBOR-REFERENCE"
        or receipt.get("qualification") != addressable.QUALIFICATION
        or receipt.get("source_locator_count") != 22
        or receipt.get("addressable_inventory_role")
        != "22_ITEM_SOURCE_LOCATOR_INVENTORY_NOT_DECISIONS"
        or receipt.get("hipaa_analysis_role")
        != "SEPARATE_SECTION_DESIGN_ANALYSIS_NOT_22_ITEM_REGISTER"
        or receipt.get("final_docket_counts") != {"CLEAN": 22, "MESSY": 22}
        or receipt.get("final_states") != {"CLEAN": "PENDING_REVIEW", "MESSY": "QUARANTINED"}
        or receipt.get("open_exception_counts") != {"CLEAN": 0, "MESSY": 1}
        or receipt.get("related_sh_pol003_gap") != "OPEN_INSUFFICIENT_SOURCE_UNCHANGED"
        or [len(receipt.get("records", {}).get(s, [])) for s in ("CLEAN", "MESSY")]
        != list(ADDR_COUNTS)
        or addressable.verify(run, repository=repository) != manifest
    ):
        raise PortfolioVerificationError("Addressable pending native claim/manifest differs")
    native, systems, journals = _frozen_rows(paths["database"])
    if (
        sorted(native)
        != sorted(
            ("SABLE-HARBOR-REFERENCE", branch, count)
            for branch, count in zip(ADDR_BRANCHES, ADDR_COUNTS, strict=True)
        )
        or sorted(systems)
        != sorted(("SABLE-HARBOR-REFERENCE", branch, ADDR_SYSTEMS) for branch in ADDR_BRANCHES)
        or any(journals.values())
    ):
        raise PortfolioVerificationError("Addressable physical branches/journals differ")
    _no_sidecars(paths["database"])
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("Addressable source changed during read")
    return {
        "source": "addressabledocket",
        "run": f"{ADDR_FOLDER}/{ADDR_RUN}",
        "review_sha256": ADDR_REVIEW_SHA,
        "manifest_sha256": ADDR_MANIFEST_SHA,
        "receipt_sha256": ADDR_RECEIPT_SHA,
        "database_sha256": {"native": ADDR_DB_SHA},
        "native_versions": 50,
        "branch_versions": dict(zip(ADDR_BRANCHES, ADDR_COUNTS, strict=True)),
        "physical_company_ids": ["SABLE-HARBOR-REFERENCE"],
        "ledger_system_counts": {"native": ADDR_SYSTEMS},
        "inherited_audit_journals": {table: 0 for table in JOURNALS},
        "pending_source_locators_per_side": 22,
        "clean_final_state": "PENDING_REVIEW",
        "messy_final_state": "QUARANTINED",
        "messy_historical_exception_open": True,
        "related_sh_pol003_gap": "OPEN_INSUFFICIENT_SOURCE_UNCHANGED",
        "actual_hipaa_applicability": "UNDETERMINED",
        "environmental_decisions": 0,
        "approved_substitutions": False,
        "implemented_safeguard_claims": False,
        "audit_task_credit": False,
    }


def verify_all(repository: Path, *, private_repository: Path | None = None) -> dict:
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository or repository).resolve(strict=True)
    reviewed = _v9_review(private)
    previous = prior.verify_all(repository, private_repository=private)
    if previous != reviewed[0]:
        raise PortfolioVerificationError("Recomputed V9 source prefix differs from reviewed report")
    if (
        previous.get("source_count"),
        previous.get("native_versions"),
        previous.get("source_component_count"),
        previous.get("source_complete"),
        previous.get("audit_task_credit"),
    ) != (30, 660, 31, False, False):
        raise PortfolioVerificationError("Reviewed V9 source count/claim boundary differs")
    sources = [*previous["sources"], _addressable_source(repository, private)]
    if len(sources) != 31 or sum(row["native_versions"] for row in sources) != 710:
        raise PortfolioVerificationError("V10 selected addressable roster differs")
    if _v9_review(private) != reviewed:
        raise PortfolioVerificationError("Reviewed V9 source/candidate prefix changed")
    return {
        "schema": SCHEMA,
        "status": "PARTIAL_REVIEWED_NATIVE_SOURCES_NOT_AUDIT_READY",
        "as_of": "2026-09-30",
        "verifier_module_sha256": _digest(Path(__file__)),
        "v9_verifier_sha256": previous["verifier_module_sha256"],
        "v9_review_sha256": V9_REVIEW_SHA,
        "source_count": 31,
        "native_versions": 710,
        "source_component_count": 32,
        "sources": sources,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": [
            "Thirty-one selected fictional cohorts, not an enterprise evidence population.",
            "Addressable docket has 22 pending source-locator cases per side, not 22 decisions.",
            "No actual HIPAA applicability, ePHI environment, addressable choice, approved "
            "substitution, implemented safeguard or legal opinion is established.",
            "Messy omission was backfilled, but the blanket-waiver exception remains OPEN; "
            "SH-POL-003 generic gap remains OPEN/INSUFFICIENT_SOURCE.",
            "2027 events are authored prospective times; imported_at records 2026 insertion.",
            "REC003 inherited audit journals are excluded from business versions.",
            "No source-complete population, fresh pair, grant, collection, task or grade claim.",
        ],
    }


def write_report(repository: Path, private_repository: Path, destination: Path) -> dict:
    report = verify_all(repository, private_repository=private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise PortfolioVerificationError("Fresh V10 report destination required")
    _private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".portfolio-v10-", dir=destination.parent) as name:
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
        raise PortfolioVerificationError("Exact one-file V10 report required")
    path = root / "REPORT.json"
    before = _pin(path, _digest(path))
    actual = _read_json(path)
    expected = verify_all(repository, private_repository=private_repository)
    if actual != expected or _identity(path) != before:
        raise PortfolioVerificationError("V10 portfolio report differs")
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
