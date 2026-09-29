import json

import pytest

from enterprise.audit_suite.company_recovery import backup, restore
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from tools.audit_suite.company_operator import main


def setup(tmp_path):
    tmp_path.chmod(0o700)
    root = tmp_path / "source"
    root.mkdir(mode=0o700)
    store = CompanyStore(root)
    store.register_system("SH", "baseline", "IAM", "owner")
    store.append_version(
        "SH",
        "baseline",
        "IAM",
        "record",
        expected_version=0,
        command_id="import",
        event_at="2027-01-01T00:00:00Z",
        available_at="2027-01-02T00:00:00Z",
        content=b"private operational record",
        provenance={"source_reference": "original"},
    )
    store.grant("auditor", "engagement", "SH", "baseline", "IAM")
    return root, store


def test_operator_discovery_collection_no_stdout_data(tmp_path, capsys):
    root, _ = setup(tmp_path)
    common = [
        "--private-root",
        str(root),
        "--company",
        "SH",
        "--branch",
        "baseline",
        "--system",
        "IAM",
        "--principal",
        "auditor",
        "--engagement",
        "engagement",
        "--as-of",
        "2027-02-01T00:00:00Z",
    ]
    listing = tmp_path / "list.json"
    main(["discover", *common, "--output", str(listing)])
    assert json.loads(listing.read_text())["records"][0]["record"] == "record"
    native, receipt = tmp_path / "native", tmp_path / "receipt.json"
    command = [
        "collect",
        *common,
        "--record",
        "record",
        "--version",
        "1",
        "--command-id",
        "collect",
        "--output",
        str(native),
        "--receipt-output",
        str(receipt),
    ]
    main(command)
    assert native.read_bytes() == b"private operational record"
    assert native.stat().st_mode & 0o077 == 0
    assert "private operational record" not in capsys.readouterr().out
    with pytest.raises(CompanyStoreError):
        main(command)
    main(["revoke", *common])
    with pytest.raises(CompanyStoreError):
        main(["discover", *common, "--output", str(tmp_path / "denied")])


def test_recovery_preserves_sources_and_revokes_every_grant(tmp_path):
    root, store = setup(tmp_path)
    before = store.collect(
        "auditor",
        "engagement",
        "SH",
        "baseline",
        "IAM",
        "record",
        version=1,
        as_of="2027-02-01T00:00:00Z",
        command_id="collection",
    )
    snapshot = tmp_path / "backup"
    backup(store, snapshot)
    restored = tmp_path / "restored"
    result = restore(snapshot, restored)
    assert result["all_read_grants_revoked"]
    copied = CompanyStore(restored)
    with pytest.raises(CompanyStoreError):
        copied.read_version(
            "auditor",
            "engagement",
            "SH",
            "baseline",
            "IAM",
            "record",
            version=1,
            as_of="2027-02-01T00:00:00Z",
        )
    copied.grant("auditor", "engagement", "SH", "baseline", "IAM")
    replay = copied.collect(
        "auditor",
        "engagement",
        "SH",
        "baseline",
        "IAM",
        "record",
        version=1,
        as_of="2027-02-01T00:00:00Z",
        command_id="collection",
    )
    assert replay == before
    with pytest.raises(CompanyStoreError):
        restore(snapshot, restored)
    with (snapshot / "company.sqlite3").open("ab") as stream:
        stream.write(b"tampered")
    with pytest.raises(CompanyStoreError):
        restore(snapshot, tmp_path / "tampered-restore")
    assert not (tmp_path / "tampered-restore").exists()


def test_backup_and_output_aliases_rejected(tmp_path):
    root, store = setup(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(CompanyStoreError):
        backup(store, alias / "backup")
    with pytest.raises(CompanyStoreError):
        restore(alias, tmp_path / "restore")
