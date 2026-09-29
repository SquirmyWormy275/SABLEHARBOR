"""Independent receipt-publication boundaries after actual local operations commit."""

import json

import pytest

from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_company_backup_runtime import ROOT
from tests.audit_suite.test_company_backup_runtime import runtime as runtime
from tools.audit_suite import company_backup_runtime as cli


def private_json(path, value):
    path.write_bytes(encoded(value))
    path.chmod(0o600)
    return path


def request(tmp_path, runtime):
    data = private_json(tmp_path / "data.json", {"records": [{"id": "ITEM", "value": 1}]})
    return private_json(
        tmp_path / "action.json",
        {
            "kind": "DATASET",
            "parameters": {
                "expected_runtime_sha256": runtime[1],
                "expected_revision": 0,
                "command_id": "DATASET-ONCE",
                "dataset_id": "DATA",
                "content_path": str(data),
                "expected_sha256": sha(data.read_bytes()),
                "event_at": "2027-01-01T08:00:00Z",
            },
        },
    )


def state(root):
    with cli.backup.database(root) as db:
        return {
            "versions": [
                tuple(r)
                for r in db.execute("SELECT * FROM versions ORDER BY system,record,version")
            ],
            "commands": [
                tuple(r)
                for r in db.execute("SELECT * FROM backup_runtime_commands ORDER BY command_id")
            ],
            "state": [tuple(r) for r in db.execute("SELECT * FROM backup_runtime_state")],
        }


@pytest.mark.parametrize("boundary", ["after_operation", "after_stage_creation", "during_publish"])
def test_replaced_receipt_parent_never_receives_private_output(
    runtime, tmp_path, monkeypatch, boundary
):
    action = request(tmp_path, runtime)
    parent, old, external = (tmp_path / n for n in ("receipts", "original-parent", "external"))
    parent.mkdir(mode=0o700)
    external.mkdir(mode=0o700)
    method, mkdtemp, rename = cli.backup.append_dataset, cli.tempfile.mkdtemp, cli.os.rename
    swapped = False

    def swap():
        parent.rename(old)
        parent.symlink_to(external, target_is_directory=True)

    def operation(*args, **kwargs):
        result = method(*args, **kwargs)
        if boundary == "after_operation":
            swap()
        return result

    def staging(*args, **kwargs):
        result = mkdtemp(*args, **kwargs)
        if boundary == "after_stage_creation":
            swap()
        return result

    def moving(*args, **kwargs):
        nonlocal swapped
        if boundary == "during_publish" and not swapped:
            swapped = True
            swap()
        return rename(*args, **kwargs)

    monkeypatch.setattr(cli.os, "rename", moving)
    monkeypatch.setattr(cli.backup, "append_dataset", operation)
    monkeypatch.setattr(cli.tempfile, "mkdtemp", staging)
    with pytest.raises((CompanyStoreError, DomainError)):
        cli.operate(runtime[0], action, parent / "result")
    assert list(external.iterdir()) == []
    assert list(old.iterdir()) == []
    saved = state(runtime[0])
    assert saved["state"][0][0] == 1
    assert len(saved["commands"]) == 1 and len(saved["versions"]) == 2


def test_committed_operation_publication_failure_exact_replay_has_no_duplicates(
    runtime, tmp_path, monkeypatch
):
    action = request(tmp_path, runtime)
    mkdir = cli.os.mkdir

    def fail(path, *args, **kwargs):
        if path == "failed-receipt":
            raise OSError("Injected receipt publication failure")
        return mkdir(path, *args, **kwargs)

    monkeypatch.setattr(cli.os, "mkdir", fail)
    with pytest.raises((OSError, DomainError)):
        cli.operate(runtime[0], action, tmp_path / "failed-receipt")
    committed = state(runtime[0])
    assert committed["state"][0][0] == 1
    assert len(committed["commands"]) == 1 and len(committed["versions"]) == 2
    assert not (tmp_path / "failed-receipt").exists()
    assert not list(tmp_path.glob(".backup-operator-receipt-*"))
    original_receipt = json.loads(committed["commands"][0][2])
    monkeypatch.setattr(cli.os, "mkdir", mkdir)
    result = cli.operate(runtime[0], action, tmp_path / "recovered-receipt")
    assert result == original_receipt
    assert state(runtime[0]) == committed
    assert json.loads((tmp_path / "recovered-receipt" / "RESULT.json").read_bytes()) == result


def test_initialize_receipt_failure_keeps_complete_runtime_and_original_declaration(
    runtime, tmp_path, monkeypatch
):
    cfg = json.loads((runtime[0] / "RUNTIME.json").read_bytes())
    config = private_json(
        tmp_path / "initialize.json",
        {
            "declaration_root": str(runtime[2].path.parent),
            "declaration_ref": cfg["declaration_ref"],
            "bindings": runtime[3],
            "datasets": [{"id": k, "format": v} for k, v in cfg["datasets"].items()],
            "service_id": cfg["service_id"],
        },
    )
    old_declaration = runtime[2].path.read_bytes()
    target = tmp_path / "initialized"
    mkdir = cli.os.mkdir

    def fail(path, *args, **kwargs):
        if path == "failed-initialize-receipt":
            raise OSError("Injected initialization receipt publication failure")
        return mkdir(path, *args, **kwargs)

    monkeypatch.setattr(cli.os, "mkdir", fail)
    with pytest.raises((OSError, DomainError)):
        cli.initialize(config, target, ROOT, tmp_path / "failed-initialize-receipt")
    committed = state(target)
    assert committed["state"][0][0] == 0
    assert len(committed["versions"]) == 1 and committed["commands"] == []
    assert (target / "RUNTIME.json").is_file() and (target / "DECLARATION.json").is_file()
    assert runtime[2].path.read_bytes() == old_declaration
    assert not (tmp_path / "failed-initialize-receipt").exists()
    monkeypatch.setattr(cli.os, "mkdir", mkdir)
    with pytest.raises(DomainError, match="New destination"):
        cli.initialize(config, target, ROOT, tmp_path / "retry-initialize-receipt")
    digest = sha((target / "RUNTIME.json").read_bytes())
    report = cli.reconcile(target, digest, "2027-01-02T11:00:00Z", tmp_path / "inspection")
    assert report["missing_due_count"] == 3 and report["declared_count"] == 4
    assert state(target) == committed
    assert runtime[2].path.read_bytes() == old_declaration
