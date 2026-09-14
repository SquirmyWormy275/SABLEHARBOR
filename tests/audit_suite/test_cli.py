import json

import pytest

from enterprise.audit_suite.__main__ import main


def test_private_principal_file_no_credential_stdout_and_no_overwrite(tmp_path, capsys):
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    credential = private / "trainer.json"
    args = [
        "provision",
        "--private-root",
        str(private / "state"),
        "--name",
        "Trainer",
        "--role",
        "instructor",
        "--credential-file",
        str(credential),
    ]
    main(args)
    value = json.loads(credential.read_text())
    assert value["credential"] not in capsys.readouterr().out
    assert credential.stat().st_mode & 0o077 == 0
    original = credential.read_bytes()
    with pytest.raises(SystemExit):
        main(args)
    assert credential.read_bytes() == original


def test_operator_backup_restore_and_explicit_new_membership(tmp_path, capsys):
    from enterprise.audit_suite.store import DomainError, Store

    tmp_path.chmod(0o700)
    original = Store(tmp_path / "original")
    principal = original.provision("Original trainer", ["instructor"])
    state = original.create(
        principal["id"], {"title": "Neutral recovery fixture", "artifacts": []}, "create"
    )
    main(
        ["backup", "--private-root", str(original.root), "--destination", str(tmp_path / "backup")]
    )
    main(
        [
            "restore",
            "--source",
            str(tmp_path / "backup"),
            "--destination",
            str(tmp_path / "restored"),
        ]
    )
    restored = Store(tmp_path / "restored")
    with pytest.raises(DomainError):
        restored.authenticate(principal["credential"])
    new = restored.provision("Recovery operator", ["instructor"])
    main(
        [
            "grant",
            "--private-root",
            str(restored.root),
            "--engagement",
            state["id"],
            "--principal",
            new["id"],
            "--permission",
            "instruct",
        ]
    )
    assert restored.membership(new["id"], state["id"]) == "instruct"
    output = capsys.readouterr().out
    assert (
        "ALL_REVOKED" in output
        and principal["credential"] not in output
        and new["credential"] not in output
    )
    with pytest.raises(SystemExit):
        main(
            [
                "restore",
                "--source",
                str(tmp_path / "backup"),
                "--destination",
                str(tmp_path / "restored"),
            ]
        )
