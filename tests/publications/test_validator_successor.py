"""Historical validator pins have exact maintenance successors, never artifact exceptions."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "validator_successor", ROOT / "tools/legal_gaps/validator_successor.py"
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


@pytest.fixture
def copied(tmp_path):
    record = json.loads((ROOT / module.RECORD).read_text())
    paths = [module.RECORD]
    for entry in record["entries"]:
        paths.extend([entry["path"], entry["baseline_snapshot"]])
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    return tmp_path, record


def test_both_original_review_pins_have_exact_successors(copied):
    root, record = copied
    receipt = json.loads(
        (ROOT / "docs/legal/gap-instruments/review-support/qa/v4.3/REVIEW.json").read_text()
    )
    for entry in record["entries"]:
        assert receipt["input_hashes"][entry["path"]] == entry["before_sha256"]
        assert module.verified_validator_successor(root, entry["path"], entry["before_sha256"])


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("kind", ["current", "snapshot", "record"])
@pytest.mark.parametrize("operation", ["change", "delete"])
def test_missing_or_altered_evidence_rejected(copied, index, kind, operation):
    root, record = copied
    entry = record["entries"][index]
    relative = {
        "current": entry["path"],
        "snapshot": entry["baseline_snapshot"],
        "record": module.RECORD,
    }[kind]
    path = root / relative
    if operation == "delete":
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + b"\n")
    assert not module.verified_validator_successor(root, entry["path"], entry["before_sha256"])


def test_artifact_and_resealed_original_digest_rejected(copied):
    root, record = copied
    entry = record["entries"][0]
    assert not module.verified_validator_successor(
        root, "docs/legal/approved.pdf", entry["before_sha256"]
    )
    assert not module.verified_validator_successor(root, entry["path"], entry["after_sha256"])
