"""Focused native chronology and fail-closed checks for selected BCM source."""

import hashlib
import json
import shutil
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest

from enterprise.audit_suite import company_bcm_shared_runtime_exercise as bcm
from enterprise.audit_suite.company_store import CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path(__file__).resolve().parents[2]


def _build(tmp_path):
    root = tmp_path / "run"
    bcm.create(root, repository=REPOSITORY, private_repository=PRIVATE)
    return root


def _bodies(root):
    with sqlite3.connect(
        (root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        return {
            (branch, system, record, version): json.loads(content)
            for branch, system, record, version, content in db.execute(
                "SELECT branch,system,record,version,content FROM versions"
            )
        }


def _clone_private(tmp_path):
    clone = tmp_path / "private-copy"
    clone.mkdir(mode=0o700)
    for rel in bcm.PRIVATE_PINS:
        source = PRIVATE / rel
        target = clone / rel
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return clone


def test_selected_authority_capacity_and_open_messy_exception(tmp_path):
    root = _build(tmp_path)
    result = bcm.verify(root, repository=REPOSITORY, private_repository=PRIVATE)
    assert result["branch_counts"] == {"CLEAN": 8, "MESSY": 10}
    assert result["selected_route_counts"] == {"A": 11, "B": 11}
    bodies = _bodies(root)
    for branch in ("BCM-CLEAN", "BCM-MESSY"):
        delegation = bodies[(branch, "authority_decision", "SELECTED-SERVICE", 1)]
        technical = bodies[(branch, "technical_objectives", "SVC-COMPUTE", 1)]
        bia = bodies[(branch, "business_impact", "SVC-COMPUTE", 1)]
        plan = bodies[(branch, "exercise_plan", "MARKER-RECOVERY", 1)]
        assert delegation["actor_person_id"] == "P001"
        assert delegation["detail"]["delegate"] == "AS-P001"
        assert technical["actor_person_id"] == "AS-P007"
        assert bia["actor_person_id"] == "AS-P001"
        assert plan["detail"]["approved_emergency_ephi_access"] is False
        assert all(
            body["actor_person_id"] != "AS-P004"
            and body["real_world_operation"] is False
            and body["actual_phi_processing"] is False
            and body["audit_task_credit"] is False
            for key, body in bodies.items()
            if key[0] == branch
        )
    clean = bodies[("BCM-CLEAN", "business_impact", "SVC-COMPUTE", 1)]
    messy = bodies[("BCM-MESSY", "business_impact", "SVC-COMPUTE", 1)]
    assert clean["detail"]["accepted_local_objectives"] is True
    assert messy["detail"]["accepted_local_objectives"] is False
    assert (
        bodies[("BCM-MESSY", "demand_forecast", "SVC-COMPUTE", 1)]["detail"]["threshold_exceeded"]
        is True
    )
    failed = bodies[("BCM-MESSY", "exercise_result", "MARKER-RECOVERY", 1)]
    retest = bodies[("BCM-MESSY", "exercise_result", "MARKER-RECOVERY", 2)]
    closure = bodies[("BCM-MESSY", "closure_gate", "KEY-AND-CAPACITY", 1)]
    assert failed["detail"]["numeric_targets_met"] is False
    assert failed["detail"]["historical_bypass_exception_id"] == bcm.EXCEPTION_ID
    assert retest["detail"]["numeric_targets_met"] is True
    assert retest["detail"]["historical_bypass_exception_open"] is True
    assert closure["status"] == "DENIED_PENDING_AUTHORITY_AND_VALIDATION"
    with sqlite3.connect(
        (root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_uncheckpointed_transition_sidecar_rejected(tmp_path, suffix):
    clone = _clone_private(tmp_path)
    sidecar = Path(str(clone / bcm.TRANSITION_REL / "company.sqlite3") + suffix)
    sidecar.write_bytes(b"pending source mutation")
    sidecar.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="SQLite sidecar"):
        bcm.create(tmp_path / "rejected", repository=REPOSITORY, private_repository=clone)


def test_resealed_native_false_acceptance_rejected(tmp_path):
    root = _build(tmp_path)
    db_path = root / "company.sqlite3"
    with sqlite3.connect(db_path) as db:
        db.execute("DROP TRIGGER no_version_update")
        row = db.execute(
            "SELECT content FROM versions WHERE branch='BCM-MESSY' AND system='business_impact'"
        ).fetchone()
        body = json.loads(row[0])
        body["detail"]["accepted_local_objectives"] = True
        content = bcm.encoded(body)
        db.execute(
            "UPDATE versions SET content=?,sha256=? WHERE branch='BCM-MESSY' "
            "AND system='business_impact'",
            (content, bcm.sha(content)),
        )
    manifest_path = root / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["company_db_sha256"] = hashlib.sha256(db_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True))
    manifest_path.chmod(0o600)
    with pytest.raises(CompanyStoreError, match="native event/content/clock differs"):
        bcm.verify(root, repository=REPOSITORY, private_repository=PRIVATE)


def test_missing_fictional_delegation_and_premature_exercise_fail(tmp_path, monkeypatch):
    original = bcm._steps

    def no_delegation(scenario):
        return original(scenario)[1:]

    monkeypatch.setattr(bcm, "_steps", no_delegation)
    with pytest.raises(CompanyStoreError, match="prior local source unavailable"):
        bcm.create(tmp_path / "no-authority", repository=REPOSITORY, private_repository=PRIVATE)
    monkeypatch.setattr(bcm, "_steps", original)

    def early_exercise(scenario):
        steps = original(scenario)
        if scenario == "MESSY":
            for step in steps:
                if step["system"] == "exercise_plan":
                    step["at"] = "2027-07-25T10:00:00+00:00"
        return steps

    monkeypatch.setattr(bcm, "_steps", early_exercise)
    with pytest.raises(CompanyStoreError, match="precedes reviewed transition availability"):
        bcm.create(tmp_path / "premature", repository=REPOSITORY, private_repository=PRIVATE)


def test_exercise_finish_must_match_simulated_duration(tmp_path, monkeypatch):
    original = bcm._steps

    def inconsistent_duration(scenario):
        steps = original(scenario)
        for step in steps:
            if step["system"] == "exercise_result" and step["version"] == 1:
                step["detail"]["measured_restore_minutes_simulated"] += 1
        return steps

    monkeypatch.setattr(bcm, "_steps", inconsistent_duration)
    with pytest.raises(CompanyStoreError, match="measurement clock differs"):
        bcm.create(tmp_path / "bad-clock", repository=REPOSITORY, private_repository=PRIVATE)


def test_ceo_actor_id_must_join_locked_governance():
    chartbook = json.loads((REPOSITORY / "docs/organization/source/chartbook.json").read_text())
    governance = (REPOSITORY / "docs/governance/BOARD_AND_CAPITAL_GOVERNANCE_v1.0.1.md").read_text()
    closeout = (
        REPOSITORY / "docs/canon/DECISION_REGISTER_ADDENDUM_2026-09-06_CLOSEOUT.md"
    ).read_text()
    bcm._validate_ceo_actor(chartbook, governance, closeout)
    wrong = deepcopy(chartbook)
    next(n for n in wrong["nodes"] if n.get("id") == "P001")["title"] = "Corporate Secretary"
    with pytest.raises(CompanyStoreError, match="P001-to-Daniel/CEO"):
        bcm._validate_ceo_actor(wrong, governance, closeout)
    wrong = deepcopy(chartbook)
    next(n for n in wrong["nodes"] if n.get("id") == "P001")["person_id"] = "P004"
    with pytest.raises(CompanyStoreError, match="P001-to-Daniel/CEO"):
        bcm._validate_ceo_actor(wrong, governance, closeout)
    with pytest.raises(CompanyStoreError, match="P001-to-Daniel/CEO"):
        bcm._validate_ceo_actor(
            chartbook, governance.replace("CEO, director", "director"), closeout
        )
