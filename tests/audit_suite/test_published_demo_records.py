"""A repository checkout supplies the actual, immutable client submissions."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RECORDS = ROOT / "docs/audit-suite/demo-2026-11/client-records"


@pytest.mark.parametrize(
    ("stage", "edition", "count", "manifest_sha256"),
    [
        (
            "initial",
            "SH-NOV2026-0-v1",
            58,
            "6a827d65478af38409d5cb8c4960706eeba65a8c647c7e59b543ef41ae88615d",
        ),
        (
            "follow-up",
            "SH-NOV2026-1-v1",
            5,
            "a70e1bd7c7928149bd570d1bc98f623fde6401b058235aa24a0fe7ed89d1418a",
        ),
        (
            "correction",
            "SH-NOV2026-2-v1",
            7,
            "3fdaedefb890e1f9cf4ef4ea2e79002578000d3c4537c6dbca6388ef3f12b28a",
        ),
    ],
)
def test_published_submission_without_local_workspace(
    tmp_path, stage, edition, count, manifest_sha256
):
    directory = RECORDS / stage
    assert hashlib.sha256((directory / "manifest.json").read_bytes()).hexdigest() == (
        manifest_sha256
    )
    # Isolated Python and an unrelated working directory prevent hidden reliance
    # on the company runtime, credentials, private databases or authoring state.
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(ROOT / "tools/audit_suite/demo_source_delivery.py"),
            "verify",
            str(directory),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout) == {
        "status": "VERIFIED",
        "edition": edition,
        "artifacts": count,
    }
