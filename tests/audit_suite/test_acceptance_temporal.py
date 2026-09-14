"""Neutral Engine timing regressions; private case mechanisms are not embedded here."""

from copy import deepcopy

import pytest

from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.store import DomainError, digest


@pytest.fixture
def temporal_engine(tmp_path):
    engine = Engine(tmp_path / "private")
    actor = engine.store.provision("Neutral learner", ["learner"])["id"]
    manifest = engine.artifacts.retain(
        "neutral",
        "Source.csv",
        b"record_id,occurred_at\nR1,2027-06-30\n",
        source={"kind": "NEUTRAL_TEST_FIXTURE"},
        coverage={"control_id": "C1"},
    )
    manifest.update(status="AVAILABLE", received_at="2028-01-05T09:00:00+00:00")
    state = {name: [] for name in COLLECTIONS}
    state.update(
        title="Neutral dated work",
        phase="ACTIVE",
        discipline="IT",
        mode="CLEAN",
        simulated_at="2028-01-02T09:00:00+00:00",
        scope={
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "temporal_basis": "PERIOD",
            "timezone": "UTC",
            "boundaries": ["B1"],
        },
        configuration={"selections": []},
        controls=[{"id": "C1", "owner_ids": ["P1"], "implementation_version": "v1"}],
        people=[{"id": "P1"}, {"id": "P2"}],
        artifacts=[manifest],
    )
    state = engine.store.create(actor, state, "create")
    return engine, actor, state


def command(engine, actor, state, kind, payload, suffix=""):
    return engine.command(
        actor,
        state["id"],
        {
            "command_id": f"cmd-{state['revision']}-{suffix}",
            "expected_revision": state["revision"],
            "kind": kind,
            "payload": payload,
        },
    )


def payload(state, **overrides):
    return {
        "implementation_id": "IMPL-E0-C1-B1",
        "covered_start": "2027-01-01",
        "covered_end": "2027-12-31",
        "procedure_kind": "TOE",
        "result": "RECORDED",
        "evidence_ids": [state["artifacts"][0]["id"]],
        "rationale": "Neutral bounded source comparison",
        "methodology": "Explicit test methodology, no professional sufficiency claim",
        "nature_timing_extent": "Inspect supplied source and attribute covered interval",
        **overrides,
    }


def test_engine_excludes_future_received_source_until_clock_reaches_capture(temporal_engine):
    engine, actor, state = temporal_engine
    state = command(engine, actor, state, "coverage.record", payload(state))
    assert not state["temporal_reports"][0]["reported_work_complete"]
    original = deepcopy(state["temporal_current"]["work"])
    state = command(
        engine, actor, state, "clock.advance", {"mode": "TARGET_DATE", "target": "2028-01-10"}
    )
    assert state["temporal_reports"][0]["reported_work_complete"]
    assert state["temporal_reports"][0]["professional_sufficiency"] == "NOT_ASSERTED"
    assert digest(state["temporal_current"]["work"]) == digest(original)
    assert engine.artifacts.read(state["artifacts"][0]).endswith(b"R1,2027-06-30\n")


def test_engine_split_preserves_exception_and_rejects_cross_version_atomically(temporal_engine):
    engine, actor, state = temporal_engine
    state = command(
        engine, actor, state, "clock.advance", {"mode": "TARGET_DATE", "target": "2028-01-10"}
    )
    state = command(engine, actor, state, "coverage.record", payload(state, result="EXCEPTION"))
    original = deepcopy(state["temporal_current"]["work"])
    state = command(
        engine,
        actor,
        state,
        "implementation.change",
        {
            "implementation_id": "IMPL-E0-C1-B1",
            "effective_at": "2027-07-01",
            "owner_id": "P2",
            "implementation_version": "v2",
            "rationale": "New dated implementation source requires reassessment",
        },
    )
    assert digest(state["temporal_current"]["work"]) == digest(original)
    report = state["temporal_reports"][0]
    assert report["historical_exception_ids"] == [original[0]["id"]]
    assert report["records_requiring_reassessment"] == [original[0]["id"]]
    history = engine.store.history(actor, state["id"])
    with pytest.raises(DomainError, match="crosses implementation"):
        command(engine, actor, state, "coverage.record", payload(state), "invalid")
    assert engine.store.history(actor, state["id"]) == history
    assert engine.get(actor, state["id"])["revision"] == state["revision"]
