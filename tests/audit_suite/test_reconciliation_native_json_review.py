"""Raw-byte source integrity does not resolve ambiguous JSON interpretation."""

import hashlib

import pytest

from enterprise.audit_suite.source_dependency_reconciliation import reconcile
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_source_dependency_reconciliation import prepared
from tests.audit_suite.test_source_dependency_reconciliation import setup as portfolio_setup


@pytest.fixture
def setup(tmp_path):
    return portfolio_setup.__wrapped__(tmp_path)


def _append_raw(setup, raw):
    engine, actor, eid, plan = prepared(setup)
    store = setup[2]["one"]
    native = store.append_version(
        "NATIVE",
        "branch",
        "records",
        "AMBIGUOUS",
        expected_version=0,
        command_id="ambiguous-native",
        event_at="2027-01-01T00:00:00Z",
        available_at="2027-01-01T00:00:00Z",
        content=raw,
        provenance={"source_reference": "neutral-parser-regression"},
    )
    assert native["sha256"] == hashlib.sha256(raw).hexdigest()
    plan["source_refs"] = [
        {**plan["source_refs"][0], "record": "AMBIGUOUS", "version": 1, "sha256": native["sha256"]}
    ]
    return engine, actor, eid, plan


@pytest.mark.parametrize(
    "raw",
    [
        b'{"classification":"UNVERIFIED","classification":"LOCAL_VERIFIED"}',
        b'{"removed_permission_probes":{"billing-admin":"ALLOW","billing-admin":"DENY"}}',
        b'{"observation":NaN}',
        b'{"observation":Infinity}',
        b'{"observation":1e999}',
        b'{"observation":-1e999}',
    ],
)
def test_pinned_native_json_ambiguity_is_rejected(setup, raw):
    engine, actor, eid, plan = _append_raw(setup, raw)
    before = engine.store.get(actor, eid)
    with pytest.raises(DomainError, match="JSON"):
        reconcile(engine, actor, eid, plan)
    assert engine.store.get(actor, eid) == before


def test_ordinary_nested_native_json_still_reconciles(setup):
    engine, actor, eid, plan = _append_raw(
        setup,
        b'{"classification":"LOCAL_EXERCISE","removed_permission_probes":{"billing-admin":"DENY"},"count":1,"optional":null}',
    )
    result = reconcile(engine, actor, eid, plan)
    assert result["sources"][0]["native_qualifiers"]["classification"] == "LOCAL_EXERCISE"
    assert result["control_effectiveness"] == "NOT_ASSESSED"
