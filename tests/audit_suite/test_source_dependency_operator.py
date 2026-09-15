import json
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_portfolio_explanation import setup as base_setup
from tests.audit_suite.test_source_dependency_reconciliation import prepared
from tools.audit_suite import reconcile_source_dependencies as operator


def write(path, value):
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    return path


def test_operator_reads_explicit_existing_portfolio_without_commands(tmp_path):
    setup = base_setup.__wrapped__(tmp_path)
    engine, actor, eid, plan = prepared(setup)
    before = engine.store.get(actor, eid)
    bindings = write(tmp_path / "bindings.json", engine.company_bindings)
    plan_path = write(tmp_path / "plan.json", plan)
    config = write(
        tmp_path / "config.json",
        {
            "audit_root": str(engine.store.root),
            "actor_id": actor,
            "engagement_id": eid,
            "company_registry": str(setup[4]),
            "company_profile": "portfolio",
            "company_bindings": str(bindings),
            "plan": str(plan_path),
        },
    )
    output = tmp_path / "report"
    result = operator.run(config, output)
    assert Path(result["path"]) == output
    report = json.loads((output / "REPORT.json").read_text())
    assert report["coherent_operating_year"] == "NOT_ESTABLISHED"
    assert engine.store.get(actor, eid) == before
    with pytest.raises(DomainError):
        operator.run(config, output)
    read_only = operator.ReadOnlyStore(engine.store.root)
    with read_only.connect() as db, pytest.raises(sqlite3.OperationalError):
        db.execute("CREATE TABLE forbidden_write (id TEXT)")
    blank = tmp_path / "blank-audit"
    blank.mkdir(mode=0o700)
    database = blank / "engagements.sqlite3"
    database.touch(mode=0o600)
    value = json.loads(config.read_text())
    value["audit_root"] = str(blank)
    write(config, value)
    with pytest.raises((DomainError, sqlite3.DatabaseError)):
        operator.run(config, tmp_path / "blank-report")
    assert database.read_bytes() == b""
    assert list(blank.iterdir()) == [database]
    assert not (tmp_path / "blank-report").exists()


@pytest.mark.parametrize("raw", ['{"x":1,"x":2}', '{"x":NaN}', "[]"])
def test_ambiguous_or_nonobject_input_is_rejected(tmp_path, raw):
    tmp_path.chmod(0o700)
    path = tmp_path / "config.json"
    path.write_text(raw)
    path.chmod(0o600)
    with pytest.raises(DomainError):
        operator.run(path, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_changed_private_input_and_missing_audit_never_initialize_store(tmp_path, monkeypatch):
    tmp_path.chmod(0o700)
    path = write(tmp_path / "config.json", {"example": "value"})
    original = operator.os.open

    def changed(value, *args, **kwargs):
        if Path(value) == path:
            path.chmod(0o644)
        return original(value, *args, **kwargs)

    monkeypatch.setattr(operator.os, "open", changed)
    with pytest.raises(DomainError):
        operator.read_json(path)
    monkeypatch.setattr(operator.os, "open", original)
    config = {key: "explicit-value" for key in operator.FIELDS}
    config["audit_root"] = str(tmp_path / "missing-audit")
    write(path, config)
    with pytest.raises((DomainError, FileNotFoundError)):
        operator.run(path, tmp_path / "output")
    assert not (tmp_path / "missing-audit").exists()
