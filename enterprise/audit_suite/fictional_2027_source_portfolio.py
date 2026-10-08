"""Read-only verification of reviewed fictional 2027 company source cohorts.

This does not create a company source, audit registry, engagement or evidence.
Its fixed roster is deliberately partial and must never certify coverage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import stat
from dataclasses import dataclass
from pathlib import Path

from . import (
    company_assurance_findings_exercise as assurance,
)
from . import (
    company_controlled_record_exercise as controlled_record,
)
from . import (
    company_critical_role_2027_simulation as critical_role,
)
from . import (
    company_dataset_classification_exercise as dataset,
)
from . import (
    company_phi_ba_2027_simulation as phi_ba,
)
from . import (
    company_processing_purpose_2027_simulation as processing,
)
from . import (
    company_provider_lifecycle_2027_simulation as provider,
)
from . import (
    company_risk_governance_stagegate_exercise as stagegate,
)
from . import (
    company_runtime_transition_exercise as transition,
)
from . import (
    company_source_extraction_exercise as extraction,
)

BASE = Path("enterprise/generated/audit-suite")
TRAINING_ROOT = BASE / "company-training-2026-09-14/company"


class PortfolioVerificationError(ValueError):
    """A source or independent review differs from the selected checkpoint."""


@dataclass(frozen=True)
class Source:
    key: str
    folder: str
    run: str
    review: str
    review_sha256: str


SOURCES = (
    Source(
        "transition",
        "company-runtime-transition-2026-09-29",
        "run-v3",
        "independent-review-v3/REVIEW.json",
        "f1acaeaea963055f99b0de120fd1b0347ee984edf085d353e7af1e427234d5a9",
    ),
    Source(
        "phi_ba",
        "company-phi-ba-2027-simulation-2026-09-29",
        "run-v1",
        "independent-review-v1/REVIEW.json",
        "39bb9b071179ed672c5cf07c2867285d36b2f3e8cdce2106dc4472d17047911e",
    ),
    Source(
        "provider",
        "company-provider-lifecycle-2026-09-29",
        "run-v2",
        "independent-review-v1/REVIEW.json",
        "bde642fd35fd4412bda49867b4d7961289bc97deae216bb56e325a19f371b634",
    ),
    Source(
        "stagegate",
        "company-risk-governance-stagegate-2026-09-29",
        "run-v2",
        "independent-review-v2/REVIEW.json",
        "78dbf2b9585efd8f51a08a598d6c56aa342ef7845b56e6c0892a239a968fde34",
    ),
    Source(
        "assurance",
        "company-assurance-findings-2026-09-29",
        "run-v1",
        "independent-review-v1/REVIEW.json",
        "23033dcf6641d18038bc58a1e02fd1b014a4e550fe0ae78bd854e1f7f5552f58",
    ),
    Source(
        "critical_role",
        "company-critical-role-2027-simulation-2026-09-29",
        "run-v3",
        "independent-review-v3/REVIEW.json",
        "582d9250cc923efd720c36b68a44ced544bf8d453cc30816042afeecfdc52aa6",
    ),
    Source(
        "dataset",
        "company-dataset-classification-2026-09-29",
        "run-v1",
        "independent-review-v1/REVIEW.json",
        "4d1cd9c423781bf97ff586075c460c891cc60f621b42a29a22db59df929ff52e",
    ),
    Source(
        "controlled_record",
        "company-controlled-record-2026-09-29",
        "run-v1",
        "independent-review-v1/REVIEW.json",
        "968187ce495df23b72b6fe7e2d58b9ff017be42927cc0f3f1881d5e6669cd989",
    ),
    Source(
        "extraction",
        "company-source-extraction-2026-09-29",
        "run-v1",
        "independent-review-v1/REVIEW.json",
        "b2940aaedb5721d91367503c997eceece71a53370e67335985cb77ea95165a4d",
    ),
    Source(
        "processing",
        "company-processing-purpose-2027-simulation-2026-09-29",
        "run-v1",
        "independent-review-v2/REVIEW.json",
        "d768b1fa01d7e2a1b56326c5a0ba14df61564d7e4cc9ccee208f0996b4f050f1",
    ),
)


def _digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            result.update(block)
    return result.hexdigest()


def _identity(path: Path) -> tuple[int, int, int, int, int]:
    info = path.stat()
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IMODE(info.st_mode),
        info.st_size,
        info.st_mtime_ns,
    )


def _private(path: Path, *, directory: bool = False) -> None:
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise PortfolioVerificationError("Private source cannot contain symlinks")
    info = path.stat()
    if info.st_mode & 0o077 or not (
        stat.S_ISDIR(info.st_mode)
        if directory
        else stat.S_ISREG(info.st_mode) and info.st_nlink == 1
    ):
        raise PortfolioVerificationError("Private regular source/review required")


def _pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise PortfolioVerificationError("Duplicate receipt/review field")
        result[key] = value
    return result


def _read_json(path: Path) -> dict:
    _private(path)
    value = json.loads(path.read_bytes(), object_pairs_hook=_pairs)
    if not isinstance(value, dict):
        raise PortfolioVerificationError("Expected private JSON object")
    return value


def _run_verifier(key: str, run: Path, repository: Path, private_repository: Path) -> dict:
    transition_root = private_repository / BASE / SOURCES[0].folder / SOURCES[0].run
    phi_root = private_repository / BASE / SOURCES[1].folder / SOURCES[1].run
    if key == "transition":
        return transition.verify(run, repository=repository)
    if key == "phi_ba":
        return phi_ba.verify(run, transition_root=transition_root, repository=repository)
    if key == "provider":
        return provider.verify(
            run, repository=repository, transition_root=transition_root, phi_root=phi_root
        )
    if key == "stagegate":
        return stagegate.verify(run, repository=repository, private_repository=private_repository)
    if key == "assurance":
        return assurance.verify(run, repository=repository, private_repository=private_repository)
    if key == "critical_role":
        return critical_role.verify(
            run, repository=repository, training_root=private_repository / TRAINING_ROOT
        )
    if key == "dataset":
        return dataset.verify(run, repository=repository, private_repository=private_repository)
    if key == "controlled_record":
        return controlled_record.verify(
            run, repository=repository, private_repository=private_repository
        )
    if key == "extraction":
        return extraction.verify(run, repository=repository, private_repository=private_repository)
    if key == "processing":
        return processing.verify(run, repository=repository, private_repository=private_repository)
    raise PortfolioVerificationError("Unknown fixed source cohort")


def verify_all(repository: Path, *, private_repository: Path | None = None) -> dict:
    """Reperform selected source verifiers and return a no-credit diagnostic."""
    repository = Path(repository).resolve()
    private_repository = Path(private_repository or repository).resolve()
    rows = []
    for source in SOURCES:
        folder = private_repository / BASE / source.folder
        run = folder / source.run
        review = folder / source.review
        _private(folder, directory=True)
        _private(run, directory=True)
        _private(review.parent, directory=True)
        _private(review)
        if _digest(review) != source.review_sha256:
            raise PortfolioVerificationError(f"{source.key} independent review hash differs")
        verdict = _read_json(review).get("verdict")
        if not isinstance(verdict, str) or not verdict.startswith("PASS"):
            raise PortfolioVerificationError(f"{source.key} independent review did not pass")
        paths = {name: run / name for name in ("MANIFEST.json", "RECEIPT.json", "company.sqlite3")}
        for path in paths.values():
            _private(path)
        db_path = paths["company.sqlite3"]
        if any(
            Path(str(db_path) + suffix).exists() or Path(str(db_path) + suffix).is_symlink()
            for suffix in ("-wal", "-shm", "-journal")
        ):
            raise PortfolioVerificationError(f"{source.key} database has an active sidecar")
        before = {name: _digest(path) for name, path in paths.items()}
        identities = {name: _identity(path) for name, path in paths.items()}
        manifest = _read_json(paths["MANIFEST.json"])
        _read_json(paths["RECEIPT.json"])
        if (
            manifest.get("company_db_sha256") != before["company.sqlite3"]
            or manifest.get("receipt_sha256") != before["RECEIPT.json"]
            or manifest.get("audit_task_credit") is not False
        ):
            raise PortfolioVerificationError(f"{source.key} manifest does not pin source bytes")
        result = _run_verifier(source.key, run, repository, private_repository)
        if not isinstance(result, dict) or result.get("audit_task_credit") is not False:
            raise PortfolioVerificationError(f"{source.key} verifier gave audit credit")
        if {name: _digest(path) for name, path in paths.items()} != before:
            raise PortfolioVerificationError(f"{source.key} source changed during verification")
        if {name: _identity(path) for name, path in paths.items()} != identities:
            raise PortfolioVerificationError(f"{source.key} source identity changed")
        if _digest(review) != source.review_sha256:
            raise PortfolioVerificationError(f"{source.key} review changed during verification")
        with sqlite3.connect(db_path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
            db.execute("PRAGMA query_only=ON")
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise PortfolioVerificationError(f"{source.key} database integrity failed")
            if any(
                db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("grants", "collections", "access_events")
            ):
                raise PortfolioVerificationError(f"{source.key} contains audit access")
            versions = db.execute("SELECT COUNT(*) FROM versions").fetchone()[0]
            companies = sorted(
                row[0] for row in db.execute("SELECT DISTINCT company FROM versions")
            )
        if (
            {name: _digest(path) for name, path in paths.items()} != before
            or {name: _identity(path) for name, path in paths.items()} != identities
        ):
            raise PortfolioVerificationError(f"{source.key} source changed during database read")
        expected = result.get("native_version_count", result.get("source_version_count"))
        if versions != expected:
            raise PortfolioVerificationError(f"{source.key} native count differs")
        rows.append(
            {
                "source": source.key,
                "run": f"{source.folder}/{source.run}",
                "review_sha256": source.review_sha256,
                "manifest_sha256": before["MANIFEST.json"],
                "receipt_sha256": before["RECEIPT.json"],
                "database_sha256": before["company.sqlite3"],
                "native_versions": versions,
                "physical_company_ids": companies,
                "audit_task_credit": False,
            }
        )
    return {
        "schema": "SH_FICTIONAL_2027_REVIEWED_SOURCE_PORTFOLIO_DIAGNOSTIC_V1",
        "status": "PARTIAL_REVIEWED_NATIVE_SOURCES_NOT_AUDIT_READY",
        "as_of": "2026-09-29",
        "verifier_module_sha256": _digest(Path(__file__)),
        "source_count": len(rows),
        "native_versions": sum(row["native_versions"] for row in rows),
        "sources": rows,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": [
            "Future fictional 2027 source events authored in 2026; no real operating year.",
            "Selected source cohorts only; 283 routes per side remain unresolved.",
            "No audit grants, collections, task credit, Key or source-complete registry.",
            "Reference-world company IDs are not actual Sable Harbor operation.",
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
