"""Private operator receipts preserve actual operation and exact replay boundaries."""

import json

import pytest

from enterprise.audit_suite.operating_source_bridge import encoded
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_configuration_runtime import command, snapshot
from tests.audit_suite.test_company_configuration_runtime import ready as ready
from tools.audit_suite import company_configuration_runtime as cli


def action_file(tmp_path, ready, operation, identifier):
    parameters = command(ready, operation, identifier)
    parameters.pop("operation")
    path = tmp_path / (identifier + ".json")
    path.write_bytes(encoded({"kind": operation, "parameters": parameters}))
    path.chmod(0o600)
    return path


def test_private_inspection_apply_and_exact_receipt_replay(ready, tmp_path):
    root, initial, *_ = ready
    before = snapshot(root)
    cli.main(
        [
            "inspect",
            "--runtime",
            str(root),
            "--runtime-sha256",
            initial["runtime_sha256"],
            "--output",
            str(tmp_path / "inspection"),
        ]
    )
    assert snapshot(root) == before
    action = action_file(tmp_path, ready, "APPLY", "apply")
    first = cli.operate(root, action, tmp_path / "receipt")
    after = snapshot(root)
    assert cli.operate(root, action, tmp_path / "replay") == first
    assert snapshot(root) == after
    for folder in ("inspection", "receipt", "replay"):
        assert (tmp_path / folder).stat().st_mode & 0o077 == 0
        for path in (tmp_path / folder).iterdir():
            assert path.stat().st_mode & 0o077 == 0
    assert json.loads((tmp_path / "receipt/RESULT.json").read_text()) == first
    assert json.loads((tmp_path / "receipt/MANIFEST.json").read_text())["format"] == (
        "COMPANY_CONFIGURATION_OPERATOR_RECEIPT_V1"
    )


def test_initialize_cli_retains_exact_source_and_refuses_replacement(ready, tmp_path):
    _, _, source, refs = ready
    before = (source / "company.sqlite3").read_bytes()
    path = tmp_path / "initialize.json"
    path.write_bytes(
        encoded(
            {
                "source_root": str(source),
                "source_pins": refs,
                "as_of": "2027-02-02T00:00:00Z",
                "target_id": "CLI-TARGET",
            }
        )
    )
    path.chmod(0o600)
    target = tmp_path / "cli-runtime"
    cli.main(
        [
            "initialize",
            "--configuration",
            str(path),
            "--destination",
            str(target),
            "--output",
            str(tmp_path / "initialized"),
        ]
    )
    value = json.loads((tmp_path / "initialized/RESULT.json").read_text())
    assert value["revision"] == 0
    current = snapshot(target)
    with pytest.raises(DomainError):
        cli.initialize(path, target, tmp_path / "replacement")
    assert snapshot(target) == current
    assert (source / "company.sqlite3").read_bytes() == before


def test_receipt_failure_is_recoverable_without_repeating_operation(ready, tmp_path, monkeypatch):
    root, *_ = ready
    action = action_file(tmp_path, ready, "APPLY", "apply")
    original = cli.publish_receipt

    def fail(*args):
        raise OSError("Receipt disk unavailable")

    monkeypatch.setattr(cli, "publish_receipt", fail)
    with pytest.raises(DomainError, match="OPERATION_COMMITTED_RECEIPT_NOT_PUBLISHED"):
        cli.operate(root, action, tmp_path / "failed")
    after = snapshot(root)
    monkeypatch.setattr(cli, "publish_receipt", original)
    assert cli.operate(root, action, tmp_path / "recovered")["revision"] == 1
    assert snapshot(root) == after


def test_bad_fields_and_runtime_receipt_destination_reject_before_operation(ready, tmp_path):
    root, *_ = ready
    action = action_file(tmp_path, ready, "APPLY", "apply")
    before = snapshot(root)
    with pytest.raises(DomainError):
        cli.operate(root, action, root / "receipt")
    value = json.loads(action.read_text())
    value["parameters"]["configuration"] = {}
    action.write_bytes(encoded(value))
    with pytest.raises(DomainError):
        cli.operate(root, action, tmp_path / "receipt")
    assert snapshot(root) == before
