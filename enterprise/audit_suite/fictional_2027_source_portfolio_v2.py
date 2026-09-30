"""Read-only successor for fifteen reviewed, partial fictional 2027 cohorts.

V1's ten-source checkpoint is untouched. This successor adds only five exact
independently reviewed company-native runs and never grants audit access.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from . import company_bcm_shared_runtime_exercise as bcm
from . import company_contract_obligation_triage as contract
from . import company_integrity_chain_2027_exercise as integrity
from . import company_policy_exception_2027_exercise as policy
from . import company_retention_hold_negative_gate as retention
from . import fictional_2027_source_portfolio as historical

PortfolioVerificationError = historical.PortfolioVerificationError
BASE = historical.BASE


@dataclass(frozen=True)
class ExtraSource:
    key: str
    folder: str
    run: str
    review: str
    verdict: str
    review_sha256: str
    manifest_sha256: str
    receipt_sha256: str
    database_sha256: str
    native_versions: int


EXTRA_SOURCES = (
    ExtraSource(
        "contract",
        "company-contract-obligation-triage-2026-09-29",
        "run-v1",
        "independent-review-v1/REVIEW.json",
        "PASS_PRIVATE_FICTIONAL_SOURCE_FOR_INTEGRATION_REVIEW",
        "ae4d988c15edec4ecba009244535ad53827b53e681aa82527dbe9a02e2ea970c",
        "0cc28e7b939bd3e725482c817a9b9551164355cb5e5b5171b1ff21663424e7fd",
        "9e413b4f14912ad2034e8b4df7b0cf250378c2b4958238277222cd35d7b30d7e",
        "8528778b155989f937978a33018496b4fa8cd69de725a8189982532564ae95e5",
        4,
    ),
    ExtraSource(
        "retention",
        "company-retention-hold-gate-2026-09-29",
        "run-v1",
        "independent-review-main-v1/REVIEW.json",
        "PASS_MAIN_LOCAL_REGENERATED_PRIVATE_SOURCE_NO_AUDIT_CREDIT",
        "468f2f56ec32fe61d3f6458471b5304f89f7e14c68bea91ed404eacfeb321499",
        "91f3f6900217042810d0d7b11f72ce566a4537253a44e3d90edf54b6af2f57e3",
        "13d0312ac10c0374f66f74e0be62d0e21f5485bf162994513ad04d93e8eff93b",
        "a3ae653c0fd27c75047e34aeb5b4c391a2d4353ae6fbec15690c0ffe79984e70",
        8,
    ),
    ExtraSource(
        "integrity",
        "company-integrity-chain-2026-09-29",
        "run-v1",
        "independent-review-main-v1/REVIEW.json",
        "PASS_MAIN_LOCAL_REGENERATED_PRIVATE_SOURCE_NO_AUDIT_CREDIT",
        "30dece8998714cf412acf618a0fea9b59c891fb64415e5124eb4c9d509756aee",
        "a653421101816ffbb76d8ca1950950415daa981db1464098fde74ed0859f978f",
        "1c7103abc21bb3c1e5cc955c751638417d6bea04c6ddf32e1c36fbaf2240efa0",
        "ea3dcc5ac37fe1318d6df54d3c7469b3d895bbef2a1af77ff1e2d0738313c751",
        29,
    ),
    ExtraSource(
        "bcm",
        "company-bcm-shared-runtime-2026-09-29",
        "run-v2",
        "independent-review-v2/REVIEW.json",
        "PASS_PRIVATE_FICTIONAL_SOURCE_FOR_INTEGRATION_REVIEW",
        "bff0e70bf1f8e72e2e94bf9c2fa91c4adec811a13d2a53f85788b57d967d9476",
        "ea52c6c0210da3840a94a922c122b43b3e054d986cd02650a9ff70adb316d3a1",
        "3cd0b62de445cde7c1a76f61a156fb0fd5fa9c443cf3255ca85876b6f2c4de9a",
        "9227da660fb2bf910c877fa7abbe71f119a468040c0447092d0dee8b6da64b8e",
        18,
    ),
    ExtraSource(
        "policy",
        "company-policy-exception-2026-09-29",
        "run-v1",
        "independent-review-main-v1/REVIEW.json",
        "PASS_PRIVATE_MAIN_LOCAL_FICTIONAL_SOURCE",
        "70150ae8307b0ef0ef503d3f4031a72b3c9e36ab8a77d7746c9846464b715087",
        "e04fbe2c49d5dd0430f2f98f2180302504547c456fc979c9d494bd932eae2ec8",
        "0e3a5c079b43acbf9dc2e24da7bfddf51ea9a1ea3dcc900ab01316abbdf8d1a1",
        "c9ddeec3ccb4d3aada560b07d4dccd68f35a8c713c12cdf95993f3e12ff24552",
        19,
    ),
)


def _run_verifier(source: ExtraSource, run: Path, repository: Path, private: Path) -> dict:
    module = {
        "contract": contract,
        "retention": retention,
        "integrity": integrity,
        "bcm": bcm,
        "policy": policy,
    }[source.key]
    return module.verify(run, repository=repository, private_repository=private)


def _verify_extra(source: ExtraSource, repository: Path, private: Path) -> dict:
    folder = private / BASE / source.folder
    run, review = folder / source.run, folder / source.review
    for directory in (folder, run, review.parent):
        historical._private(directory, directory=True)
    historical._private(review)
    if historical._digest(review) != source.review_sha256:
        raise PortfolioVerificationError(f"{source.key} independent review hash differs")
    if historical._read_json(review).get("verdict") != source.verdict:
        raise PortfolioVerificationError(f"{source.key} independent review verdict differs")
    paths = {name: run / name for name in ("MANIFEST.json", "RECEIPT.json", "company.sqlite3")}
    for path in paths.values():
        historical._private(path)
    db_path = paths["company.sqlite3"]
    if any(
        Path(str(db_path) + suffix).exists() or Path(str(db_path) + suffix).is_symlink()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise PortfolioVerificationError(f"{source.key} native database has sidecar")
    hashes = {name: historical._digest(path) for name, path in paths.items()}
    identities = {name: historical._identity(path) for name, path in paths.items()}
    if hashes != {
        "MANIFEST.json": source.manifest_sha256,
        "RECEIPT.json": source.receipt_sha256,
        "company.sqlite3": source.database_sha256,
    }:
        raise PortfolioVerificationError(f"{source.key} reviewed native bytes differ")
    manifest = historical._read_json(paths["MANIFEST.json"])
    receipt = historical._read_json(paths["RECEIPT.json"])
    if (
        manifest.get("company_db_sha256") != source.database_sha256
        or manifest.get("receipt_sha256") != source.receipt_sha256
        or manifest.get("audit_task_credit") is not False
        or receipt.get("audit_task_credit", False) is not False
        or set(receipt.get("branches", {})) != {"CLEAN", "MESSY"}
        or receipt["branches"]["CLEAN"] == receipt["branches"]["MESSY"]
    ):
        raise PortfolioVerificationError(f"{source.key} manifest or branch limit differs")
    own = _run_verifier(source, run, repository, private)
    if (
        own.get("audit_task_credit") is not False
        or own.get("native_version_count") != source.native_versions
    ):
        raise PortfolioVerificationError(f"{source.key} own verifier differs")
    with sqlite3.connect(db_path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise PortfolioVerificationError(f"{source.key} native SQLite integrity failed")
        if any(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("grants", "access_events", "collections")
        ):
            raise PortfolioVerificationError(f"{source.key} contains audit access")
        versions = db.execute("SELECT COUNT(*) FROM versions").fetchone()[0]
        native = db.execute(
            "SELECT company,branch,COUNT(*) FROM versions GROUP BY company,branch"
        ).fetchall()
        systems = db.execute(
            "SELECT company,branch,COUNT(*) FROM systems GROUP BY company,branch"
        ).fetchall()
    if versions != source.native_versions or len(native) != 2 or len(systems) != 2:
        raise PortfolioVerificationError(f"{source.key} selected native population differs")
    company_ids = {company for company, _, _ in native}
    if (
        len(company_ids) != 1
        or {branch for _, branch, _ in native} != set(receipt["branches"].values())
        or {branch for _, branch, _ in systems} != set(receipt["branches"].values())
        or any(n < 1 for *_, n in native + systems)
    ):
        raise PortfolioVerificationError(f"{source.key} physical company/branch route differs")
    if (
        {name: historical._digest(path) for name, path in paths.items()} != hashes
        or {name: historical._identity(path) for name, path in paths.items()} != identities
        or historical._digest(review) != source.review_sha256
    ):
        raise PortfolioVerificationError(f"{source.key} frozen source changed during verification")
    return {
        "source": source.key,
        "run": f"{source.folder}/{source.run}",
        "review_sha256": source.review_sha256,
        "manifest_sha256": source.manifest_sha256,
        "receipt_sha256": source.receipt_sha256,
        "database_sha256": source.database_sha256,
        "native_versions": versions,
        "branch_versions": {branch: n for _, branch, n in native},
        "physical_company_ids": sorted(company_ids),
        "audit_task_credit": False,
    }


def verify_all(repository: Path, *, private_repository: Path | None = None) -> dict:
    """Reperform V1 and five exact reviewed sources; return a partial diagnostic."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository or repository).resolve(strict=True)
    prior = historical.verify_all(repository, private_repository=private)
    if (
        prior["source_count"],
        prior["native_versions"],
        prior["source_complete"],
        prior["audit_task_credit"],
    ) != (10, 178, False, False):
        raise PortfolioVerificationError("Historical ten-source checkpoint differs")
    rows = list(prior["sources"])
    rows.extend(_verify_extra(source, repository, private) for source in EXTRA_SOURCES)
    if (
        len(rows) != 15
        or sum(row["native_versions"] for row in rows) != 256
        or len({row["source"] for row in rows}) != 15
    ):
        raise PortfolioVerificationError("Partial fifteen-source roster differs")
    return {
        "schema": "SH_FICTIONAL_2027_REVIEWED_SOURCE_PORTFOLIO_DIAGNOSTIC_V2",
        "status": "PARTIAL_REVIEWED_NATIVE_SOURCES_NOT_AUDIT_READY",
        "as_of": "2026-09-29",
        "verifier_module_sha256": historical._digest(Path(__file__)),
        "historical_v1_verifier_sha256": prior["verifier_module_sha256"],
        "source_count": 15,
        "native_versions": 256,
        "sources": rows,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": [
            "Future fictional 2027 source events authored in 2026; no real operating year.",
            "Selected 15 cohorts only; 283 documentary/activity routes per side remain unresolved.",
            "No audit grants, collections, task credit, Key, grade or source-complete registry.",
            "Physical company IDs and Clean/Messy source branches remain explicit.",
            "Reviewed policy cohort remains a selected local source, not complete policy coverage.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--private-repository", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            verify_all(args.repository, private_repository=args.private_repository),
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
