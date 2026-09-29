import json

import pytest

from enterprise.audit_suite import company_nonhuman_runtime as runtime
from enterprise.audit_suite.company_backup_runtime import database
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from tests.audit_suite.test_company_nonhuman_runtime import prepared as base_prepared


@pytest.fixture
def prepared(tmp_path):
    return base_prepared.__wrapped__(tmp_path)


def criterion(prepared, tmp_path, mutate=lambda b: None):
    root, _, kwargs, _ = prepared
    cfg = json.loads((root / "RUNTIME.json").read_bytes())
    plan = cfg["plan"]
    body = {
        "format": "LOCAL_NONHUMAN_RISK_CRITERION_V1",
        "status": "LOCAL_SIMULATION_RULE_APPROVED",
        "scope": {k: cfg[k] for k in ["identity_id", "workload_id", "dataset_id", "target_id"]},
        "author_id": cfg["operator_id"],
        "reviewer_id": cfg["reviewer_id"],
        "approved_at": cfg["initialized_at"],
        "effective_from": plan["period_start"],
        "effective_to_exclusive": plan["period_end_exclusive"],
        "storage": "INERT_NATIVE_COPY_NO_SECRET_MATERIAL",
        "rights": [
            {"action": "READ", "object_id": cfg["dataset_id"]},
            {"action": "WRITE", "object_id": cfg["target_id"]},
        ],
        "rationale": "Prospective bounded local criterion, not enterprise approval.",
    }
    for key, prefix in [("rotation_rules", "ROTATION-"), ("review_rules", "REVIEW-")]:
        body[key] = [
            {
                k: s[k]
                for k in ["id", "due_at", "window_start", "window_end_exclusive", "depends_on"]
            }
            for s in plan["schedule"]
            if s["id"].startswith(prefix)
        ]
    mutate(body)
    source = tmp_path / "criterion"
    source.mkdir(mode=0o700)
    store = CompanyStore(source)
    store.register_system(
        plan["company_id"], plan["branch_id"], "local_nonhuman_risk_decisions", cfg["operator_id"]
    )
    row = store.append_version(
        plan["company_id"],
        plan["branch_id"],
        "local_nonhuman_risk_decisions",
        "CRITERION",
        expected_version=0,
        command_id="criterion",
        event_at=cfg["initialized_at"],
        available_at=cfg["initialized_at"],
        content=encoded(body),
        provenance={"source_reference": "authored local fixture"},
    )
    with database(source) as db:
        metadata = dict(db.execute("SELECT * FROM versions").fetchone())
        metadata.pop("content")
    dep = {
        "root": str(source),
        "native": {k: row[k] for k in runtime.FIELDS},
        "metadata_sha256": sha(encoded(metadata)),
    }
    return dep, kwargs, cfg


def test_optional_criterion_is_retained_and_exact_replay(prepared, tmp_path):
    dep, kwargs, cfg = criterion(prepared, tmp_path)
    root = tmp_path / "approved"
    result = runtime.initialize(root, **kwargs, local_risk_criterion=dep)
    retained = json.loads((root / "RUNTIME.json").read_bytes())
    assert retained["local_risk_criterion"]["dependency"] == dep
    assert "local_risk_criterion" not in json.loads((prepared[0] / "RUNTIME.json").read_bytes())
    state = runtime.inspect(
        root, expected_runtime_sha256=result["runtime_sha256"], as_of=cfg["initialized_at"]
    )
    command = dict(
        expected_runtime_sha256=result["runtime_sha256"],
        expected_revision=0,
        expected_state_sha256=state["state_sha256"],
        command_id="check",
        action="RECONCILE",
        payload={},
        actor_id=cfg["operator_id"],
        event_at=cfg["initialized_at"],
    )
    first = runtime.execute(root, **command)
    assert runtime.execute(root, **command) == first
    with database(dep["root"], True) as db:
        for row in db.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall():
            db.execute("DROP TRIGGER " + row[0])
        db.execute("UPDATE versions SET imported_at='2026-09-21T00:00:00.000000+00:00'")
    with pytest.raises(CompanyStoreError, match="metadata"):
        runtime.execute(root, **command)
    with database(root) as db:
        assert db.execute("SELECT count(*) FROM nonhuman_commands").fetchone()[0] == 1


@pytest.mark.parametrize(
    "case",
    ["enterprise", "reviewer", "subject", "rights", "cadence", "future", "extra", "padded"],
)
def test_invalid_approved_scope_fails_before_publication(prepared, tmp_path, case):
    def mutate(body):
        if case == "enterprise":
            body["status"] = "ENTERPRISE_APPROVED"
        elif case == "reviewer":
            body["reviewer_id"] = body["author_id"]
        elif case == "subject":
            body["scope"]["identity_id"] = "OTHER"
        elif case == "rights":
            body["rights"][1]["object_id"] = "OTHER"
        elif case == "cadence":
            body["rotation_rules"] = []
        elif case == "future":
            body["effective_from"] = "2027-07-02T00:00:00.000000+00:00"
        elif case == "padded":
            body["rationale"] = " " * 2000 + "x"
        else:
            body["enterprise_acceptance"] = True

    dep, kwargs, _ = criterion(prepared, tmp_path, mutate)
    dest = tmp_path / "rejected"
    with pytest.raises(CompanyStoreError):
        runtime.initialize(dest, **kwargs, local_risk_criterion=dep)
    assert not dest.exists()


def test_final_dependency_check_rolls_back_command(prepared, tmp_path, monkeypatch):
    dep, kwargs, cfg = criterion(prepared, tmp_path)
    root = tmp_path / "approved"
    result = runtime.initialize(root, **kwargs, local_risk_criterion=dep)
    state = runtime.inspect(
        root, expected_runtime_sha256=result["runtime_sha256"], as_of=cfg["initialized_at"]
    )
    original = runtime.resolve_local_risk_criterion
    calls = 0

    def changed(*args, **kw):
        nonlocal calls
        calls += 1
        if calls == 2:
            with database(dep["root"], True) as db:
                for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='trigger'"
                ).fetchall():
                    db.execute("DROP TRIGGER " + row[0])
                db.execute("UPDATE versions SET provenance='{}'")
        return original(*args, **kw)

    monkeypatch.setattr(runtime, "resolve_local_risk_criterion", changed)
    with pytest.raises(CompanyStoreError):
        runtime.execute(
            root,
            expected_runtime_sha256=result["runtime_sha256"],
            expected_revision=0,
            expected_state_sha256=state["state_sha256"],
            command_id="race",
            action="RECONCILE",
            payload={},
            actor_id=cfg["operator_id"],
            event_at=cfg["initialized_at"],
        )
    with database(root) as db:
        assert db.execute("SELECT count(*) FROM nonhuman_commands").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM versions").fetchone()[0] == 2
