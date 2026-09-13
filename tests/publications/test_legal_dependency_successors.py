"""PR162 compatibility is exact, dependency-scoped, and fails closed."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "legal_dependency_successors", ROOT / "tools/legal_gaps/dependency_successors.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def copied(tmp_path):
    record = json.loads((ROOT / module.RECORD).read_text())
    for path in [
        module.RECORD,
        module.DEPENDENCY,
        record["baseline_snapshot"],
        record["canon_path"],
    ]:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / path).read_bytes())
    return tmp_path, record


def evaluate(root, document_id=module.DOCUMENT_ID, item=None):
    return module.accepted_dependency_successor(
        root, document_id, item or {"path": module.DEPENDENCY, "sha256": module.BEFORE_SHA256}
    )


def test_exact_accepted_transition_without_git_checkout(copied):
    root, record = copied
    assert not (root / ".git").exists()
    assert evaluate(root) == record["id"]
    _, before = module.rows((root / record["baseline_snapshot"]).read_bytes())
    _, after = module.rows((root / module.DEPENDENCY).read_bytes())
    assert len(before) == len(after) == 60
    assert [key for key in before if before[key] != after[key]] == ["SH-SITE-0002", "SH-SITE-0003"]
    assert all(
        before[key] == after[key]
        for key in ["SH-SITE-0023", "SH-SITE-0027", "SH-SITE-0005", "SH-SITE-0006"]
    )


@pytest.mark.parametrize(
    "site_id",
    [
        "SH-SITE-0002",
        "SH-SITE-0003",
        "SH-SITE-0023",
        "SH-SITE-0027",
        "SH-SITE-0006",
        "SH-SITE-0001",
    ],
)
def test_any_additional_row_drift_is_rejected(copied, site_id):
    root, _ = copied
    path = root / module.DEPENDENCY
    data = path.read_bytes()
    assert site_id.encode() in data
    path.write_bytes(data.replace(site_id.encode(), (site_id + "-CHANGED").encode(), 1))
    assert evaluate(root) is None


@pytest.mark.parametrize("change", ["whitespace", "reorder", "duplicate", "remove"])
def test_structural_and_byte_drift_is_rejected(copied, change):
    root, _ = copied
    path = root / module.DEPENDENCY
    data = path.read_bytes()
    lines = data.splitlines(keepends=True)
    altered = {
        "whitespace": data + b"\n",
        "reorder": lines[0] + lines[2] + lines[1] + b"".join(lines[3:]),
        "duplicate": data + lines[1],
        "remove": b"".join(lines[:-1]),
    }[change]
    path.write_bytes(altered)
    assert evaluate(root) is None


@pytest.mark.parametrize("evidence", ["record", "baseline", "canon", "current"])
@pytest.mark.parametrize("operation", ["delete", "modify"])
def test_missing_or_modified_audit_evidence_fails_closed(copied, evidence, operation):
    root, record = copied
    path = (
        root
        / {
            "record": module.RECORD,
            "baseline": record["baseline_snapshot"],
            "canon": record["canon_path"],
            "current": module.DEPENDENCY,
        }[evidence]
    )
    if operation == "delete":
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + b"\n")
    assert evaluate(root) is None


def test_wrong_instrument_path_or_original_pin_rejected(copied):
    root, _ = copied
    assert evaluate(root, "SH-LEGAL-DRAFT-TENURE") is None
    assert evaluate(root, item={"path": "other.csv", "sha256": module.BEFORE_SHA256}) is None
    assert evaluate(root, item={"path": module.DEPENDENCY, "sha256": "0" * 64}) is None


def test_frozen_manifest_still_records_original_whole_file_pin():
    manifest = json.loads((ROOT / "docs/legal/gap-instruments/manifest.json").read_text())
    matching = [
        (package["document_id"], item)
        for package in manifest["packages"]
        for item in package["dependencies"]
        if item["path"] == module.DEPENDENCY
    ]
    assert matching == [
        (module.DOCUMENT_ID, {"path": module.DEPENDENCY, "sha256": module.BEFORE_SHA256})
    ]
