"""Independent narrow adversarial review; no real company source mutation."""

import pytest

from enterprise.audit_suite.company_source_census import validate_query
from enterprise.audit_suite.company_source_census_collection import _period
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.store import DomainError, canonical
from tests.audit_suite import test_company_source_census as source_fixtures
from tests.audit_suite import test_company_source_census_collection as collection_fixtures
from tests.audit_suite.test_company_source_census import QUERY, run
from tests.audit_suite.test_company_source_census_collection import envelope

native = source_fixtures.native
workspace = collection_fixtures.workspace


@pytest.mark.parametrize(
    "field,value",
    [
        ("version_policy", []),
        ("unknown_event_policy", {}),
        ("event_window", {"start": "0001-01-01T00:00:00+01:00", "end": "2027-02-01T00:00:00Z"}),
        ("event_window", {"start": "2027-01-01T00:00:00Z", "end": "9999-12-31T23:59:59-01:00"}),
    ],
)
def test_malformed_and_unrepresentable_query_gets_typed_rejection(field, value):
    with pytest.raises(CompanyStoreError):
        validate_query({**QUERY, field: value})


def test_denver_dst_half_open_day_is_23_hours_not_fixed_utc_day():
    scope = {"period_start": "2027-03-14", "period_end": "2027-03-14", "timezone": "America/Denver"}
    query = {
        **QUERY,
        "event_window": {"start": "2027-03-14T07:00:00Z", "end": "2027-03-15T06:00:00Z"},
    }
    assert _period(scope, query) == (
        "2027-03-14T07:00:00+00:00",
        "2027-03-15T05:59:59.999999+00:00",
    )
    with pytest.raises(DomainError):
        _period(
            scope,
            {**query, "event_window": {**query["event_window"], "end": "2027-03-15T07:00:00Z"}},
        )


def test_retry_after_retention_failure_preserves_source_and_single_committed_receipt(
    workspace, monkeypatch
):
    e, actor, state = workspace
    command = envelope(state)
    original = e.artifacts.retain
    calls = 0

    def interrupted(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise DomainError("Isolated storage interruption")
        return original(*args, **kwargs)

    monkeypatch.setattr(e.artifacts, "retain", interrupted)
    with pytest.raises(DomainError):
        e.command(actor, state["id"], command)
    unchanged = e.store.get(actor, state["id"])
    assert unchanged["revision"] == 0 and unchanged["artifacts"] == []
    assert len(e.store.history(actor, state["id"])) == 1
    with e.company_store._db() as db:
        prior = [dict(r) for r in db.execute("SELECT * FROM versions ORDER BY record")]
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 2
    monkeypatch.setattr(e.artifacts, "retain", original)
    completed = e.command(actor, state["id"], command)
    assert canonical(e.command(actor, state["id"], command)) == canonical(completed)
    assert len(completed["requests"][0]["company_census_collections"]) == 1
    assert len(completed["artifacts"]) == 4 and not completed["populations"]
    with e.company_store._db() as db:
        assert [dict(r) for r in db.execute("SELECT * FROM versions ORDER BY record")] == prior
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 2


def test_review_only_actor_and_revoked_actor_cannot_collect_or_replay(workspace):
    e, actor, state = workspace
    reviewer = e.store.provision("Reviewer", ["reviewer"])["id"]
    e.store.grant(state["id"], reviewer, "review")
    e.company_store.grant(reviewer, state["id"], "SH", "branch", "records")
    with pytest.raises(DomainError):
        e.command(reviewer, state["id"], envelope(state))
    completed = e.command(actor, state["id"], envelope(state))
    # Revocation checks engagement identity even for exact already-committed replay.
    e.store.revoke(actor)
    with pytest.raises(DomainError):
        e.command(actor, state["id"], envelope(state))
    assert completed["revision"] == 1


def test_branch_and_metadata_quota_fail_without_partial_census(native, monkeypatch):
    from enterprise.audit_suite import company_source_census as module

    with pytest.raises(CompanyStoreError):
        run(native, branch_id="other")
    monkeypatch.setattr(module, "MAX_METADATA_BYTES", 1)
    with pytest.raises(CompanyStoreError, match="metadata quota"):
        run(native)
    with native._db() as db:
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0


@pytest.mark.parametrize(
    "change",
    [
        {"version_policy": []},
        {"unknown_event_policy": "GUESS"},
        {"event_window": {"start": "0001-01-01T00:00:00+01:00", "end": "2027-02-01T00:00:00Z"}},
    ],
)
def test_engine_malformed_query_is_400_not_source_authority_error(workspace, change):
    e, actor, state = workspace
    command = envelope(state)
    command["payload"] = {**command["payload"], "query": {**QUERY, **change}}
    with pytest.raises(DomainError) as caught:
        e.command(actor, state["id"], command)
    assert caught.value.code == "INVALID_CENSUS_QUERY" and caught.value.status == 400
    assert e.store.get(actor, state["id"])["revision"] == 0
    with e.company_store._db() as db:
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0


def test_engine_valid_query_denied_source_remains_403(workspace):
    e, actor, state = workspace
    e.company_store.grant(actor, state["id"], "SH", "branch", "records", active=False)
    with pytest.raises(DomainError) as caught:
        e.command(actor, state["id"], envelope(state))
    assert caught.value.code == "SOURCE_CENSUS_UNAVAILABLE" and caught.value.status == 403
