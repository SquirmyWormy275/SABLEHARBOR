"""Additional transaction-boundary review without private corpus dependencies."""

import pytest

from enterprise.audit_suite.company_migration import plan_legacy_documents
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_collection import envelope
from tests.audit_suite.test_company_collection import workspace as base_workspace
from tests.audit_suite.test_company_migration import fixture


@pytest.fixture
def workspace(tmp_path):
    return base_workspace.__wrapped__(tmp_path)




def test_collection_recovers_after_artifact_storage_failure(workspace, monkeypatch):
    engine, actor, state = workspace
    original = engine.artifacts.retain_company
    with monkeypatch.context() as m:

        def fail(*args, **kwargs):
            raise DomainError("Injected storage outage")

        m.setattr(engine.artifacts, "retain_company", fail)
        with pytest.raises(DomainError, match="storage outage"):
            engine.command(actor, state["id"], envelope(state))
    assert engine.store.get(actor, state["id"])["revision"] == state["revision"]
    assert engine.store.get(actor, state["id"])["artifacts"] == []
    with engine.company_store._db() as db:
        first_receipt = db.execute("SELECT receipt FROM collections").fetchone()[0]
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 1
    assert engine.artifacts.retain_company == original
    result = engine.command(actor, state["id"], envelope(state))
    assert len(result["artifacts"]) == 1
    with engine.company_store._db() as db:
        assert db.execute("SELECT receipt FROM collections").fetchone()[0] == first_receipt
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 1


def test_review_member_cannot_collect_even_with_source_grant(workspace):
    engine, _, state = workspace
    reviewer = engine.store.provision("Reviewer", ["reviewer"])["id"]
    engine.store.grant(state["id"], reviewer, "review")
    engine.company_store.grant(reviewer, state["id"], "SH", "base", "identity")
    with pytest.raises(DomainError):
        engine.command(reviewer, state["id"], envelope(state))
    assert engine.store.get(reviewer, state["id"])["artifacts"] == []


def test_migration_nested_ancestor_alias_is_rejected(tmp_path):
    root = tmp_path / "actual"
    root.mkdir()
    fixture(root)
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    # Alias is a parent of supplied root, not one of its immediate named source paths.
    nested = root / "nested"
    nested.mkdir()
    fixture(nested)
    with pytest.raises(DomainError):
        plan_legacy_documents(alias / "nested", "ENG-abc")
