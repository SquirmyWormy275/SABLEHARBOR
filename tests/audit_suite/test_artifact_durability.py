"""Do not commit an evidence receipt when durable storage reports a failure."""

import os
import stat

import pytest

from enterprise.audit_suite.artifacts import Artifacts


def retain(artifacts):
    return artifacts._retain(
        "ENG-durability",
        "original.txt",
        b"Original neutral source",
        source={},
        coverage={},
        lineage=None,
        generated=False,
        inspection={"mime": "text/plain", "status": "AVAILABLE", "reason": None},
    )


@pytest.mark.parametrize("failed_stage", ["file", "directory"])
def test_storage_flush_failure_returns_no_evidence_receipt(tmp_path, monkeypatch, failed_stage):
    artifacts = Artifacts(tmp_path / "private")
    original = os.fsync

    def failing_flush(fd):
        kind = "directory" if stat.S_ISDIR(os.fstat(fd).st_mode) else "file"
        if kind == failed_stage:
            raise OSError("Simulated storage flush failure")
        return original(fd)

    with monkeypatch.context() as patch:
        patch.setattr(os, "fsync", failing_flush)
        with pytest.raises(OSError, match="storage flush failure"):
            retain(artifacts)
    # A retry checks and flushes the retained bytes; it never fabricates a receipt
    # during the failed operation or replaces an existing original.
    receipt = retain(artifacts)
    assert artifacts.read(receipt) == b"Original neutral source"
