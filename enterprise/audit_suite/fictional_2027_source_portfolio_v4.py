"""Read-only partial V4 source roster; no audit evidence or coverage credit."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import company_ass_owner_monitor_exercise as ass
from . import company_sec005_local_boundary_2027 as sec
from . import fictional_2027_source_portfolio_v3 as prior
from . import rec003_native_snapshot_candidate as rec
from .fictional_2027_source_portfolio import (
    BASE,
    PortfolioVerificationError,
    _digest,
    _identity,
    _private,
    _read_json,
)


@dataclass(frozen=True)
class AddedSource:
    key: str
    folder: str
    run: str
    review: str
    verdict: str
    review_sha256: str
    manifest_sha256: str
    receipt_sha256: str
    database_sha256: str
    branches: tuple[str, str]
    counts: tuple[int, int]
    systems: int


STANDARD = (
    AddedSource(
        "sec005",
        "company-sec005-local-boundary-2026-09-29",
        "main-run-v1",
        "independent-review-main-v1/REVIEW.json",
        "PASS_FICTIONAL_LOCAL_BOUNDARY_TRACE_NO_CREDIT",
        "d1b1b455ce14d057b8cfe184448f8bb04ff5f4ae238bda888ad820899f97740a",
        "6216b0308a94512868e8900c5812fc4f6821243b8fe92772fe09fdc08feb45cc",
        "b0e99ea38f78064adf040ff38416a01c65a08dbe1d707e437f2c9e91d5190658",
        "b5b94ecd07f1c59faa815170b68a1a6fb59a06ac35c6188a2862370d355b5106",
        ("SEC005-LOCAL-CLEAN", "SEC005-LOCAL-MESSY"),
        (5, 8),
        6,
    ),
    AddedSource(
        "ass001002",
        "company-ass-owner-monitor-2026-09-29",
        "main-run-v1",
        "independent-review-main-v1/REVIEW.json",
        "PASS_SELECTED_LOCAL_MANAGEMENT_SOURCE_SAME_ROOT_NO_AUDIT_CREDIT",
        "eb47e363e5eaa8538ff3a9a41e98df1098f63cc46e854fdc8c7cc3af43851878",
        "716051f60ccb453cccab9dd6e0549026a803c0c908b0927be56df4222bd492a0",
        "d1181cd5a4130ecf21ccd863d1f565f966c384193331edc7b969bc34f23767d2",
        "cf50ddd8c698656ac638810c325b608a11eeb68b338810134105b3528c8865c6",
        ("ASS12-CLEAN", "ASS12-MESSY"),
        (3, 5),
        4,
    ),
)

REC_FOLDER = "company-rec003-native-snapshot-2026-09-29"
REC_RUN = "main-run-v2"
REC_REVIEW = "independent-review-main-v2/REVIEW.json"
REC_REVIEW_SHA256 = "010824ecc65c7be45fcffbc3cf22004c1dd4553c90d476e7c630a7a7cdd10eff"
REC_MANIFEST_SHA256 = "941226221a728f56af223c29efd87124755aa766fe81b65f855d0dbfc32b3eb4"
REC_RECEIPT_SHA256 = "06e7b6c09d6fdb5e43a8dd7b7e5be16be925c2d9d9b205cbd26a6f090f5614de"
REC_ROUTES_SHA256 = "90ec9d0a5db6a09ef830cd42ddb22ac1606608f1f8ae9ae93b137314add6b9de"
REC_DATABASES = {
    "A": "9b5489db2643b728fd8df846fd07af6928d6607958bd3857c46b6c9720e980ab",
    "B": "14af2e579591f0460eb3fe7c549d4c5b12ad3ac0548599de7f7ca5d3d30def12",
}
JOURNALS = {"grants": 12, "collections": 22, "access_events": 25}


def _no_sidecars(path: Path) -> None:
    if any(
        Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise PortfolioVerificationError("Frozen V4 database has SQLite sidecar")


def _pin(path: Path, expected: str) -> tuple:
    _private(path)
    identity = _identity(path)
    if _digest(path) != expected:
        raise PortfolioVerificationError(f"Reviewed V4 byte pin differs: {path.name}")
    return identity


def _review(
    path: Path, expected: str, verdict: str, run: str, manifest: str, receipt: str
) -> tuple:
    before = _pin(path, expected)
    row = _read_json(path)
    if (
        row.get("verdict") != verdict
        or row.get("selected_run") != run
        or row.get("manifest_sha256") != manifest
        or row.get("receipt_sha256") != receipt
        or row.get("active_pair_mutated") is not False
    ):
        raise PortfolioVerificationError("V4 independent review/source join differs")
    return before


def _frozen_rows(path: Path) -> tuple[list[tuple], list[tuple], dict[str, int]]:
    _no_sidecars(path)
    with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise PortfolioVerificationError("V4 source database integrity differs")
        native = db.execute(
            "SELECT company,branch,COUNT(*) FROM versions GROUP BY company,branch"
        ).fetchall()
        systems = db.execute(
            "SELECT company,branch,COUNT(*) FROM systems GROUP BY company,branch"
        ).fetchall()
        journals = {
            table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in JOURNALS
        }
    return native, systems, journals


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
        _private(directory, directory=True)
    before = {
        name: _pin(path, sha)
        for name, (path, sha) in {
            "review": (review, source.review_sha256),
            "manifest": (paths["manifest"], source.manifest_sha256),
            "receipt": (paths["receipt"], source.receipt_sha256),
            "database": (paths["database"], source.database_sha256),
        }.items()
    }
    _review(
        review,
        source.review_sha256,
        source.verdict,
        source.run,
        source.manifest_sha256,
        source.receipt_sha256,
    )
    manifest, receipt = _read_json(paths["manifest"]), _read_json(paths["receipt"])
    expected_branches = dict(zip(("CLEAN", "MESSY"), source.branches, strict=True))
    if (
        receipt.get("branches") != expected_branches
        or receipt.get("company") != "SABLE-HARBOR-REFERENCE"
        or receipt.get("audit_task_credit") is not False
        or manifest.get("audit_task_credit") is not False
        or manifest.get("native_version_count") != sum(source.counts)
        or manifest.get("receipt_sha256") != source.receipt_sha256
        or manifest.get("company_db_sha256", manifest.get("db_sha256")) != source.database_sha256
    ):
        raise PortfolioVerificationError(f"{source.key} source receipt/manifest differs")
    own = (sec if source.key == "sec005" else ass).verify(
        run, repository=repository, private_repository=private
    )
    if own.get("audit_task_credit", False) is not False:
        raise PortfolioVerificationError(f"{source.key} own verifier grants audit credit")
    native, systems, journals = _frozen_rows(paths["database"])
    expected_native = [
        ("SABLE-HARBOR-REFERENCE", branch, count)
        for branch, count in zip(source.branches, source.counts, strict=True)
    ]
    expected_systems = [
        ("SABLE-HARBOR-REFERENCE", branch, source.systems) for branch in source.branches
    ]
    if (
        sorted(native) != sorted(expected_native)
        or sorted(systems) != sorted(expected_systems)
        or any(journals.values())
    ):
        raise PortfolioVerificationError(f"{source.key} native/zero-journal roster differs")
    _no_sidecars(paths["database"])
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
        "inherited_audit_journals": {table: 0 for table in JOURNALS},
        "audit_task_credit": False,
    }


def _rec003(repository: Path, private: Path) -> dict:
    folder = private / BASE / REC_FOLDER
    run = folder / REC_RUN
    review = folder / REC_REVIEW
    paths = {
        "review": review,
        "manifest": run / "MANIFEST.json",
        "receipt": run / "RECEIPT.json",
        "routes": run / "ROUTES.json",
        **{side: run / side / "company.sqlite3" for side in "AB"},
    }
    for directory in (folder, run, review.parent, run / "A", run / "B"):
        _private(directory, directory=True)
    hashes = {
        "review": REC_REVIEW_SHA256,
        "manifest": REC_MANIFEST_SHA256,
        "receipt": REC_RECEIPT_SHA256,
        "routes": REC_ROUTES_SHA256,
        **REC_DATABASES,
    }
    before = {name: _pin(path, hashes[name]) for name, path in paths.items()}
    _review(
        review,
        REC_REVIEW_SHA256,
        "PASS_QUALIFIED_LOCAL_SOURCE_SNAPSHOT_CANDIDATE_NO_CREDIT",
        REC_RUN,
        REC_MANIFEST_SHA256,
        REC_RECEIPT_SHA256,
    )
    manifest, receipt, routes = (
        _read_json(paths[name]) for name in ("manifest", "receipt", "routes")
    )
    if (
        manifest.get("receipt_sha256") != REC_RECEIPT_SHA256
        or manifest.get("routes_sha256") != REC_ROUTES_SHA256
        or manifest.get("snapshot_sha256") != REC_DATABASES
        or manifest.get("audit_task_credit") is not False
        or receipt.get("audit_task_credit") is not False
        or receipt.get("source_complete") is not False
        or receipt.get("audit_collection") is not False
        or receipt.get("actual_operating_evidence") is not False
        or set(routes.get("sides", {})) != {"A", "B"}
    ):
        raise PortfolioVerificationError("REC003 source manifest/receipt differs")
    own = rec.verify(run, repository=repository, private_repository=private)
    if own.get("audit_task_credit") is not False:
        raise PortfolioVerificationError("REC003 own verifier grants audit credit")
    branch_versions = {}
    for side in "AB":
        route = routes["sides"][side]
        expected_branch = f"local-data-quality-{side.lower()}"
        if (
            route.get("source_store_id") != "scenario-rec003-dq"
            or route.get("root_locator") != "snapshot://" + side
            or route.get("physical_company") != "SABLEHARBOR"
            or route.get("physical_branch") != expected_branch
            or route.get("namespace") != "F27REC003DQ"
            or route.get("systems") != list(rec.SYSTEMS)
            or receipt["sides"][side].get("route_locator") != "snapshot://" + side
            or receipt["sides"][side].get("disposable_snapshot_sha256") != REC_DATABASES[side]
        ):
            raise PortfolioVerificationError("REC003 portable per-side route differs")
        native, systems, journals = _frozen_rows(paths[side])
        if (
            native != [("SABLEHARBOR", expected_branch, 11)]
            or systems != [("SABLEHARBOR", expected_branch, 6)]
            or journals != JOURNALS
            or receipt["sides"][side].get("inherited_audit_journals_excluded_from_company_lineage")
            != JOURNALS
        ):
            raise PortfolioVerificationError("REC003 11-row lineage/journal baseline differs")
        _no_sidecars(paths[side])
        branch_versions[expected_branch] = 11
    if {name: _identity(path) for name, path in paths.items()} != before:
        raise PortfolioVerificationError("REC003 changed during verification")
    return {
        "source": "rec003",
        "run": f"{REC_FOLDER}/{REC_RUN}",
        "review_sha256": REC_REVIEW_SHA256,
        "manifest_sha256": REC_MANIFEST_SHA256,
        "receipt_sha256": REC_RECEIPT_SHA256,
        "routes_sha256": REC_ROUTES_SHA256,
        "database_sha256": REC_DATABASES,
        "native_versions": 22,
        "branch_versions": branch_versions,
        "physical_company_ids": ["SABLEHARBOR"],
        "ledger_system_counts": {"A": 6, "B": 6},
        "inherited_audit_journals": JOURNALS,
        "audit_task_credit": False,
    }


def verify_all(repository: Path, *, private_repository: Path | None = None) -> dict:
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository or repository).resolve(strict=True)
    previous = prior.verify_all(repository, private_repository=private)
    if (
        previous["source_count"],
        previous["native_versions"],
        previous["source_component_count"],
        previous["source_complete"],
        previous["audit_task_credit"],
    ) != (21, 358, 22, False, False):
        raise PortfolioVerificationError("Reviewed V3 prefix differs")
    sources = [*previous["sources"], _rec003(repository, private)]
    sources.extend(_standard(source, repository, private) for source in STANDARD)
    if (
        len(sources) != 24
        or sum(row["native_versions"] for row in sources) != 401
        or len({row["source"] for row in sources}) != 24
    ):
        raise PortfolioVerificationError("Partial V4 source roster differs")
    return {
        "schema": "SH_FICTIONAL_2027_REVIEWED_SOURCE_PORTFOLIO_DIAGNOSTIC_V4",
        "status": "PARTIAL_REVIEWED_NATIVE_SOURCES_NOT_AUDIT_READY",
        "as_of": "2026-09-30",
        "verifier_module_sha256": _digest(Path(__file__)),
        "v3_verifier_sha256": previous["verifier_module_sha256"],
        "source_count": 24,
        "native_versions": 401,
        "source_component_count": 25,
        "sources": sources,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": [
            "Twenty-four selected cohorts, not an enterprise evidence population.",
            "REC003 inherited journals (12/22/25) are excluded from 22 business versions.",
            "REC003 snapshot://A/B locators resolve only when building private routing profiles.",
            "A/B are routing profiles, not new Clean/Messy audit engagements.",
            "No fresh audit pair, grant, collection, task, Key, grade or source-complete claim.",
        ],
    }


def write_report(repository: Path, private_repository: Path, destination: Path) -> dict:
    report = verify_all(repository, private_repository=private_repository)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise PortfolioVerificationError("Fresh V4 report destination required")
    _private(destination.parent, directory=True)
    with tempfile.TemporaryDirectory(prefix=".portfolio-v4-", dir=destination.parent) as temp:
        stage = Path(temp)
        path = stage / "REPORT.json"
        path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        path.chmod(0o600)
        os.rename(stage, destination)
    return verify_report(destination, repository, private_repository)


def verify_report(destination: Path, repository: Path, private_repository: Path) -> dict:
    root = Path(destination).absolute()
    _private(root, directory=True)
    if {path.name for path in root.iterdir()} != {"REPORT.json"}:
        raise PortfolioVerificationError("Exact one-file V4 report required")
    path = root / "REPORT.json"
    before = _pin(path, _digest(path))
    actual = _read_json(path)
    expected = verify_all(repository, private_repository=private_repository)
    if actual != expected or _identity(path) != before:
        raise PortfolioVerificationError("V4 portfolio report differs")
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
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
