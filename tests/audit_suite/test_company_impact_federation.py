import json
from datetime import datetime

import pytest

from enterprise.audit_suite.company_impact import report
from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_federation import portfolio


@pytest.fixture
def workspace(tmp_path):
    facade, stores, config, path = portfolio(tmp_path)
    engine = Engine(tmp_path / "audit", company_registry=path, company_profile="portfolio")
    actor = engine.store.provision("Impact investigator", ["learner"])["id"]
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Portfolio impact",
        phase="ACTIVE",
        mode="CLEAN",
        discipline="IT",
        simulated_at="2027-06-01T00:00:00Z",
        scope={"boundaries": ["corporate"]},
        configuration={},
        company_source_binding=facade.binding,
    )
    state["requests"] = [{"id": "R1", "status": "ISSUED", "artifact_ids": []}]
    state = engine.store.create(actor, state, "create")
    engine.company_bindings[state["id"]] = facade.binding
    for index, (name, store) in enumerate(stores.items()):
        store.grant(actor, state["id"], "NATIVE", "branch", "records")
        state = engine.command(
            actor,
            state["id"],
            {
                "command_id": f"collect-{index}",
                "expected_revision": state["revision"],
                "kind": "company.collect",
                "payload": {
                    "system_id": name.upper() + ":records",
                    "record_id": "ROW",
                    "version": 2,
                    "request_id": "R1",
                },
            },
        )
    return engine, actor, state, stores, config, path


def append(store, expected, at, content, **qualifiers):
    return store.append_version(
        "NATIVE",
        "branch",
        "records",
        "ROW",
        expected_version=expected,
        command_id=f"version-{expected + 1}",
        event_at=at,
        available_at=at,
        content=content,
        provenance={"source_reference": "operator-authored-update", **qualifiers},
    )


def test_per_source_correction_withdrawal_future_and_revocation(workspace):
    engine, actor, state, stores, _, _ = workspace
    original_bytes = [engine.artifacts.read(a) for a in state["artifacts"]]
    initial = report(engine, actor, state["id"])
    assert initial["compared_artifacts"] == 2 and initial["changes"] == []
    append(
        stores["one"], 2, "2027-05-01T00:00:00Z", b"corrected original", record_state="CORRECTED"
    )
    correction = report(engine, actor, state["id"])
    assert len(correction["changes"]) == 1
    row = correction["changes"][0]
    assert row["latest_visible_version"] == 3
    assert row["source_identity"]["source_system_alias"] == "ONE:records"
    assert row["source_identity"]["source_store_id"] == "one"
    assert row["source_identity"]["company"] == "NATIVE"
    assert row["source_identity"]["system"] == "records"
    assert row["latest_source_qualifiers"] == {"record_state": "CORRECTED"}
    append(
        stores["one"],
        3,
        "2027-05-10T00:00:00Z",
        b"Withdrawal notice: prior original retained",
        record_state="WITHDRAWN",
    )
    append(
        stores["one"], 4, "2027-07-01T00:00:00Z", b"Future republication", record_state="PUBLISHED"
    )
    result = report(engine, actor, state["id"])
    assert result["compared_artifacts"] == 2 and result["unavailable_comparisons"] == 0
    row = result["changes"][0]
    assert (
        row["latest_visible_version"] == 4
        and row["latest_source_qualifiers"]["record_state"] == "WITHDRAWN"
    )
    assert row["automatic_invalidation"] is False
    assert (
        datetime.fromisoformat(result["started_at"])
        <= datetime.fromisoformat(row["discovered_at"])
        <= datetime.fromisoformat(row["rechecked_at"])
        <= datetime.fromisoformat(result["completed_at"])
    )
    assert result["snapshot_isolation"] == "PER_SOURCE_OPERATION_NOT_GLOBAL"
    assert (result["engagement_id"], result["engagement_revision"]) == (
        state["id"],
        state["revision"],
    )
    assert [engine.artifacts.read(a) for a in state["artifacts"]] == original_bytes
    stores["one"].grant(actor, state["id"], "NATIVE", "branch", "records", active=False)
    denied = report(engine, actor, state["id"])
    assert (
        denied["changes"] == []
        and denied["unavailable_comparisons"] == 1
        and denied["compared_artifacts"] == 1
    )
    assert "WITHDRAWN" not in json.dumps(denied)
    assert engine.get(actor, state["id"])["revision"] == state["revision"]


def test_registry_and_cross_component_identity_cannot_redirect_comparisons(workspace):
    engine, actor, state, stores, config, path = workspace
    identity = state["artifacts"][0]["source"]["receipt"]["source"]
    bad = {**identity, "source_store_id": "two"}
    with pytest.raises(ValueError):
        engine.company_store.resolve_source_identity(bad)
    config["components"]["one"]["namespace"] = "NEW"
    path.write_text(json.dumps(config))
    with pytest.raises(DomainError):
        report(engine, actor, state["id"])


def test_grant_revoked_after_first_catalogue_does_not_return_changed_or_unchanged(
    workspace, monkeypatch
):
    engine, actor, state, stores, _, _ = workspace
    append(stores["one"], 2, "2027-05-01T00:00:00Z", b"Changed first source")
    old = engine.company_store.list_records

    def revoke_after_other(*args, **kwargs):
        result = old(*args, **kwargs)
        if args[4] == "TWO:records":
            stores["one"].grant(actor, state["id"], "NATIVE", "branch", "records", active=False)
        return result

    monkeypatch.setattr(engine.company_store, "list_records", revoke_after_other)
    result = report(engine, actor, state["id"])
    assert (
        result["changes"] == []
        and result["compared_artifacts"] == 1
        and result["unavailable_comparisons"] == 1
    )


def test_incomplete_or_repeated_catalogue_is_unavailable(workspace, monkeypatch):
    engine, actor, state, _, _, _ = workspace
    old = engine.company_store.list_records

    def repeated(*args, **kwargs):
        result = old(*args, **{**kwargs, "after_record": None})
        result["next_after_record"] = "ROW"
        return result

    monkeypatch.setattr(engine.company_store, "list_records", repeated)
    result = report(engine, actor, state["id"])
    assert (
        result["changes"] == []
        and result["compared_artifacts"] == 0
        and result["unavailable_comparisons"] == 2
    )


def test_corrupt_retained_original_is_unavailable_not_unchanged(workspace):
    engine, actor, state, _, _, _ = workspace
    # Both independent sources have identical bytes, so the content-addressed copy
    # is shared. Corrupt only this disposable test artifact, never a source store.
    artifact = state["artifacts"][0]
    (engine.artifacts.root / artifact["sha256"]).write_bytes(b"corrupted retained copy")
    result = report(engine, actor, state["id"])
    assert result["changes"] == []
    assert result["compared_artifacts"] == 0 and result["unavailable_comparisons"] == 2
