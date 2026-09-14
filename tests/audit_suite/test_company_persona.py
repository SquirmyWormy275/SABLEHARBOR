import json

from enterprise.audit_suite.company_persona import sources
from enterprise.audit_suite.engine import COLLECTIONS, Engine


def test_owner_and_auditor_intersection_future_and_forecast_qualifiers(tmp_path):
    root = tmp_path / "company"
    root.mkdir(mode=0o700)
    e = Engine(tmp_path / "audit", company_root=root)
    actor = e.store.provision("Auditor", ["learner"])["id"]
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Company",
        evidence_acquisition="COMPANY_SOURCE_COLLECTION",
        simulated_at="2027-05-01T00:00:00Z",
        people=[{"id": "owner"}, {"id": "other"}],
    )
    state = e.store.create(actor, state, "create")
    e.company_bindings[state["id"]] = {"company": "SH", "branch": "base"}
    for system, owner in [("owned", "owner"), ("different", "other"), ("denied", "owner")]:
        e.company_store.register_system("SH", "base", system, owner)
        for record, date in [
            ("available", "2027-01-01T00:00:00Z"),
            ("future", "2028-01-01T00:00:00Z"),
        ]:
            e.company_store.append_version(
                "SH",
                "base",
                system,
                record,
                expected_version=0,
                command_id=system + record,
                event_at=date,
                available_at=date,
                content=json.dumps(
                    {"forecast": "PROPOSED MODEL ONLY", "system": system, "record": record}
                ).encode(),
                provenance={
                    "source_reference": {"private_path": "NOT_MODEL_CONTEXT"},
                    "name": "forecast.json",
                    "forecast_status": "NOT_ACTUAL",
                },
            )
        if system != "denied":
            e.company_store.grant(actor, state["id"], "SH", "base", system)
    result = sources(e, actor, state, "owner")
    originals = [row for row in result if row["kind"] == "COMPANY_ORIGINAL_RECORD"]
    assert len(originals) == 1 and originals[0]["value"]["system_id"] == "owned"
    assert originals[0]["value"]["record_id"] == "available"
    assert originals[0]["value"]["qualifiers"] == {"forecast_status": "NOT_ACTUAL"}
    assert "PROPOSED MODEL ONLY" in json.dumps(result)
    assert "NOT_MODEL_CONTEXT" not in json.dumps(result)
    forged = {**state, "simulated_at": "2030-01-01T00:00:00Z"}
    assert sources(e, actor, forged, "owner") == result
    e.company_store.grant(actor, state["id"], "SH", "base", "owned", active=False)
    assert len(sources(e, actor, state, "owner")) == 1
    assert e.store.get(actor, state["id"])["revision"] == state["revision"]


def test_sampling_limits_and_no_truncated_claims(tmp_path, monkeypatch):
    from enterprise.audit_suite import company_persona

    root = tmp_path / "company"
    root.mkdir(mode=0o700)
    e = Engine(tmp_path / "audit", company_root=root)
    actor = e.store.provision("Auditor", ["learner"])["id"]
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Bounded",
        evidence_acquisition="COMPANY_SOURCE_COLLECTION",
        simulated_at="2027-05-01T00:00:00Z",
        people=[{"id": "owner"}],
    )
    state = e.store.create(actor, state, "create")
    e.company_bindings[state["id"]] = {"company": "SH", "branch": "base"}
    e.company_store.register_system("SH", "base", "owned", "owner")
    e.company_store.grant(actor, state["id"], "SH", "base", "owned")
    for number in range(6):
        e.company_store.append_version(
            "SH",
            "base",
            "owned",
            f"record{number}",
            expected_version=0,
            command_id=f"import{number}",
            event_at="2027-01-01T00:00:00Z",
            available_at="2027-01-01T00:00:00Z",
            content=b"complete original statement",
            provenance={"source_reference": "synthetic", "name": "source.txt"},
        )
    result = sources(e, actor, state, "owner")
    assert len(result) == 5  # Four originals plus explicit sample boundary.
    assert result[0]["value"]["population_status"] == "NOT_POPULATION_COMPLETE"
    monkeypatch.setattr(company_persona, "MAX_CHARACTERS", 5)
    limited = sources(e, actor, state, "owner")
    assert len(limited) == 1  # Full statement omitted; no misleading five-character excerpt.
