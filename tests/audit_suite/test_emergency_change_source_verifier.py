"""Physical SH-ENG-005 source check, without audit collection or task credit."""

import copy
import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.emergency_change_source_verifier import (
    PRIVATE_PINS,
    RUN_REL,
    _check_bodies,
    _routes,
    verify,
)

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


def _copy_private(tmp_path: Path) -> Path:
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    for relative in PRIVATE_PINS:
        source, destination = PRIVATE / relative, private / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.parent.chmod(0o700)
        shutil.copy2(source, destination)
    return private


def test_exact_raw_source_reperformance_and_uncredited_four_routes():
    report = verify(REPOSITORY, private_repository=PRIVATE)
    assert report["native_versions"] == len(report["native_originals"]) == 19
    assert report["branch_versions"] == {"CLEAN": 8, "MESSY": 11}
    assert {side: len(rows) for side, rows in report["route_disposition"].items()} == {
        "A": 4,
        "B": 4,
    }
    assert all(
        row["current_status"] == "NOT_STARTED"
        and row["current_conclusion"] == "NOT_RUN"
        and row["task_credit"] is False
        for routes in report["route_disposition"].values()
        for row in routes
    )
    assert all(
        row["event_at"] == row["available_at"]
        and row["event_at"].startswith("2027-")
        and row["imported_at"].startswith("2026-")
        for row in report["native_originals"]
    )
    assert report["source_complete"] is False
    assert report["audit_task_credit"] is False
    assert report["corporate_emergency_approval"] is False
    assert report["deployed_change"] is False


def test_frozen_native_source_rejects_sqlite_sidecar(tmp_path):
    private = _copy_private(tmp_path)
    assert verify(REPOSITORY, private_repository=private)["native_versions"] == 19
    sidecar = private / RUN_REL / "run-v1/company.sqlite3-wal"
    sidecar.write_bytes(b"uncheckpointed source")
    sidecar.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="SQLite sidecar"):
        verify(REPOSITORY, private_repository=private)


def test_pinned_recipe_file_and_semantic_digest_are_distinct(tmp_path):
    private = _copy_private(tmp_path)
    recipe = private / RUN_REL / "RECIPE.json"
    recipe.write_text(json.dumps(json.loads(recipe.read_text()), indent=2))
    recipe.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="Pinned emergency input differs"):
        verify(REPOSITORY, private_repository=private)


def test_route_credit_or_retroactive_approval_cannot_be_inferred():
    matrix = json.loads(
        (
            PRIVATE / "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/"
            "run-v2/MATRIX.json"
        ).read_text()
    )
    altered = copy.deepcopy(matrix)
    control = next(
        control
        for family in altered["sides"]["A"]["families"]
        for control in family["controls"]
        if control["control_id"] == "SH-ENG-005"
    )
    control["tasks"][0]["task_credit"] = True
    with pytest.raises(CompanyStoreError, match="task gate"):
        _routes(altered)

    receipt = json.loads((PRIVATE / RUN_REL / "run-v1/SOURCE_RECEIPT.json").read_text())
    database = PRIVATE / RUN_REL / "run-v1/company.sqlite3"
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        bodies = {
            (branch, record): json.loads(content)
            for branch, record, content in db.execute("SELECT branch,record,content FROM versions")
        }
    bodies[(receipt["messy_branch"], "REVIEW")]["corporate_retroactive_approval"] = True
    with pytest.raises(CompanyStoreError, match="Local review became corporate approval"):
        _check_bodies(bodies, receipt)
