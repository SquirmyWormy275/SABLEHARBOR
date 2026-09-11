"""Evidence rejection tests use synthetic temporary files, never invented canon."""

import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

spec = importlib.util.spec_from_file_location("evidence", Path(__file__).with_name("evidence.py"))
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)


@pytest.fixture
def intake(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "evidence.txt"
    source.write_text("TEST FIXTURE ONLY; not real evidence.\n")
    matrix = {
        "source_main_sha": "a" * 40,
        "input_sha256": {"evidence.txt": e.digest(source.read_bytes())},
        "records": [
            {
                "id": "SH-SITE-TEST",
                "name": "Test",
                "status": "unresolved",
                "classification": "test fixture",
                "reason": "Evidence missing",
                "provenance": [{"path": "evidence.txt"}],
                "actual_occupancy": None,
            }
        ],
    }
    p = root / e.COVERAGE
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(matrix))
    r = e.submission_template(root)
    r.update(
        evidence_id="SH-EVID-TEST-001",
        scope_ids=["SH-SITE-TEST"],
        source={
            "path": "evidence.txt",
            "sha256": e.digest(source.read_bytes()),
            "locator": "line:1",
        },
        proposed_changes=[
            {"scope_id": "SH-SITE-TEST", "field": "actual_occupancy", "before": None, "after": 3}
        ],
    )
    return root, r


def test_queue_and_valid_pending_candidate(intake, tmp_path):
    root, r = intake
    assert not e.validate_submission(root, r)
    assert e.build_evidence_queue(root)["records"][0]["scope_id"] == "SH-SITE-TEST"
    output = tmp_path / "candidate.json"
    e.export_candidate(root, r, output)
    assert json.loads(output.read_text())["state"] == "REVIEW_CANDIDATE_NOT_CANON"
    with pytest.raises(FileExistsError):
        e.export_candidate(root, r, output)
    with pytest.raises(ValueError, match="outside repository"):
        e.export_candidate(root, r, root / "forbidden.json")


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r["baseline"].update(coverage_sha256="0" * 64),
        lambda r: r.update(scope_ids=["UNKNOWN"]),
        lambda r: r["source"].update(sha256="0" * 64),
        lambda r: r["source"].update(path="../outside"),
        lambda r: r["effective_interval"].update(start="2026-02-30"),
        lambda r: r["effective_interval"].update(start="2026-10-01", end="2026-09-01"),
        lambda r: r.update(decision="ACCEPTED_CANDIDATE", reviewer="test"),
        lambda r: r.update(decision=True),
        lambda r: r["proposed_changes"][0].update(field="unapproved_field"),
        lambda r: r["proposed_changes"][0].update(after=-1),
        lambda r: r["proposed_changes"][0].update(before=0),
        lambda r: r["proposed_changes"].append(r["proposed_changes"][0].copy()),
        lambda r: r["proposed_changes"][0].update(
            field="status", before="unresolved", after="LOCKED"
        ),
    ],
)
def test_rejects_invalid_and_unauthorized_claims(intake, mutation):
    root, r = intake
    mutation(r)
    assert e.validate_submission(root, r)


def test_stale_coverage_source_fails_closed(intake):
    root, r = intake
    (root / "evidence.txt").write_text("changed")
    assert e.validate_submission(root, r)
    with pytest.raises(ValueError, match="stale coverage input"):
        e.build_evidence_queue(root)


def test_accepted_canon_binding_and_pending_branch_rejection(intake):
    root, r = intake

    def git(*args):
        return (
            subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )

    git("init", "-b", "main")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "Test fixture")
    r.update(decision="ACCEPTED_CANDIDATE", reviewer="Fixture reviewer")
    keys = [
        "evidence_id",
        "scope_ids",
        "claim_type",
        "source",
        "effective_interval",
        "precision",
        "fictionality",
        "evidence_kind",
        "proposed_changes",
    ]
    binding = {
        "decision": "ACCEPTED",
        "reviewer": r["reviewer"],
        "claim_sha256": e.canonical_hash({k: r[k] for k in keys}),
    }
    path = root / "docs/canon/TEST.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "TEST FIXTURE ONLY\n```facility-evidence-decision\n" + json.dumps(binding) + "\n```\n"
    )
    git("add", ".")
    git("commit", "-m", "test fixture acceptance")
    commit = git("rev-parse", "HEAD")
    r["decision_provenance"] = {
        "path": "docs/canon/TEST.md",
        "sha256": e.digest(path.read_bytes()),
        "commit": commit,
    }
    assert e.validate_submission(root, r)  # No accepted main ref exists.
    git("update-ref", "refs/remotes/origin/main", commit)
    assert not e.validate_submission(root, r)
    r["proposed_changes"][0]["after"] = 4
    assert e.validate_submission(root, r)  # Decision binds exact claim, not ID alone.


def test_nonphysical_records_do_not_request_buildings(intake):
    root, _ = intake
    path = root / e.COVERAGE
    matrix = json.loads(path.read_text())
    matrix["records"][0].update(
        {
            "class": 6,
            "classification": "distributed/nonphysical/reference",
            "tenure": "unknown",
            "precision": "UNLOCATED",
        }
    )
    path.write_text(json.dumps(matrix))
    item = e.build_evidence_queue(root)["records"][0]
    assert item["unresolved_fields"] == []
    assert set(item["field_applicability"].values()) == {"NOT_APPLICABLE"}
    assert item["scope_id"] == "SH-SITE-TEST"
    assert item["provenance"] and item["disposition"]


@pytest.mark.parametrize("value", [-1, float("inf"), float("nan"), True, "3", 3.5, [], {}])
def test_workforce_counts_are_finite_nonnegative_integers(intake, value):
    root, r = intake
    r["claim_type"] = "workforce"
    r["proposed_changes"][0].update(field="current_named_employees", after=value)
    assert e.validate_submission(root, r)


@pytest.mark.parametrize(
    "field,value,claim",
    [
        (None, 1, "occupancy"),
        ("occupancy_start", "20260911", "occupancy"),
        ("tenure", False, "tenure"),
        ("precision", "ACTUAL", "parcel"),
        ("fictionality", "PROVEN", "parcel"),
        ("geometry", "not geometry", "parcel"),
        ("geometry", {"type": "Polygon", "coordinates": []}, "parcel"),
    ],
)
def test_explicit_change_field_types(intake, field, value, claim):
    root, r = intake
    r["claim_type"] = claim
    r["proposed_changes"][0].update(field=field, after=value)
    assert e.validate_submission(root, r)
