"""V17 partial roster: reviewed ENG005 operation and GOV oversight sources."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from . import company_eng005_operating_2027 as eng
from . import company_gov_selected_oversight_2027 as gov
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
from .fictional_2027_source_portfolio_v16 import P1_FREEZE

SCHEMA = "SH_FICTIONAL_2027_REVIEWED_SOURCE_PORTFOLIO_DIAGNOSTIC_V17"
BASE = "enterprise/generated/audit-suite"
V16_FOLDER = "company-source-portfolio-v16-2026-10-01"
V16_REVIEW_SHA = "30923f186892af9f99d49acbd341fc5298ac8d95347d65499783590f226ede2c"
V16_REPORT_SHA = "e5e311f4bf38f2d94caf827e3bbe6b6e0e1f5dca25328f31f51b398a9dd39d67"
V16_CANDIDATE_SHA = {
    "A.json": "f8559bd7bca5af378506d65493e244a2be0a7814b427815c3006baa8c41fb527",
    "B.json": "71fc721a391ae2302a86e87bb4137d4b703fa9069b8515bd6c89cf868904e2ae",
    "REPORT.json": "88eb2b8efda6f9a98d8d0113092ef6c5c9f4b28e62a2673999956890fa43bb4f",
}
V16_ISOLATED_REVIEW_SHA = "921da0a73e097ebf257d6dec887d47fe78086ad48ee3265cfb5ccc71f9a9fcb8"
SOURCES = (
    {
        "source": "eng005operating",
        "folder": "company-eng005-operating-2026-09-30",
        "module": eng,
        "module_name": "company_eng005_operating_2027.py",
        "module_sha": "a9c7c2d373ec29bfa8c2c2606aec22de30c60c9f2cb0b4873d4d158e34968622",
        "spec_sha": "a497fab4b3ca909f55b3376efec15c28f6195394d6f085d4aaf0b99d51043d6a",
        "review_sha": "03453687ff227cb6ef4376e6b1b313638e5a5841fc78f43cd09551fd62e44075",
        "review_verdict": "PASS_MAIN_SELECTED_SOURCE_NO_AUDIT_CREDIT",
        "manifest_sha": "505be4531461c0d73e0466fb39540b5757512bf13b9d4ed8f44c13d86e90fc75",
        "receipt_sha": "0d9209de464d0f4e9186eb41824ac66beba1b7f7e1e735364ba64cded20f02bd",
        "db_sha": "8696b55b03ec1df8597556d0b949f82a34c0e0cabc9d8130fae078e6b2812ee3",
        "counts": (12, 22),
        "systems": 10,
    },
    {
        "source": "govoversight",
        "folder": "company-gov-selected-oversight-2026-10-01",
        "module": gov,
        "module_name": "company_gov_selected_oversight_2027.py",
        "module_sha": "e1b747263b419de84b949c9014a2368921a8a07f8948761896f9e82f85b152ab",
        "spec_sha": "ff5151cc7e788f502d0324b1aa859750284d36c80a7558817fd38aff923e23a6",
        "review_sha": "54f59bd5a7db74ab29ead5d322908f4ad9e844c746c2f1b6f0cf3b0731bbcb01",
        "review_verdict": "PASS_MAIN_SELECTED_GOV_SOURCE_NO_AUDIT_CREDIT",
        "manifest_sha": "09cee311aac8f62cc5aee39626fccf67b6bbb5a8be4a1c218f533a7c7c7cbad4",
        "receipt_sha": "6c4b5a9c56e930e7875667fc3cd85e7825f69a5e4901f9d940c2f10ab29c40bd",
        "db_sha": "81aef24a796a07e4daf2fc32f1dcfec10712a944b6d58f757eae2a73ef03228e",
        "counts": (9, 14),
        "systems": 11,
    },
)


def reviewed_v16(repository: Path, private: Path) -> tuple[dict, dict, dict]:
    """Trust only exact main-reviewed V16 bytes, not a recursive V16 rebuild."""
    root = private / BASE / V16_FOLDER
    paths = {
        "review": root / "independent-review-main-v1/REVIEW.json",
        "report": root / "main-report-v1/REPORT.json",
        **{name: root / "main-candidate-v1" / name for name in V16_CANDIDATE_SHA},
    }
    expected = {"review": V16_REVIEW_SHA, "report": V16_REPORT_SHA, **V16_CANDIDATE_SHA}
    for directory in (
        root,
        paths["review"].parent,
        paths["report"].parent,
        root / "main-candidate-v1",
    ):
        _private(directory, directory=True)
    before = {name: _pin(path, expected[name]) for name, path in paths.items()}
    review = _read_json(paths["review"])
    report = _read_json(paths["report"])
    candidates = {name: _read_json(paths[name]) for name in V16_CANDIDATE_SHA}
    module = repository / "enterprise/audit_suite/fictional_2027_source_portfolio_v16.py"
    if (
        review.get("verdict") != "PASS_MAIN_PARTIAL_CANDIDATE_NO_AUDIT_CREDIT"
        or review.get("integrated_commit") != "d9d62a16"
        or review.get("isolated_review_sha256") != V16_ISOLATED_REVIEW_SHA
        or review.get("output_sha256")
        != {
            "main-report-v1/REPORT.json": V16_REPORT_SHA,
            **{f"main-candidate-v1/{name}": digest for name, digest in V16_CANDIDATE_SHA.items()},
        }
        or any(
            review.get(key) is not False
            for key in ("source_complete", "fresh_audit_pair_created", "audit_task_credit")
        )
        or "P1 freeze 538 exact inventory" not in review.get("checks", [])
        or not module.is_file()
        or module.is_symlink()
        or report.get("verifier_module_sha256") != _digest(module)
        or (
            report.get("source_count"),
            report.get("native_versions"),
            report.get("source_component_count"),
        )
        != (37, 840, 38)
        or len(report.get("sources", [])) != 37
        or report["sources"][-1].get("source") != "prdconcern"
        or any(
            report.get(key) is not False
            for key in ("source_complete", "fresh_audit_pair_created", "audit_task_credit")
        )
        or candidates["REPORT.json"].get("reviewed_native_versions") != 840
        or candidates["REPORT.json"].get("portfolio_verifier_sha256")
        != report["verifier_module_sha256"]
        or any(
            candidates["REPORT.json"].get(key) is not False
            for key in (
                "source_complete",
                "fresh_audit_pair_created",
                "audit_task_credit",
                "grants_or_collections_created",
            )
        )
    ):
        raise PortfolioVerificationError("Reviewed V16 prefix differs")
    for side in "AB":
        selected = candidates["REPORT.json"]["sides"][side]
        manifest = candidates[f"{side}.json"]
        if (
            len(manifest.get("components", {})) != 51
            or len(selected.get("source_pins", [])) != 38
            or (
                selected.get("component_count"),
                selected.get("scenario_source_component_count"),
                selected.get("system_alias_count"),
            )
            != (51, 38, 324)
            or selected.get("registry_sha256") != V16_CANDIDATE_SHA[f"{side}.json"]
            or selected.get("source_complete") is not False
            or selected["source_pins"][-1].get("source") != "prdconcern"
            or "scenario-prdconcern" not in manifest["components"]
        ):
            raise PortfolioVerificationError("Reviewed V16 candidate prefix differs")
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("Reviewed V16 bytes changed during read")
    return report, candidates, before


def _qualify(repository: Path, private: Path, selected: dict) -> dict:
    module = selected["module"]
    code = repository / "enterprise/audit_suite" / selected["module_name"]
    spec = repository / module.SPEC
    if (
        not code.is_file()
        or code.is_symlink()
        or _digest(code) != selected["module_sha"]
        or not spec.is_file()
        or spec.is_symlink()
        or _digest(spec) != selected["spec_sha"]
    ):
        raise PortfolioVerificationError("Selected source tracked module/spec differs")
    folder = private / BASE / selected["folder"]
    run = folder / "main-run-v1"
    paths = {
        "review": folder / "independent-review-main-v1/REVIEW.json",
        "manifest": run / "MANIFEST.json",
        "receipt": run / "RECEIPT.json",
        "database": run / "company.sqlite3",
    }
    for directory in (folder, run, paths["review"].parent):
        _private(directory, directory=True)
    expected = {
        "review": selected["review_sha"],
        "manifest": selected["manifest_sha"],
        "receipt": selected["receipt_sha"],
        "database": selected["db_sha"],
    }
    before = {name: _pin(path, expected[name]) for name, path in paths.items()}
    review = _read_json(paths["review"])
    manifest = _read_json(paths["manifest"])
    receipt = _read_json(paths["receipt"])
    counts = dict(zip(("CLEAN", "MESSY"), selected["counts"], strict=True))
    if (
        review.get("verdict") != selected["review_verdict"]
        or review.get("main_run_sha256")
        != {
            "MANIFEST.json": selected["manifest_sha"],
            "RECEIPT.json": selected["receipt_sha"],
            "company.sqlite3": selected["db_sha"],
        }
        or review.get("p1_freeze") != P1_FREEZE
        or review.get("source_complete") is not False
        or review.get("audit_task_credit") is not False
        or manifest.get("module_sha256") != selected["module_sha"]
        or manifest.get("receipt_sha256") != selected["receipt_sha"]
        or manifest.get("db_sha256") != selected["db_sha"]
        or manifest.get("native_version_count") != sum(selected["counts"])
        or manifest.get("audit_task_credit") is not False
        or receipt.get("schema") != module.SCHEMA
        or receipt.get("company") != module.COMPANY
        or receipt.get("branches") != module.BRANCHES
        or receipt.get("native_version_counts") != counts
        or receipt.get("source_complete") is not False
        or receipt.get("audit_task_credit") is not False
    ):
        raise PortfolioVerificationError("Selected reviewed source boundary differs")
    if (
        module.verify(run, repository=repository, private_repository=private).get(
            "native_version_counts"
        )
        != counts
    ):
        raise PortfolioVerificationError("Selected native source verifier differs")
    native, systems, journals = _frozen_rows(paths["database"])
    branches = tuple(module.BRANCHES.values())
    if (
        sorted(native)
        != sorted(
            (module.COMPANY, branch, count)
            for branch, count in zip(branches, selected["counts"], strict=True)
        )
        or sorted(systems)
        != sorted((module.COMPANY, branch, selected["systems"]) for branch in branches)
        or any(journals.values())
        or any(
            row["event_at"] == row["imported_at"]
            or row["event_at"] < "2027-01-01"
            or row["imported_at"] >= "2027-01-01"
            for rows in receipt["records"].values()
            for row in rows
        )
    ):
        raise PortfolioVerificationError("Selected source rows, clocks or journals differ")
    _no_sidecars(paths["database"])
    if selected["source"] == "eng005operating":
        extra = {
            "selected_population_count": 2,
            "corporate_emergency_authority_status": "NOT_EVIDENCED_OPEN",
            "open_exception_counts": {"CLEAN": 0, "MESSY": 2},
            "real_deployment": False,
            "actual_phi": False,
            "authored_eng005_clause_satisfied": False,
            "enterprise_policy_approved": False,
            "full_period_or_enterprise_change_population_complete": False,
            "external_packets_or_writes": 0,
        }
        if (
            len(receipt.get("selected_population", [])) != 2
            or receipt.get("corporate_emergency_authority_status")
            != extra["corporate_emergency_authority_status"]
            or receipt.get("open_exception_counts") != extra["open_exception_counts"]
            or any(
                receipt.get(key) is not False
                for key in (
                    "real_deployment",
                    "actual_phi",
                    "authored_eng005_clause_satisfied",
                    "enterprise_policy_approved",
                    "full_period_or_enterprise_change_population_complete",
                    "historical_exercise_is_operating_source",
                )
            )
            or receipt.get("external_packets_or_writes") != 0
            or review.get("real_deployment") is not False
        ):
            raise PortfolioVerificationError("ENG005 authority/deployment boundary differs")
    else:
        extra = {
            "selected_case_count": 1,
            "clean_selected_finding_status": "CLOSED_SELECTED_ONLY",
            "messy_historical_governance_exception_status": "OPEN",
            "messy_historical_sec003_exception_status": "OPEN",
            "actual_board_meeting": False,
            "adopted_minutes": False,
            "legal_quorum_established": False,
            "actual_phi_processing": False,
            "authored_cc12_clause_satisfied": False,
            "complete_oversight_population": False,
            "independent_assurance_completed": False,
            "real_external_messages_sent": 0,
        }
        if (
            any(receipt.get(key) != value for key, value in extra.items())
            or receipt.get("fresh_audit_pair_created") is not False
            or review.get("fresh_audit_pair_created") is not False
            or review.get("native_versions") != counts
        ):
            raise PortfolioVerificationError("GOV oversight Board/population boundary differs")
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("Selected reviewed source changed during read")
    return {
        "source": selected["source"],
        "run": f"{selected['folder']}/main-run-v1",
        "review_sha256": selected["review_sha"],
        "manifest_sha256": selected["manifest_sha"],
        "receipt_sha256": selected["receipt_sha"],
        "database_sha256": {"native": selected["db_sha"]},
        "native_versions": sum(selected["counts"]),
        "branch_versions": dict(zip(branches, selected["counts"], strict=True)),
        "physical_company_ids": [module.COMPANY],
        "ledger_system_counts": {"native": selected["systems"]},
        "inherited_audit_journals": {name: 0 for name in JOURNALS},
        **extra,
        "source_complete": False,
        "audit_task_credit": False,
    }


def _compose(previous: dict, additions: list[dict]) -> dict:
    if (
        (
            previous.get("source_count"),
            previous.get("native_versions"),
            previous.get("source_component_count"),
        )
        != (37, 840, 38)
        or len(previous.get("sources", [])) != 37
        or any(
            previous.get(key) is not False
            for key in ("source_complete", "fresh_audit_pair_created", "audit_task_credit")
        )
        or [row.get("source") for row in additions] != ["eng005operating", "govoversight"]
        or [row.get("native_versions") for row in additions] != [34, 23]
    ):
        raise PortfolioVerificationError("V17 reviewed extension boundary differs")
    sources = [*previous["sources"], *additions]
    if (
        len(sources) != 39
        or len({row["source"] for row in sources}) != 39
        or sum(row["native_versions"] for row in sources) != 897
    ):
        raise PortfolioVerificationError("V17 roster differs")
    return {
        "schema": SCHEMA,
        "status": "PARTIAL_REVIEWED_NATIVE_SOURCES_NOT_AUDIT_READY",
        "as_of": "2026-10-01",
        "verifier_module_sha256": _digest(Path(__file__)),
        "v16_verifier_sha256": previous["verifier_module_sha256"],
        "v16_review_sha256": V16_REVIEW_SHA,
        "source_count": 39,
        "native_versions": 897,
        "source_component_count": 40,
        "sources": sources,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": [
            "Thirty-nine selected fictional cohorts, not an enterprise or period "
            "evidence population.",
            "ENG005 is two data-only selected changes; corporate emergency authority "
            "remains NOT_EVIDENCED_OPEN and Messy exceptions stay open.",
            "No actual deployment, packet, PHI or customer effect follows from ENG005.",
            "GOV is one secretary-owned selected committee cycle; no actual Board meeting, "
            "adopted minutes, quorum or independent assurance is asserted.",
            "GOV Messy historical governance and SEC003 exceptions remain OPEN; "
            "authored CC1.2 remains unsupported.",
            "2027 event/availability clocks are authored; native import clocks "
            "record actual creation separately.",
            "No source completion, fresh pair, grant, collection, task credit, Key or grade.",
        ],
    }


def verify_all(repository: Path, *, private_repository: Path | None = None) -> dict:
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository or repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise PortfolioVerificationError("Frozen P1 inventory differs")
    previous, _, prefix = reviewed_v16(repository, private)
    additions = [_qualify(repository, private, selected) for selected in SOURCES]
    if reviewed_v16(repository, private)[2] != prefix or _p1_inventory(private) != freeze:
        raise PortfolioVerificationError("Reviewed V16 prefix or P1 changed during source read")
    return _compose(previous, additions)


def write_report(repository: Path, private_repository: Path, destination: Path) -> dict:
    report = verify_all(repository, private_repository=private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise PortfolioVerificationError("Fresh V17 report destination required")
    _private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".portfolio-v17-", dir=destination.parent) as name:
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
        raise PortfolioVerificationError("Exact one-file V17 report required")
    path = root / "REPORT.json"
    before = _pin(path, _digest(path))
    actual = _read_json(path)
    if (
        actual != verify_all(repository, private_repository=private_repository)
        or _identity(path) != before
    ):
        raise PortfolioVerificationError("V17 portfolio report differs")
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
