import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.explanation_binding import bind_snapshot, verify_snapshot
from enterprise.audit_suite.instructor_comparison import _inventory
from enterprise.audit_suite.service import create_app
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_federation import portfolio

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def setup(tmp_path):
    facade, stores, config, path = portfolio(tmp_path)
    engine = Engine(
        tmp_path / "audit", repository=ROOT, company_registry=path, company_profile="portfolio"
    )
    teacher = engine.store.provision("Teacher", ["instructor"])
    learner = engine.store.provision("Learner", ["learner"])
    reviewer = engine.store.provision("Reviewer", ["reviewer"])
    state = {k: [] for k in COLLECTIONS}
    state.update(
        scope={
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "boundaries": ["corporate"],
        },
        simulated_at="2027-02-01T00:00:00Z",
        controls=[{"id": "SH-CFG-001"}],
        company_source_binding=facade.binding,
    )
    state = engine.store.create(teacher["id"], state, "create")
    for p, permission in [(learner, "learn"), (reviewer, "review")]:
        engine.store.grant(state["id"], p["id"], permission)
    engine.company_bindings[state["id"]] = facade.binding
    references = []
    artifacts = []
    for index, (key, native) in enumerate(stores.items()):
        for actor in [learner["id"], "OPERATOR"]:
            native.grant(actor, state["id"], "NATIVE", "branch", "records")
        alias = key.upper() + ":records"
        row = facade.read_version(
            "OPERATOR",
            state["id"],
            "LOGICAL",
            "portfolio",
            alias,
            "ROW",
            version=1,
            as_of="2027-05-01T00:00:00Z",
        )
        receipt = facade.collect(
            learner["id"],
            state["id"],
            "LOGICAL",
            "portfolio",
            alias,
            "ROW",
            version=1,
            as_of=state["simulated_at"],
            command_id="collect-" + key,
        )
        artifacts.append(
            engine.artifacts.retain(
                state["id"],
                "original.json",
                row["content"],
                source={"kind": "COLLECTED_COMPANY_SOURCE", "receipt": receipt},
                coverage={},
            )
        )
        references.append(
            {
                "id": "S" + str(index),
                **{
                    k: row[k]
                    for k in [
                        "company",
                        "branch",
                        "system",
                        "record",
                        "version",
                        "sha256",
                        "source_store_id",
                        "source_system_alias",
                        "registry_sha256",
                    ]
                },
            }
        )
    stores["two"].grant(learner["id"], state["id"], "NATIVE", "branch", "records", active=False)
    future = facade.read_version(
        "OPERATOR",
        state["id"],
        "LOGICAL",
        "portfolio",
        "ONE:records",
        "ROW",
        version=2,
        as_of="2027-05-01T00:00:00Z",
    )
    references.append({"id": "FUTURE", **{k: future[k] for k in references[0] if k != "id"}})

    def reducer(s, c, a):
        s["artifacts"] = artifacts
        return s

    state = engine.store.command(
        teacher["id"],
        state["id"],
        {"command_id": "retain", "expected_revision": 0, "kind": "fixture.retain", "payload": {}},
        reducer,
        permissions={"instruct"},
    )
    args = dict(
        instructor_id=teacher["id"],
        audited_actor_id=learner["id"],
        engagement_id=state["id"],
        source_operator_id="OPERATOR",
        source_as_of="2027-05-01T00:00:00Z",
        source_refs=references,
        authored={
            "issues": [],
            "expectations": [],
            "uncertainty": ["No professional validation"],
            "source_pins": {},
        },
        output=tmp_path / "snapshot",
    )
    return engine, args, stores, config, path, teacher, learner, reviewer, artifacts


def test_native_collision_visibility_and_retained_copy_remain_distinct(setup):
    e, args, _, _, _, _, _, _, artifacts = setup
    receipt = bind_snapshot(e, **args)
    snap = verify_snapshot(args["output"], expected_manifest_sha256=receipt["manifest_sha256"])
    assert (
        snap["snapshot_isolation"] == "PER_COMPONENT_NOT_GLOBAL"
        and len(snap["component_snapshots"]) == 2
    )
    s = {x["id"]: x for x in snap["sources"]}
    assert s["S0"]["retained_audit_artifact_ids"] == [artifacts[0]["id"]]
    assert s["S1"]["retained_audit_artifact_ids"] == [artifacts[1]["id"]]
    assert s["S1"]["actor_visibility_at_binding"] == "ACCESS_NOT_GRANTED"
    assert s["FUTURE"]["actor_visibility_at_binding"] == "FUTURE_UNAVAILABLE"
    state = e.store.get(args["instructor_id"], args["engagement_id"])
    report = _inventory(snap, state, e.store.history(args["instructor_id"], args["engagement_id"]))
    matched = {x["source_id"]: x for x in report["sources"]}
    assert [x["id"] for x in matched["S0"]["exact_retained_artifacts"]] == [artifacts[0]["id"]]
    assert [x["id"] for x in matched["S1"]["exact_retained_artifacts"]] == [artifacts[1]["id"]]


def test_grant_revoked_during_capture_leaves_no_snapshot(setup, monkeypatch):
    e, args, stores, *_ = setup
    native = e.company_store._stores["one"]
    original = native._read
    with stores["one"]._db() as db:
        db.execute("PRAGMA journal_mode=WAL")
    revoked = False

    def read(*a, **kw):
        nonlocal revoked
        row = original(*a, **kw)
        if not revoked:
            stores["one"].grant(
                "OPERATOR", args["engagement_id"], "NATIVE", "branch", "records", active=False
            )
            revoked = True
        return row

    monkeypatch.setattr(native, "_read", read)
    with pytest.raises(DomainError):
        bind_snapshot(e, **args)
    assert not args["output"].exists()


def test_instructor_only_route_and_changed_registry_fail_closed(setup, tmp_path):
    e, args, stores, config, path, teacher, learner, reviewer, _ = setup
    receipt = bind_snapshot(e, **args)
    bindings = tmp_path / "instructor.json"
    bindings.write_text(
        json.dumps(
            {
                args["engagement_id"]: {
                    "path": str(args["output"]),
                    "manifest_sha256": receipt["manifest_sha256"],
                }
            }
        )
    )
    bindings.chmod(0o600)
    companies = tmp_path / "companies.json"
    companies.write_text(json.dumps(e.company_bindings))
    companies.chmod(0o600)
    app = create_app(
        e.store.root,
        repository=ROOT,
        company_registry=path,
        company_profile="portfolio",
        company_bindings=companies,
        instructor_bindings=bindings,
        allowed_hosts=["testserver"],
    )
    client = TestClient(app, base_url="https://testserver")
    url = f"/api/engagements/{args['engagement_id']}/instructor-binding"

    def get(person):
        return client.get(url, headers={"Authorization": "Bearer " + person["credential"]})

    assert get(learner).status_code == 403 and get(reviewer).status_code == 403
    assert get(teacher).status_code == 200
    config["components"]["one"]["root"] = config["components"]["two"]["root"]
    path.write_text(json.dumps(config))
    denied = get(teacher)
    assert denied.status_code == 503 and str(path) not in denied.text
    e.store.revoke(teacher["id"])
    assert get(teacher).status_code == 401


def test_publication_failure_preserves_no_partial_snapshot(setup, monkeypatch):
    from enterprise.audit_suite import explanation_binding as module

    e, args, *_ = setup
    original = module._write

    def interrupted(path, value):
        if path.name == "manifest.json":
            raise OSError("Isolated write interruption")
        return original(path, value)

    monkeypatch.setattr(module, "_write", interrupted)
    with pytest.raises(OSError):
        bind_snapshot(e, **args)
    assert not args["output"].exists()
    assert not list(args["output"].parent.glob("portfolio-snapshot-*"))


def test_changed_scope_preserves_historical_snapshot_without_comparison_promotion(setup):
    from enterprise.audit_suite.instructor_comparison import compare

    e, args, *_ = setup
    receipt = bind_snapshot(e, **args)
    before = (args["output"] / "snapshot.json").read_bytes()
    state = e.store.get(args["instructor_id"], args["engagement_id"])

    def revised(s, c, a):
        s["scope"] = {**s["scope"], "period_end": "2027-06-30"}
        return s

    later = e.store.command(
        args["instructor_id"],
        args["engagement_id"],
        {
            "command_id": "scope-change",
            "expected_revision": state["revision"],
            "kind": "fixture.scope",
            "payload": {},
        },
        revised,
        permissions={"instruct"},
    )
    result = compare(
        e,
        {"id": args["instructor_id"]},
        args["engagement_id"],
        {
            args["engagement_id"]: {
                "path": args["output"],
                "manifest_sha256": receipt["manifest_sha256"],
            }
        },
        revision=later["revision"],
    )
    assert result["status"] == "CONTEXT_MISMATCH" and "sources" not in result
    assert (args["output"] / "snapshot.json").read_bytes() == before
