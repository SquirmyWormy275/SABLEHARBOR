"""V18 partial source roster over reviewed V17 plus LEG/DAT selected originals."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime
from pathlib import Path

from . import company_dat002_rights_scope_2027 as dat
from . import company_leg001_provision_overlay_2027 as leg
from . import fictional_2027_source_portfolio_v17 as prior
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

SCHEMA = "SH_FICTIONAL_2027_REVIEWED_SOURCE_PORTFOLIO_DIAGNOSTIC_V18"
BASE = prior.BASE
P1_FREEZE = prior.P1_FREEZE
V17_FOLDER = "company-source-portfolio-v17-2026-10-01"
V17_REVIEW_SHA = "c006878e9ece6251fbfb52333322ad33e3fd7cdaad9a9394649e4865c019f967"
V17_REPORT_SHA = "82f8edc2f1f71d27420a073ff39bf7b6661cca1d2926f1d81be780ce068c15b9"
V17_CANDIDATE_SHA = {
    "A.json": "4e4345719f8b9e1b0fa1123d478c289b9651343b88fc83f0c3f395a6f231bc46",
    "B.json": "99ec160cce55def5fe981d8175bee6d636e9c0c2e068400e906c9cf5f28579e8",
    "REPORT.json": "c5cbccbbbd8cec184927432836f0568dc76c38c09ad1023f7125f0f6e55bb80f",
}
SOURCES = (
    {
        "source": "legprovision",
        "folder": "company-leg001-provision-overlay-2027-10-01",
        "module": leg,
        "module_name": "company_leg001_provision_overlay_2027.py",
        "module_sha": "0f3041f392b2d94393c9744fc20ca1ffd3e59912df7901cff994efa6a434c967",
        "spec": leg.SPEC,
        "spec_sha": "84e575a931ebe29e2146378af3998bd85c039709570f302517cada9fdfed64da",
        "review_sha": "359196741f6b82af450104997d78ebb301a6abcdcbfce29d9cf0ef47393c8583",
        "review_schema": "SH_INDEPENDENT_LEG001_PROVISION_OVERLAY_MAIN_REVIEW_V1",
        "review_verdict": "PASS_MAIN_SELECTED_LOCATORS_OPEN_NO_AUDIT_CREDIT",
        "manifest_sha": "add1462a98ea9b8cfc30a8195c8094f7213ea64c468c878d4c15151ac2abdc69",
        "receipt_sha": "ce1066519a21ab84a0a55c93ba143d637014dfac4d503126a0301e5ef22f187f",
        "db_sha": "5ffb1eb1cc9429b87f60171fa2ff170d85be3b83f6854ebe246b3f0d59945d0e",
        "counts": (20, 20),
        "systems": (3, 3),
        "branches": {"CLEAN": "LEGOV-CLEAN", "MESSY": "LEGOV-MESSY"},
    },
    {
        "source": "dat002rights",
        "folder": "company-dat002-rights-scope-2027-2026-10-01",
        "module": dat,
        "module_name": "company_dat002_rights_scope_2027.py",
        "module_sha": "fc0ce32741fafe0946f04865c2b8c21c7236a31ea237576ca245c345603869f1",
        "spec": None,
        "spec_sha": None,
        "review_sha": "7c244ae5938868b1caf97500682a8f4cad1402d59e29a45c08fb8110e388763e",
        "review_schema": "SH_INDEPENDENT_DAT002_RIGHTS_SCOPE_MAIN_REVIEW_V1",
        "review_verdict": "PASS_MAIN_SELECTED_SOURCE_NO_AUDIT_CREDIT",
        "manifest_sha": "222b21ad5a90e05fb1c690951e7a94537148a682a69a39a661fbc0fd0ff2f91f",
        "receipt_sha": "55502c4210f1855e570352d4972c002ca8726c74db551691e1e89eb4230064ad",
        "db_sha": "07deca8ba563281439167f5b274364942dab9a9fdc96b01209a722d3f13e1a44",
        "counts": (5, 6),
        "systems": (5, 6),
        "branches": dat.BRANCHES,
    },
)


def reviewed_v17(repository: Path, private: Path) -> tuple[dict, dict, dict]:
    """Read exact independently reviewed V17 bytes without rebuilding V17."""
    root = private / BASE / V17_FOLDER
    paths = {
        "review": root / "independent-review-main-v1/REVIEW.json",
        "report": root / "main-report-v1/REPORT.json",
        **{name: root / "main-candidate-v1" / name for name in V17_CANDIDATE_SHA},
    }
    expected = {"review": V17_REVIEW_SHA, "report": V17_REPORT_SHA, **V17_CANDIDATE_SHA}
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
    candidates = {name: _read_json(paths[name]) for name in V17_CANDIDATE_SHA}
    code = repository / "enterprise/audit_suite/fictional_2027_source_portfolio_v17.py"
    if (
        review.get("schema") != "SH_INDEPENDENT_ENG_GOV_PORTFOLIO_V17_MAIN_REVIEW_V1"
        or review.get("verdict") != "PASS_MAIN_PARTIAL_CANDIDATE_NO_AUDIT_CREDIT"
        or review.get("output_sha256")
        != {
            "main-report-v1/REPORT.json": V17_REPORT_SHA,
            **{f"main-candidate-v1/{name}": digest for name, digest in V17_CANDIDATE_SHA.items()},
        }
        or any(
            review.get(key) is not False
            for key in ("source_complete", "fresh_audit_pair_created", "audit_task_credit")
        )
        or not code.is_file()
        or code.is_symlink()
        or report.get("verifier_module_sha256") != _digest(code)
        or report.get("schema") != prior.SCHEMA
        or (
            report.get("source_count"),
            report.get("native_versions"),
            report.get("source_component_count"),
        )
        != (39, 897, 40)
        or len(report.get("sources", [])) != 39
        or [row.get("source") for row in report["sources"][-2:]]
        != ["eng005operating", "govoversight"]
        or any(
            report.get(key) is not False
            for key in ("source_complete", "fresh_audit_pair_created", "audit_task_credit")
        )
        or candidates["REPORT.json"].get("schema")
        != "SH_FICTIONAL_2027_PARTIAL_CANDIDATE_REGISTRY_DIAGNOSTIC_V17"
        or candidates["REPORT.json"].get("reviewed_native_versions") != 897
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
        raise PortfolioVerificationError("Reviewed V17 prefix differs")
    for side in "AB":
        selected = candidates["REPORT.json"]["sides"][side]
        manifest = candidates[f"{side}.json"]
        if (
            len(manifest.get("components", {})) != 53
            or len(selected.get("source_pins", [])) != 40
            or selected.get("registry_sha256") != V17_CANDIDATE_SHA[f"{side}.json"]
            or (
                selected.get("component_count"),
                selected.get("scenario_source_component_count"),
                selected.get("system_alias_count"),
            )
            != (53, 40, 345)
            or selected["source_pins"][-2]["source"] != "eng005operating"
            or selected["source_pins"][-1]["source"] != "govoversight"
            or "scenario-eng005operating" not in manifest["components"]
            or "scenario-govoversight" not in manifest["components"]
            or selected.get("source_complete") is not False
        ):
            raise PortfolioVerificationError("Reviewed V17 candidate prefix differs")
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("Reviewed V17 bytes changed during read")
    return report, candidates, before


def _assert_originals(database: Path, receipt: dict, selected: dict) -> None:
    """Check each reviewed receipt tuple against its native ordinary DB row."""
    module = selected["module"]
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise PortfolioVerificationError("Selected native database integrity differs")
        for scenario, branch in selected["branches"].items():
            refs = receipt["records"][scenario]
            if len(refs) != selected["counts"][("CLEAN", "MESSY").index(scenario)]:
                raise PortfolioVerificationError("Selected branch original count differs")
            seen = set()
            for ref in refs:
                key = (ref["system"], ref["record"], ref["version"])
                if key in seen:
                    raise PortfolioVerificationError("Duplicate selected native receipt key")
                seen.add(key)
                row = db.execute(
                    "SELECT * FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND version=?",
                    (module.COMPANY, branch, *key),
                ).fetchone()
                if (
                    row is None
                    or ref["company"] != module.COMPANY
                    or ref["branch"] != branch
                    or ref["origin"] != "AUTHORED_TRAINING_SOURCE"
                    or row["origin"] != ref["origin"]
                    or row["sha256"] != ref["sha256"]
                    or row["sha256"] != _digest_bytes(row["content"])
                    or any(
                        row[field] != ref[field]
                        for field in ("event_at", "available_at", "imported_at")
                    )
                    or json.loads(row["provenance"]) != ref["provenance"]
                    or ref["event_at"] >= ref["available_at"]
                    or datetime.fromisoformat(ref["imported_at"])
                    >= datetime.fromisoformat(ref["event_at"])
                ):
                    raise PortfolioVerificationError("Selected native original differs")


def _digest_bytes(value: bytes) -> str:
    import hashlib

    return hashlib.sha256(value).hexdigest()


def _qualify(repository: Path, private: Path, selected: dict) -> dict:
    module = selected["module"]
    code = repository / "enterprise/audit_suite" / selected["module_name"]
    if not code.is_file() or code.is_symlink() or _digest(code) != selected["module_sha"]:
        raise PortfolioVerificationError("Selected source tracked module differs")
    if selected["spec"]:
        spec = repository / selected["spec"]
        if not spec.is_file() or spec.is_symlink() or _digest(spec) != selected["spec_sha"]:
            raise PortfolioVerificationError("Selected LEG tracked spec differs")
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
    review, manifest, receipt = (
        _read_json(paths[name]) for name in ("review", "manifest", "receipt")
    )
    counts = dict(zip(("CLEAN", "MESSY"), selected["counts"], strict=True))
    if (
        review.get("schema") != selected["review_schema"]
        or review.get("verdict") != selected["review_verdict"]
        or review.get("main_run_sha256")
        != {
            "MANIFEST.json": selected["manifest_sha"],
            "RECEIPT.json": selected["receipt_sha"],
            "company.sqlite3": selected["db_sha"],
        }
        or review.get("source_complete") is not False
        or review.get("audit_task_credit") is not False
        or manifest.get("schema") != module.SCHEMA + "_MANIFEST"
        or manifest.get("module_sha256") != selected["module_sha"]
        or manifest.get("receipt_sha256") != selected["receipt_sha"]
        or manifest.get("company_db_sha256") != selected["db_sha"]
        or manifest.get("native_version_count") != sum(selected["counts"])
        or manifest.get("audit_task_credit") is not False
        or receipt.get("schema") != module.SCHEMA
        or receipt.get("company") != module.COMPANY
        or receipt.get("branches") != selected["branches"]
        or receipt.get("audit_task_credit") is not False
        or set(receipt.get("records", {})) != set(selected["branches"])
    ):
        raise PortfolioVerificationError("Selected reviewed source boundary differs")
    native, systems, journals = _frozen_rows(paths["database"])
    branches = tuple(selected["branches"].values())
    if (
        sorted(native)
        != sorted(
            (module.COMPANY, branch, count)
            for branch, count in zip(branches, selected["counts"], strict=True)
        )
        or sorted(systems)
        != sorted(
            (module.COMPANY, branch, count)
            for branch, count in zip(branches, selected["systems"], strict=True)
        )
        or any(journals.values())
    ):
        raise PortfolioVerificationError("Selected native rows, systems or journals differ")
    _assert_originals(paths["database"], receipt, selected)
    _no_sidecars(paths["database"])
    if selected["source"] == "legprovision":
        if (
            receipt.get("source_complete") is not False
            or receipt.get("2027_legal_text_verified") is not False
            or receipt.get("real_hipaa_applicability") != "UNDETERMINED"
            or receipt.get("real_contract_executed") is not False
            or receipt.get("actual_phi") is not False
            or receipt.get("outside_message_sent") is not False
            or receipt.get("selected_term_count_per_branch") != 34
            or receipt.get("provision_locator_count_per_branch") != 18
            or receipt.get("bounded_authored_provision_candidates_per_side") != 16
            or receipt.get("remaining_unmodeled_authored_candidates_per_side") != 50
            or receipt.get("open_historical_exception_ids")
            != {
                "CLEAN": [],
                "MESSY": ["EXC-SIM-BA-FLOWDOWN-01", "EXC-SIM-PROVIDER-SUPPORT-OMISSION-01"],
            }
        ):
            raise PortfolioVerificationError("LEG locator/legal-status/open exceptions differ")
        extra = {
            "selected_term_count_per_branch": 34,
            "provision_locator_count_per_branch": 18,
            "bounded_authored_provision_candidates_per_side": 16,
            "remaining_unmodeled_authored_candidates_per_side": 50,
            "open_historical_exception_ids": receipt["open_historical_exception_ids"],
            "2027_legal_text_verified": False,
            "real_hipaa_applicability": "UNDETERMINED",
            "actual_phi": False,
            "real_contract_executed": False,
        }
    else:
        if (
            receipt.get("native_versions_per_branch") != counts
            or receipt.get("baseline_untargeted_task_ids_per_side") != list(dat.UNTARGETED_TASKS)
            or receipt.get("discovery_only_task_ids_per_side") != list(dat.DISCOVERY_TASKS)
            or receipt.get("selected_synthetic_inquiries_per_branch") != 1
            or receipt.get("actual_requests_or_external_responses") != 0
            or receipt.get("accepted_amendments_or_accounting_completions") != 0
            or receipt.get("open_scope_exception_ids") != {"CLEAN": [], "MESSY": [dat.EXCEPTION_ID]}
            or receipt.get("complete_record_or_period_population") is not False
            or receipt.get("actual_phi_or_ba_claim") is not False
            or receipt.get("fresh_audit_pair_created") is not False
        ):
            raise PortfolioVerificationError("DAT rights scope, authority or exception differs")
        extra = {
            "selected_synthetic_inquiries_per_branch": 1,
            "discovery_only_task_ids_per_side": list(dat.DISCOVERY_TASKS),
            "open_scope_exception_ids": receipt["open_scope_exception_ids"],
            "actual_requests_or_external_responses": 0,
            "accepted_amendments_or_accounting_completions": 0,
            "complete_record_or_period_population": False,
            "actual_phi_or_ba_claim": False,
        }
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
        "ledger_system_counts": {
            branch: count for branch, count in zip(branches, selected["systems"], strict=True)
        },
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
        != (39, 897, 40)
        or len(previous.get("sources", [])) != 39
        or any(
            previous.get(key) is not False
            for key in ("source_complete", "fresh_audit_pair_created", "audit_task_credit")
        )
        or [row.get("source") for row in additions] != ["legprovision", "dat002rights"]
        or [row.get("native_versions") for row in additions] != [40, 11]
    ):
        raise PortfolioVerificationError("V18 reviewed extension boundary differs")
    sources = [*previous["sources"], *additions]
    if len(sources) != 41 or len({row["source"] for row in sources}) != 41:
        raise PortfolioVerificationError("V18 source cohort roster differs")
    return {
        "schema": SCHEMA,
        "status": "PARTIAL_REVIEWED_NATIVE_SOURCES_NOT_AUDIT_READY",
        "as_of": "2026-10-01",
        "verifier_module_sha256": _digest(Path(__file__)),
        "v17_verifier_sha256": previous["verifier_module_sha256"],
        "v17_review_sha256": V17_REVIEW_SHA,
        "source_count": 41,
        "native_versions": 948,
        "source_component_count": 42,
        "sources": sources,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": [
            *previous["limits"],
            "LEG provision locators remain status holds; no verified 2027 legal text, "
            "real applicability or opinion, and Messy historical exceptions remain open.",
            "DAT rights source is one internally seeded payload-free inquiry per branch, "
            "not a received customer/individual request or completed right.",
            "DAT customer delegation, record-set and period populations remain unresolved; "
            "Messy premature no-record scope exception remains OPEN.",
            "No grants, collections, fresh pair, source completion, task credit, Key or grade.",
        ],
    }


def verify_all(repository: Path, *, private_repository: Path | None = None) -> dict:
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository or repository).resolve(strict=True)
    freeze = _p1_inventory(private)
    if freeze != P1_FREEZE:
        raise PortfolioVerificationError("Frozen P1 inventory differs")
    previous, _, prefix = reviewed_v17(repository, private)
    additions = [_qualify(repository, private, selected) for selected in SOURCES]
    if reviewed_v17(repository, private)[2] != prefix or _p1_inventory(private) != freeze:
        raise PortfolioVerificationError("Reviewed V17 prefix or frozen P1 changed")
    return _compose(previous, additions)


def write_report(repository: Path, private_repository: Path, destination: Path) -> dict:
    report = verify_all(repository, private_repository=private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise PortfolioVerificationError("Fresh V18 report destination required")
    _private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".portfolio-v18-", dir=destination.parent) as name:
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
        raise PortfolioVerificationError("Exact one-file V18 report required")
    path = root / "REPORT.json"
    before = _pin(path, _digest(path))
    actual = _read_json(path)
    if (
        actual != verify_all(repository, private_repository=private_repository)
        or _identity(path) != before
    ):
        raise PortfolioVerificationError("V18 portfolio report differs")
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
