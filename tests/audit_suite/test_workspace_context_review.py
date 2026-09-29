from copy import deepcopy

import pytest

from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_workspace_context import change, payload
from tests.audit_suite.test_workspace_context import workspace as original_workspace


@pytest.fixture
def workspace(tmp_path):
    return original_workspace.__wrapped__(tmp_path)


@pytest.mark.parametrize(
    "field,value",
    [
        ("company_source_binding", {"company": "company-one", "branch": "different-branch"}),
        ("evidence_acquisition", "COMPANY_SOURCES"),
    ],
)
def test_source_basis_change_preserves_exact_historical_links(workspace, field, value):
    contexts, engine, actor, state = workspace
    saved = contexts.create(actor, state["id"], payload(contexts, actor, state), command_id="save")
    assert saved["context_status"] == "CURRENT"
    change(engine, actor, state, lambda s: s.update({field: value}))
    current = contexts.read(actor, state["id"], saved["id"])
    assert current["scope_status"] == "CURRENT"
    assert current["context_status"] == "CONTEXT_CHANGED"
    assert current["user"] == saved["user"]
    assert current["context_basis"] == saved["context_basis"]
    assert all(link["status"] == "EXACT_PIN_AVAILABLE" for link in current["link_status"])


def test_permission_change_is_not_silently_current(workspace):
    contexts, engine, actor, state = workspace
    saved = contexts.create(actor, state["id"], payload(contexts, actor, state), command_id="save")
    engine.store.grant(state["id"], actor, "review")
    current = contexts.read(actor, state["id"], saved["id"])
    assert current["context_status"] == "CONTEXT_CHANGED"
    assert current["user"] == saved["user"]


def test_old_snapshot_does_not_claim_unrecorded_basis_current(workspace):
    contexts, engine, actor, state = workspace
    saved = contexts.create(actor, state["id"], payload(contexts, actor, state), command_id="save")
    old = deepcopy(saved)
    del old["context_basis"]
    del old["context_basis_sha256"]
    assert (
        contexts._view(old, engine.get(actor, state["id"]))["context_status"] == "BASIS_UNRECORDED"
    )


def test_permission_changed_during_save_rolls_back(workspace, monkeypatch):
    contexts, engine, actor, state = workspace
    data = payload(contexts, actor, state)
    original = contexts._payload

    def revoke_write_basis(s, p):
        result = original(s, p)
        engine.store.grant(state["id"], actor, "review")
        return result

    monkeypatch.setattr(contexts, "_payload", revoke_write_basis)
    with pytest.raises(DomainError) as failure:
        contexts.create(actor, state["id"], data, command_id="race")
    assert failure.value.status == 409
    assert contexts.listing(actor, state["id"]) == []
