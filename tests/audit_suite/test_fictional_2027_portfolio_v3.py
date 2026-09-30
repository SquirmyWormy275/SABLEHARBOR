"""Reviewed V3 partial roster and distinct IAM source ledger routing."""

import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_candidate_registry_v3 as candidate
from enterprise.audit_suite import fictional_2027_source_portfolio_v2 as previous
from enterprise.audit_suite import fictional_2027_source_portfolio_v3 as portfolio

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


def test_exact_reviewed_roster_preserves_v2_and_separate_iam_ledgers():
    before = previous.verify_all(REPOSITORY, private_repository=PRIVATE)
    report = portfolio.verify_all(REPOSITORY, private_repository=PRIVATE)
    assert report["sources"][:15] == before["sources"]
    assert [row["source"] for row in report["sources"][15:]] == [
        "eng005",
        "prd",
        "eth004",
        "eth003",
        "ppl002",
        "iam005",
    ]
    assert report["source_count"] == 21
    assert report["native_versions"] == 358
    assert report["source_component_count"] == 22
    iam = report["sources"][-1]
    assert set(iam["database_sha256"]) == {"human", "service"}
    assert iam["ledger_system_counts"] == {"human": 3, "service": 4}
    assert iam["branch_versions"] == {"IAM005-TRACE-CLEAN": 13, "IAM005-TRACE-MESSY": 16}
    assert report["source_complete"] is report["audit_task_credit"] is False


def test_candidate_has_exact_private_noncredit_routes(tmp_path):
    tmp_path.chmod(0o700)
    root = tmp_path / "candidate-v3"
    report = candidate.write_candidate(REPOSITORY, PRIVATE, root)
    assert report == candidate.verify_candidate(root, REPOSITORY, PRIVATE)
    assert report["reviewed_native_versions"] == 358
    assert report["source_complete"] is report["audit_task_credit"] is False
    for side in "AB":
        row = report["sides"][side]
        assert (
            row["component_count"],
            row["source_cohort_count"],
            row["scenario_source_component_count"],
            row["system_alias_count"],
        ) == (35, 21, 22, 211)
        assert {pin["ledger"] for pin in row["source_pins"] if pin["source"] == "iam005"} == {
            "human",
            "service",
        }
    assert set((root / "A.json").parent.iterdir()) == {
        root / "A.json",
        root / "B.json",
        root / "REPORT.json",
    }


def test_independent_review_pin_rejected():
    altered = replace(portfolio.NEW_SOURCES[0], review_sha256="0" * 64)
    with pytest.raises(portfolio.PortfolioVerificationError, match="independent review differs"):
        portfolio._verify_new(altered, REPOSITORY, PRIVATE)


def test_iam_human_component_rejects_active_sidecar(tmp_path):
    tmp_path.chmod(0o700)
    source = portfolio.NEW_SOURCES[-1]
    origin = PRIVATE / portfolio.BASE / source.folder
    target = tmp_path / portfolio.BASE / source.folder
    target.parent.mkdir(parents=True)
    for parent in (tmp_path / "enterprise", tmp_path / portfolio.BASE):
        parent.chmod(0o700)
    shutil.copytree(origin, target)
    for directory in (target, target / source.run, target / source.run / "human"):
        directory.chmod(0o700)
    for path in target.rglob("*"):
        if path.is_file():
            path.chmod(0o600)
        elif path.is_dir():
            path.chmod(0o700)
    component, pin = candidate._new_component(tmp_path, source, "CLEAN", "human")
    assert component["branch"] == "IAM005-TRACE-CLEAN"
    assert pin["ledger"] == "human" and pin["system_count"] == 3
    sidecar = target / source.run / "human/company.sqlite3-wal"
    sidecar.write_bytes(b"uncheckpointed source")
    sidecar.chmod(0o600)
    with pytest.raises(candidate.CandidateRegistryError, match="sidecar"):
        candidate._new_component(tmp_path, source, "CLEAN", "human")
