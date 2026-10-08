"""Native initializer identities remain unique in one exact multi-branch edition."""

import hashlib
import importlib.util
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import pytest

from enterprise.audit_suite import company_backup_runtime as backup
from enterprise.audit_suite.company_operating_period import create_period
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha

REPO = Path(__file__).resolve().parents[2]
PUBLISHER = REPO / "enterprise/audit_suite/company_source_edition.py"
PUBLISHER_SHA = "bc7b5cb6e5fc03953aa9b744ef98810737d4f8054776320ed85c95471b5e8983"


def rows(path):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        return [
            dict(r)
            for r in db.execute(
                "SELECT * FROM versions ORDER BY company,branch,system,record,version"
            )
        ]


def image(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_runtime(parent, branch):
    parent.mkdir(mode=0o700)
    ledger = parent / "ledger"
    ledger.mkdir(mode=0o700)
    store = CompanyStore(ledger)
    plan = {
        "period_id": "OWN-NAMESPACE-" + branch,
        "company_id": "OWN-SAME-COMPANY",
        "branch_id": branch,
        "owner_id": "AS-P007",
        "control_ids": ["SH-BCM-002"],
        "declared_at": "2026-12-31T00:00:00Z",
        "period_start": "2027-01-01T00:00:00Z",
        "period_end_exclusive": "2027-01-03T00:00:00Z",
        "inventory": [{"id": "DATA", "description": "One bounded owned local byte dataset"}],
        "local_basis": "Owned two-branch namespace mechanism; no operating-year or audit credit",
        "schedule": [
            {
                "id": "B1",
                "inventory_ids": ["DATA"],
                "control_id": "SH-BCM-002",
                "window_start": "2027-01-01T00:00:00Z",
                "window_end_exclusive": "2027-01-02T00:00:00Z",
                "due_at": "2027-01-01T10:00:00Z",
                "depends_on": [],
            }
        ],
    }
    declaration = create_period(store, repository=REPO, plan=plan)
    destination = parent / "runtime"
    arguments = {
        "repository": REPO,
        "declaration_root": ledger,
        "declaration_ref": backup.pin(declaration),
        "bindings": [{"occurrence_id": "B1", "dataset_id": "DATA", "operation": "BACKUP"}],
        "datasets": [{"id": "DATA", "format": "JSON_RECORDS"}],
    }
    result = backup.initialize(destination, **arguments)
    return destination, result, arguments, store.path


def publisher():
    assert image(PUBLISHER) == PUBLISHER_SHA
    name = "enterprise.audit_suite.company_source_edition"
    spec = importlib.util.spec_from_file_location(name, PUBLISHER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    assert image(PUBLISHER) == PUBLISHER_SHA
    return module


def component(directory, identifier):
    with closing(
        sqlite3.connect((directory / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        systems = db.execute("SELECT COUNT(*) FROM systems").fetchone()[0]
        versions = db.execute("SELECT COUNT(*) FROM versions").fetchone()[0]
    return {
        "id": identifier,
        "database": {
            "path": str(directory / "company.sqlite3"),
            "sha256": image(directory / "company.sqlite3"),
        },
        "systems": systems,
        "versions": versions,
    }


def test_single_initializer_legacy_api_native_body_and_existing_destination_refusal(tmp_path):
    tmp_path.chmod(0o700)
    root, result, arguments, ledger = make_runtime(tmp_path / "single", "ALPHA")
    config = json.loads((root / "RUNTIME.json").read_bytes())
    native = rows(root / "company.sqlite3")
    assert len(native) == 1
    row = native[0]
    assert row["command_id"] == "backup-runtime-definition-" + sha(
        encoded([config["runtime_id"], arguments["declaration_ref"]])
    )
    assert row["record"] == config["plan"]["period_id"]
    assert row["content"] == (root / "RUNTIME.json").read_bytes()
    assert row["sha256"] == result["runtime_sha256"] == sha(row["content"])
    assert result["source_versions"] == 1 and result["operation_execution"] == "NOT_STARTED"
    before = image(root / "company.sqlite3"), image(ledger), image(root / "RUNTIME.json")
    with pytest.raises(CompanyStoreError, match="New absolute private runtime"):
        backup.initialize(root, **arguments)
    assert before == (image(root / "company.sqlite3"), image(ledger), image(root / "RUNTIME.json"))


def test_single_runtime_exact_operation_replay_preserves_native_initializer_and_files(tmp_path):
    tmp_path.chmod(0o700)
    root, result, _, ledger = make_runtime(tmp_path / "idempotent", "ALPHA")
    definition = rows(root / "company.sqlite3")[0]
    source_before = image(ledger)
    raw = encoded({"records": [{"id": "ONE", "value": 1}]})
    kwargs = {
        "expected_runtime_sha256": result["runtime_sha256"],
        "expected_revision": 0,
        "command_id": "OWN-DATA-ONE",
        "dataset_id": "DATA",
        "content": raw,
        "expected_sha256": sha(raw),
        "event_at": "2027-01-01T08:00:00Z",
    }
    first = backup.append_dataset(root, **kwargs)
    before = image(root / "company.sqlite3")
    second = backup.append_dataset(root, **kwargs)
    assert first == second and before == image(root / "company.sqlite3")
    assert source_before == image(ledger)
    assert (
        next(r for r in rows(root / "company.sqlite3") if r["system"] == "runtime_definition")
        == definition
    )


def test_two_branch_same_company_initializers_publish_exact_all14_fields_with_strict_publisher(
    tmp_path,
):
    tmp_path.chmod(0o700)
    a, _, _, al = make_runtime(tmp_path / "alpha", "ALPHA")
    b, _, _, bl = make_runtime(tmp_path / "beta", "BETA")
    originals = {
        path: (image(path), rows(path))
        for path in (a / "company.sqlite3", b / "company.sqlite3", al, bl)
    }
    command_ids = [r["command_id"] for path, (_, native) in originals.items() for r in native]
    assert len(command_ids) == len(set(command_ids)) == 4
    module = publisher()
    output = tmp_path / "published"
    result = module.publish_edition(
        [
            component(a, "ALPHA-RUNTIME"),
            component(b, "BETA-RUNTIME"),
            component(al.parent, "ALPHA-PERIOD"),
            component(bl.parent, "BETA-PERIOD"),
        ],
        output,
    )
    expected = sorted(
        [r for _, native in originals.values() for r in native],
        key=lambda r: tuple(r[k] for k in ("company", "branch", "system", "record", "version")),
    )
    assert rows(output / "company/company.sqlite3") == expected
    assert image(output / "MANIFEST.json") == result["sha256"]
    for path, (before, native) in originals.items():
        assert image(path) == before and rows(path) == native
    with closing(sqlite3.connect(output / "company/company.sqlite3")) as db:
        assert all(
            db.execute("SELECT COUNT(*) FROM " + name).fetchone()[0] == 0
            for name in ("grants", "collections", "access_events")
        )
