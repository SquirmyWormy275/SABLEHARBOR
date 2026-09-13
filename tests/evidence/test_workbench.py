import csv
import hashlib
import json
import subprocess

import pytest

from tools.evidence.inventory import fingerprints, inventory
from tools.evidence.workbench import render


def source_fixture(root):
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "source.txt").write_bytes(b"A source\x00with binary bytes\n")
    subprocess.run(["git", "add", "source.txt"], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "Baseline",
        ],
        cwd=root,
        check=True,
    )
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    register = root / "geospatial/registers"
    register.mkdir(parents=True)
    (register / "CENSUS_MANIFEST.json").write_text(json.dumps({"source_commit": revision}))
    (register / "SITE_REGISTER.csv").write_text("object_id,canonical_name\nSITE-1,Test site\n")
    row = {
        "source_path": "source.txt",
        "source_commit": revision,
        "bytes": len((root / "source.txt").read_bytes()),
        "file_sha256": hashlib.sha256((root / "source.txt").read_bytes()).hexdigest(),
        "extraction_method": "TEXT_SCANNED",
    }
    with (register / "SOURCE_COVERAGE.csv").open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    return revision, register


def test_inventory_checks_archived_bytes_and_preserves_boundaries(tmp_path):
    revision, _ = source_fixture(tmp_path)
    result = inventory(tmp_path, revision, [{"source_path": "source.txt"}])
    assert result["summary"]["baseline_files_verified"] == 1
    assert result["baseline_sources"][0]["residual_occurrences"] == 1
    assert not result["summary"]["semantic_census_complete"]
    assert result["baseline_sources"][0]["review_boundary"] == "SEMANTIC_REVIEW_NOT_ESTABLISHED"
    assert not result["subsequent_changes"]
    blob = result["baseline_sources"][0]["baseline_git_blob"]
    assert fingerprints(tmp_path, [blob])[blob] == (
        27,
        hashlib.sha256(b"A source\x00with binary bytes\n").hexdigest(),
    )


def test_inventory_rejects_a_false_source_hash(tmp_path):
    revision, register = source_fixture(tmp_path)
    path = register / "SOURCE_COVERAGE.csv"
    path.write_text(
        path.read_text().replace(
            hashlib.sha256(b"A source\x00with binary bytes\n").hexdigest(), "0" * 64
        )
    )
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        inventory(tmp_path, revision, [])


def test_embedded_source_cannot_end_the_json_script(tmp_path):
    attack = '</script><img src=x onerror="window.injected=true">'
    render(
        tmp_path, "a" * 40, False, [], [{"occurrence_id": "ONE", "text": attack}], [], {}, "1.1.0"
    )
    html = (tmp_path / "review.html").read_text()
    assert attack not in html
    payload = html.split('<script id="evidence-data" type="application/json">', 1)[1].split(
        "</script>", 1
    )[0]
    assert json.loads(payload)["backlog"][0]["text"] == attack
