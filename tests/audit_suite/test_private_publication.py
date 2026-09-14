from pathlib import Path

import pytest

from enterprise.audit_suite import private_publication


@pytest.mark.parametrize("fault", ["second_move", "destination_sync", "parent_sync"])
def test_failed_publication_restores_staged_bytes_and_allows_retry(tmp_path, monkeypatch, fault):
    stage = tmp_path / "stage"
    stage.mkdir(mode=0o700)
    for name in ["first", "second"]:
        (stage / name).write_bytes(name.encode())
        (stage / name).chmod(0o600)
    destination = tmp_path / "output"
    rename, sync = private_publication.os.rename, private_publication._sync
    moves = []

    def faulty_move(source, target):
        if Path(target).parent == destination:
            moves.append(target)
            if fault == "second_move" and len(moves) == 2:
                raise OSError("injected publication move failure")
        return rename(source, target)

    def faulty_sync(path):
        if (fault == "destination_sync" and path == destination) or (
            fault == "parent_sync" and path == destination.parent
        ):
            raise OSError("injected directory sync failure")
        return sync(path)

    with monkeypatch.context() as patch:
        patch.setattr(private_publication.os, "rename", faulty_move)
        patch.setattr(private_publication, "_sync", faulty_sync)
        with pytest.raises(OSError, match="injected"):
            private_publication.publish(stage, destination)
    assert not destination.exists()
    assert {p.name: p.read_bytes() for p in stage.iterdir()} == {
        "first": b"first",
        "second": b"second",
    }
    private_publication.publish(stage, destination)
    assert {p.name: p.read_bytes() for p in destination.iterdir()} == {
        "first": b"first",
        "second": b"second",
    }
    assert destination.stat().st_mode & 0o077 == 0


def test_existing_empty_target_is_never_replaced(tmp_path):
    stage, destination = tmp_path / "stage", tmp_path / "output"
    stage.mkdir(mode=0o700)
    destination.mkdir(mode=0o700)
    inode = destination.stat().st_ino
    (stage / "original").write_bytes(b"original")
    with pytest.raises(FileExistsError):
        private_publication.publish(stage, destination)
    assert destination.stat().st_ino == inode
    assert (stage / "original").read_bytes() == b"original"
    assert not list(destination.iterdir())
