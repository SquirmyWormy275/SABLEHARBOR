"""Operator boundary checks using actual private native stores and copied bytes."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_company_backup_runtime import runtime as runtime_fixture

from enterprise.audit_suite.operating_source_bridge import encoded, sha
from enterprise.audit_suite.store import DomainError
from tools.audit_suite import company_backup_runtime as cli

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def runtime(tmp_path):
    return runtime_fixture.__wrapped__(tmp_path)


def private_json(path, value):
    path.write_bytes(encoded(value))
    path.chmod(0o600)
    return path


def action(tmp_path, rt, kind, revision, command, **parameters):
    return private_json(
        tmp_path / (command + ".json"),
        {
            "kind": kind,
            "parameters": {
                "expected_runtime_sha256": rt[1],
                "expected_revision": revision,
                "command_id": command,
                **parameters,
            },
        },
    )


def run_cli(rt, request, output):
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.audit_suite.company_backup_runtime",
            "operate",
            "--runtime",
            str(rt[0]),
            "--action",
            str(request),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    manifest = json.loads((output / "MANIFEST.json").read_bytes())
    for name, digest in manifest["files"].items():
        assert sha((output / name).read_bytes()) == digest
        assert (output / name).stat().st_mode & 0o777 == 0o600
    return json.loads(done.stdout), json.loads((output / "RESULT.json").read_bytes())


def test_actual_cli_dataset_lease_copy_replay_failure_and_readonly_report(runtime, tmp_path):
    content = private_json(tmp_path / "content.json", {"records": [{"id": "ONE", "value": 1}]})
    _, source = run_cli(
        runtime,
        action(
            tmp_path,
            runtime,
            "DATASET",
            0,
            "data",
            dataset_id="DATA",
            content_path=str(content),
            expected_sha256=sha(content.read_bytes()),
            event_at="2027-01-01T08:00:00Z",
        ),
        tmp_path / "data-receipt",
    )
    _, lease = run_cli(
        runtime,
        action(
            tmp_path,
            runtime,
            "LEASE",
            1,
            "lease",
            operation="BACKUP_WRITE",
            enabled=True,
            valid_from="2027-01-01T00:00:00Z",
            expires_at="2027-01-02T10:00:00Z",
            event_at="2027-01-01T09:00:00Z",
        ),
        tmp_path / "lease-receipt",
    )
    request = action(
        tmp_path,
        runtime,
        "BACKUP",
        2,
        "copy",
        occurrence_id="B1",
        source_pin=source["source_pin"],
        lease_pin=lease["lease_pin"],
        attempted_at="2027-01-01T10:00:00Z",
        rationale="Explicit local selected copy",
    )
    stdout, copied = run_cli(runtime, request, tmp_path / "copy-receipt")
    assert stdout["result_status"] == "COMPLETED"
    before = (runtime[0] / "company.sqlite3").read_bytes()
    assert run_cli(runtime, request, tmp_path / "replay-receipt")[1] == copied
    assert (runtime[0] / "company.sqlite3").read_bytes() == before
    stdout, failed = run_cli(
        runtime,
        action(
            tmp_path,
            runtime,
            "BACKUP",
            3,
            "expired",
            occurrence_id="B2",
            source_pin=source["source_pin"],
            lease_pin=lease["lease_pin"],
            attempted_at="2027-01-02T10:00:00Z",
            rationale="Explicit scheduled local copy",
        ),
        tmp_path / "failed-receipt",
    )
    assert stdout["status"] == "RECEIPT_WRITTEN" and stdout["result_status"] == "FAILED"
    assert failed["object_pin"] is None
    before = (runtime[0] / "company.sqlite3").read_bytes()
    report = cli.reconcile(runtime[0], runtime[1], "2027-01-04T00:00:00Z", tmp_path / "report")
    assert report["due_count"] == 4 and report["missing_due_count"] == 2
    assert report["failed_occurrence_count"] == 1
    assert (runtime[0] / "company.sqlite3").read_bytes() == before


@pytest.mark.parametrize("failure", ["extra", "missing", "unknown", "existing", "inside"])
def test_preflight_rejects_without_native_mutation(runtime, tmp_path, failure):
    request = action(
        tmp_path,
        runtime,
        "LEASE",
        0,
        "lease",
        operation="BACKUP_WRITE",
        enabled=True,
        valid_from="2027-01-01T00:00:00Z",
        expires_at="2027-01-03T00:00:00Z",
        event_at="2027-01-01T09:00:00Z",
    )
    body = json.loads(request.read_bytes())
    output = tmp_path / "receipt"
    if failure == "extra":
        body["parameters"]["unexpected"] = True
    elif failure == "missing":
        del body["parameters"]["enabled"]
    elif failure == "unknown":
        body["kind"] = "UNSUPPORTED"
    elif failure == "existing":
        output.mkdir(mode=0o700)
    else:
        output = runtime[0] / "receipt"
    private_json(request, body)
    before = (runtime[0] / "company.sqlite3").read_bytes()
    with pytest.raises(DomainError):
        cli.operate(runtime[0], request, output)
    assert (runtime[0] / "company.sqlite3").read_bytes() == before


def test_initialize_rejects_receipt_inside_source_before_runtime_creation(runtime, tmp_path):
    config = json.loads((runtime[0] / "RUNTIME.json").read_bytes())
    selected = {k: config[k] for k in ["declaration_ref", "bindings", "datasets", "service_id"]}
    selected["declaration_root"] = str(runtime[2].path.parent)
    selected["bindings"] = runtime[3]
    selected["datasets"] = [{"id": k, "format": v} for k, v in config["datasets"].items()]
    path = private_json(tmp_path / "initialize.json", selected)
    before = runtime[2].path.read_bytes()
    with pytest.raises(DomainError, match="outside"):
        cli.initialize(path, tmp_path / "new-runtime", ROOT, runtime[2].path.parent / "receipt")
    assert runtime[2].path.read_bytes() == before
    assert not (tmp_path / "new-runtime").exists()


def test_actual_initialize_cli_preserves_declaration_and_creates_receipt(runtime, tmp_path):
    config = json.loads((runtime[0] / "RUNTIME.json").read_bytes())
    selected = {k: config[k] for k in ["declaration_ref", "bindings", "datasets", "service_id"]}
    selected["declaration_root"] = str(runtime[2].path.parent)
    selected["bindings"] = runtime[3]
    selected["datasets"] = [{"id": k, "format": v} for k, v in config["datasets"].items()]
    path = private_json(tmp_path / "initialize.json", selected)
    before = runtime[2].path.read_bytes()
    destination, output = tmp_path / "new-runtime", tmp_path / "initialized"
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.audit_suite.company_backup_runtime",
            "initialize",
            "--config",
            str(path),
            "--destination",
            str(destination),
            "--repository",
            str(ROOT),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(done.stdout)["status"] == "RECEIPT_WRITTEN"
    result = json.loads((output / "RESULT.json").read_bytes())
    assert result["runtime_sha256"] == sha((destination / "RUNTIME.json").read_bytes())
    assert runtime[2].path.read_bytes() == before
