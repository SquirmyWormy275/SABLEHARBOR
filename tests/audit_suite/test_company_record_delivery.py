"""Actual company delivery remains complete and independently readable after cloning."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools.audit_suite import company_record_delivery as delivery

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "docs/audit-suite/company-records"


def test_actual_complete_company_source_delivery():
    result = delivery.verify(PUBLIC)
    assert result["manifest_sha256"] == (
        "30cbdf23a68532e5026a87d0dddb06cd09242b87ea3a58d009b39aacddc629c7"
    )
    assert result["verified_source_versions"] == 5714
    assert result["verified_source_systems"] == 922
    assert result["originals"] == 5709
    assert result["derivatives"] == 5
    assert result["source_content_bytes"] == 15126033
    manifest = json.loads((PUBLIC / "manifest.json").read_text())
    assert {row["source_branch"]: row["version_count"] for row in manifest["histories"]} == {
        "HARBOR-OPERATIONS-A": 2793,
        "HARBOR-OPERATIONS-B": 2921,
    }
    assert manifest["snapshot"]["omitted_metadata"] == []
    assert len(manifest["provenance_files"]) == 2
    assert sum(len(row["redactions"]) for row in manifest["records"]) == 5


def test_isolated_consumer_needs_only_delivered_files_and_standard_python(tmp_path):
    consumer = tmp_path / "company-records"
    shutil.copytree(PUBLIC, consumer)
    tool = tmp_path / "verify.py"
    shutil.copy2(Path(delivery.__file__), tool)
    completed = subprocess.run(
        [sys.executable, "-I", str(tool), "verify", "--root", str(consumer)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(completed.stdout)
    assert result["verified_source_versions"] == 5714
    assert result["originals"] == 5709 and result["derivatives"] == 5


@pytest.mark.parametrize("mutation", ["content", "provenance", "extra", "duplicate_key"])
def test_modified_delivery_is_rejected(tmp_path, mutation):
    consumer = tmp_path / "company-records"
    shutil.copytree(PUBLIC, consumer)
    manifest_path = consumer / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if mutation == "content":
        path = consumer / manifest["records"][0]["path"]
        path.write_bytes(path.read_bytes() + b"changed")
    elif mutation == "provenance":
        path = consumer / manifest["provenance_files"][0]["path"]
        path.write_bytes(path.read_bytes() + b"{}\n")
    elif mutation == "extra":
        (consumer / "unexpected.json").write_text("{}")
    else:
        manifest_path.write_text('{"schema":"ignored",' + manifest_path.read_text()[1:])
    with pytest.raises(ValueError):
        delivery.verify(consumer)
