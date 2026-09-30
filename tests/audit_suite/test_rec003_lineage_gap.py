"""Existing local transform lineage is a bounded candidate, never audit credit."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.rec003_lineage_gap import _frozen, create, verify

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


def test_exact_existing_lineage_and_no_credit(tmp_path):
    root = tmp_path / "packet"
    assert create(root, repository=REPOSITORY, private_repository=PRIVATE) == verify(
        root, repository=REPOSITORY, private_repository=PRIVATE
    )
    packet = json.loads((root / "LINEAGE.json").read_text())
    assert {side: len(routes) for side, routes in packet["routes"].items()} == {
        "A": 4,
        "B": 4,
    }
    assert {
        side: len(branch["native_original_refs"]) for side, branch in packet["branches"].items()
    } == {
        "A": 11,
        "B": 11,
    }
    assert packet["branches"]["A"]["successor_transform"] == {
        "status": "LOCAL_RULES_PASSED_NOT_SOURCE_ACCEPTANCE",
        "accepted_rows_only_total": 23,
        "missing_usable_expected_ids": [],
    }
    assert packet["branches"]["B"]["successor_transform"] == {
        "status": "PARTIAL_UNRELIABLE",
        "accepted_rows_only_total": 21,
        "missing_usable_expected_ids": ["R4"],
    }
    assert packet["new_company_operation"] is False
    assert packet["audit_collection"] is False
    assert packet["audit_task_credit"] is False
    assert packet["branches"]["A"]["audit_journal_counts_excluded_from_company_lineage"] == {
        "grants": 12,
        "collections": 22,
        "access_events": 25,
    }


def test_frozen_business_source_rejects_sidecar(tmp_path):
    source = PRIVATE / (
        "enterprise/generated/audit-suite/company-data-quality-runtime-2026-09-22/"
        "run-v1/a/company.sqlite3"
    )
    clone = tmp_path / "company.sqlite3"
    shutil.copy2(source, clone)
    assert _frozen(clone)[-1] == hashlib.sha256(source.read_bytes()).hexdigest()
    sidecar = tmp_path / "company.sqlite3-wal"
    sidecar.write_bytes(b"uncheckpointed source")
    sidecar.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="active sidecar"):
        _frozen(clone)


def test_resealed_task_credit_rejected(tmp_path):
    root = tmp_path / "packet"
    create(root, repository=REPOSITORY, private_repository=PRIVATE)
    packet = json.loads((root / "LINEAGE.json").read_text())
    packet["audit_task_credit"] = True
    (root / "LINEAGE.json").write_text(json.dumps(packet, sort_keys=True))
    manifest = json.loads((root / "MANIFEST.json").read_text())
    manifest["lineage_sha256"] = hashlib.sha256((root / "LINEAGE.json").read_bytes()).hexdigest()
    (root / "MANIFEST.json").write_text(json.dumps(manifest, sort_keys=True))
    with pytest.raises(CompanyStoreError, match="lineage or gap differs"):
        verify(root, repository=REPOSITORY, private_repository=PRIVATE)
