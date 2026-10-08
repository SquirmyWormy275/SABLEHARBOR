"""Fail-closed checks for a partial, no-credit source portfolio diagnostic."""

import json
from pathlib import Path

import pytest

from enterprise.audit_suite import fictional_2027_source_portfolio as portfolio
from enterprise.audit_suite.company_store import CompanyStore


def _source(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    tmp_path.chmod(0o700)
    folder = tmp_path / portfolio.BASE / "fake"
    run = folder / "run-v1"
    review_dir = folder / "independent-review-v1"
    run.mkdir(parents=True, mode=0o700)
    review_dir.mkdir(mode=0o700)
    for parent in (tmp_path / "enterprise", tmp_path / portfolio.BASE, folder):
        parent.chmod(0o700)
    store = CompanyStore(run)
    store.register_system("SABLE-HARBOR-REFERENCE", "CLEAN", "records", "OWNER")
    store.append_version(
        "SABLE-HARBOR-REFERENCE",
        "CLEAN",
        "records",
        "R1",
        expected_version=0,
        command_id="APPEND-1",
        event_at="2027-01-01T00:00:00Z",
        available_at="2027-01-01T00:00:00Z",
        content=b"selected fictional record",
        provenance={"source_reference": "test"},
    )
    receipt = run / "RECEIPT.json"
    receipt.write_text("{}\n")
    receipt.chmod(0o600)
    manifest = run / "MANIFEST.json"
    manifest.write_text(
        json.dumps(
            {
                "company_db_sha256": portfolio._digest(run / "company.sqlite3"),
                "receipt_sha256": portfolio._digest(receipt),
                "audit_task_credit": False,
            }
        )
    )
    manifest.chmod(0o600)
    review = review_dir / "REVIEW.json"
    review.write_text('{"verdict":"PASS_PRIVATE_TEST"}\n')
    review.chmod(0o600)
    monkeypatch.setattr(
        portfolio,
        "SOURCES",
        (
            portfolio.Source(
                "fake",
                "fake",
                "run-v1",
                "independent-review-v1/REVIEW.json",
                portfolio._digest(review),
            ),
        ),
    )
    monkeypatch.setattr(
        portfolio,
        "_run_verifier",
        lambda *_args: {"audit_task_credit": False, "native_version_count": 1},
    )
    return run, review


def test_diagnostic_preserves_no_credit_and_rejects_review_tamper(tmp_path, monkeypatch):
    _, review = _source(tmp_path, monkeypatch)
    report = portfolio.verify_all(tmp_path)
    assert report["source_count"] == report["native_versions"] == 1
    assert report["source_complete"] is report["audit_task_credit"] is False
    review.write_text('{"verdict":"PASS_CHANGED"}\n')
    with pytest.raises(portfolio.PortfolioVerificationError, match="review hash differs"):
        portfolio.verify_all(tmp_path)


def test_diagnostic_rejects_uncheckpointed_source_sidecar(tmp_path, monkeypatch):
    run, _ = _source(tmp_path, monkeypatch)
    sidecar = run / "company.sqlite3-wal"
    sidecar.write_bytes(b"uncheckpointed")
    sidecar.chmod(0o600)
    with pytest.raises(portfolio.PortfolioVerificationError, match="active sidecar"):
        portfolio.verify_all(tmp_path)
