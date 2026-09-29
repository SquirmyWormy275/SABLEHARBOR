"""Neutral native source records exercise actual company delivery and lineage."""

import json
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from enterprise.audit_suite import parent_support, populations
from enterprise.audit_suite.artifacts import Artifacts
from enterprise.audit_suite.engine import Engine
from enterprise.audit_suite.store import DomainError


@pytest.fixture
def context(tmp_path):
    private = tmp_path / "runtime"
    private.mkdir(mode=0o700)
    corpus = tmp_path / "corpus"
    (corpus / "parent-support").mkdir(parents=True, mode=0o700)
    source = {
        "schema_version": 1,
        "source_id": "neutral-source",
        "version": "1",
        "origin": "AUTHORED_TRAINING_RECORDS",
        "applicable_control_ids": ["CONTROL-A"],
        "boundaries": ["unit-a"],
        "period_start": "2027-01-01T00:00:00+00:00",
        "period_end": "2027-12-31T23:59:59+00:00",
        "tables": {},
    }
    tables = {
        "sites": [
            {"id": i, "boundary_id": "unit-a", "occurred_at": "2027-01-01T00:00:00+00:00"}
            for i in ["SITE-A", "SITE-B"]
        ],
        "tickets": [
            {
                "id": i,
                "site_id": site,
                "boundary_id": "unit-a",
                "occurred_at": at,
                "quantity": str(n),
            }
            for i, site, at, n in [
                ("T1", "SITE-A", "2027-06-01T10:00:00+00:00", 10),
                ("T2", "SITE-A", "2027-07-01T10:00:00+00:00", 20),
                ("T3", "SITE-B", "2027-06-01T10:00:00+00:00", 30),
            ]
        ],
        "support": [
            {
                "id": "U" + str(n),
                "ticket_id": "T" + str(n),
                "boundary_id": "unit-a",
                "occurred_at": "2027-07-02T10:00:00+00:00",
                "source_reading": str(n * 10),
            }
            for n in range(1, 4)
        ],
    }
    source["tables"] = {k: {"columns": list(v[0]), "rows": v} for k, v in tables.items()}
    path = corpus / "parent-support/source.json"
    path.write_text(json.dumps(source))
    path.chmod(0o600)
    engine = SimpleNamespace(
        store=SimpleNamespace(root=private),
        corpus_root=corpus,
        artifacts=Artifacts(private),
        _population=Engine._population,
        _selection=Engine._selection,
    )
    state = {
        "id": "ENG-" + "a" * 24,
        "generation_epoch": 0,
        "phase": "ACTIVE",
        "simulated_at": "2027-01-01T00:00:00+00:00",
        "scope": {
            "boundaries": ["unit-a"],
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "timezone": "UTC",
        },
        "controls": [{"id": "CONTROL-A", "assignment": {"custodian_person_id": "PERSON-A"}}],
        "people": [{"id": "PERSON-A"}],
        "requests": [],
        "artifacts": [],
        "populations": [],
        "selections": [],
    }
    return engine, state, path, source


def request(context, kind="sites", selection=None):
    engine, state, _, _ = context
    payload = {
        "support_kind": kind,
        "purpose": "Inspect original records",
        "rationale": "Trace selected units",
    }
    if selection:
        payload["parent_selection_id"] = selection["id"]
    else:
        payload.update(control_id="CONTROL-A", boundary_id="unit-a")
    result = parent_support.create_request(engine, state, payload, {})
    state["requests"].append(result)
    return result


def deliver(context, req):
    engine, state, _, _ = context
    req["status"] = "ISSUED"
    state["simulated_at"] = "2027-12-31T23:59:59+00:00"
    plan = parent_support.request_plan(engine, state, req)
    for manifest in plan["prepared_artifacts"]:
        state["artifacts"].append(manifest)
        req["artifact_ids"].append(manifest["id"])
        parent_support.import_delivered_population(engine, state, manifest, req, {})
    return state["populations"][-1]


def select(context, population, ids, name):
    engine, state, _, _ = context
    obj = populations.select(
        engine._population(population),
        selection_id=name,
        method="MANUAL",
        purpose="Inspect selected records",
        rationale="Neutral purposive sample",
        ids=ids,
    )
    row = {"id": obj.id, "population_id": obj.population_id, "immutable": asdict(obj)}
    state["selections"].append(row)
    return row


def test_company_sites_to_tickets_to_original_support(context):
    engine, state, _, source = context
    sites_request = request(context)
    assert not state["artifacts"] and not state["populations"]
    sites = deliver(context, sites_request)
    chosen = select(context, sites, ["SITE-A"], "SEL-SITES")
    tickets = deliver(context, request(context, "tickets", chosen))
    assert [r["id"] for r in tickets["rows"]] == ["T1", "T2"]
    assert tickets["rows"] == source["tables"]["tickets"]["rows"][:2]
    child_choice = select(context, tickets, ["T2"], "SEL-TICKETS")
    support = deliver(context, request(context, "support", child_choice))
    assert support["rows"] == [source["tables"]["support"]["rows"][1]]
    child = engine._population(support)
    assert child.parent_population_digest == engine._population(tickets).sha256
    assert child.parent_selection_digest == engine._selection(child_choice).sha256
    assert child.parent_key == "ticket_id" and child.status == "PROVISIONAL"
    assert "T3" not in json.dumps(parent_support.request_plan(engine, state, state["requests"][-1]))


def test_no_import_before_request_issue_or_availability(context):
    engine, state, _, _ = context
    req = request(context)
    manifest = parent_support.request_plan(engine, state, req)["prepared_artifacts"][0]
    req["artifact_ids"].append(manifest["id"])
    with pytest.raises(DomainError, match="delivered original"):
        parent_support.import_delivered_population(engine, state, manifest, req, {})
    req["status"] = "ISSUED"
    with pytest.raises(DomainError, match="delivered original"):
        parent_support.import_delivered_population(engine, state, manifest, req, {})
    assert not state["populations"]


def test_retry_after_uncommitted_request_reuses_exact_manifest_ids(context):
    engine, state, _, _ = context
    first = request(context)
    state["requests"].clear()
    again = request(context)
    assert again == first
    deliver(context, again)
    count = len(state["populations"])
    plan = parent_support.request_plan(engine, state, again)
    parent_support.import_delivered_population(
        engine, state, plan["prepared_artifacts"][0], again, {}
    )
    assert len(state["populations"]) == count


def test_source_freezes_original_bytes_across_external_corpus_changes(context):
    engine, state, path, source = context
    sites = deliver(context, request(context))
    chosen = select(context, sites, ["SITE-A"], "SEL-A")
    source["tables"]["tickets"]["rows"][0]["quantity"] = "999"
    path.write_text(json.dumps(source))
    tickets = deliver(context, request(context, "tickets", chosen))
    assert tickets["rows"][0]["quantity"] == "10"


@pytest.mark.parametrize("mutation", ["duplicate", "orphan", "boundary", "mode", "symlink"])
def test_invalid_private_native_source_rejected(context, mutation):
    _, _, path, source = context
    if mutation == "duplicate":
        source["tables"]["tickets"]["rows"].append(source["tables"]["tickets"]["rows"][0])
    elif mutation == "orphan":
        source["tables"]["tickets"]["rows"][0]["site_id"] = "OUTSIDE"
    elif mutation == "boundary":
        source["tables"]["tickets"]["rows"][0]["boundary_id"] = "outside"
    path.write_text(json.dumps(source))
    if mutation == "mode":
        path.chmod(0o644)
    if mutation == "symlink":
        target = path.with_name("target.json")
        path.rename(target)
        path.symlink_to(target)
    with pytest.raises(DomainError):
        request(context)


@pytest.mark.parametrize(
    "mutation", ["learner_parent", "scope_epoch", "immutable_rows", "wrong_parent_kind"]
)
def test_child_requires_authentic_matching_parent_lineage(context, mutation):
    engine, state, _, _ = context
    sites = deliver(context, request(context))
    chosen = select(context, sites, ["SITE-A"], "SEL-A")
    if mutation == "learner_parent":
        sites.pop("company_support")
    elif mutation == "scope_epoch":
        state["generation_epoch"] = 1
    elif mutation == "immutable_rows":
        raw = sites["immutable"]["records_json"]
        sites["immutable"]["records_json"] = (raw[0].replace("SITE-A", "FAKE"), *raw[1:])
    else:
        sites["company_support"]["kind"] = "support"
    with pytest.raises((DomainError, ValueError)):
        request(context, "tickets", chosen)


def test_frozen_plan_and_delivered_bytes_cannot_be_replaced(context):
    engine, state, _, _ = context
    req = request(context)
    plan = parent_support.request_plan(engine, state, req)
    path = engine.artifacts.root / plan["prepared_artifacts"][0]["sha256"]
    path.write_bytes(b"different original")
    with pytest.raises(DomainError):
        deliver(context, req)


def test_period_and_boundary_are_not_silently_rebound(context):
    _, state, _, _ = context
    state["scope"]["period_end"] = "2028-01-01"
    with pytest.raises(DomainError, match="source coverage"):
        request(context)
    state["scope"]["period_end"] = "2027-12-31"
    state["scope"]["boundaries"] = ["outside"]
    with pytest.raises(DomainError, match="active scope"):
        request(context)


def test_date_scope_respects_local_timezone_without_rewriting_native_dates(context):
    engine, state, _, _ = context
    state["scope"].update(
        period_start="2027-06-01", period_end="2027-06-30", timezone="America/Los_Angeles"
    )
    sites = deliver(context, request(context))
    assert engine._population(sites).scope["period_start"] == "2027-06-01T00:00:00-07:00"
    chosen = select(context, sites, ["SITE-A"], "SEL-JUNE")
    tickets = deliver(context, request(context, "tickets", chosen))
    assert [r["id"] for r in tickets["rows"]] == ["T1"]
    assert tickets["rows"][0]["occurred_at"] == "2027-06-01T10:00:00+00:00"


def test_frozen_source_hash_detects_in_place_mutation(context):
    engine, state, _, _ = context
    request(context)
    path = engine.store.root / "worlds" / state["id"] / "parent-support/source.json"
    value = json.loads(path.read_text())
    value["version"] = "tampered"
    path.write_text(json.dumps(value))
    with pytest.raises(DomainError, match="differs on retry"):
        request(context)


def test_real_engine_command_chain_retains_company_lineage(context):
    """Actual authenticated command/storage path, using only neutral source facts."""
    from enterprise.audit_suite.engine import COLLECTIONS

    fixture, initial, _, source = context
    engine = Engine(fixture.store.root / "command-runtime", corpus_root=fixture.corpus_root)
    actor = engine.store.provision("Neutral learner", ["learner"])["id"]
    for collection in COLLECTIONS:
        initial.setdefault(collection, [])
    initial["simulated_at"] = "2028-01-03T09:00:00+00:00"
    initial["mode"] = "CUSTOM"
    current = engine.store.create(actor, initial, "neutral-command-source")
    engagement_id = current["id"]
    sequence = 0

    def command(kind, payload):
        nonlocal current, sequence
        sequence += 1
        request = {
            "command_id": f"neutral-{sequence}",
            "expected_revision": current["revision"],
            "kind": kind,
            "payload": payload,
        }
        current = engine.command(actor, engagement_id, request)
        assert json.dumps(engine.command(actor, engagement_id, request), sort_keys=True) == (
            json.dumps(current, sort_keys=True)
        )
        return current

    parent_id = None
    for kind, chosen_ids in [("sites", ["SITE-A"]), ("tickets", ["T2"]), ("support", [])]:
        payload = {
            "support_kind": kind,
            "purpose": "Trace company records",
            "rationale": "Inspect the selected original source rows",
        }
        if parent_id:
            payload["parent_selection_id"] = parent_id
        else:
            payload.update(control_id="CONTROL-A", boundary_id="unit-a")
        prior_artifacts = len(current["artifacts"])
        command("population.request_support", payload)
        req = current["requests"][-1]
        assert "parent_support" not in req and req["status"] == "DRAFT"
        assert len(current["artifacts"]) == prior_artifacts
        command("pbc.issue", {"request_id": req["id"]})
        assert len(current["artifacts"]) == prior_artifacts + 2
        pop = current["populations"][-1]
        assert pop.get("parent_selection_id") == parent_id
        if kind == "tickets":
            assert pop["rows"] == source["tables"]["tickets"]["rows"][:2]
        elif kind == "support":
            assert pop["rows"] == [source["tables"]["support"]["rows"][1]]
        if chosen_ids:
            command(
                "population.select",
                {
                    "population_id": pop["id"],
                    "method": "MANUAL",
                    "ids": chosen_ids,
                    "purpose": "Inspect original source support",
                    "rationale": "Neutral targeted inspection",
                },
            )
            parent_id = current["selections"][-1]["id"]
    assert len(current["populations"]) == 3
    assert engine.store.get(actor, engagement_id)["requests"][0]["parent_support"]
