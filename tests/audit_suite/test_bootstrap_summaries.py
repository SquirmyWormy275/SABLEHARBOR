"""Small navigation projections retain authorization without full-state decoding."""

import json
import time

import pytest
from fastapi.testclient import TestClient

from enterprise.audit_suite import store as store_module
from enterprise.audit_suite.service import create_app
from enterprise.audit_suite.store import DomainError, Store, canonical

FIELDS = ("id", "title", "discipline", "mode", "phase", "revision", "simulated_at")


def seed(store, actor, title):
    return store.create(
        actor["id"],
        {
            "title": title,
            "discipline": "IT",
            "mode": "CLEAN",
            "phase": "CONFIGURING",
            "simulated_at": "2027-01-01",
            "workpapers": [{"private": "x" * 2048}],
            "hidden_key": {"answer": "never in navigation"},
        },
        "create-" + title,
    )


@pytest.fixture
def context(tmp_path):
    store = Store(tmp_path / "state")
    actor = store.provision("Learner", ["learner"])
    other = store.provision("Other", ["learner"])
    first = seed(store, actor, "First")
    second = seed(store, actor, "Second ☃")
    seed(store, other, "Other")
    return store, actor, other, first, second


def test_exact_projection_order_and_no_full_state_json_decode(context, monkeypatch):
    store, actor, _, _, _ = context
    expected = [{k: state[k] for k in FIELDS} for state in store.listing(actor["id"])]
    original = json.loads
    decoded = []

    def small_only(value, *args, **kwargs):
        assert len(value) < 1024
        assert "workpapers" not in value and "never in navigation" not in value
        decoded.append(value)
        return original(value, *args, **kwargs)

    monkeypatch.setattr(store_module.json, "loads", small_only)
    assert store.listing_summaries(actor["id"]) == expected
    assert len(decoded) == 3  # Principal role list and two small summary arrays.


def test_membership_revocation_and_identity_expiry(context):
    store, actor, other, first, second = context
    assert [x["title"] for x in store.listing_summaries(other["id"])] == ["Other"]
    with store.connect() as db:
        db.execute(
            "DELETE FROM members WHERE engagement=? AND principal=?", (second["id"], actor["id"])
        )
    assert [x["id"] for x in store.listing_summaries(actor["id"])] == [first["id"]]
    with store.connect() as db:
        db.execute("UPDATE principals SET expires=? WHERE id=?", (time.time() - 1, actor["id"]))
    with pytest.raises(DomainError) as expired:
        store.listing_summaries(actor["id"])
    assert expired.value.status == 401
    store.revoke(other["id"])
    with pytest.raises(DomainError) as revoked:
        store.listing_summaries(other["id"])
    assert revoked.value.status == 401


@pytest.mark.parametrize(
    "change",
    [
        {"id": "wrong"},
        {"revision": 12},
        {"revision": True},
        {"title": None},
        {"mode": {"private": "wrong type"}},
        {"discipline": None},
    ],
)
def test_invalid_summary_fails_closed(context, change):
    store, actor, _, first, _ = context
    with store.connect() as db:
        db.execute(
            "UPDATE engagements SET state=? WHERE id=?", (canonical(first | change), first["id"])
        )
    with pytest.raises(DomainError) as failure:
        store.listing_summaries(actor["id"])
    assert failure.value.code == "INVALID_STATE" and failure.value.status == 500
    assert "private" not in str(failure.value)


def test_missing_field_and_malformed_state(context):
    store, actor, _, first, _ = context
    incomplete = dict(first)
    del incomplete["simulated_at"]
    for value in (canonical(incomplete), "{not-json"):
        with store.connect() as db:
            db.execute("UPDATE engagements SET state=? WHERE id=?", (value, first["id"]))
        with pytest.raises(DomainError, match="Invalid engagement summary"):
            store.listing_summaries(actor["id"])


def test_bootstrap_uses_summary_path_with_same_response(tmp_path, monkeypatch):
    app = create_app(tmp_path / "state", allowed_hosts=["testserver"])
    store = app.state.engine.store
    actor = store.provision("Learner", ["learner"])
    seed(store, actor, "Visible")
    expected = [{k: state[k] for k in FIELDS} for state in store.listing(actor["id"])]
    client = TestClient(app, base_url="https://testserver")
    headers = {"Authorization": "Bearer " + actor["credential"]}
    with monkeypatch.context() as legacy:
        legacy.setattr(
            store,
            "listing_summaries",
            lambda actor_id: [{k: state[k] for k in FIELDS} for state in store.listing(actor_id)],
        )
        previous = client.get("/api/bootstrap", headers=headers)
    assert previous.status_code == 200

    def forbidden(*args):
        raise AssertionError("Bootstrap must not load complete engagement states")

    monkeypatch.setattr(store, "listing", forbidden)
    response = client.get("/api/bootstrap", headers=headers)
    assert response.status_code == 200
    assert response.json() == previous.json()
    assert response.json()["engagements"] == expected
    assert response.json()["viewer"]["id"] == actor["id"]
    assert response.json()["capabilities"]["review_feedback"] is True
    assert "hidden_key" not in response.text and "never in navigation" not in response.text
