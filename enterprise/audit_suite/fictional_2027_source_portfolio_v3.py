"""Read-only, partial successor for 21 independently reviewed 2027 cohorts."""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from . import company_eth003_speakup_activity as eth003
from . import company_eth004_conflict_activity as eth004
from . import company_iam005_local_trace_2027 as iam005
from . import company_ppl002_screening_gate as ppl002
from . import company_product_customer_internal_2027_simulation as prd
from . import emergency_change_source_verifier as eng005
from . import fictional_2027_source_portfolio_v2 as prior
from .fictional_2027_source_portfolio import (
    BASE,
    PortfolioVerificationError,
    _digest,
    _identity,
    _private,
    _read_json,
)


@dataclass(frozen=True)
class NewSource:
    key: str
    folder: str
    run: str
    review: str
    verdict: str
    review_sha256: str
    manifest_name: str
    receipt_name: str
    manifest_sha256: str
    receipt_sha256: str
    databases: tuple[tuple[str, str], ...]
    branches: tuple[str, str]
    branch_counts: tuple[int, int]
    system_counts: tuple[int, ...]


NEW_SOURCES = (
    NewSource(
        "eng005",
        "company-emergency-change-2027-simulation-2026-09-29",
        "run-v1",
        "company-emergency-change-verifier-2026-09-29/independent-review-v2/REVIEW.json",
        "PASS_SELECTED_PHYSICAL_SOURCE_GAP_CHECK_NO_AUDIT_CREDIT",
        "3719b01d86d4bd3451e712ba209342abe4da354454476e5cb6e2000629cf78ce",
        "RUN-MANIFEST.json",
        "SOURCE_RECEIPT.json",
        "a941aff10990a59bbd964c88e3029006c02b726ec55f2f37a3c44bf6794bd9ad",
        "efa67bb2cf9934a62e91ea51b109e61f2954bbb8b83ef84e2c5f1e6f344d78d9",
        (("native", "123599b469c7d5799fd1c068739e76c7e73501c5e2bb8cac6170205ee53a64a0"),),
        ("ENG005-CLEAN", "ENG005-MESSY"),
        (8, 11),
        (4,),
    ),
    NewSource(
        "prd",
        "company-prd-internal-customer-2026-09-29",
        "run-v2",
        "company-prd-internal-customer-2026-09-29/independent-review-v2/REVIEW.json",
        "PASS_BOUNDED_FICTIONAL_SOURCE_FOR_INTEGRATION",
        "5f5289ec43d7644f4e623ca7dbf13896f807f351d5488461dc5ba257119f9122",
        "MANIFEST.json",
        "RECEIPT.json",
        "438e21b197d7768a23912cf5850b076ec1ddb35b564e885fd144acd9ca9c9d2b",
        "81b5a7f15636f824c6c48c449c726c1176d95c4ce7e70105b813730dc2b17842",
        (("native", "a0ebf7b743f530408ea497abb791b2991694f65f5b076b933c16fc8a61318507"),),
        ("PRD-CLEAN", "PRD-MESSY"),
        (5, 10),
        (8,),
    ),
    NewSource(
        "eth004",
        "company-eth004-conflict-2026-09-29",
        "run-v1",
        "company-eth004-conflict-2026-09-29/independent-review-v1/REVIEW.json",
        "PASS_PRIVATE_SELECTED_FICTIONAL_SOURCE_NO_AUDIT_CREDIT",
        "82d6f7007fccb77f2808069f3b97bf4ebfa4e001cc8cb7f838775ca0b4c97604",
        "RUN-MANIFEST.json",
        "SOURCE_RECEIPT.json",
        "2d119428e36d7f79b0dd658ab4ed889c655d2f066b15f442d401c2b21c50d72a",
        "77551779dca444c96a8cdd9430559897aef700fc1233b68de78afa2c6f2d2179",
        (("native", "262ce124e2066843d180d97ab308d7f78cbda2a7c1f51295cd50f05d2206558c"),),
        ("ETH004-CLEAN", "ETH004-MESSY"),
        (6, 7),
        (3,),
    ),
    NewSource(
        "eth003",
        "company-eth003-speakup-2026-09-29",
        "run-v1",
        "company-eth003-speakup-2026-09-29/independent-review-v1/REVIEW.json",
        "PASS_BOUNDED_FICTIONAL_SOURCE_FOR_INTEGRATION",
        "1dcf8b57b9e665bc496b03659ad37e50de9b81c40be43478425290fc8362046d",
        "RUN-MANIFEST.json",
        "SOURCE_RECEIPT.json",
        "33ca02377b6520ce6a8f2094ef51fae015766dbe56a46c3a8a487c957c2a95bf",
        "0695f0d1da9a943570007ebfa79158b1879ac43267b5bc1b612ed13b5cd6e8e5",
        (("native", "395fe76db63d346dddff577e3090df1f92941b675db2eaedb19b1bea2c7d4804"),),
        ("ETH003-CLEAN", "ETH003-MESSY"),
        (6, 8),
        (4,),
    ),
    NewSource(
        "ppl002",
        "company-ppl002-screening-gate-2026-09-29",
        "run-v1",
        "company-ppl002-screening-gate-2026-09-29/independent-review-v1/REVIEW.json",
        "PASS_BOUNDED_FICTIONAL_NEGATIVE_GATE_FOR_INTEGRATION",
        "1d3ad3fd6ca61c5a31f18c601e1f21c18eea4c37efafc58f8e77425f55a8e8b0",
        "RUN-MANIFEST.json",
        "SOURCE_RECEIPT.json",
        "c15bc455ff45dad56403655fdde39b1778ab86b76d237d303f149eaf087af467",
        "21e65ed9b762cc0ff71b4733fe9feae874da2d15b89f5f9e584e265370a4bb80",
        (("native", "86d9c1bd229d275cf8c32e0d06e166f5a4c62cbb3fdc75b2734c374cf71da697"),),
        ("PPL002-CLEAN", "PPL002-MESSY"),
        (5, 7),
        (3,),
    ),
    NewSource(
        "iam005",
        "company-iam005-local-trace-2026-09-29",
        "run-v1",
        "company-iam005-local-trace-2026-09-29/independent-review-v1/REVIEW.json",
        "PASS_BOUNDED_FICTIONAL_LOCAL_SOURCE_FOR_INTEGRATION",
        "3c7a90b412743fec9b6d6fd8a291358a3a4d672386a3237e60c197d57e55547f",
        "MANIFEST.json",
        "RECEIPT.json",
        "c0ba05b1e841ba09ee3f3b86e741a456d43948795854a4a06509cdc7f08f3f11",
        "9d4365455ef3b0964fbe1e03999a75f5ca16053c990c63590cddb9c8dedd1536",
        (
            ("human", "6db57dc7695f8f9c3421c40fa94e3f535bb752bddd50f7af3ab6dc6b26adbb47"),
            ("service", "b2fdd1138f956e1f6c5ec307fdb2fd6de7fdd275a1401863d24601907f96b67a"),
        ),
        ("IAM005-TRACE-CLEAN", "IAM005-TRACE-MESSY"),
        (13, 16),
        (3, 4),
    ),
)


def _db_path(run: Path, ledger: str) -> Path:
    return run / ("company.sqlite3" if ledger == "native" else f"{ledger}/company.sqlite3")


def _own(source: NewSource, run: Path, repository: Path, private: Path) -> dict:
    if source.key == "eng005":
        return eng005.verify(repository, private_repository=private)
    module = {"prd": prd, "eth004": eth004, "eth003": eth003, "ppl002": ppl002, "iam005": iam005}[
        source.key
    ]
    return module.verify(run, repository=repository, private_repository=private)


def _branches(source: NewSource, receipt: dict) -> dict:
    if source.key == "eng005":
        value = {"CLEAN": receipt.get("clean_branch"), "MESSY": receipt.get("messy_branch")}
    else:
        key = "branch_ids" if source.key in {"eth004", "eth003", "ppl002"} else "branches"
        value = receipt.get(key)
    if value != dict(zip(("CLEAN", "MESSY"), source.branches, strict=True)):
        raise PortfolioVerificationError(f"{source.key} physical branch declaration differs")
    return value


def _manifest(source: NewSource, manifest: dict) -> None:
    expected = dict(source.databases)
    if source.key in {"eng005", "eth004", "eth003", "ppl002"}:
        keys = ("source_receipt_sha256", "native_db_sha256")
    elif source.key == "iam005":
        keys = ("receipt_sha256", "human_db_sha256", "service_db_sha256")
    else:
        keys = ("receipt_sha256", "company_db_sha256")
    values = (source.receipt_sha256, *expected.values())
    if any(manifest.get(key) != value for key, value in zip(keys, values, strict=True)):
        raise PortfolioVerificationError(f"{source.key} manifest source hashes differ")
    if manifest.get("audit_task_credit") is not False:
        raise PortfolioVerificationError(f"{source.key} manifest grants audit credit")
    count = manifest.get(
        "record_count", manifest.get("native_count", manifest.get("native_version_count"))
    )
    if count != sum(source.branch_counts):
        raise PortfolioVerificationError(f"{source.key} manifest native count differs")


def _verify_new(source: NewSource, repository: Path, private: Path) -> dict:
    folder = private / BASE / source.folder
    run = folder / source.run
    review = private / BASE / source.review
    for directory in (folder, run, review.parent):
        _private(directory, directory=True)
    manifest_path, receipt_path = run / source.manifest_name, run / source.receipt_name
    files = {"manifest": manifest_path, "receipt": receipt_path}
    files.update({ledger: _db_path(run, ledger) for ledger, _ in source.databases})
    for path in (review, *files.values()):
        _private(path)
    if (
        _digest(review) != source.review_sha256
        or _read_json(review).get("verdict") != source.verdict
    ):
        raise PortfolioVerificationError(f"{source.key} independent review differs")
    expected_hashes = {
        "manifest": source.manifest_sha256,
        "receipt": source.receipt_sha256,
        **dict(source.databases),
    }
    before = {name: _identity(path) for name, path in files.items()}
    if {name: _digest(path) for name, path in files.items()} != expected_hashes:
        raise PortfolioVerificationError(f"{source.key} reviewed source bytes differ")
    manifest, receipt = _read_json(manifest_path), _read_json(receipt_path)
    _manifest(source, manifest)
    branches = _branches(source, receipt)
    if receipt.get("audit_task_credit") is not False:
        raise PortfolioVerificationError(f"{source.key} receipt grants audit credit")
    own = _own(source, run, repository, private)
    if own.get("audit_task_credit") is not False:
        raise PortfolioVerificationError(f"{source.key} own verifier grants audit credit")
    db_rows = {}
    for ledger, _sha in source.databases:
        path = files[ledger]
        if ledger != "native":
            _private(path.parent, directory=True)
        if any(
            Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
            for suffix in ("-wal", "-shm", "-journal")
        ):
            raise PortfolioVerificationError(f"{source.key}/{ledger} native database has sidecar")
        with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
            db.execute("PRAGMA query_only=ON")
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok" or any(
                db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("grants", "access_events", "collections")
            ):
                raise PortfolioVerificationError(
                    f"{source.key}/{ledger} integrity or audit access differs"
                )
            native = db.execute(
                "SELECT company,branch,COUNT(*) FROM versions GROUP BY company,branch"
            ).fetchall()
            systems = db.execute(
                "SELECT company,branch,COUNT(*) FROM systems GROUP BY company,branch"
            ).fetchall()
        if len(native) != 2 or len(systems) != 2:
            raise PortfolioVerificationError(f"{source.key}/{ledger} branch population differs")
        db_rows[ledger] = {
            "versions": {branch: count for _, branch, count in native},
            "systems": {branch: count for _, branch, count in systems},
            "company_ids": sorted({company for company, _, _ in native + systems}),
        }
        if db_rows[ledger]["company_ids"] != ["SABLE-HARBOR-REFERENCE"]:
            raise PortfolioVerificationError(f"{source.key}/{ledger} physical company differs")
    for scenario, branch in branches.items():
        if (
            sum(item["versions"].get(branch, 0) for item in db_rows.values())
            != source.branch_counts[("CLEAN", "MESSY").index(scenario)]
        ):
            raise PortfolioVerificationError(f"{source.key} selected branch versions differ")
        if any(
            item["systems"].get(branch) != count
            for item, count in zip(db_rows.values(), source.system_counts, strict=True)
        ):
            raise PortfolioVerificationError(f"{source.key} selected branch systems differ")
    if any(
        set(item["versions"]) != set(branches.values())
        or set(item["systems"]) != set(branches.values())
        for item in db_rows.values()
    ):
        raise PortfolioVerificationError(f"{source.key} unexpected native branch differs")
    if {name: _identity(path) for name, path in files.items()} != before or _digest(
        review
    ) != source.review_sha256:
        raise PortfolioVerificationError(f"{source.key} source changed during re-performance")
    return {
        "source": source.key,
        "run": f"{source.folder}/{source.run}",
        "review_sha256": source.review_sha256,
        "manifest_sha256": source.manifest_sha256,
        "receipt_sha256": source.receipt_sha256,
        "database_sha256": dict(source.databases),
        "native_versions": sum(source.branch_counts),
        "branch_versions": dict(zip(source.branches, source.branch_counts, strict=True)),
        "physical_company_ids": ["SABLE-HARBOR-REFERENCE"],
        "ledger_system_counts": dict(
            zip((ledger for ledger, _ in source.databases), source.system_counts, strict=True)
        ),
        "audit_task_credit": False,
    }


def verify_all(repository: Path, *, private_repository: Path | None = None) -> dict:
    """Reperform V2 and six reviewed additions; still no source-complete claim."""
    repository = Path(repository).resolve(strict=True)
    private = Path(private_repository or repository).resolve(strict=True)
    previous = prior.verify_all(repository, private_repository=private)
    if (
        previous["source_count"],
        previous["native_versions"],
        previous["source_complete"],
        previous["audit_task_credit"],
    ) != (15, 256, False, False):
        raise PortfolioVerificationError("Reviewed V2 checkpoint differs")
    sources = list(previous["sources"])
    sources.extend(_verify_new(source, repository, private) for source in NEW_SOURCES)
    if (
        len(sources) != 21
        or sum(row["native_versions"] for row in sources) != 358
        or len({row["source"] for row in sources}) != 21
    ):
        raise PortfolioVerificationError("Expected partial 21-source/358-version roster differs")
    return {
        "schema": "SH_FICTIONAL_2027_REVIEWED_SOURCE_PORTFOLIO_DIAGNOSTIC_V3",
        "status": "PARTIAL_REVIEWED_NATIVE_SOURCES_NOT_AUDIT_READY",
        "as_of": "2026-09-29",
        "verifier_module_sha256": _digest(Path(__file__)),
        "v2_verifier_sha256": previous["verifier_module_sha256"],
        "source_count": 21,
        "native_versions": 358,
        "source_component_count": 22,
        "sources": sources,
        "source_complete": False,
        "fresh_audit_pair_created": False,
        "audit_task_credit": False,
        "limits": [
            "Twenty-one selected future-fictional source cohorts, not an enterprise population.",
            "IAM005 has separate human/service physical databases; no silent ledger merge.",
            "Authored 2027 events remain future as of 2026-09-29; "
            "imported_at is actual source creation.",
            "No fresh audit pair, grant, collection, task credit, Key or grade.",
            "Frozen 283 documentary/activity routes per side remain unresolved.",
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
