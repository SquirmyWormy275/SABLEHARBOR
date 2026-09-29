"""Adversarial contract for the opt-in company rights and legacy portal routes.

These assertions deliberately fail on the isolated producer branch until the
same rights boundary covers native discovery, collection, and retained bytes.
They are a handoff to the portal integration owner, not a deployment claim.
"""

import hashlib

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite.company_rights_producer import CompanyRightsProducer
from enterprise.audit_suite.engine import COLLECTIONS
from enterprise.audit_suite.service import create_app
from tests.audit_suite.test_company_rights_http import decide, row, validate_record


@pytest.fixture
def protected_company(tmp_path):
    for name in ("rights", "checkpoint", "company"):
        (tmp_path / name).mkdir(mode=0o700)
    policy = tmp_path / "policy.json"
    policy.write_text('{"accepted":"test-only"}')
    raw = b"PRIVATE-SYNTHETIC-COMPANY-RECORD\n"
    producer_holder = {}

    def factory(engine):
        producer = CompanyRightsProducer(
            store=engine.store,
            rights_root=tmp_path / "rights",
            checkpoint_root=tmp_path / "checkpoint",
            policy_file=policy,
            policy_sha256=hashlib.sha256(policy.read_bytes()).hexdigest(),
            source_commit="a" * 40,
            source_bytes=lambda path: {"docs/company.txt": raw}[path],
            validate_record=validate_record,
            decide=decide,
            known_person_ids=frozenset({"PERSON-1"}),
        )
        producer_holder["producer"] = producer
        return producer

    app = create_app(
        tmp_path / "audit",
        company_root=tmp_path / "company",
        allowed_hosts=["testserver"],
        company_rights_factory=factory,
    )
    engine = app.state.engine
    person = engine.store.provision("Auditor", ["learner"])
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Protected source audit",
        phase="ACTIVE",
        discipline="IT",
        mode="CLEAN",
        simulated_at="2027-06-01T00:00:00Z",
        scope={"boundaries": ["corporate"], "period_start": "2027-01-01",
               "period_end": "2027-12-31", "timezone": "UTC"},
        configuration={"selections": []},
    )
    state["requests"] = [{"id": "R1", "status": "ISSUED", "artifact_ids": []}]
    state = engine.store.create(person["id"], state, "create")
    engine.company_bindings[state["id"]] = {"company": "SH", "branch": "base"}
    company = engine.company_store
    company.register_system("SH", "base", "identity", "owner")
    company.append_version(
        "SH", "base", "identity", "REC-1",
        expected_version=0,
        command_id="import",
        event_at="2027-01-01T00:00:00Z",
        available_at="2027-01-02T00:00:00Z",
        content=raw,
        provenance={"source_reference": "synthetic-test-original", "name": "company.txt"},
    )
    # An ordinary audit system grant must not act as a per-record disclosure
    # grant when the protected company rights producer is installed.
    company.grant(person["id"], state["id"], "SH", "base", "identity")
    client = TestClient(app, base_url="https://testserver")
    login = client.post("/api/session", json={"credential": person["credential"]})
    assert login.status_code == 200
    producer = producer_holder["producer"]
    producer.bind_person(
        principal_id=person["id"], engagement_id=state["id"],
        person_id="PERSON-1", tenant="SH", purpose="inspection", expected_revision=0,
    )
    producer.put_record(
        row("REC-1", "docs/company.txt", raw, None), expected_revision=1,
    )
    return app, client, engine, state, producer, raw, login.json()["csrf_token"]


def _root(state):
    return f"/api/engagements/{state['id']}"


def _collect(client, state, csrf):
    return client.post(
        _root(state) + "/commands",
        headers={"X-CSRF-Token": csrf},
        json={
            "command_id": "collect",
            "expected_revision": state["revision"],
            "kind": "company.collect",
            "payload": {"system_id": "identity", "record_id": "REC-1",
                        "version": 1, "request_id": "R1"},
        },
    )


def test_native_discovery_does_not_bypass_absent_record_grant(protected_company):
    _, client, _, state, _, _, _ = protected_company
    root = _root(state)
    assert client.get(root + "/company/rights/records/REC-1").status_code == 403
    assert client.get(root + "/company/rights/count?q=PRIVATE").json() == {"count": 0}
    assert client.get(root + "/company/rights/search?q=PRIVATE").json()["records"] == []
    systems = client.get(root + "/company/systems")
    assert systems.status_code in {403, 404} or systems.json() == {"systems": []}


def test_native_record_metadata_does_not_bypass_absent_record_grant(protected_company):
    _, client, _, state, _, _, _ = protected_company
    root = _root(state)
    records = client.get(root + "/company/systems/identity/records")
    assert records.status_code in {403, 404} or records.json()["records"] == []


def test_native_collection_does_not_bypass_absent_record_grant(protected_company):
    _, client, _, state, _, _, csrf = protected_company
    assert _collect(client, state, csrf).status_code in {403, 404}


def test_retained_download_rechecks_deleted_company_record(protected_company):
    _, client, engine, state, producer, raw, _ = protected_company
    producer.put_record(
        row("REC-1", "docs/company.txt", raw, ["read", "export"]), expected_revision=2,
    )
    # Model a source already collected into retained audit evidence before the
    # protected HTTP path is enabled or while the record was still permitted.
    saved = engine.command(state["created_by"], state["id"], {
        "command_id": "collect-prior",
        "expected_revision": state["revision"],
        "kind": "company.collect",
        "payload": {"system_id": "identity", "record_id": "REC-1",
                    "version": 1, "request_id": "R1"},
    })
    artifact_id = saved["artifacts"][0]["id"]
    url = _root(state) + f"/artifacts/{artifact_id}/download"
    assert client.get(url).status_code == 200
    producer.delete_record("REC-1")
    assert client.get(_root(state) + "/company/rights/records/REC-1").status_code == 403
    assert client.get(url).status_code in {403, 404}
