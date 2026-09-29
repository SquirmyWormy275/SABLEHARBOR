"""Actual source-backed CLI transitions and recoverable private receipts."""

import json

import pytest

from enterprise.audit_suite.operating_source_bridge import encoded
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_security_event_runtime import inputs as inputs
from tests.audit_suite.test_company_security_event_runtime import prepared
from tools.audit_suite import company_security_event_runtime as cli


@pytest.fixture
def initialized(tmp_path, inputs):
    source, _, config = prepared(tmp_path, inputs)
    config.pop("repository")
    config["source_root"] = str(config["source_root"])
    path = tmp_path / "initialize.json"
    path.write_bytes(encoded(config))
    path.chmod(0o600)
    target = tmp_path / "runtime"
    source_before = (source / "company.sqlite3").read_bytes()
    cli.main(
        [
            "initialize",
            "--configuration",
            str(path),
            "--destination",
            str(target),
            "--output",
            str(tmp_path / "initial"),
        ]
    )
    assert (source / "company.sqlite3").read_bytes() == source_before
    result = json.loads((tmp_path / "initial/RESULT.json").read_text())
    return target, result, path


def action_file(tmp_path, initialized, action="INTAKE", identifier="intake", minute=1):
    target, initial, _ = initialized
    view = cli.runtime.inspect(target, expected_runtime_sha256=initial["runtime_sha256"])
    path = tmp_path / (identifier + ".json")
    path.write_bytes(
        encoded(
            {
                "kind": action,
                "parameters": {
                    "expected_runtime_sha256": initial["runtime_sha256"],
                    "expected_revision": view["state"]["revision"],
                    "expected_state_sha256": view["state_sha256"],
                    "command_id": identifier,
                    "operator_id": "AS-P008",
                    "event_at": f"2027-02-02T01:{minute:02}:00Z",
                    "payload": {"subject_id": "EVENT-1"},
                },
            }
        )
    )
    path.chmod(0o600)
    return path


def test_cli_intake_triage_inspection_and_historical_replay(initialized, tmp_path):
    target, initial, _ = initialized
    intake = action_file(tmp_path, initialized)
    first = cli.operate(target, intake, tmp_path / "intake-receipt")
    triage = action_file(tmp_path, initialized, "TRIAGE", "triage", 2)
    result = cli.operate(target, triage, tmp_path / "triage-receipt")
    assert result["outcome"]["classification"] == "LOCAL_RESPONSE_REQUIRED"
    before = (target / "company.sqlite3").read_bytes()
    cli.inspect(target, initial["runtime_sha256"], tmp_path / "inspection")
    assert cli.operate(target, intake, tmp_path / "historical-replay") == first
    assert (target / "company.sqlite3").read_bytes() == before
    assert json.loads((tmp_path / "triage-receipt/MANIFEST.json").read_text())["format"] == (
        "COMPANY_SECURITY_EVENT_OPERATOR_RECEIPT_V1"
    )
    for path in (tmp_path / "triage-receipt").iterdir():
        assert path.stat().st_mode & 0o077 == 0


def test_cli_committed_receipt_failure_replays_without_new_transition(
    initialized, tmp_path, monkeypatch
):
    target, _, _ = initialized
    action = action_file(tmp_path, initialized)
    original = cli.publish_receipt

    def fail(*args):
        raise OSError("Receipt disk unavailable")

    monkeypatch.setattr(cli, "publish_receipt", fail)
    with pytest.raises(DomainError, match="OPERATION_COMMITTED_RECEIPT_NOT_PUBLISHED"):
        cli.operate(target, action, tmp_path / "failed")
    before = (target / "company.sqlite3").read_bytes()
    monkeypatch.setattr(cli, "publish_receipt", original)
    assert cli.operate(target, action, tmp_path / "recovered")["revision"] == 1
    assert (target / "company.sqlite3").read_bytes() == before


def test_cli_invalid_fields_and_destinations_preserve_runtime(initialized, tmp_path):
    target, _, config = initialized
    action = action_file(tmp_path, initialized)
    before = (target / "company.sqlite3").read_bytes()
    with pytest.raises(DomainError):
        cli.initialize(config, target, tmp_path / "replacement")
    with pytest.raises(DomainError):
        cli.operate(target, action, target / "receipt")
    value = json.loads(action.read_text())
    value["parameters"]["outcome"] = "CLOSED"
    action.write_bytes(encoded(value))
    with pytest.raises(DomainError):
        cli.operate(target, action, tmp_path / "denied")
    assert (target / "company.sqlite3").read_bytes() == before
