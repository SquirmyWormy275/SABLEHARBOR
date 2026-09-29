"""Trusted export CLI keeps native target bytes distinct from receipt envelopes."""

import json

import pytest

from enterprise.audit_suite.company_backup_runtime import database, native
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_configuration_runtime import command, snapshot
from tests.audit_suite.test_company_configuration_runtime import ready as ready
from tools.audit_suite import company_configuration_export as cli


def export_action(tmp_path, ready):
    parameters = command(ready, "RECONCILE", "export-current")
    parameters.pop("operation")
    path = tmp_path / "export.json"
    path.write_bytes(encoded({"kind": "EXPORT_CURRENT", "parameters": parameters}))
    path.chmod(0o600)
    return path


def test_cli_exports_original_bytes_and_exact_replay_keeps_one_export(ready, tmp_path):
    root, *_ = ready
    with database(root) as db:
        current = dict(db.execute("SELECT * FROM configuration_state WHERE id=1").fetchone())
    raw = (root / "objects" / current["file"]).read_bytes()
    action = export_action(tmp_path, ready)
    cli.main(
        ["--runtime", str(root), "--action", str(action), "--output", str(tmp_path / "receipt")]
    )
    result = json.loads((tmp_path / "receipt/RESULT.json").read_text())
    assert result["native_pin"]["sha256"] == sha(raw)
    with database(root) as db:
        assert native(db, result["native_pin"])["content"] == raw
        after = dict(db.execute("SELECT * FROM configuration_state WHERE id=1").fetchone())
    assert after["file"] == current["file"] and after["sha256"] == current["sha256"]
    before_replay = snapshot(root)
    assert cli.run(root, action, tmp_path / "replay") == result
    assert snapshot(root) == before_replay
    assert json.loads((tmp_path / "receipt/MANIFEST.json").read_text())["format"] == (
        "COMPANY_CONFIGURATION_EXPORT_RECEIPT_V1"
    )
    for path in (tmp_path / "receipt").iterdir():
        assert path.stat().st_mode & 0o077 == 0


def test_export_receipt_failure_recovers_without_second_native_export(ready, tmp_path, monkeypatch):
    root, *_ = ready
    action = export_action(tmp_path, ready)
    original = cli.publish_receipt

    def fail(*args, **kwargs):
        raise OSError("Receipt unavailable")

    monkeypatch.setattr(cli, "publish_receipt", fail)
    with pytest.raises(DomainError, match="EXPORT_COMMITTED_RECEIPT_NOT_PUBLISHED"):
        cli.run(root, action, tmp_path / "failed")
    before_replay = snapshot(root)
    monkeypatch.setattr(cli, "publish_receipt", original)
    cli.run(root, action, tmp_path / "recovered")
    assert snapshot(root) == before_replay


def test_export_cli_rejects_extra_fields_and_runtime_receipt_before_operation(ready, tmp_path):
    root, *_ = ready
    action = export_action(tmp_path, ready)
    before = snapshot(root)
    with pytest.raises(DomainError):
        cli.run(root, action, root / "receipt")
    value = json.loads(action.read_text())
    value["parameters"]["configuration"] = {}
    action.write_bytes(encoded(value))
    with pytest.raises(DomainError):
        cli.run(root, action, tmp_path / "receipt")
    assert snapshot(root) == before
