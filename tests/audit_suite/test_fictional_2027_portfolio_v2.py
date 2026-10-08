"""Exact reviewed roster, branch routes and no-credit candidate checks."""

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_candidate_registry_v2 as candidate
from enterprise.audit_suite import fictional_2027_source_portfolio_v2 as portfolio

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


def test_fifteen_reviewed_sources_keep_physical_branches_distinct():
    report = portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)
    assert (report["source_count"], report["native_versions"]) == (15, 256)
    assert report["source_complete"] is report["audit_task_credit"] is False
    assert [(r["source"], r["native_versions"]) for r in report["sources"][10:]] == [
        ("contract", 4),
        ("retention", 8),
        ("integrity", 29),
        ("bcm", 18),
        ("policy", 19),
    ]
    for source in report["sources"][10:]:
        assert source["audit_task_credit"] is False
        assert len(source["physical_company_ids"]) == 1
        assert len(source["branch_versions"]) == 2
        assert all(n >= 1 for n in source["branch_versions"].values())


def test_static_review_pin_and_uncheckpointed_sidecar_fail(tmp_path):
    source = portfolio.EXTRA_SOURCES[0]
    wrong_review = replace(source, review_sha256="0" * 64)
    with pytest.raises(portfolio.PortfolioVerificationError, match="review hash differs"):
        portfolio._verify_extra(wrong_review, REPOSITORY, PRIVATE)

    clone = tmp_path / "private-copy"
    clone.mkdir(mode=0o700)
    original = PRIVATE / portfolio.BASE / source.folder
    target = clone / portfolio.BASE / source.folder
    target.parent.mkdir(parents=True, mode=0o700)
    for parent in (clone / "enterprise", clone / portfolio.BASE):
        parent.chmod(0o700)
    shutil.copytree(original, target)
    sidecar = target / source.run / "company.sqlite3-wal"
    sidecar.write_bytes(b"uncheckpointed source change")
    sidecar.chmod(0o600)
    with pytest.raises(portfolio.PortfolioVerificationError, match="sidecar"):
        portfolio._verify_extra(source, REPOSITORY, clone)


def test_private_candidate_is_partial_and_reconstruction_rejects_tamper(tmp_path):
    destination = tmp_path / "candidate"
    report = candidate.write_candidate(REPOSITORY, PRIVATE, destination)
    assert report["reviewed_native_versions"] == 256
    assert report["source_complete"] is report["audit_task_credit"] is False
    assert report["grants_or_collections_created"] is False
    for side in "AB":
        row = report["sides"][side]
        assert (row["component_count"], row["scenario_source_count"]) == (28, 15)
        assert row["system_alias_count"] == 182
        assert row["source_complete"] is False
        assert len({pin["source"] for pin in row["source_pins"]}) == 15
    assert candidate.verify_candidate(destination, REPOSITORY, PRIVATE) == report
    path = destination / "A.json"
    manifest = json.loads(path.read_text())
    manifest["profiles"][report["sides"]["A"]["profile_id"]]["qualification"] = "FALSE"
    path.write_text(json.dumps(manifest, sort_keys=True))
    path.chmod(0o600)
    with pytest.raises(candidate.CandidateRegistryError, match="manifest differs"):
        candidate.verify_candidate(destination, REPOSITORY, PRIVATE)
