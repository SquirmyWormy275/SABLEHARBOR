from copy import deepcopy

import pytest

from tools.company_closeout.working_copy_restore import (
    RestoreError,
    capture,
    checkpoint,
    disclose,
    restore,
    sha,
    write_private,
)


@pytest.fixture
def case(tmp_path):
    tmp_path.chmod(0o700)
    state = {
        "revision": 0,
        "pending": None,
        "inventory": [
            {"id": i, "recorded_status": "PRESENT", "holds": [], "matches_initial_identity": True}
            for i in ["gone", "held", "open"]
        ],
    }
    copies = {}
    hashes = {}
    for row in state["inventory"]:
        i = row["id"]
        p = tmp_path / i
        data = ("private fixture " + i).encode()
        write_private(p, data)
        copies[i] = p
        hashes[i] = sha(data)
    backup = tmp_path / "backup"
    digest = capture(backup, copies, state, expected_hashes=hashes)
    return tmp_path, state, backup, digest


def restored(case):
    root, old, backup, digest = case
    state = deepcopy(old)
    state["revision"] = 3
    state["inventory"][0]["recorded_status"] = "UNLINKED"
    state["inventory"][1]["holds"] = ["HOLD-1"]
    pin = checkpoint(state)
    target = root / "restored"
    receipt = restore(
        backup, target, backup_sha256=digest, current_reader=lambda: state, expected_checkpoint=pin
    )
    return target, state, pin, receipt


def test_real_files_restore_suppresses_deleted_preserves_held(case):
    target, state, pin, receipt = restored(case)
    assert not (target / (sha(b"gone") + ".bin")).exists()
    assert (target / (sha(b"held") + ".bin")).read_bytes() == b"private fixture held"
    assert (
        disclose(
            target,
            "open",
            current_reader=lambda: state,
            expected_checkpoint=pin,
            authorized=lambda i, a: True,
        )
        == b"private fixture open"
    )
    assert [r["disposition"] for r in receipt["members"]] == [
        "SUPPRESSED_DELETED",
        "PRESERVED_RESTRICTED_HOLD",
        "RESTORED",
    ]


@pytest.mark.parametrize(
    "action",
    [
        "read",
        "snippet",
        "citation",
        "export",
        "vector",
        "count",
        "graph",
        "tool_result",
        "answer",
        "search",
        "personal_memory",
    ],
)
@pytest.mark.parametrize("ident", ["gone", "held"])
def test_every_indirect_surface_denied(case, action, ident):
    target, state, pin, _ = restored(case)
    with pytest.raises(RestoreError):
        disclose(
            target,
            ident,
            current_reader=lambda: state,
            expected_checkpoint=pin,
            authorized=lambda i, a: True,
            action=action,
        )


def test_revoked_context_denied_even_with_old_valid_restore(case):
    target, state, pin, _ = restored(case)
    with pytest.raises(RestoreError, match="Not authorized"):
        disclose(
            target,
            "open",
            current_reader=lambda: state,
            expected_checkpoint=pin,
            authorized=lambda i, a: False,
        )


def test_stale_or_missing_checkpoint_cannot_restore(case):
    root, state, backup, digest = case
    stale = checkpoint(state)
    state["revision"] += 1
    for pin in [None, stale]:
        with pytest.raises(RestoreError, match="checkpoint"):
            restore(
                backup,
                root / "rejected",
                backup_sha256=digest,
                current_reader=lambda: state,
                expected_checkpoint=pin,
            )
        assert not (root / "rejected").exists()


def test_state_change_during_restore_does_not_publish(case):
    root, state, backup, digest = case
    pin = checkpoint(state)
    calls = []

    def current():
        calls.append(1)
        if len(calls) > 1:
            state["revision"] += 1
        return state

    with pytest.raises(RestoreError, match="changed"):
        restore(
            backup,
            root / "rejected",
            backup_sha256=digest,
            current_reader=current,
            expected_checkpoint=pin,
        )
    assert not (root / "rejected").exists()


def test_changed_backup_and_restored_bytes_rejected(case):
    target, state, pin, _ = restored(case)
    p = target / (sha(b"open") + ".bin")
    p.write_bytes(b"changed")
    with pytest.raises(RestoreError, match="content changed"):
        disclose(
            target,
            "open",
            current_reader=lambda: state,
            expected_checkpoint=pin,
            authorized=lambda i, a: True,
        )
    root, _, backup, digest = case
    (backup / (sha(b"open") + ".bin")).write_bytes(b"changed")
    with pytest.raises(RestoreError, match="member changed"):
        restore(
            backup,
            root / "bad",
            backup_sha256=digest,
            current_reader=lambda: state,
            expected_checkpoint=pin,
        )


def test_symlink_and_extra_member_rejected(case):
    root, state, backup, digest = case
    (backup / "extra").write_text("not declared")
    with pytest.raises(RestoreError, match="unlisted"):
        restore(
            backup,
            root / "bad",
            backup_sha256=digest,
            current_reader=lambda: state,
            expected_checkpoint=checkpoint(state),
        )
    (backup / "extra").unlink()
    p = backup / (sha(b"open") + ".bin")
    p.unlink()
    p.symlink_to(root / "open")
    with pytest.raises(RestoreError, match="alias"):
        restore(
            backup,
            root / "bad2",
            backup_sha256=digest,
            current_reader=lambda: state,
            expected_checkpoint=checkpoint(state),
        )


def test_interrupted_and_unknown_disposal_states_fail_closed(case):
    root, state, backup, digest = case
    state["pending"] = {"intent": "unfinished"}
    with pytest.raises(RestoreError, match="Unfinished"):
        checkpoint(state)
    state["pending"] = None
    state["inventory"][0]["recorded_status"] = "MISSING_UNATTRIBUTED"
    with pytest.raises(RestoreError, match="Unattributed"):
        restore(
            backup,
            root / "bad",
            backup_sha256=digest,
            current_reader=lambda: state,
            expected_checkpoint=checkpoint(state),
        )


def test_revocation_during_read_blocks_result(case):
    target, state, pin, _ = restored(case)
    calls = []

    def authority(i, a):
        calls.append(1)
        return len(calls) == 1

    with pytest.raises(RestoreError, match="revoked during"):
        disclose(
            target,
            "open",
            current_reader=lambda: state,
            expected_checkpoint=pin,
            authorized=authority,
        )


@pytest.mark.parametrize("action", ["count", "citation", "graph", "search", "snippet"])
def test_limited_surface_grant_does_not_return_raw_bytes(case, action):
    target, state, pin, _ = restored(case)
    result = disclose(
        target,
        "open",
        current_reader=lambda: state,
        expected_checkpoint=pin,
        authorized=lambda i, a: a == action,
        action=action,
    )
    assert not isinstance(result, bytes)
    if action == "count":
        assert result == 1
    if action in {"citation", "graph"}:
        assert "private fixture" not in str(result)
