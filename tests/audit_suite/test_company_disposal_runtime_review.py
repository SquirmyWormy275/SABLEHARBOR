"""Independent checks of retained copies after abort and completed replay."""

import os

import pytest

from enterprise.audit_suite import company_disposal_runtime as runtime
from enterprise.audit_suite.company_store import CompanyStoreError
from tests.audit_suite import test_company_disposal_runtime as fixtures
from tests.audit_suite.test_company_disposal_runtime import (
    PAYLOAD,
    authorize,
    base,
    cfg,
    dispose_args,
    retry,
    view,
)

prepared = fixtures.prepared


def test_completed_replay_never_unlinks_replacement_copy(prepared):
    p = prepared
    authorize(p)
    args = dispose_args(p)
    first = runtime.dispose(p[0], **args)
    name = cfg(p)["copies"]["ACTIVE1"]["file"]
    replacement = p[0] / "copies" / name
    replacement.write_bytes(PAYLOAD)
    replacement.chmod(0o600)
    before = replacement.stat()
    assert runtime.dispose(p[0], **args) == first
    assert replacement.read_bytes() == PAYLOAD
    assert replacement.stat().st_ino == before.st_ino
    row = next(x for x in view(p)["inventory"] if x["id"] == "ACTIVE1")
    assert row["path_present"] and row["recorded_status"] == "UNLINKED"


def test_abort_preserves_quarantined_bytes_and_does_not_reselect_them(prepared, monkeypatch):
    p = prepared
    authorize(p)
    real_unlink = os.unlink

    def deny_quarantine(name, *args, **kwargs):
        if str(name).startswith("pending-"):
            raise PermissionError("Independent interruption after verified rename")
        return real_unlink(name, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(runtime.os, "unlink", deny_quarantine)
        with pytest.raises(PermissionError):
            runtime.dispose(p[0], **dispose_args(p))
    staged = list((p[0] / "copies").glob("pending-*"))
    assert len(staged) == 1 and staged[0].read_bytes() == PAYLOAD
    runtime.control(
        p[0],
        **base(p, "abort-quarantine"),
        action="ABORT_PENDING",
        payload={"rationale": "Preserve staged bytes for explicit investigation"},
    )
    assert view(p)["pending"] is None
    with pytest.raises(CompanyStoreError, match="inode"):
        runtime.dispose(p[0], **(dispose_args(p) | {"command_id": "new-dispose"}))
    assert staged[0].read_bytes() == PAYLOAD
    assert staged[0].name in view(p)["retained_internal_files"]


def test_quarantine_symlink_is_not_followed_on_retry(prepared, monkeypatch, tmp_path):
    p = prepared
    authorize(p)
    real_unlink = os.unlink

    def deny_quarantine(name, *args, **kwargs):
        if str(name).startswith("pending-"):
            raise PermissionError("Preserve quarantine for symlink substitution test")
        return real_unlink(name, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(runtime.os, "unlink", deny_quarantine)
        with pytest.raises(PermissionError):
            runtime.dispose(p[0], **dispose_args(p))
    staged = next((p[0] / "copies").glob("pending-*"))
    preserved = tmp_path / "preserved-original.bin"
    staged.rename(preserved)
    staged.symlink_to(preserved)
    with pytest.raises(OSError):
        retry(p)
    assert preserved.read_bytes() == PAYLOAD
    assert staged.is_symlink()
