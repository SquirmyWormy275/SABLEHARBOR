"""Exact toolchain history retains frozen manifest and artifact validation."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "toolchain_successor", ROOT / "tools/legal_gaps/toolchain_successor.py"
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


@pytest.fixture
def copied(tmp_path):
    record = json.loads((ROOT / module.RECORD).read_text())
    for path in (module.RECORD, module.DEPENDENCY, record["baseline_snapshot"]):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / path).read_bytes())
    return tmp_path, record


def test_historical_input_matches_original_snapshot(copied):
    root, record = copied
    manifest = json.loads((ROOT / "docs/legal/gap-instruments/manifest.json").read_text())
    item = next(item for item in manifest["inputs"] if item["path"] == module.DEPENDENCY)
    assert item["sha256"] == record["before_sha256"]
    assert module.historical_toolchain_successor(root, item) == record["id"]


@pytest.mark.parametrize("evidence", ["record", "baseline", "current"])
@pytest.mark.parametrize("operation", ["delete", "change"])
def test_evidence_drift_fails_closed(copied, evidence, operation):
    root, record = copied
    path = (
        root
        / {
            "record": module.RECORD,
            "baseline": record["baseline_snapshot"],
            "current": module.DEPENDENCY,
        }[evidence]
    )
    if operation == "delete":
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + b"\n")
    assert (
        module.historical_toolchain_successor(
            root, {"path": module.DEPENDENCY, "sha256": record["before_sha256"]}
        )
        is None
    )


@pytest.mark.parametrize("change", ["wrong_path", "wrong_original_hash", "current_hash"])
def test_other_inputs_or_resealed_pin_not_accepted(copied, change):
    root, record = copied
    item = {"path": module.DEPENDENCY, "sha256": record["before_sha256"]}
    if change == "wrong_path":
        item["path"] = "tools/legal_gaps/build.py"
    else:
        item["sha256"] = record["after_sha256"] if change == "current_hash" else "0" * 64
    assert module.historical_toolchain_successor(root, item) is None
