import pytest

from enterprise.audit_suite.company_collection import discover
from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.store import DomainError


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "company"
    root.mkdir(mode=0o700)
    e = Engine(tmp_path / "audit", company_root=root)
    actor = e.store.provision("Auditor", ["learner"])["id"]
    state = {k: [] for k in COLLECTIONS}
    state.update(
        title="Source collection",
        phase="ACTIVE",
        discipline="IT",
        mode="CLEAN",
        simulated_at="2027-06-01T00:00:00Z",
        scope={
            "boundaries": ["corporate"],
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "timezone": "UTC",
        },
        configuration={"selections": []},
    )
    state["requests"] = [{"id": "R1", "status": "ISSUED", "artifact_ids": []}]
    state = e.store.create(actor, state, "create")
    e.company_bindings[state["id"]] = {"company": "SH", "branch": "base"}
    s = e.company_store
    s.register_system("SH", "base", "identity", "owner")
    s.append_version(
        "SH",
        "base",
        "identity",
        "record",
        expected_version=0,
        command_id="import",
        event_at="2027-01-01T00:00:00Z",
        available_at="2027-01-02T00:00:00Z",
        content=b"identity record\n",
        provenance={"source_reference": "system-event-1", "name": "identity.txt"},
    )
    s.grant(actor, state["id"], "SH", "base", "identity")
    return e, actor, state


def envelope(s):
    return {
        "command_id": "collect",
        "expected_revision": s["revision"],
        "kind": "company.collect",
        "payload": {
            "system_id": "identity",
            "record_id": "record",
            "version": 1,
            "request_id": "R1",
        },
    }


def test_discover_collect_and_retry_without_prepared_evidence(workspace):
    e, actor, s = workspace
    assert not s["artifacts"]
    assert discover(e, actor, s["id"], "identity")["records"][0]["record"] == "record"
    cmd = envelope(s)
    out = e.command(actor, s["id"], cmd)
    assert len(out["artifacts"]) == 1
    assert e.artifacts.read(out["artifacts"][0]) == b"identity record\n"
    assert out["requests"][0]["status"] == "SUBMITTED"
    assert e.command(actor, s["id"], cmd) == out
    assert out["artifacts"][0]["source"]["receipt"]["source"]["version"] == 1


def test_source_revocation_blocks_discovery_and_new_collection(workspace):
    e, actor, s = workspace
    e.company_store.grant(actor, s["id"], "SH", "base", "identity", active=False)
    with pytest.raises(DomainError):
        discover(e, actor, s["id"], "identity")
    with pytest.raises(DomainError):
        e.command(actor, s["id"], envelope(s))
    assert e.store.get(actor, s["id"])["artifacts"] == []


def test_client_cannot_choose_company_branch_or_clock(workspace):
    e, actor, s = workspace
    cmd = envelope(s)
    cmd["payload"]["as_of"] = "2030-01-01T00:00:00Z"
    with pytest.raises(DomainError):
        e.command(actor, s["id"], cmd)
    assert e.store.get(actor, s["id"])["artifacts"] == []


def test_instructor_activation_creates_no_evidence_or_world(workspace):
    e, actor, original = workspace
    instructor = e.store.provision("Instructor", ["instructor"])["id"]
    state = {k: [] for k in COLLECTIONS}
    state.update(
        title="Fresh source audit",
        phase="CONFIGURING",
        discipline="IT",
        mode="CLEAN",
        simulated_at=original["simulated_at"],
        scope=original["scope"],
        configuration={"selections": []},
    )
    state = e.store.create(instructor, state, "create-source")
    e.store.grant(state["id"], instructor, "instruct")
    e.store.grant(state["id"], actor, "learn")
    e.company_bindings[state["id"]] = {"company": "SH", "branch": "base"}
    cmd = {
        "command_id": "activate",
        "expected_revision": state["revision"],
        "kind": "company.activate",
        "payload": {},
    }
    with pytest.raises(DomainError):
        e.command(actor, state["id"], cmd)
    result = e.command(instructor, state["id"], cmd)
    assert result["phase"] == "READY"
    assert result["artifacts"] == result["requests"] == []
    assert not (e.store.root / "worlds" / state["id"]).exists()
    e.company_bindings[state["id"]]["branch"] = "other"
    with pytest.raises(DomainError, match="binding changed"):
        discover(e, instructor, state["id"], "identity")


def test_distinct_retry_deduplicates_but_correction_keeps_both_versions(workspace):
    e, actor, s = workspace
    out = e.command(actor, s["id"], envelope(s))
    retry = envelope(out)
    retry["command_id"] = "different-command"
    out = e.command(actor, s["id"], retry)
    assert len(out["artifacts"]) == 1
    e.company_store.append_version(
        "SH",
        "base",
        "identity",
        "record",
        expected_version=1,
        command_id="correction",
        event_at="2027-01-01T00:00:00Z",
        available_at="2027-02-01T00:00:00Z",
        content=b"corrected company record\n",
        provenance={"source_reference": "correction-event", "name": "identity.txt"},
    )
    revised = envelope(out)
    revised["command_id"] = "collect-correction"
    revised["payload"]["version"] = 2
    out = e.command(actor, s["id"], revised)
    assert len(out["artifacts"]) == 2
    assert e.artifacts.read(out["artifacts"][0]) == b"identity record\n"
    assert e.artifacts.read(out["artifacts"][1]) == b"corrected company record\n"
