"""Focused source and negative-chronology checks for the bounded ERM slice."""

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite.company_risk_governance_stagegate_exercise import create, verify
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


def _build(tmp_path):
    root = tmp_path / "stagegate"
    create(root, repository=REPOSITORY, private_repository=PRIVATE)
    return root


def _clone_private(tmp_path):
    clone = tmp_path / "private-copy"
    clone.mkdir(mode=0o700)
    rel = "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/run-v3"
    target = clone / rel
    target.parent.mkdir(mode=0o700, parents=True)
    shutil.copytree(PRIVATE / rel, target)
    for name in (
        "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/independent-review-v3/REVIEW.json",
        "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/run-v2/MATRIX.json",
        "enterprise/generated/audit-suite/documentary-discovery-routes-2026-09-29/independent-review-v2/REVIEW.json",
        "enterprise/generated/audit-suite/company-risk-assessment-2026-09-14/aligned-v2/company/company.sqlite3",
    ):
        dest = clone / name
        dest.parent.mkdir(mode=0o700, parents=True)
        shutil.copy2(PRIVATE / name, dest)
    return clone


def _bodies(root):
    with sqlite3.connect(
        (root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        return {
            (r["branch"], r["system"], r["record"], r["version"]): json.loads(r["content"])
            for r in db.execute("SELECT * FROM versions")
        }


def test_exact_branch_causality_and_no_approval(tmp_path):
    root = _build(tmp_path)
    assert (
        verify(root, repository=REPOSITORY, private_repository=PRIVATE)["native_version_count"]
        == 19
    )
    receipt = json.loads((root / "RECEIPT.json").read_text())
    assert {
        k: sum(map(len, groups.values()))
        for k, groups in receipt["selected_route_task_ids"].items()
    } == {"A": 9, "B": 9}
    assert {k: len(v) for k, v in receipt["records"].items()} == {"CLEAN": 8, "MESSY": 11}
    bodies = _bodies(root)
    assert len(bodies) == 19
    for branch in ("RISK-CLEAN", "RISK-MESSY"):
        assert {
            bodies[(branch, "stage_input", f"INPUT-{role}", 1)]["actor_person_id"]
            for role in ("TECHNOLOGY", "SECURITY", "PROCUREMENT", "LEGAL")
        } == {"AS-P007", "AS-P008", "AS-P013", "AS-P003"}
        assessed = bodies[(branch, "stage_assessment", "BOISE-RECOVERY", 1)]
        assert len(assessed["local_prior_source_sha256"]) == 4
        assert assessed["erm001_method_context"]["record"] == "ASSESSMENT"
        assert all(
            b["risk_acceptance"] == "NOT_PERFORMED"
            and b["appetite_status"] == "NOT_ESTABLISHED"
            and b["enterprise_approval"] is False
            and b["real_world_operation"] is False
            and b["audit_task_credit"] is False
            for key, b in bodies.items()
            if key[0] == branch
        )
    clean_gate = bodies[("RISK-CLEAN", "technical_gate", "BOISE-RECOVERY", 1)]
    messy_hold = bodies[("RISK-MESSY", "technical_gate", "BOISE-RECOVERY", 1)]
    messy_later = bodies[("RISK-MESSY", "technical_gate", "BOISE-RECOVERY", 2)]
    assert clean_gate["status"] == "LOCAL_TECHNICAL_RECOMMENDATION"
    assert messy_hold["status"] == "LOCAL_HOLD_NO_WAIVER"
    assert messy_later["status"] == "LOCAL_CONDITIONAL_RECOMMENDATION_EXCEPTION_OPEN"
    assert messy_later["historical_bypass_exception_open"] is True
    assert (
        bodies[("RISK-MESSY", "residual_request", "BOISE-RECOVERY", 2)]["status"]
        == "PENDING_AUTHORITY_DECISION"
    )
    assert all(
        b["status"] == "PENDING_AUTHORITY_DECISION"
        for key, b in bodies.items()
        if key[1] == "residual_request"
    )
    with sqlite3.connect(
        (root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0


def test_missing_transition_dependency_fails_closed(tmp_path):
    clone = _clone_private(tmp_path)
    # Exact private pin must reject a changed source even if an attacker reseals its own receipt.
    receipt = (
        clone / "enterprise/generated/audit-suite/company-runtime-transition-2026-09-29/"
        "run-v3/RECEIPT.json"
    )
    raw = json.loads(receipt.read_text())
    raw["records"]["MESSY"] = [
        r for r in raw["records"]["MESSY"] if not (r["record"] == "EX-BOISE" and r["version"] == 2)
    ]
    receipt.write_text(json.dumps(raw, sort_keys=True))
    receipt.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="Reviewed private input differs"):
        create(tmp_path / "rejected", repository=REPOSITORY, private_repository=clone)


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_frozen_erm001_sidecars_rejected_before_immutable_read(tmp_path, suffix):
    clone = _clone_private(tmp_path)
    db = (
        clone / "enterprise/generated/audit-suite/company-risk-assessment-2026-09-14/"
        "aligned-v2/company/company.sqlite3"
    )
    sidecar = Path(str(db) + suffix)
    sidecar.write_bytes(b"pending logical database mutation")
    sidecar.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="active sidecar"):
        create(tmp_path / "rejected", repository=REPOSITORY, private_repository=clone)


def test_resealed_false_risk_acceptance_rejected(tmp_path):
    root = _build(tmp_path)
    with sqlite3.connect(root / "company.sqlite3") as db:
        db.execute("DROP TRIGGER no_version_update")
        row = db.execute(
            "SELECT content FROM versions WHERE branch='RISK-CLEAN' "
            "AND system='residual_request' AND version=1"
        ).fetchone()
        body = json.loads(row[0])
        body["risk_acceptance"] = "ACCEPTED"
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(raw).hexdigest()
        db.execute(
            "UPDATE versions SET content=?,sha256=? WHERE branch='RISK-CLEAN' "
            "AND system='residual_request' AND version=1",
            (raw, digest),
        )
    receipt = json.loads((root / "RECEIPT.json").read_text())
    for ref in receipt["records"]["CLEAN"]:
        if ref["system"] == "residual_request":
            ref["sha256"] = digest
    (root / "RECEIPT.json").write_text(json.dumps(receipt, sort_keys=True))
    manifest = json.loads((root / "MANIFEST.json").read_text())
    manifest["company_db_sha256"] = hashlib.sha256(
        (root / "company.sqlite3").read_bytes()
    ).hexdigest()
    manifest["receipt_sha256"] = hashlib.sha256((root / "RECEIPT.json").read_bytes()).hexdigest()
    (root / "MANIFEST.json").write_text(json.dumps(manifest, sort_keys=True))
    with pytest.raises(CompanyStoreError, match="content or future clock"):
        verify(root, repository=REPOSITORY, private_repository=PRIVATE)
