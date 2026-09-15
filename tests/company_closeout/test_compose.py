import json
import subprocess

import pytest

from tools.company_closeout.compose import generate
from tools.company_closeout.edition import EditionError, sha


@pytest.fixture
def tree(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "source.json").write_text('{"record_id":"SOURCE-01"}')
    (tmp_path / "historical.zip").write_bytes(b"excluded prior archive")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    revision = subprocess.check_output(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"], text=True
    ).strip()
    source_hashes = {"source.json": sha((tmp_path / "source.json").read_bytes())}
    finance = tmp_path / "enterprise/generated/company-closeout-v1"
    finance.mkdir(parents=True)
    identity = {
        "source_revision": revision,
        "source_files": source_hashes,
        "dirty_development_build": False,
    }
    (finance / "identity.json").write_text(json.dumps(identity))
    (finance / "manifest.json").write_text(
        json.dumps({"identity.json": sha((finance / "identity.json").read_bytes())})
    )
    people = tmp_path / "enterprise/generated/completed-period-2026-08"
    people.mkdir(parents=True)
    (people / "records.json").write_text('{"population": []}')
    (people / "manifest.json").write_text(
        json.dumps(
            {
                "source_commit": revision,
                "source_hashes": source_hashes,
                "artifacts": {"records.json": sha((people / "records.json").read_bytes())},
            }
        )
    )
    september = tmp_path / "enterprise/generated/september-custody-2026"
    september.mkdir(parents=True)
    (september / "records.json").write_text(
        json.dumps(
            {
                "repository_source_commit": revision,
                "publishable_source_snapshot": True,
                "source_hashes": source_hashes,
            }
        )
    )
    return tmp_path


def test_explicit_history_exclusion_and_three_populations(tree):
    contract = generate(tree, "2099-01-01T00:00:00Z", "test")
    assert contract["historical_zip_exclusions"] == ["historical.zip"]
    assert len(contract["components"]) == 3
    assert contract["components"][0]["members"][0]["path"] == "source.json"
    assert any(
        m["path"].endswith("september-custody-2026/records.json")
        for m in contract["components"][2]["members"]
    )


@pytest.mark.parametrize(
    "fault",
    [
        "source",
        "derivative",
        "extra",
        "revision",
        "backdate",
        "september_revision",
        "september_extra",
    ],
)
def test_stale_or_unavailable_generated_population_rejected(tree, fault):
    finance = tree / "enterprise/generated/company-closeout-v1"
    if fault == "source":
        (tree / "source.json").write_text('{"record_id":"changed"}')
    elif fault == "derivative":
        (tree / "enterprise/generated/completed-period-2026-08/records.json").write_text("[]")
    elif fault == "extra":
        (finance / "unmanifested.txt").write_text("unexpected")
    elif fault == "revision":
        identity = json.loads((finance / "identity.json").read_bytes())
        identity["source_revision"] = "0" * 40
        (finance / "identity.json").write_text(json.dumps(identity))
    elif fault == "september_revision":
        p = tree / "enterprise/generated/september-custody-2026/records.json"
        record = json.loads(p.read_text())
        record["repository_source_commit"] = "0" * 40
        p.write_text(json.dumps(record))
    elif fault == "september_extra":
        (tree / "enterprise/generated/september-custody-2026/unmanifested.txt").write_text("extra")
    with pytest.raises(EditionError):
        generate(
            tree, "2026-08-31T00:00:00Z" if fault == "backdate" else "2099-01-01T00:00:00Z", "test"
        )
