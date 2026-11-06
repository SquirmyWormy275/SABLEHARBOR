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
        "98fe97f4689c1912d53477b844aec02cefb0737e3e003c04fa8cbf777f6b4cd8"
    )
    assert result["verified_source_versions"] == 5753
    assert result["verified_source_systems"] == 928
    assert result["originals"] == 5748
    assert result["derivatives"] == 5
    assert result["source_content_bytes"] == 15192741
    manifest = json.loads((PUBLIC / "manifest.json").read_text())
    assert {row["source_branch"]: row["version_count"] for row in manifest["histories"]} == {
        "HARBOR-OPERATIONS-A": 2816,
        "HARBOR-OPERATIONS-B": 2937,
    }
    assert manifest["snapshot"]["omitted_metadata"] == []
    assert len(manifest["provenance_files"]) == 2
    assert sum(len(row["redactions"]) for row in manifest["records"]) == 5
    base = manifest["snapshot"]
    assert (base["base_source_version_count"], base["base_source_system_count"]) == (5714, 922)
    extension = base["authored_extensions"][0]
    assert extension["prior_manifest_sha256"] == (
        "30cbdf23a68532e5026a87d0dddb06cd09242b87ea3a58d009b39aacddc629c7"
    )
    assert extension["version_count"] == 39 and extension["new_system_count"] == 6


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
    assert result["verified_source_versions"] == 5753
    assert result["originals"] == 5748 and result["derivatives"] == 5


@pytest.mark.parametrize(
    "mutation", ["content", "provenance", "extra", "duplicate_key", "extension"]
)
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
    elif mutation == "extension":
        manifest["snapshot"]["authored_extensions"][0]["version_count"] -= 1
        manifest_path.write_bytes(delivery.encoded(manifest))
    else:
        manifest_path.write_text('{"schema":"ignored",' + manifest_path.read_text()[1:])
    with pytest.raises(ValueError):
        delivery.verify(consumer)


@pytest.mark.parametrize(
    ("scenario", "history_id", "branch", "records", "systems"),
    [
        ("CLEAN", "history-01", "HARBOR-OPERATIONS-A", 2816, 450),
        ("MESSY", "history-02", "HARBOR-OPERATIONS-B", 2937, 478),
    ],
)
def test_scenario_selection_returns_one_verified_history(
    scenario, history_id, branch, records, systems
):
    summary, rows = delivery.select(PUBLIC, scenario)
    assert summary == {
        "scenario": scenario,
        "history_id": history_id,
        "branch": branch,
        "records": records,
        "systems": systems,
        "provenance": f"{history_id}/provenance.jsonl",
        "manifest_sha256": "98fe97f4689c1912d53477b844aec02cefb0737e3e003c04fa8cbf777f6b4cd8",
    }
    manifest = json.loads((PUBLIC / "manifest.json").read_text())
    assert rows == [row for row in manifest["records"] if row["history_id"] == history_id]


def test_standalone_scenario_selection_writes_json_lines(tmp_path):
    consumer = tmp_path / "company-records"
    shutil.copytree(PUBLIC, consumer)
    tool = tmp_path / "verify.py"
    shutil.copy2(Path(delivery.__file__), tool)
    output = tmp_path / "messy.jsonl"
    command = [sys.executable, "-I", str(tool), "select", "--root", str(consumer)]
    completed = subprocess.run(
        [*command, "--scenario", "MESSY", "--output", str(output)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(completed.stderr)["records"] == 2937
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(rows) == 2937 and {row["history_id"] for row in rows} == {"history-02"}
    (consumer / "unexpected.json").write_text("{}")
    refused = subprocess.run(
        [*command, "--scenario", "CLEAN"], cwd=tmp_path, capture_output=True, text=True
    )
    assert refused.returncode != 0 and refused.stdout == ""
    assert "Delivery membership differs" in refused.stderr
